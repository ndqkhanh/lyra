"""
LP-RAG — Link Prediction Retrieval-Augmented Generation.

Casts retrieval as inductive link prediction on a chunk-query graph,
supervised by synthetically generated queries. Model-agnostic —
works with any link prediction method.

Source: LP-RAG (Y8Txo8vaH7), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4


class LLMClient(Protocol):
    """Protocol for LLM interaction."""

    async def complete(self, prompt: str) -> str: ...


class LinkPredictor(Protocol):
    """Protocol for link prediction models."""

    def predict_links(
        self, query_node: object, candidate_nodes: list[object],
    ) -> list[float]: ...

    def add_edge(self, query: object, chunk: object) -> None: ...

    def train(self) -> None: ...


@dataclass
class Chunk:
    """A document chunk with content and metadata."""

    id: str = field(default_factory=lambda: uuid4().hex)
    content: str = ""
    source_doc: str = ""
    index: int = 0

    @property
    def node(self) -> str:
        return self.id


@dataclass
class LPRAGRetriever:
    """Retrieval via link prediction on chunk-query graph.

    LP-RAG consistently outperforms HippoRAG, GFM-RAG, and NodeRAG
    on retrieval benchmarks by casting retrieval as link prediction.
    """

    llm: LLMClient
    link_predictor: LinkPredictor | None = None
    chunks: dict[str, Chunk] = field(default_factory=dict)
    _trained: bool = False

    async def retrieve(self, query: str, k: int = 10) -> list[Chunk]:
        """Predict which chunks are linked to this query.

        When a trained link predictor is available, uses it. Falls back
        to LLM-driven relevance scoring when no predictor exists.
        """
        if self.link_predictor is not None and self._trained:
            return await self._predictor_retrieve(query, k)
        return await self._llm_retrieve(query, k)

    async def _predictor_retrieve(self, query: str, k: int) -> list[Chunk]:
        """Use link predictor for retrieval."""
        query_node = self._embed_query(query)
        chunk_list = list(self.chunks.values())
        scores = self.link_predictor.predict_links(
            query_node, [c.node for c in chunk_list]
        )
        scored = sorted(
            zip(chunk_list, scores), key=lambda x: x[1], reverse=True,
        )
        return [c for c, _ in scored[:k]]

    async def _llm_retrieve(self, query: str, k: int) -> list[Chunk]:
        """Fallback: LLM-driven relevance scoring."""
        if not self.chunks:
            return []

        chunk_list = list(self.chunks.values())
        formatted = "\n".join(
            f"[{c.id[:8]}] {c.content[:200]}" for c in chunk_list[:30]
        )

        prompt = f"""Given this query, identify the {k} most relevant chunk IDs.

Query: {query[:500]}

Chunks:
{formatted}

Output JSON array of chunk IDs in order of relevance:
["chunk_id_1", "chunk_id_2", ...]"""

        response = await self.llm.complete(prompt)
        return self._parse_chunk_ids(response, k)

    async def train_on_synthetic(self, documents: list[str]) -> None:
        """Generate synthetic queries and train link predictor."""
        if self.link_predictor is None:
            return

        for doc in documents:
            chunks = self._chunk_document(doc)
            for c in chunks:
                self.chunks[c.id] = c

            synthetic_queries = await self._generate_synthetic_queries(chunks)
            for query in synthetic_queries:
                relevant = await self._identify_relevant_chunks(query, chunks)
                for rc in relevant:
                    self.link_predictor.add_edge(query, rc.node)

        self.link_predictor.train()
        self._trained = True

    def add_chunk(self, content: str, source_doc: str = "", index: int = 0) -> Chunk:
        """Add a chunk to the index."""
        chunk = Chunk(content=content, source_doc=source_doc, index=index)
        self.chunks[chunk.id] = chunk
        return chunk

    async def _generate_synthetic_queries(
        self, chunks: list[Chunk],
    ) -> list[str]:
        """Generate synthetic queries from document chunks."""
        joined = " ".join(c.content[:200] for c in chunks[:5])
        prompt = f"""Generate 3 diverse queries that this text could answer:

Text:
{joined[:2000]}

Output JSON array of query strings only."""
        response = await self.llm.complete(prompt)
        return self._parse_queries(response)

    async def _identify_relevant_chunks(
        self, query: str, chunks: list[Chunk],
    ) -> list[Chunk]:
        """Identify which chunks are relevant to a query."""
        formatted = "\n".join(
            f"[{c.id[:8]}] {c.content[:150]}" for c in chunks[:10]
        )
        prompt = f"""Query: {query[:300]}

Chunks:
{formatted}

Which chunks are relevant? Output JSON array of chunk IDs only."""
        response = await self.llm.complete(prompt)
        ids = self._parse_ids(response)
        return [c for c in chunks if c.id in ids]

    @staticmethod
    def _chunk_document(text: str, chunk_size: int = 500) -> list[Chunk]:
        """Split document into fixed-size chunks."""
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size):
            chunk_text = " ".join(words[i:i + chunk_size])
            chunks.append(Chunk(content=chunk_text, index=i // chunk_size))
        return chunks

    @staticmethod
    def _embed_query(query: str) -> str:
        """Create a node identifier for a query."""
        return f"query:{hash(query) & 0xFFFFFFFF:08x}"

    @staticmethod
    def _parse_chunk_ids(response: str, k: int) -> list[Chunk]:
        import json

        try:
            data = json.loads(_extract_json(response))
            ids = [str(x) for x in data if isinstance(x, str)]
            return [Chunk(id=cid) for cid in ids[:k]]
        except (json.JSONDecodeError, TypeError):
            return []

    @staticmethod
    def _parse_queries(response: str) -> list[str]:
        import json

        try:
            data = json.loads(_extract_json(response))
            return [str(q) for q in data if isinstance(q, str)]
        except (json.JSONDecodeError, TypeError):
            return []

    @staticmethod
    def _parse_ids(response: str) -> list[str]:
        import json

        try:
            data = json.loads(_extract_json(response))
            return [str(x) for x in data if isinstance(x, str)]
        except (json.JSONDecodeError, TypeError):
            return []


def _extract_json(text: str) -> str:
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()
    brace_start = text.find("[")
    brace_end = text.rfind("]")
    if brace_start >= 0 and brace_end > brace_start:
        return text[brace_start : brace_end + 1]
    return text.strip()
