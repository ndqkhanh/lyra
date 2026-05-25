"""
System 1 / System 2 Memory Router — dual-process memory routing inspired by
human cognition: fast intuitive (S1) vs slow deliberative (S2).

System 1: Fast, embedding similarity + valence boost for high-urgency queries
System 2: Slow, active reconstruction via Cue-Tag-Content graph traversal

Source: Human-Like Lifelong Memory (QufkvHbQs7), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class VectorStore(Protocol):
    """Protocol for vector similarity search."""

    async def search(self, embedding: list[float], k: int) -> list[dict]: ...


class Embedder(Protocol):
    """Protocol for embedding generation."""

    async def embed(self, text: str) -> list[float]: ...


class ActiveEngine(Protocol):
    """Protocol for active reconstruction engine."""

    async def reconstruct(self, query: str) -> object: ...


class LLMClient(Protocol):
    """Protocol for LLM interaction."""

    async def complete(self, prompt: str) -> str: ...


@dataclass
class MemoryResult:
    """Result from System 1 or System 2 retrieval."""

    memories: list[dict] = field(default_factory=list)
    system: str = "S1"
    latency: str = "fast"
    confidence: float = 0.0


@dataclass
class System12MemoryRouter:
    """Dual-process memory routing: fast intuitive vs slow deliberative.

    Routes queries based on urgency, complexity, and available context:
    - High urgency or low complexity → System 1 (fast, embedding-based)
    - Low urgency and high complexity → System 2 (slow, reconstruction-based)

    System 1 response time target: ~50ms
    System 2 response time target: ~2000ms (iterative exploration)
    """

    vector_store: VectorStore
    embedder: Embedder
    llm: LLMClient
    active_engine: ActiveEngine | None = None

    s1_confidence_threshold: float = 0.8
    s2_complexity_threshold: float = 0.3

    def __post_init__(self) -> None:
        self._s1_conversation_count = 0
        self._s2_conversation_count = 0

    async def route(self, query: str, context: dict | None = None) -> MemoryResult:
        """Route a memory query to System 1 or System 2.

        Args:
            query: The user's query
            context: Optional context including urgency, complexity hints

        Returns:
            MemoryResult with retrieved memories and routing metadata
        """
        ctx = context or {}
        urgency = float(ctx.get("urgency", 0.5))
        complexity = float(ctx.get("complexity", -1))
        if complexity < 0:
            complexity = await self._estimate_complexity(query)

        if urgency > 0.7 or complexity < self.s2_complexity_threshold:
            return await self._system1_retrieve(query)
        return await self._system2_reconstruct(query)

    async def _system1_retrieve(self, query: str) -> MemoryResult:
        """Fast path: embedding similarity + k-NN + valence boost.

        Retrieves top-k semantic matches and boosts their scores by valence
        salience. High-valence memories surface even with lower raw similarity.
        """
        self._s1_conversation_count += 1
        embedding = await self.embedder.embed(query)
        candidates = await self.vector_store.search(embedding, k=20)

        memories = []
        for c in candidates:
            base_score = float(c.get("score", c.get("similarity", 0.5)))
            valence = c.get("valence_salience", 0.0)
            boosted = base_score * (1.0 + valence)
            memories.append({
                "id": c.get("id", ""),
                "content": c.get("content", ""),
                "keywords": c.get("keywords", []),
                "score": round(boosted, 4),
                "valence_boost": round(valence, 4),
            })

        memories.sort(key=lambda m: m["score"], reverse=True)
        top = memories[:5]

        return MemoryResult(
            memories=top,
            system="S1",
            latency="fast",
            confidence=top[0]["score"] if top else 0.0,
        )

    async def _system2_reconstruct(self, query: str) -> MemoryResult:
        """Slow path: active iterative reconstruction through memory graph.

        Uses the ActiveReconstructionEngine when available; falls back to
        embedding-based retrieval when no engine is configured.
        """
        self._s2_conversation_count += 1

        if self.active_engine is not None:
            result = await self.active_engine.reconstruct(query)
            memories = getattr(result, "evidence", [])
            return MemoryResult(
                memories=[{
                    "id": e.content.id,
                    "content": e.content.content,
                    "score": round(e.confidence, 4),
                    "path_depth": e.path_depth,
                } for e in memories],
                system="S2",
                latency="deliberative",
                confidence=memories[0].confidence if memories else 0.0,
            )

        # Fallback: embed + similarity
        embedding = await self.embedder.embed(query)
        candidates = await self.vector_store.search(embedding, k=10)
        return MemoryResult(
            memories=[{"id": c.get("id", ""), "content": c.get("content", ""),
                       "score": float(c.get("score", 0.5))} for c in candidates[:5]],
            system="S2",
            latency="fallback",
            confidence=candidates[0].get("score", 0.5) if candidates else 0.0,
        )

    async def _estimate_complexity(self, query: str) -> float:
        """Estimate query complexity using a lightweight LLM call."""
        prompt = f"""Rate the complexity of this query on a scale 0.0 to 1.0.

Query: {query[:500]}

Consider: multi-step reasoning, domain breadth, abstraction level.
Output only the number."""
        try:
            return float(await self.llm.complete(prompt))
        except (ValueError, TypeError):
            return 0.5

    @property
    def s1_count(self) -> int:
        return self._s1_conversation_count

    @property
    def s2_count(self) -> int:
        return self._s2_conversation_count
