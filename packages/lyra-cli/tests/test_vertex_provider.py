"""Contract tests for the GeminiVertexLLM provider.

google-cloud-aiplatform is an optional dependency (lyra[vertex]).
"""
from __future__ import annotations

import pytest

from harness_core.messages import Message, StopReason
from lyra_cli.providers.vertex import (
    GeminiVertexLLM,
    VertexUnavailable,
    vertex_available,
)


class _FakeVertexResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeVertexModel:
    def __init__(self, text: str = "hello from vertex") -> None:
        self._text = text
        self.last_args: tuple | None = None

    def generate_content(self, contents, **kwargs):
        self.last_args = (contents, kwargs)
        return _FakeVertexResponse(self._text)


def test_vertex_unavailable_when_no_client() -> None:
    with pytest.raises(VertexUnavailable):
        GeminiVertexLLM(model="gemini-2.5-pro", project="p", location="us-central1")


def test_generate_routes_through_generate_content() -> None:
    fake = _FakeVertexModel(text="from-vertex")
    llm = GeminiVertexLLM(
        model="gemini-2.5-pro",
        project="my-project",
        location="us-central1",
        client=fake,
    )
    out = llm.generate([Message.user("hi")], max_tokens=100)
    assert out.content == "from-vertex"
    assert out.stop_reason == StopReason.END_TURN
    assert fake.last_args is not None
    contents, kwargs = fake.last_args
    assert isinstance(contents, list)
    assert kwargs.get("generation_config") is not None


def test_vertex_available_returns_bool() -> None:
    assert isinstance(vertex_available(), bool)
