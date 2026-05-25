"""Tests for memory_evolver.py — memory evolution on write."""
from __future__ import annotations

import pytest

from lyra_memory.agentic.memory_evolver import EvolutionResult, MemoryEvolver


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
        return '{"should_update": false, "reason": "no update needed"}'


@pytest.fixture
def evolver():
    llm = StubLLM()
    return MemoryEvolver(llm=llm)


@pytest.mark.unit
class TestMemoryEvolver:
    """Unit tests for MemoryEvolver."""

    async def test_empty_nearby_returns_nothing(self, evolver):
        results = await evolver.evolve("new content", [])
        assert results == []

    async def test_evolves_existing_note(self, evolver):
        evolver.llm.responses = ["""```json
{
    "should_update": true,
    "reason": "new information refines the existing knowledge",
    "new_content": "Updated: pytest fixtures provide setup and teardown, and support scoping",
    "new_keywords": ["pytest", "fixtures", "scoping"],
    "new_tags": ["testing", "python", "advanced"]
}
```"""]

        nearby = [
            {
                "id": "note-1",
                "content": "pytest fixtures help with test setup and teardown",
                "keywords": ["pytest", "fixtures"],
                "tags": ["testing", "python"],
            }
        ]

        results = await evolver.evolve(
            "pytest fixtures also support module, class, and function scoping",
            nearby,
        )

        assert len(results) == 1
        assert results[0].was_updated
        assert results[0].note_id == "note-1"
        assert "scoping" in results[0].new_content
        assert "scoping" in results[0].new_keywords
        assert "advanced" in results[0].new_tags

    async def test_no_update_when_redundant(self, evolver):
        evolver.llm.responses = ["""```json
{
    "should_update": false,
    "reason": "new info is redundant with existing knowledge"
}
```"""]

        nearby = [
            {
                "id": "note-1",
                "content": "already knows this",
                "keywords": ["known"],
                "tags": ["known"],
            }
        ]

        results = await evolver.evolve("redundant information", nearby)
        assert len(results) == 0

    async def test_respects_max_evolutions(self, evolver):
        evolver.llm.responses = [f"""{{"should_update": true, "reason": "update {i}", "new_content": "updated {i}", "new_keywords": ["kw{i}"], "new_tags": ["tag{i}"]}}""" for i in range(10)]

        nearby = [
            {"id": f"note-{i}", "content": f"content {i}", "keywords": [], "tags": []}
            for i in range(10)
        ]

        results = await evolver.evolve("new content", nearby)
        assert len(results) <= evolver.max_evolutions_per_write

    async def test_handles_invalid_llm_response(self, evolver):
        evolver.llm.responses = ["garbage response"]

        nearby = [{"id": "note-1", "content": "c", "keywords": [], "tags": []}]
        results = await evolver.evolve("new", nearby)
        assert len(results) == 0


@pytest.mark.unit
class TestEvolutionResult:
    """Tests for EvolutionResult dataclass."""

    def test_no_update_result(self):
        r = EvolutionResult(note_id="n1", was_updated=False, reason="unchanged")
        assert not r.was_updated
        assert r.new_content is None

    def test_updated_result(self):
        r = EvolutionResult(
            note_id="n1",
            was_updated=True,
            new_content="updated",
            new_keywords=["a"],
            new_tags=["b"],
            reason="refined",
        )
        assert r.was_updated
        assert r.new_content == "updated"
