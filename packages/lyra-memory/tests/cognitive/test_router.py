"""Tests for System12MemoryRouter."""

import pytest

from lyra_memory.cognitive.router import MemoryResult, System12MemoryRouter


class StubLLM:
    def __init__(self, responses: list[str] | None = None):
        self._responses = responses or []
        self._idx = 0
        self.prompts: list[str] = []

    @property
    def responses(self) -> list[str]:
        return self._responses

    @responses.setter
    def responses(self, value: list[str]) -> None:
        self._responses = value
        self._idx = 0

    async def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self._idx < len(self._responses):
            resp = self._responses[self._idx]
            self._idx += 1
            return resp
        return "0.5"


class StubEmbedder:
    def __init__(self, embedding: list[float] | None = None):
        self.embedding = embedding or [0.1, 0.2, 0.3]
        self.calls: list[str] = []

    async def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        return self.embedding


class StubVectorStore:
    def __init__(self, results: list[dict] | None = None):
        self.results = results or []
        self.searches: list[tuple[list[float], int]] = []

    async def search(self, embedding: list[float], k: int) -> list[dict]:
        self.searches.append((embedding, k))
        return self.results[:k]


class StubActiveEngine:
    def __init__(self, evidence: list | None = None):
        self._evidence = evidence or []
        self.queries: list[str] = []

    async def reconstruct(self, query: str) -> object:
        self.queries.append(query)
        result = type("ReconResult", (), {"evidence": self._evidence})()
        return result


class TestMemoryResult:
    def test_default_values(self):
        r = MemoryResult()
        assert r.memories == []
        assert r.system == "S1"
        assert r.latency == "fast"
        assert r.confidence == 0.0

    def test_custom_values(self):
        r = MemoryResult(
            memories=[{"id": "m1", "content": "test"}],
            system="S2",
            latency="deliberative",
            confidence=0.9,
        )
        assert r.system == "S2"
        assert r.latency == "deliberative"
        assert r.confidence == 0.9
        assert len(r.memories) == 1


class TestSystem12MemoryRouter:
    def _make_router(self, **kwargs) -> System12MemoryRouter:
        defaults = dict(
            vector_store=StubVectorStore(),
            embedder=StubEmbedder(),
            llm=StubLLM(),
        )
        defaults.update(kwargs)
        return System12MemoryRouter(**defaults)

    def _sample_results(self) -> list[dict]:
        return [
            {"id": "a", "content": "memory a", "score": 0.9, "valence_salience": 0.3},
            {"id": "b", "content": "memory b", "score": 0.8, "valence_salience": 0.1},
            {"id": "c", "content": "memory c", "score": 0.7, "valence_salience": 0.5},
        ]

    # ── S1 routing ──

    async def test_routes_to_s1_on_high_urgency(self):
        store = StubVectorStore(results=self._sample_results())
        router = self._make_router(vector_store=store)
        result = await router.route("urgent query", {"urgency": 0.9})
        assert result.system == "S1"
        assert result.latency == "fast"

    async def test_routes_to_s1_on_low_complexity(self):
        store = StubVectorStore(results=self._sample_results())
        router = self._make_router(vector_store=store)
        result = await router.route("simple", {"complexity": 0.1})
        assert result.system == "S1"

    async def test_s1_route_applies_valence_boost(self):
        results = [
            {"id": "x", "content": "boosted", "score": 0.5, "valence_salience": 0.6},
        ]
        store = StubVectorStore(results=results)
        router = self._make_router(vector_store=store)
        result = await router.route("test", {"urgency": 0.9})
        assert len(result.memories) == 1
        assert result.memories[0]["score"] == pytest.approx(0.5 * 1.6, rel=1e-9)
        assert result.memories[0]["valence_boost"] == 0.6

    async def test_s1_route_sorts_by_boosted_score(self):
        results = [
            {"id": "low", "content": "low", "score": 0.9, "valence_salience": 0.0},
            {"id": "high", "content": "high", "score": 0.5, "valence_salience": 0.9},
        ]
        store = StubVectorStore(results=results)
        router = self._make_router(vector_store=store)
        result = await router.route("test", {"urgency": 0.9})
        scored = [(m["id"], m["score"]) for m in result.memories]
        assert scored[0][0] == "high"

    async def test_s1_returns_top_5(self):
        results = [
            {"id": str(i), "content": f"m{i}", "score": 0.5, "valence_salience": 0.0}
            for i in range(10)
        ]
        store = StubVectorStore(results=results)
        router = self._make_router(vector_store=store)
        result = await router.route("test", {"urgency": 0.9})
        assert len(result.memories) == 5

    async def test_s1_empty_candidates(self):
        store = StubVectorStore(results=[])
        router = self._make_router(vector_store=store)
        result = await router.route("test", {"urgency": 0.9})
        assert result.memories == []
        assert result.confidence == 0.0

    # ── S2 routing ──

    async def test_routes_to_s2_on_low_urgency_high_complexity(self):
        store = StubVectorStore(results=self._sample_results())
        router = self._make_router(vector_store=store)
        result = await router.route("complex query", {"urgency": 0.2, "complexity": 0.8})
        assert result.system == "S2"

    async def test_s2_active_engine_reconstruction(self):
        from dataclasses import dataclass

        @dataclass
        class Content:
            id: str
            content: str

        @dataclass
        class Evidence:
            content: Content
            confidence: float = 0.0
            path_depth: int = 0

        e1 = Evidence(content=Content(id="n1", content="reconstructed"), confidence=0.85, path_depth=2)

        engine = StubActiveEngine(evidence=[e1])
        router = self._make_router(active_engine=engine)
        result = await router.route("complex", {"urgency": 0.2, "complexity": 0.8})
        assert result.system == "S2"
        assert result.latency == "deliberative"
        assert result.memories[0]["id"] == "n1"
        assert result.memories[0]["content"] == "reconstructed"
        assert result.memories[0]["score"] == 0.85
        assert result.memories[0]["path_depth"] == 2

    async def test_s2_fallback_when_no_engine(self):
        results = [{"id": "f1", "content": "fallback", "score": 0.75}]
        store = StubVectorStore(results=results)
        router = self._make_router(vector_store=store)
        result = await router.route("complex", {"urgency": 0.2, "complexity": 0.8})
        assert result.system == "S2"
        assert result.latency == "fallback"
        assert result.memories[0]["id"] == "f1"

    async def test_s2_fallback_empty(self):
        store = StubVectorStore(results=[])
        router = self._make_router(vector_store=store)
        result = await router.route("complex", {"urgency": 0.2, "complexity": 0.8})
        assert result.confidence == 0.0

    # ── Complexity estimation ──

    async def test_estimates_complexity_when_not_provided(self):
        store = StubVectorStore(results=self._sample_results())
        llm = StubLLM(responses=["0.12"])
        router = self._make_router(vector_store=store, llm=llm)
        result = await router.route("simple factual question")
        assert result.system == "S1"

    async def test_estimate_complexity_defaults_on_error(self):
        store = StubVectorStore(results=self._sample_results())
        llm = StubLLM(responses=["not a number"])
        router = self._make_router(vector_store=store, llm=llm)
        result = await router.route("test", {"urgency": 0.0})
        assert isinstance(result, MemoryResult)

    # ── Counters ──

    async def test_s1_counter_increments(self):
        store = StubVectorStore(results=self._sample_results())
        router = self._make_router(vector_store=store)
        assert router.s1_count == 0
        await router.route("q1", {"urgency": 0.9})
        assert router.s1_count == 1
        await router.route("q2", {"urgency": 0.9})
        assert router.s1_count == 2

    async def test_s2_counter_increments(self):
        store = StubVectorStore(results=self._sample_results())
        router = self._make_router(vector_store=store)
        assert router.s2_count == 0
        await router.route("q", {"urgency": 0.1, "complexity": 0.9})
        assert router.s2_count == 1

    # ── Confidence from missing score key ──

    async def test_s1_handles_missing_score_key(self):
        results = [{"id": "x", "content": "no score", "similarity": 0.6, "valence_salience": 0.2}]
        store = StubVectorStore(results=results)
        router = self._make_router(vector_store=store)
        result = await router.route("test", {"urgency": 0.9})
        assert result.memories[0]["score"] == pytest.approx(0.6 * 1.2, rel=1e-9)
