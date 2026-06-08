"""
Unit tests for the memory-augmented compound router.

Tests all public methods and helper functions including BM25 scoring,
cosine similarity, confidence gate, greedy diversity selection,
and the MemoryAugmentedRouter routing pipeline.
"""

from __future__ import annotations

import math
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lyra.routing.memory_router import (
    ConfidenceDecision,
    MemoryAugmentedRouter,
    MemoryEntry,
    MemoryRouterLayer,
    MemoryRouterMetrics,
    MemorySearchResult,
    _bm25_score,
    _cosine_similarity,
    _hybrid_similarity,
    _tokenise,
    confidence_gate,
)
from lyra.routing.provider.types import CompletionResponse, TokenUsage

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# MemoryEntry
# ---------------------------------------------------------------------------


class TestMemoryEntry:
    def test_default_timestamp(self) -> None:
        entry = MemoryEntry(query="q", response="r")
        assert entry.timestamp > 0
        assert abs(entry.timestamp - time.time()) < 2  # within 2 seconds

    def test_explicit_timestamp(self) -> None:
        entry = MemoryEntry(query="q", response="r", timestamp=100.0)
        assert entry.timestamp == 100.0

    def test_defaults(self) -> None:
        entry = MemoryEntry(query="q", response="r")
        assert entry.success is True
        assert entry.confidence == 1.0
        assert entry.cost == 0.0
        assert entry.embedding is None
        assert entry.task_type == "standard"
        assert entry.metadata == {}


# ---------------------------------------------------------------------------
# MemorySearchResult
# ---------------------------------------------------------------------------


class TestMemorySearchResult:
    def test_defaults(self) -> None:
        entry = MemoryEntry(query="q", response="r")
        result = MemorySearchResult(entry=entry, similarity=0.9)
        assert result.bm25_score == 0.0
        assert result.cosine_score == 0.0


# ---------------------------------------------------------------------------
# _tokenise
# ---------------------------------------------------------------------------


class TestTokenise:
    def test_simple(self) -> None:
        assert _tokenise("hello world") == ["hello", "world"]

    def test_punctuation(self) -> None:
        assert _tokenise("hello, world!") == ["hello", "world"]

    def test_multiple_spaces(self) -> None:
        assert _tokenise("hello   world") == ["hello", "world"]

    def test_case_insensitive(self) -> None:
        assert _tokenise("Hello World") == ["hello", "world"]

    def test_empty_string(self) -> None:
        assert _tokenise("") == []

    def test_only_punctuation(self) -> None:
        assert _tokenise("!!! ???") == []


# ---------------------------------------------------------------------------
# _bm25_score
# ---------------------------------------------------------------------------


class TestBM25Score:
    def test_identical(self) -> None:
        query_tokens = ["hello", "world"]
        doc_tokens = ["hello", "world"]
        score = _bm25_score(query_tokens, doc_tokens)
        assert score > 0

    def test_no_overlap(self) -> None:
        query_tokens = ["hello"]
        doc_tokens = ["goodbye"]
        score = _bm25_score(query_tokens, doc_tokens)
        assert score == 0.0

    def test_partial_overlap(self) -> None:
        query_tokens = ["hello", "world", "foo"]
        doc_tokens = ["hello", "world"]
        score = _bm25_score(query_tokens, doc_tokens)
        assert score > 0

    def test_empty_query(self) -> None:
        assert _bm25_score([], ["hello"]) == 0.0

    def test_empty_doc(self) -> None:
        assert _bm25_score(["hello"], []) == 0.0


# ---------------------------------------------------------------------------
# _cosine_similarity
# ---------------------------------------------------------------------------


class TestCosineSimilarity:
    def test_identical_vectors(self) -> None:
        a = [1.0, 2.0, 3.0]
        b = [1.0, 2.0, 3.0]
        assert _cosine_similarity(a, b) == 1.0

    def test_orthogonal(self) -> None:
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert _cosine_similarity(a, b) == 0.0

    def test_opposite(self) -> None:
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert _cosine_similarity(a, b) == -1.0

    def test_empty_vectors(self) -> None:
        assert _cosine_similarity([], []) == 0.0

    def test_dimension_mismatch(self) -> None:
        assert _cosine_similarity([1.0], [1.0, 2.0]) == 0.0

    def test_zero_norm(self) -> None:
        assert _cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


# ---------------------------------------------------------------------------
# _hybrid_similarity
# ---------------------------------------------------------------------------


class TestHybridSimilarity:
    def test_without_embedding_uses_pure_bm25(self) -> None:
        entry = MemoryEntry(query="hello world", response="hi")
        combined, bm25, cosine = _hybrid_similarity("hello world", entry)
        assert combined > 0
        assert cosine == 0.0
        assert combined == bm25

    def test_with_embedding_uses_weighted(self) -> None:
        entry = MemoryEntry(
            query="hello world",
            response="hi",
            embedding=[1.0, 0.0],
        )
        combined, bm25, cosine = _hybrid_similarity("hello world", entry)
        # cosine: [0, 0] placeholder with [1, 0] = 0
        # combined = 0.4 * bm25 + 0.6 * 0
        assert combined == 0.4 * bm25
        assert cosine >= 0  # placeholder vs [1,0] gives 0


# ---------------------------------------------------------------------------
# confidence_gate
# ---------------------------------------------------------------------------


class TestConfidenceGate:
    def _make_response(self, logprobs: list[float] | None = None,
                       usage_logprobs: list[float] | None = None) -> CompletionResponse:
        if logprobs is not None:
            response = CompletionResponse(
                content="test", tool_calls=None,
                usage=TokenUsage(), finish_reason="stop", model="m", latency_ms=1.0,
            )
            object.__setattr__(response, "token_logprobs", logprobs)
            return response
        if usage_logprobs is not None:
            usage = TokenUsage()
            object.__setattr__(usage, "token_logprobs", usage_logprobs)
            return CompletionResponse(
                content="test", tool_calls=None,
                usage=usage, finish_reason="stop", model="m", latency_ms=1.0,
            )
        return CompletionResponse(
            content="test", tool_calls=None,
            usage=TokenUsage(), finish_reason="stop", model="m", latency_ms=1.0,
        )

    def test_accept_when_nsp_above_threshold(self) -> None:
        # logprobs [-0.5, -0.3] -> mean -0.4 -> nsp = exp(-0.4) ≈ 0.67 > 0.50
        response = self._make_response(logprobs=[-0.5, -0.3])
        assert confidence_gate(response) == ConfidenceDecision.ACCEPT

    def test_reject_when_nsp_below_threshold(self) -> None:
        # logprobs [-2.0, -2.5] -> mean -2.25 -> nsp = exp(-2.25) ≈ 0.105 < 0.50
        response = self._make_response(logprobs=[-2.0, -2.5])
        assert confidence_gate(response) == ConfidenceDecision.REJECT

    def test_escalate_when_logprobs_none_on_response(self) -> None:
        response = self._make_response(logprobs=None)
        assert confidence_gate(response) == ConfidenceDecision.ESCALATE

    def test_escalate_when_logprobs_is_empty(self) -> None:
        response = self._make_response(logprobs=[])
        assert confidence_gate(response) == ConfidenceDecision.ESCALATE

    def test_accept_with_custom_threshold(self) -> None:
        response = self._make_response(logprobs=[-0.1, -0.05])
        assert confidence_gate(response, threshold=0.5) == ConfidenceDecision.ACCEPT

    def test_escalate_when_non_numeric_in_logprobs(self) -> None:
        response = self._make_response(logprobs=["bad", "data"])  # type: ignore[list-item]
        assert confidence_gate(response) == ConfidenceDecision.ESCALATE

    def test_uses_usage_token_logprobs_fallback(self) -> None:
        response = self._make_response(usage_logprobs=[-0.1, -0.2])
        result = confidence_gate(response)
        # exp((-0.1 + -0.2) / 2) = exp(-0.15) ≈ 0.86 > 0.5
        assert result == ConfidenceDecision.ACCEPT


# ---------------------------------------------------------------------------
# MemoryRouterMetrics
# ---------------------------------------------------------------------------


class TestMemoryRouterMetrics:
    def test_cache_hit_rate_zero_when_no_queries(self) -> None:
        m = MemoryRouterMetrics()
        assert m.cache_hit_rate == 0.0

    def test_cache_hit_rate(self) -> None:
        m = MemoryRouterMetrics(total_queries=100, cache_hits=30)
        assert m.cache_hit_rate == 0.3

    def test_acceptance_rate_zero_when_no_hits(self) -> None:
        m = MemoryRouterMetrics()
        assert m.acceptance_rate == 0.0

    def test_acceptance_rate(self) -> None:
        m = MemoryRouterMetrics(cache_hits=10, confidence_accepts=7)
        assert m.acceptance_rate == 0.7

    def test_cost_reduction_pct_zero_when_no_costs(self) -> None:
        m = MemoryRouterMetrics()
        assert m.cost_reduction_pct == 0.0

    def test_cost_reduction_pct(self) -> None:
        m = MemoryRouterMetrics(total_cost_saved=40, total_cost_incurred=60)
        assert m.cost_reduction_pct == 40.0  # 40 / (40+60) * 100


# ---------------------------------------------------------------------------
# MemoryAugmentedRouter
# ---------------------------------------------------------------------------


class InMemoryStore:
    """Simple in-memory MemoryStore implementation for testing."""

    def __init__(self, entries: list[MemoryEntry] | None = None) -> None:
        self._entries = entries or []

    def hybrid_search(self, query: str, k: int = 3, min_similarity: float = 0.85) -> list[MemorySearchResult]:
        results = []
        for entry in self._entries:
            combined, bm25, cosine = _hybrid_similarity(query, entry)
            if combined >= min_similarity:
                results.append(MemorySearchResult(
                    entry=entry, similarity=combined,
                    bm25_score=bm25, cosine_score=cosine,
                ))
        # Sort by similarity descending
        results.sort(key=lambda r: r.similarity, reverse=True)
        return results[:k]

    def store(self, entry: MemoryEntry) -> None:
        self._entries.append(entry)

    def store_batch(self, entries: list[MemoryEntry]) -> None:
        self._entries.extend(entries)


class MockChatModel:
    """Simple mock ChatModel for testing."""

    def __init__(self, response_text: str = "mock answer",
                 success: bool = True, logprobs: list[float] | None = None) -> None:
        self.response_text = response_text
        self.response = CompletionResponse(
            content=response_text, tool_calls=None,
            usage=TokenUsage(input_tokens=5, output_tokens=10),
            finish_reason="stop", model="mock", latency_ms=5.0,
        )
        if logprobs is not None:
            object.__setattr__(self.response, "token_logprobs", logprobs)

    async def chat(self, messages: list[dict[str, str]], effort=None, max_tokens=4096):
        return self.response


@pytest.fixture
def memory_store():
    """In-memory memory store with test entries."""
    return InMemoryStore([
        MemoryEntry(
            query="What is the capital of France?",
            response="Paris is the capital of France.",
            success=True,
            confidence=0.95,
            cost=0.001,
            task_type="geography",
        ),
        MemoryEntry(
            query="What is the weather in London?",
            response="It is rainy.",
            success=False,
            confidence=0.3,
            cost=0.002,
        ),
        MemoryEntry(
            query="Explain quantum computing",
            response="Quantum computing uses qubits.",
            success=True,
            confidence=0.8,
            cost=0.005,
        ),
    ])


@pytest.fixture
def cheap_model():
    return MockChatModel(response_text="Paris is the capital.", success=True,
                         logprobs=[-0.1, -0.2])


class TestMemoryAugmentedRouterInit:
    def test_default_init(self) -> None:
        router = MemoryAugmentedRouter()
        assert router.cache_hit_threshold == 0.95
        assert router.memory_search_k == 3
        assert router.memory_min_similarity == 0.85
        assert router.confidence_threshold == 0.50
        assert router.diversity_k == 3
        assert router.cheap_effort.value == "low"
        assert router.metrics.total_queries == 0
        assert router._fallback_router is None
        assert router.active_layer == MemoryRouterLayer.FULL_ROUTING

    def test_set_fallback(self) -> None:
        router = MemoryAugmentedRouter()
        fallback = MagicMock()
        router.set_fallback(fallback)
        assert router._fallback_router is fallback

    def test_reset_metrics(self) -> None:
        router = MemoryAugmentedRouter()
        router.metrics.total_queries = 100
        router.metrics.cache_hits = 50
        router.reset_metrics()
        assert router.metrics.total_queries == 0
        assert router.metrics.cache_hits == 0


class TestMemoryAugmentedRouterRoute:
    async def test_no_memory_store_falls_through(self) -> None:
        """Without a memory store, route falls through to FULL_ROUTING."""
        router = MemoryAugmentedRouter()
        result = await router.route("test query")
        assert result == MemoryRouterLayer.FULL_ROUTING

    async def test_memory_hit_accepts(self, memory_store, cheap_model) -> None:
        """Memory hit with high similarity and confidence gate accept."""
        router = MemoryAugmentedRouter()
        router.memory_store = memory_store
        router.cheap_model = cheap_model
        # The first store entry has query about France capital
        result = await router.route("What is the capital of France?")
        assert result == MemoryRouterLayer.CROSS_AGENT_MEMORY
        assert router.metrics.cache_hits == 1
        assert router.metrics.confidence_accepts == 1

    async def test_memory_hit_rejects(self) -> None:
        """Memory hit but confidence gate rejects (low logprobs)."""
        class LowConfidenceChatModel:
            async def chat(self, messages, effort=None, max_tokens=4096):
                response = CompletionResponse(
                    content="unsure", tool_calls=None,
                    usage=TokenUsage(), finish_reason="stop",
                    model="m", latency_ms=1.0,
                )
                object.__setattr__(response, "token_logprobs", [-5.0, -5.0])
                return response

        store = InMemoryStore([
            MemoryEntry(
                query="What is the capital of France?",
                response="Paris", success=True,
            ),
        ])
        router = MemoryAugmentedRouter()
        router.memory_store = store
        router.cheap_model = LowConfidenceChatModel()
        result = await router.route("What is the capital of France?")
        # Should reject due to low NSP (exp(-5.0) ≈ 0.0067 < 0.50)
        assert result == MemoryRouterLayer.FULL_ROUTING
        assert router.metrics.cache_hits == 1
        assert router.metrics.confidence_rejects == 1

    async def test_memory_hit_escalates(self) -> None:
        """Memory hit but confidence cannot decide."""

        class EscalateChatModel:
            async def chat(self, messages, effort=None, max_tokens=4096):
                return CompletionResponse(
                    content="hmm", tool_calls=None,
                    usage=TokenUsage(), finish_reason="stop",
                    model="m", latency_ms=1.0,
                )

        store = InMemoryStore([
            MemoryEntry(
                query="What is the capital of France?",
                response="Paris", success=True,
            ),
        ])
        router = MemoryAugmentedRouter()
        router.memory_store = store
        router.cheap_model = EscalateChatModel()
        result = await router.route("What is the capital of France?")
        # No logprobs -> ESCALATE -> returns None -> FULL_ROUTING
        assert result == MemoryRouterLayer.FULL_ROUTING
        assert router.metrics.confidence_escalations == 1

    async def test_memory_miss_low_similarity(self, memory_store) -> None:
        """Query with low similarity to any stored entry returns None."""
        router = MemoryAugmentedRouter()
        router.memory_store = memory_store
        result = await router.route("Completely unrelated topic about astrophysics")
        # Should miss entirely -> FULL_ROUTING
        assert result == MemoryRouterLayer.FULL_ROUTING
        assert router.metrics.cache_misses == 1

    async def test_memory_hit_unsuccessful_entry(self, memory_store) -> None:
        """Entry where success=False should be treated as miss."""
        router = MemoryAugmentedRouter()
        router.memory_store = memory_store
        # The second entry (weather) has success=False
        result = await router.route("What is the weather in London?")
        # Even if similarity > threshold, success=False -> miss
        assert result == MemoryRouterLayer.FULL_ROUTING
        assert router.metrics.cache_misses == 1

    async def test_layer_hits_are_recorded(self, memory_store, cheap_model) -> None:
        """Layer hits dict is populated correctly."""
        router = MemoryAugmentedRouter()
        router.memory_store = memory_store
        router.cheap_model = cheap_model
        await router.route("What is the capital of France?")
        assert router.metrics.layer_hits.get("static_prefix_cache", 0) == 1
        assert router.metrics.layer_hits.get("cross_agent_memory", 0) == 1

    async def test_diversity_route_without_cheap_model(self) -> None:
        """Diversity route returns layer name even without cheap model."""
        router = MemoryAugmentedRouter()
        result = await router.route("q", recent_outputs=["a", "b", "c"])
        assert result == MemoryRouterLayer.DIVERSITY_CONTEXT

    async def test_diversity_route_with_single_output(self) -> None:
        """Single output does not trigger diversity route."""
        router = MemoryAugmentedRouter()
        result = await router.route("q", recent_outputs=["only one"])
        assert result == MemoryRouterLayer.FULL_ROUTING


class TestTryMemoryRoute:
    async def test_no_store_returns_none(self) -> None:
        router = MemoryAugmentedRouter()
        result = await router._try_memory_route("query")
        assert result is None

    async def test_empty_search_results_returns_none(self) -> None:
        router = MemoryAugmentedRouter()
        router.memory_store = InMemoryStore([])
        result = await router._try_memory_route("query")
        assert result is None

    async def test_no_cheap_model_returns_layer(self) -> None:
        """When cheap_model is None but memory match exists, return layer."""
        store = InMemoryStore([
            MemoryEntry(query="hello", response="world", success=True),
        ])
        router = MemoryAugmentedRouter()
        router.memory_store = store
        # Set low thresholds to guarantee match
        router.cache_hit_threshold = 0.0
        router.memory_min_similarity = 0.0
        result = await router._try_memory_route("hello")
        assert result == MemoryRouterLayer.CROSS_AGENT_MEMORY


class TestTryDiversityRoute:
    async def test_too_few_outputs_returns_none(self) -> None:
        router = MemoryAugmentedRouter()
        result = await router._try_diversity_route("q", ["only one"])
        assert result is None

    async def test_diversity_route_returns_layer(self) -> None:
        router = MemoryAugmentedRouter()
        result = await router._try_diversity_route("q", ["a", "b", "c", "d"])
        assert result == MemoryRouterLayer.DIVERSITY_CONTEXT

    async def test_diversity_with_cheap_model(self) -> None:
        router = MemoryAugmentedRouter()
        router.cheap_model = MockChatModel(response_text="synthesized answer")
        result = await router._try_diversity_route("q", ["opt a", "opt b", "opt c"])
        assert result == MemoryRouterLayer.DIVERSITY_CONTEXT


# ---------------------------------------------------------------------------
# _greedy_diversity_select
# ---------------------------------------------------------------------------


class TestGreedyDiversitySelect:
    @pytest.fixture
    def router(self) -> MemoryAugmentedRouter:
        return MemoryAugmentedRouter()

    def test_empty_list(self, router: MemoryAugmentedRouter) -> None:
        assert router._greedy_diversity_select([], k=3) == []

    def test_fewer_than_k(self, router: MemoryAugmentedRouter) -> None:
        result = router._greedy_diversity_select(["a", "b"], k=5)
        assert result == ["a", "b"]

    def test_exactly_k(self, router: MemoryAugmentedRouter) -> None:
        result = router._greedy_diversity_select(["a", "b", "c"], k=3)
        assert len(result) == 3

    def test_selects_diverse_outputs(self, router: MemoryAugmentedRouter) -> None:
        """Greedy selection should pick texts with minimal Jaccard overlap."""
        outputs = [
            "apple banana cherry",
            "apple banana cherry",
            "dog elephant fox",
            "apple banana cherry",
        ]
        result = router._greedy_diversity_select(outputs, k=2)
        # Should pick the first one and the third one (most diverse)
        assert "dog" in result[1] or "elephant" in result[1]

    def test_k_defaults_to_3(self, router: MemoryAugmentedRouter) -> None:
        outputs = ["a b", "c d", "e f", "g h", "i j"]
        result = router._greedy_diversity_select(outputs)
        assert len(result) == 3

    def test_preserves_first_element(self, router: MemoryAugmentedRouter) -> None:
        """The first element is always the starting point."""
        outputs = ["unique a", "duplicate a", "duplicate a"]
        result = router._greedy_diversity_select(outputs, k=2)
        assert result[0] == "unique a"
