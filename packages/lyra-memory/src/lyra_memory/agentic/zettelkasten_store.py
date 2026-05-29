"""
Full Zettelkasten Memory Store — integrates note construction, link generation,
and memory evolution into a single coherent write path.

Source: A-Mem (FiM0M8gcct), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from lyra_memory.agentic.link_generator import Link, LinkGenerator
from lyra_memory.agentic.memory_evolver import MemoryEvolver
from lyra_memory.agentic.note_constructor import (
    EmbeddingModel,
    LLMClient,
    NoteConstructor,
)


@dataclass
class AgenticMemoryNote:
    """A single memory note in the Zettelkasten store.

    7-field structure:
    - content: The core memory content
    - timestamp: Creation/last-update time
    - keywords: Extracted keywords for retrieval
    - tags: Semantic tags
    - contextual_description: When/why this memory matters
    - embedding: Dense vector for similarity search
    - linked_memories: IDs of connected notes
    """

    id: str = field(default_factory=lambda: uuid4().hex)
    content: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    keywords: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    contextual_description: str = ""
    embedding: list[float] | None = None
    linked_memories: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "keywords": self.keywords,
            "tags": self.tags,
            "contextual_description": self.contextual_description,
            "linked_memories": self.linked_memories,
        }


class VectorStore(Protocol):
    """Protocol for vector similarity search."""

    async def search(self, embedding: list[float], k: int) -> list[dict]: ...

    async def insert(self, note_id: str, embedding: list[float], metadata: dict) -> None: ...

    async def update(self, note_id: str, embedding: list[float], metadata: dict) -> None: ...

    async def delete(self, note_id: str) -> None: ...


@dataclass
class ZettelkastenMemoryStore:
    """Agentic memory store implementing the A-Mem Zettelkasten architecture.

    Write path:
        1. NoteConstructor decides what/how to store
        2. LinkGenerator creates typed links to similar notes
        3. MemoryEvolver updates existing notes if new info changes them

    Read path:
        1. Embed query
        2. Vector similarity search
        3. Return notes with their linked context
    """

    llm: LLMClient
    embedder: EmbeddingModel
    vector_store: VectorStore

    def __post_init__(self):
        self.constructor = NoteConstructor(self.llm, self.embedder)
        self.linker = LinkGenerator(self.llm)
        self.evolver = MemoryEvolver(self.llm)
        self._notes: dict[str, AgenticMemoryNote] = {}
        self._links: dict[str, list[Link]] = {}  # source_id -> outgoing links

    async def write(self, content: str) -> AgenticMemoryNote | None:
        """Store new content using the full agentic write pipeline.

        Returns the created note, or None if the constructor decided not to store.
        """
        # 1. Find nearby notes for context
        embedding = await self.embedder.embed(content)
        nearby = await self.vector_store.search(embedding, k=10)

        # 2. Decide whether and how to store
        decision = await self.constructor.construct(content, nearby)
        if not decision.should_store:
            return None

        # 3. Handle merge case
        if decision.merge_target_id and decision.merged_content:
            target = self._notes.get(decision.merge_target_id)
            if target:
                target.content = decision.merged_content
                target.timestamp = datetime.now(timezone.utc)
                target.keywords = decision.keywords
                target.tags = decision.tags
                new_embedding = await self.embedder.embed(decision.merged_content)
                target.embedding = new_embedding
                await self.vector_store.update(
                    target.id, new_embedding, target.to_dict()
                )
                return target

        # 4. Create new note
        note = AgenticMemoryNote(
            content=content,
            keywords=decision.keywords,
            tags=decision.tags,
            contextual_description=decision.contextual_description,
            embedding=embedding,
        )

        # 5. Generate links
        candidate_dicts = [
            {"id": n["id"], "content": n.get("content", ""), "keywords": n.get("keywords", [])}
            for n in nearby
        ]
        links = await self.linker.generate_links(
            note.id, content, decision.keywords, candidate_dicts
        )
        note.linked_memories = [link.target_id for link in links]

        # 6. Evolve nearby notes
        evolution_results = await self.evolver.evolve(content, nearby)
        for result in evolution_results:
            if result.was_updated and result.note_id in self._notes:
                existing = self._notes[result.note_id]
                existing.content = result.new_content or existing.content
                existing.keywords = result.new_keywords or existing.keywords
                existing.tags = result.new_tags or existing.tags
                existing.timestamp = datetime.now(timezone.utc)
                new_emb = await self.embedder.embed(existing.content)
                existing.embedding = new_emb
                await self.vector_store.update(
                    existing.id, new_emb, existing.to_dict()
                )

        # 7. Persist
        self._notes[note.id] = note
        self._links[note.id] = links
        await self.vector_store.insert(note.id, embedding, note.to_dict())

        return note

    async def read(self, query: str, k: int = 10) -> list[AgenticMemoryNote]:
        """Retrieve notes by semantic similarity to the query.

        Returns notes with their linked context for richer retrieval.
        """
        embedding = await self.embedder.embed(query)
        results = await self.vector_store.search(embedding, k=k)
        notes = []
        for r in results:
            note = self._notes.get(r["id"])
            if note:
                notes.append(note)
        return notes

    async def get_with_context(self, note_id: str, depth: int = 1) -> dict:
        """Retrieve a note with its linked neighborhood up to given depth."""
        note = self._notes.get(note_id)
        if not note:
            return {}

        result = {"note": note.to_dict(), "links": [], "linked_notes": []}

        outgoing = self._links.get(note_id, [])
        result["links"] = [
            {"target_id": link.target_id, "type": link.link_type.value}
            for link in outgoing
        ]

        if depth > 0:
            for link in outgoing:
                linked = self._notes.get(link.target_id)
                if linked:
                    result["linked_notes"].append(linked.to_dict())

        return result

    @property
    def note_count(self) -> int:
        return len(self._notes)

    @property
    def link_count(self) -> int:
        return sum(len(links) for links in self._links.values())
