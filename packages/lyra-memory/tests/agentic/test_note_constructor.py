"""Tests for note_constructor.py — agentic note construction."""

from __future__ import annotations

import pytest

from lyra_memory.agentic.note_constructor import ConstructionDecision, NoteConstructor


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
        return '{"should_store": false, "reason": "no more responses"}'

    async def embed(self, text: str) -> list[float]:
        return [0.1] * 8  # deterministic stub embedding


class StubEmbedder:
    """Stub embedder returning fixed vectors."""

    async def embed(self, text: str) -> list[float]:
        return [0.1] * 8


@pytest.fixture
def constructor():
    llm = StubLLM()
    embedder = StubEmbedder()
    return NoteConstructor(llm=llm, embedder=embedder)


@pytest.mark.unit
class TestNoteConstructor:
    """Unit tests for NoteConstructor."""

    async def test_rejects_short_content(self, constructor):
        result = await constructor.construct("hi")
        assert not result.should_store
        assert "too short" in result.reason

    async def test_rejects_empty_content(self, constructor):
        result = await constructor.construct("")
        assert not result.should_store

    async def test_accepts_valid_content(self, constructor):
        constructor.llm.responses = ["""```json
{
    "should_store": true,
    "keywords": ["python", "testing", "pytest"],
    "tags": ["testing", "python"],
    "contextual_description": "Learned about pytest fixtures",
    "merge_target_index": null,
    "merged_content": null,
    "reason": "new testing knowledge"
}
```"""]

        result = await constructor.construct(
            "I learned that pytest fixtures are great for test setup and teardown"
        )
        assert result.should_store
        assert "python" in result.keywords
        assert "testing" in result.tags
        assert result.contextual_description == "Learned about pytest fixtures"

    async def test_handles_merge_decision(self, constructor):
        constructor.llm.responses = ["""```json
{
    "should_store": true,
    "keywords": ["pytest", "fixtures"],
    "tags": ["testing"],
    "contextual_description": "Updated pytest fixture knowledge",
    "merge_target_index": 2,
    "merged_content": "Combined pytest fixture knowledge",
    "reason": "extends existing note"
}
```"""]

        nearby = [
            {"id": "1", "content": "old note about testing", "keywords": [], "tags": []},
            {"id": "2", "content": "pytest basics", "keywords": ["pytest"], "tags": ["testing"]},
        ]

        result = await constructor.construct("pytest fixtures are powerful", nearby)
        assert result.should_store
        assert result.merge_target_id == "2"
        assert "Combined" in result.merged_content

    async def test_extracts_json_from_markdown_fence(self, constructor):
        constructor.llm.responses = ["""Here is my analysis:

```json
{
    "should_store": true,
    "keywords": ["api", "design"],
    "tags": ["architecture"],
    "contextual_description": "REST API design principles",
    "merge_target_index": null,
    "merged_content": null,
    "reason": "important architectural knowledge"
}
```

This is a solid pattern to remember."""]

        result = await constructor.construct(
            "REST APIs should use consistent error response formats"
        )
        assert result.should_store
        assert result.keywords == ["api", "design"]

    async def test_rejects_when_should_store_false(self, constructor):
        constructor.llm.responses = ["""```json
{
    "should_store": false,
    "keywords": [],
    "tags": [],
    "contextual_description": "",
    "merge_target_index": null,
    "merged_content": null,
    "reason": "duplicate of existing knowledge"
}
```"""]

        result = await constructor.construct("This is something I already know well")
        assert not result.should_store
        assert result.reason == "duplicate of existing knowledge"

    async def test_handles_invalid_json(self, constructor):
        constructor.llm.responses = ["not valid json at all"]

        result = await constructor.construct("some content that causes bad json response")
        assert not result.should_store
        assert "failed to parse" in result.reason

    async def test_enforces_max_keywords(self, constructor):
        constructor.llm.responses = ["""```json
{
    "should_store": true,
    "keywords": ["a", "b", "c", "d", "e", "f", "g", "h", "i", "extra"],
    "tags": ["test"],
    "contextual_description": "test",
    "merge_target_index": null,
    "merged_content": null,
    "reason": "test"
}
```"""]

        result = await constructor.construct("test content with many keywords")
        assert len(result.keywords) <= constructor.max_keywords

    async def test_extracts_json_without_fence(self, constructor):
        constructor.llm.responses = [
(
                '{"should_store": true, "keywords": ["simple"], "tags": ["test"],'
                '"contextual_description": "simple test", "merge_target_index": null,'
                '"merged_content": null, "reason": "simple"}'
            )
        ]

        result = await constructor.construct("simple test content for direct json parsing")
        assert result.should_store
        assert result.keywords == ["simple"]


@pytest.mark.unit
class TestConstructionDecision:
    """Tests for ConstructionDecision dataclass."""

    def test_default_decision_is_no_store(self):
        d = ConstructionDecision(should_store=False, reason="test")
        assert not d.should_store
        assert d.keywords == []
        assert d.tags == []

    def test_store_decision_with_metadata(self):
        d = ConstructionDecision(
            should_store=True,
            keywords=["kw1"],
            tags=["tag1"],
            contextual_description="ctx",
            reason="valid",
        )
        assert d.should_store
        assert d.keywords == ["kw1"]
        assert d.tags == ["tag1"]
        assert d.contextual_description == "ctx"
