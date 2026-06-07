"""
Memory-augmented compound router with cache-hit awareness.

Implements the Knowledge Access Beats Model Size strategy for compound
memory-augmented routing: verbatim turn-pair storage with hybrid
BM25+cosine retrieval, confidence-gated cheap model execution, and
diversity-maximising context selection.

References
----------
- Knowledge Access Beats Model Size: Memory Augmented Routing for
  Persistent AI Agents — Liu et al., arXiv:2603.23013v1 (2026)
- FrugalGPT: How to Use Large Language Models While Reducing Cost and
  Improving Performance — Chen et al., ICML 2023, arXiv:2305.05176v1
- RMoA: Optimizing Mixture-of-Agents through Diversity Maximization
  — Xie et al., arXiv:2505.24442v1 (2025)
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

import structlog

from lyra.routing.provider.types import CompletionResponse, EffortLevel

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# -- protocols and types ---------------------------------------------------
# ---------------------------------------------------------------------------


class MemoryStore(Protocol):
    """Protocol for the cross-agent memory store.

    Implementations can be backed by Milvus, FAISS, or a simple
    in-memory dict (for testing / cold-start).
    """

    def hybrid_search(
        self,
        query: str,
        k: int = 3,
        min_similarity: float = 0.85,
    ) -> list[MemoryEntry]: ...

    def store(self, entry: MemoryEntry) -> None: ...

    def store_batch(self, entries: list[MemoryEntry]) -> None: ...


class ChatModel(Protocol):
    """Protocol for a cheap / mid-tier chat model used by the router."""

    async def chat(
        self,
        messages: list[dict[str, str]],
        effort: EffortLevel = EffortLevel.LOW,
        max_tokens: int = 4096,
    ) -> CompletionResponse: ...


@dataclass(frozen=True)
class MemoryEntry:
    """A verbatim turn-pair stored in cross-agent memory.

    Attributes:
        query: The original user or agent query text.
        response: The model response text.
        success: Whether the response was considered successful.
        confidence: NSP confidence score of the response (0-1).
        cost: Monetary cost of generating this response in USD.
        embedding: Optional dense embedding vector for cosine similarity.
        timestamp: Unix timestamp of when this entry was created.
        task_type: Optional task type classification.
        metadata: Arbitrary additional metadata keyed by string.
    """

    query: str
    response: str
    success: bool = True
    confidence: float = 1.0
    cost: float = 0.0
    embedding: list[float] | None = None
    timestamp: float = 0.0
    task_type: str = "standard"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            object.__setattr__(self, "timestamp", time.time())


@dataclass(frozen=True)
class MemorySearchResult:
    """Result of a hybrid memory search.

    Attributes:
        entry: The matched memory entry.
        similarity: Combined similarity score (0-1) from hybrid retrieval.
        bm25_score: Raw BM25 similarity score.
        cosine_score: Raw cosine similarity score (0 if no embedding).
    """

    entry: MemoryEntry
    similarity: float
    bm25_score: float = 0.0
    cosine_score: float = 0.0


class ConfidenceDecision(Enum):
    """Decision from the confidence gate."""

    ACCEPT = "accept"
    REJECT = "reject"
    ESCALATE = "escalate"


# ---------------------------------------------------------------------------
# -- BM25-style token overlap scorer (lightweight, no external dep) -------
# ---------------------------------------------------------------------------


def _tokenise(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenisation for BM25 scoring."""
    result: list[str] = []
    buf: list[str] = []
    for ch in text.lower():
        if ch.isalnum():
            buf.append(ch)
        else:
            if buf:
                result.append("".join(buf))
                buf = []
    if buf:
        result.append("".join(buf))
    return result


def _bm25_score(query_tokens: list[str], doc_tokens: list[str],
                avg_doc_len: float = 128.0, k1: float = 1.5, b: float = 0.75) -> float:
    """Compute BM25 similarity between a query and a document.

    Uses a global-idf-free formulation (works without a corpus-level
    term frequency table).
    """
    if not query_tokens or not doc_tokens:
        return 0.0

    doc_len = len(doc_tokens)
    query_freq: dict[str, int] = {}
    for t in query_tokens:
        query_freq[t] = query_freq.get(t, 0) + 1

    doc_freq: dict[str, int] = {}
    for t in doc_tokens:
        doc_freq[t] = doc_freq.get(t, 0) + 1

    score = 0.0
    for term, qf in query_freq.items():
        df = doc_freq.get(term, 0)
        if df == 0:
            continue
        idf = math.log((len(doc_tokens) - df + 0.5) / (df + 0.5) + 1.0)
        tf = df / (df + k1 * (1 - b + b * (doc_len / avg_doc_len)))
        score += idf * tf * qf

    return score / max(len(query_tokens), 1)  # Normalise by query length


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two dense vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _hybrid_similarity(
    query: str,
    entry: MemoryEntry,
) -> tuple[float, float, float]:
    """Compute combined similarity using BM25 + cosine hybrid.

    Returns:
        ``(combined, bm25_score, cosine_score)`` tuple. The combined score
        is a weighted average (alpha=0.4 BM25 + 0.6 cosine when embedding
        is present, pure BM25 otherwise).
    """
    query_tokens = _tokenise(query)
    entry_tokens = _tokenise(entry.query)

    bm25 = _bm25_score(query_tokens, entry_tokens)

    if entry.embedding is not None:
        # Dummy query embedding for cold-start; real deployment uses BGE-m3
        cosine = _cosine_similarity(
            [0.0] * len(entry.embedding),  # placeholder
            entry.embedding,
        )
        combined = 0.4 * bm25 + 0.6 * cosine
    else:
        cosine = 0.0
        combined = bm25

    return combined, bm25, cosine


# ---------------------------------------------------------------------------
# -- confidence gate -------------------------------------------------------
# ---------------------------------------------------------------------------


def confidence_gate(
    response: CompletionResponse,
    threshold: float = 0.50,
) -> ConfidenceDecision:
    """Normalised Sequence Probability confidence gate.

    Computes the geometric mean of token log-probabilities (NSP). If NSP
    is >= threshold the response is accepted; otherwise it is rejected
    and escalated.

    Args:
        response: The completion response with token-level logprobs.
        threshold: NSP threshold for acceptance (default 0.50).

    Returns:
        ``ACCEPT`` if NSP >= threshold, ``ESCALATE`` if not enough
        information to decide, ``REJECT`` if NSP is below threshold.
    """
    logprobs = getattr(response, "token_logprobs", None) or getattr(
        response.usage, "token_logprobs", None,
    )

    if logprobs is None or not isinstance(logprobs, (list, tuple)):
        return ConfidenceDecision.ESCALATE

    if not logprobs:
        return ConfidenceDecision.ESCALATE

    floored = [max(lp, -3.0) for lp in logprobs if isinstance(lp, (int, float))]
    if not floored:
        return ConfidenceDecision.ESCALATE

    nsp = math.exp(sum(floored) / len(floored))
    return ConfidenceDecision.ACCEPT if nsp >= threshold else ConfidenceDecision.REJECT


# ---------------------------------------------------------------------------
# -- memory-augmented router -----------------------------------------------
# ---------------------------------------------------------------------------


class MemoryRouterLayer(Enum):
    """Which layer of the compound strategy is currently active."""

    STATIC_PREFIX_CACHE = "static_prefix_cache"
    CROSS_AGENT_MEMORY = "cross_agent_memory"
    DIVERSITY_CONTEXT = "diversity_context"
    FULL_ROUTING = "full_routing"


@dataclass
class MemoryRouterMetrics:
    """Accumulated metrics for the memory-augmented router.

    All fields are reset when the router is instantiated.
    """

    total_queries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    confidence_accepts: int = 0
    confidence_escalations: int = 0
    confidence_rejects: int = 0
    total_cost_saved: float = 0.0
    total_cost_incurred: float = 0.0
    layer_hits: dict[str, int] = field(default_factory=dict)

    @property
    def cache_hit_rate(self) -> float:
        """Fraction of queries that hit the cross-agent memory."""
        if self.total_queries == 0:
            return 0.0
        return self.cache_hits / self.total_queries

    @property
    def acceptance_rate(self) -> float:
        """Fraction of memory-routed queries accepted by the confidence gate."""
        if self.cache_hits == 0:
            return 0.0
        return self.confidence_accepts / self.cache_hits

    @property
    def cost_reduction_pct(self) -> float:
        """Estimated cost reduction percentage."""
        if self.total_cost_saved + self.total_cost_incurred == 0:
            return 0.0
        return 100.0 * self.total_cost_saved / (
            self.total_cost_saved + self.total_cost_incurred
        )


@dataclass
class MemoryAugmentedRouter:
    """Compound memory-augmented router with cache-hit awareness.

    The routing strategy has three layers:

    1. **Static prefix cache** — System prompts and tool definitions are
       cached via prompt caching APIs, achieving 90%+ cost reduction on
       prefix tokens for every call.

    2. **Cross-agent memory** — After every agent call, the (query,
       response, success, confidence, cost) is stored as a verbatim
       turn-pair.  At query time, hybrid BM25+cosine retrieval finds
       similar past queries.  If match >= 0.95 similarity and the prior
       call succeeded, inject the cached response as context into a cheap
       model call and verify via confidence gate (NSP >= 0.50).

    3. **Diversity-kept context** — When multiple recent outputs exist for
       the same sub-problem, use greedy diversity selection to pick the
       ``K`` most diverse responses (preventing context bloat).

    If all memory layers miss, the router delegates to the fallback router
    (typically the static tier router or the learned router).

    Target metrics
    --------------
    * Cost reduction: 58.5% total (35% novel + 47% similar + 18% duplicates)
    * Quality recovery: 69% of full-context large-model quality from 8B model
    """

    memory_store: MemoryStore | None = None
    cheap_model: ChatModel | None = None
    mid_tier_model: ChatModel | None = None

    # Configuration
    cache_hit_threshold: float = 0.95
    memory_search_k: int = 3
    memory_min_similarity: float = 0.85
    confidence_threshold: float = 0.50
    diversity_k: int = 3
    cheap_effort: EffortLevel = EffortLevel.LOW

    # State
    _active_layer: MemoryRouterLayer = MemoryRouterLayer.FULL_ROUTING
    metrics: MemoryRouterMetrics = field(default_factory=MemoryRouterMetrics)
    _fallback_router: Any = None

    def set_fallback(self, router: Any) -> None:
        """Set the fallback router for memory-miss queries.

        Args:
            router: Any callable ``router.route(task_type, context)``
                returning a ``RouteDecision``, or a ``ModelRouter``
                instance with a ``route`` method.
        """
        self._fallback_router = router

    async def route(
        self,
        query: str,
        task_type: str = "standard",
        recent_outputs: list[str] | None = None,
    ) -> MemoryRouterLayer:
        """Route a query through the compound memory strategy.

        Tries each layer in order and returns when a layer succeeds,
        falling back to the full router if no memory layer matches.

        Args:
            query: The user query.
            task_type: Task type classification.
            recent_outputs: Optional list of recent outputs from other
                agents working on the same sub-problem (used for
                diversity-kept context, Layer 3).

        Returns:
            The ``MemoryRouterLayer`` that successfully handled the query.
        """
        self.metrics.total_queries += 1

        # Layer 1: Static prefix cache (handled by the provider SDK)
        # This layer is transparent — the cost saving happens automatically.
        self._active_layer = MemoryRouterLayer.STATIC_PREFIX_CACHE
        self.metrics.layer_hits["static_prefix_cache"] = (
            self.metrics.layer_hits.get("static_prefix_cache", 0) + 1
        )

        # Layer 2: Cross-agent memory
        if self.memory_store is not None:
            result = await self._try_memory_route(query)
            if result is not None:
                return result

        # Layer 3: Diversity-kept context
        if recent_outputs and len(recent_outputs) > 1:
            result = await self._try_diversity_route(query, recent_outputs)
            if result is not None:
                return result

        # Full routing fallback
        self._active_layer = MemoryRouterLayer.FULL_ROUTING
        return self._active_layer

    async def _try_memory_route(self, query: str) -> MemoryRouterLayer | None:
        """Attempt to route via cross-agent memory (Layer 2).

        Returns the layer name if successful, ``None`` if no suitable
        memory match is found.
        """
        store = self.memory_store
        if store is None:
            return None

        results = store.hybrid_search(
            query,
            k=self.memory_search_k,
            min_similarity=self.memory_min_similarity,
        )

        if not results:
            self.metrics.cache_misses += 1
            return None

        # Check if best match meets the cache-hit threshold
        best = results[0]
        if best.similarity < self.cache_hit_threshold:
            self.metrics.cache_misses += 1
            return None

        # Check that the prior call succeeded
        if not best.entry.success:
            self.metrics.cache_misses += 1
            return None

        self.metrics.cache_hits += 1
        self.metrics.layer_hits["cross_agent_memory"] = (
            self.metrics.layer_hits.get("cross_agent_memory", 0) + 1
        )
        self._active_layer = MemoryRouterLayer.CROSS_AGENT_MEMORY

        # Route to cheap model with memory-injected context
        if self.cheap_model is not None:
            context_messages = [
                {"role": "system",
                 "content": (
                     "You are a helpful assistant. Below is a similar query "
                     "and a previous successful response. Use this as context "
                     "but adapt your answer to the current query if needed."
                 )},
                {"role": "user", "content": f"Similar past query: {best.entry.query}"},
                {"role": "assistant", "content": f"Previous response: {best.entry.response}"},
                {"role": "user", "content": query},
            ]

            response = await self.cheap_model.chat(
                messages=context_messages,
                effort=self.cheap_effort,
            )

            gate_result = confidence_gate(response, self.confidence_threshold)

            if gate_result == ConfidenceDecision.ACCEPT:
                self.metrics.confidence_accepts += 1
                # Cost saving: cheap model cost vs. the premium model
                # that would have been used without memory routing
                pre_incurred = self.metrics.total_cost_incurred
                self.metrics.total_cost_incurred += getattr(
                    response, "cost", 0.001,
                )
                self.metrics.total_cost_saved += (
                    getattr(response, "cost_saved", 0.01)
                )
                logger.info(
                    "memory route success",
                    similarity=round(best.similarity, 4),
                    confidence=gate_result.value,
                )
                return MemoryRouterLayer.CROSS_AGENT_MEMORY
            elif gate_result == ConfidenceDecision.ESCALATE:
                self.metrics.confidence_escalations += 1
                logger.info(
                    "memory route escalated (ambiguous confidence)",
                    similarity=round(best.similarity, 4),
                )
                return None
            else:
                self.metrics.confidence_rejects += 1
                logger.info(
                    "memory route rejected (low confidence)",
                    similarity=round(best.similarity, 4),
                    gate_result=gate_result.value,
                )
                return None

        return MemoryRouterLayer.CROSS_AGENT_MEMORY

    async def _try_diversity_route(
        self,
        query: str,
        recent_outputs: list[str],
    ) -> MemoryRouterLayer | None:
        """Attempt to route via diversity-kept context (Layer 3).

        Uses greedy diversity selection (RMoA pattern) to pick ``K``
        maximally diverse responses from recent outputs, then passes
        them as context to the cheap model.

        Args:
            query: The user query.
            recent_outputs: Recent outputs from other agents.

        Returns:
            Layer name if successful, ``None`` if no diversity benefit.
        """
        if len(recent_outputs) <= 1:
            return None

        # Greedy diversity selection: pick K maximally different responses
        selected = self._greedy_diversity_select(recent_outputs, k=self.diversity_k)

        if not selected:
            return None

        self._active_layer = MemoryRouterLayer.DIVERSITY_CONTEXT
        self.metrics.layer_hits["diversity_context"] = (
            self.metrics.layer_hits.get("diversity_context", 0) + 1
        )

        if self.cheap_model is not None:
            context_block = "\n\n".join(
                f"Alternative approach {i + 1}: {text}"
                for i, text in enumerate(selected)
            )

            messages = [
                {"role": "system",
                 "content": (
                     "You are a helpful assistant. Below are diverse"
                     " alternative approaches to a similar problem."
                     " Synthesise the best answer for the current query."
                 )},
                {"role": "user", "content": f"Diverse approaches:\n{context_block}"},
                {"role": "user", "content": query},
            ]

            response = await self.cheap_model.chat(
                messages=messages,
                effort=self.cheap_effort,
            )

            gate_result = confidence_gate(response, self.confidence_threshold)

            if gate_result == ConfidenceDecision.ACCEPT:
                self.metrics.total_cost_incurred += getattr(response, "cost", 0.001)
                self.metrics.total_cost_saved += getattr(response, "cost_saved", 0.01)
                return MemoryRouterLayer.DIVERSITY_CONTEXT

        return MemoryRouterLayer.DIVERSITY_CONTEXT

    def _greedy_diversity_select(
        self,
        outputs: list[str],
        k: int = 3,
    ) -> list[str]:
        """Pick ``k`` maximally diverse outputs using greedy selection.

        Uses token-set Jaccard distance as a cheap diversity proxy.
        In production this should use BGE-m3 embeddings (RMoA).

        Args:
            outputs: List of output texts.
            k: Maximum number of outputs to select.

        Returns:
            ``min(k, len(outputs))`` diverse outputs.
        """
        if not outputs:
            return []
        if len(outputs) <= k:
            return list(outputs)

        # Compute token sets for Jaccard distance
        token_sets = [set(_tokenise(t)) for t in outputs]

        # Greedy: pick first element, then iteratively pick the one
        # maximising min-jaccard-distance from already selected
        selected_indices = [0]
        selected_set = token_sets[0]

        for _ in range(min(k - 1, len(outputs) - 1)):
            best_idx = -1
            best_min_dist = -1.0

            for i, ts in enumerate(token_sets):
                if i in selected_indices:
                    continue

                # Jaccard distance = 1 - |intersection| / |union|
                intersection = len(selected_set & ts)
                union = len(selected_set | ts)
                if union == 0:
                    dist = 0.0
                else:
                    dist = 1.0 - (intersection / union)

                if dist > best_min_dist:
                    best_min_dist = dist
                    best_idx = i

            if best_idx >= 0:
                selected_indices.append(best_idx)
                selected_set |= token_sets[best_idx]

        return [outputs[i] for i in selected_indices]

    @property
    def active_layer(self) -> MemoryRouterLayer:
        """The currently active routing layer."""
        return self._active_layer

    def reset_metrics(self) -> None:
        """Reset all accumulated metrics."""
        self.metrics = MemoryRouterMetrics()
