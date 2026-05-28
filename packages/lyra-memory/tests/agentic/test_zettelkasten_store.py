"""Tests for zettelkasten_store.py — full Zettelkasten integration."""
from __future__ import annotations

import pytest

from lyra_memory.agentic.zettelkasten_store import AgenticMemoryNote, ZettelkastenMemoryStore


class StubLLM:
    """Stub LLM for testing the Zettelkasten store."""

    def __init__(self, responses: list[str] | None = None):
        self._responses = responses or []
        self.calls: list[str] = []
        self._idx = 0

    @property
    def responses(self) -> list[str]:
        return self._responses

    @responses.setter
    def responses(self, value: list[str]) -> None:
        self._responses = value
        self._idx = 0

    async def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        if self._idx < len(self._responses):
            resp = self._responses[self._idx]
            self._idx += 1
            return resp
        return '{"should_store": false, "reason": "default no store"}'

    async def embed(self, text: str) -> list[float]:
        return [0.1] * 8


class StubEmbedder:
    """Stub embedder returning fixed vectors."""

    async def embed(self, text: str) -> list[float]:
        return [0.1] * 8


class StubVectorStore:
    """In-memory vector store for testing."""

    def __init__(self):
        self._store: dict[str, tuple[list[float], dict]] = {}
        self.search_history: list[tuple] = []

    async def search(self, embedding: list[float], k: int) -> list[dict]:
        self.search_history.append((embedding, k))
        results = []
        for nid, (emb, meta) in self._store.items():
            results.append({"id": nid, "content": meta.get("content", ""),
                          "keywords": meta.get("keywords", [])})
        return results[:k]

    async def insert(self, note_id: str, embedding: list[float], metadata: dict) -> None:
        self._store[note_id] = (embedding, metadata)

    async def update(self, note_id: str, embedding: list[float], metadata: dict) -> None:
        self._store[note_id] = (embedding, metadata)

    async def delete(self, note_id: str) -> None:
        self._store.pop(note_id, None)


@pytest.fixture
def store():
    llm = StubLLM()
    embedder = StubEmbedder()
    vector = StubVectorStore()
    return ZettelkastenMemoryStore(llm=llm, embedder=embedder, vector_store=vector)


@pytest.mark.unit
class TestZettelkastenMemoryStore:
    """Unit tests for ZettelkastenMemoryStore."""

    async def test_initial_state(self, store):
        assert store.note_count == 0
        assert store.link_count == 0

    async def test_write_rejected_content(self, store):
        """When the constructor rejects content, write() returns None."""
        store.llm.responses = [
            '{"should_store": false, "reason": "duplicate", "keywords": [], "tags": [], "contextual_description": "", "merge_target_index": null, "merged_content": null}',
        ]

        result = await store.write("this is a duplicate content that should be rejected")
        assert result is None
        assert store.note_count == 0

    async def test_write_stores_valid_content(self, store):
        """Valid content should be stored as a new note."""
        store.llm.responses = [
            # Note constructor
            '{"should_store": true, "keywords": ["test", "pytest"], "tags": ["testing"], "contextual_description": "learned about testing", "merge_target_index": null, "merged_content": null, "reason": "new knowledge"}',
            # Link generator
            "[]",
            # Memory evolver
            '{"should_update": false, "reason": "no existing notes to evolve"}',
        ]

        result = await store.write("pytest is a great testing framework")
        assert result is not None
        assert result.keywords == ["test", "pytest"]
        assert result.tags == ["testing"]
        assert store.note_count == 1

    async def test_write_with_links(self, store):
        """Writing a note that connects to existing notes creates links."""
        # First, seed an existing note
        store.llm.responses = [
            '{"should_store": true, "keywords": ["base"], "tags": ["base"], "contextual_description": "base", "merge_target_index": null, "merged_content": null, "reason": "first"}',
            "[]",
            '{"should_update": false, "reason": "none"}',
        ]
        first = await store.write("base knowledge about testing")
        assert first is not None

        # Now write a second note that links to the first
        store.llm.responses = [
            '{"should_store": true, "keywords": ["extended"], "tags": ["extended"], "contextual_description": "extends base", "merge_target_index": null, "merged_content": null, "reason": "extend"}',
            f'[{{"target_id": "{first.id}", "link_type": "extends", "confidence": 0.9, "rationale": "builds on base"}}]',
            '{"should_update": false, "reason": "no update"}',
        ]

        second = await store.write("extended testing knowledge with advanced topics")
        assert second is not None
        assert first.id in second.linked_memories
        assert store.link_count == 1
        assert store.note_count == 2

    async def test_read_returns_matching_notes(self, store):
        """Read should return notes matching the query."""
        # Seed notes
        for i in range(3):
            store.llm.responses = [
                f'{{"should_store": true, "keywords": ["kw{i}"], "tags": ["tag{i}"], "contextual_description": "note {i}", "merge_target_index": null, "merged_content": null, "reason": "seed"}}',
                "[]",
                '{"should_update": false, "reason": "no update"}',
            ]
            await store.write(f"test content for memory note number {i} with enough length")

        results = await store.read("find note 1")
        assert len(results) == 3  # Stub returns all stored notes

    async def test_get_with_context(self, store):
        """Retrieve a note with its linked neighborhood."""
        store.llm.responses = [
            '{"should_store": true, "keywords": ["a"], "tags": ["a"], "contextual_description": "note a", "merge_target_index": null, "merged_content": null, "reason": "first"}',
            "[]",
            '{"should_update": false, "reason": "none"}',
        ]
        note_a = await store.write("this is content about topic alpha with some length")

        store.llm.responses = [
            '{"should_store": true, "keywords": ["b"], "tags": ["b"], "contextual_description": "note b", "merge_target_index": null, "merged_content": null, "reason": "second"}',
            f'[{{"target_id": "{note_a.id}", "link_type": "extends", "confidence": 0.9, "rationale": "extends a"}}]',
            '{"should_update": false, "reason": "none"}',
        ]
        note_b = await store.write("this is content about topic beta that extends alpha")

        context = await store.get_with_context(note_b.id)
        assert context["note"]["id"] == note_b.id
        assert len(context["links"]) == 1
        assert context["links"][0]["type"] == "extends"

    async def test_write_with_evolution(self, store):
        """Writing related content should trigger evolution of nearby notes."""
        store.llm.responses = [
            '{"should_store": true, "keywords": ["orig"], "tags": ["orig"], "contextual_description": "original", "merge_target_index": null, "merged_content": null, "reason": "first"}',
            "[]",
            '{"should_update": false, "reason": "none"}',
        ]
        original = await store.write("original knowledge about memory systems")

        # Now write something that evolves the original
        store.llm.responses = [
            '{"should_store": true, "keywords": ["refined"], "tags": ["refined"], "contextual_description": "refined", "merge_target_index": null, "merged_content": null, "reason": "refine"}',
            "[]",
            '{"should_update": true, "reason": "refined", "new_content": "updated original", "new_keywords": ["updated"], "new_tags": ["updated"]}',
        ]

        refined = await store.write("more specific original knowledge")
        assert refined is not None
        # Original should now have updated content in the store
        assert store._notes[original.id].content == "updated original"

    async def test_write_with_merge(self, store):
        """When constructor decides to merge, existing note should be updated."""
        store.llm.responses = [
            '{"should_store": true, "keywords": ["base"], "tags": ["base"], "contextual_description": "base", "merge_target_index": null, "merged_content": null, "reason": "first"}',
            "[]",
            '{"should_update": false, "reason": "none"}',
        ]
        original = await store.write("initial content about a topic")

        # Now write content that merges into the original
        original_id = original.id
        store.llm.responses = [
            f'{{"should_store": true, "keywords": ["merged"], "tags": ["merged"], "contextual_description": "merged", "merge_target_index": "{original_id}", "merged_content": "merged combined content", "reason": "merge"}}',
            "[]",
            '{"should_update": false, "reason": "none"}',
        ]

        merged = await store.write("additional details about the same topic")
        assert merged is not None
        assert merged.id == original_id
        assert store._notes[original_id].content == "merged combined content"


@pytest.mark.unit
class TestAgenticMemoryNote:
    """Tests for AgenticMemoryNote dataclass."""

    def test_default_construction(self):
        note = AgenticMemoryNote()
        assert note.id
        assert note.content == ""
        assert note.keywords == []

    def test_full_construction(self):
        note = AgenticMemoryNote(
            id="test-id",
            content="test content",
            keywords=["kw1"],
            tags=["tag1"],
            contextual_description="ctx",
            embedding=[0.1, 0.2],
            linked_memories=["n1", "n2"],
        )
        assert note.id == "test-id"
        assert note.content == "test content"
        assert note.linked_memories == ["n1", "n2"]

    def test_to_dict(self):
        note = AgenticMemoryNote(
            id="n1", content="c", keywords=["k"], tags=["t"],
            contextual_description="cd", linked_memories=["n2"],
        )
        d = note.to_dict()
        assert d["id"] == "n1"
        assert d["content"] == "c"
        assert d["keywords"] == ["k"]
        assert d["linked_memories"] == ["n2"]
