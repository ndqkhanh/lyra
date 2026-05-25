"""Tests for link_generator.py — autonomous link generation."""
from __future__ import annotations

import pytest

from lyra_memory.agentic.link_generator import Link, LinkGenerator, LinkType


class StubLLM:
    """Stub LLM that returns controlled responses."""

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
        return "[]"


@pytest.fixture
def generator():
    llm = StubLLM()
    return LinkGenerator(llm=llm)


@pytest.mark.unit
class TestLinkGenerator:
    """Unit tests for LinkGenerator."""

    async def test_empty_candidates_returns_no_links(self, generator):
        links = await generator.generate_links(
            "note-1", "some content", ["kw1"], []
        )
        assert links == []

    async def test_generates_typed_links(self, generator):
        generator.llm.responses = ["""```json
[
    {
        "target_id": "existing-1",
        "link_type": "extends",
        "confidence": 0.9,
        "rationale": "adds detail to existing note"
    },
    {
        "target_id": "existing-2",
        "link_type": "relates",
        "confidence": 0.7,
        "rationale": "same topic area"
    }
]
```"""]

        candidates = [
            {"id": "existing-1", "content": "base knowledge", "keywords": ["base"]},
            {"id": "existing-2", "content": "related topic", "keywords": ["related"]},
            {"id": "existing-3", "content": "unrelated", "keywords": ["other"]},
        ]

        links = await generator.generate_links(
            "note-1", "detailed extension of base", ["extension"], candidates
        )

        assert len(links) == 2
        assert links[0].source_id == "note-1"
        assert links[0].target_id == "existing-1"
        assert links[0].link_type == LinkType.EXTENDS
        assert links[0].confidence == 0.9
        assert links[1].link_type == LinkType.RELATES

    async def test_filters_low_confidence_links(self, generator):
        generator.llm.responses = ["""```json
[
    {
        "target_id": "existing-1",
        "link_type": "relates",
        "confidence": 0.3,
        "rationale": "weak connection"
    },
    {
        "target_id": "existing-2",
        "link_type": "extends",
        "confidence": 0.8,
        "rationale": "strong connection"
    }
]
```"""]

        candidates = [
            {"id": "existing-1", "content": "topic a", "keywords": ["a"]},
            {"id": "existing-2", "content": "topic b", "keywords": ["b"]},
        ]

        links = await generator.generate_links(
            "note-1", "content", ["kw"], candidates
        )

        # Only the high-confidence link should pass
        assert len(links) == 1
        assert links[0].target_id == "existing-2"

    async def test_rejects_links_to_unknown_targets(self, generator):
        generator.llm.responses = ["""```json
[
    {
        "target_id": "ghost-note",
        "link_type": "relates",
        "confidence": 0.9,
        "rationale": "connected to non-existent note"
    }
]
```"""]

        candidates = [
            {"id": "real-1", "content": "real", "keywords": ["real"]},
        ]

        links = await generator.generate_links("note-1", "content", ["kw"], candidates)
        assert len(links) == 0

    async def test_handles_invalid_llm_response(self, generator):
        generator.llm.responses = ["not json"]

        candidates = [{"id": "n1", "content": "c", "keywords": []}]
        links = await generator.generate_links("n2", "c", ["kw"], candidates)
        assert links == []

    async def test_all_link_types(self, generator):
        for lt in LinkType:
            generator.llm.responses = [f"""[{{
                "target_id": "n1",
                "link_type": "{lt.value}",
                "confidence": 0.9,
                "rationale": "test"
            }}]"""]

            candidates = [{"id": "n1", "content": "c", "keywords": []}]
            links = await generator.generate_links("n2", "c", ["kw"], candidates)
            assert len(links) == 1
            assert links[0].link_type == lt

    async def test_no_connections_returns_empty(self, generator):
        generator.llm.responses = ["[]"]

        candidates = [
            {"id": "n1", "content": "completely unrelated topic", "keywords": ["unrelated"]},
        ]

        links = await generator.generate_links(
            "n2", "different content", ["different"], candidates
        )
        assert links == []


@pytest.mark.unit
class TestLink:
    """Tests for Link dataclass."""

    def test_link_immutable(self):
        link = Link(source_id="a", target_id="b", link_type=LinkType.EXTENDS)
        with pytest.raises(Exception):
            link.source_id = "c"

    def test_link_has_all_fields(self):
        link = Link(
            source_id="a",
            target_id="b",
            link_type=LinkType.CAUSES,
            confidence=0.95,
            rationale="explains why",
        )
        assert link.source_id == "a"
        assert link.target_id == "b"
        assert link.link_type == LinkType.CAUSES
        assert link.confidence == 0.95
        assert link.rationale == "explains why"
