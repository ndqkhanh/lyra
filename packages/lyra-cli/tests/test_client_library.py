"""Tests for :mod:`lyra_cli.client` — the embedded Python client."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from harness_core.messages import Message
from harness_core.models import MockLLM

from lyra_cli.client import (
    ChatRequest,
    ChatResponse,
    LyraClient,
    StreamEvent,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """An empty workspace; ``LyraClient`` will materialise ``.lyra/``."""
    return tmp_path


@pytest.fixture
def scripted_provider() -> MockLLM:
    """A ``MockLLM`` pre-loaded with one response.

    Reused across tests; assertion on ``.calls`` lets us verify the
    message list the client built.
    """
    return MockLLM(scripted_outputs=["hello, embedded world"])


@pytest.fixture
def factory(scripted_provider: MockLLM):
    """Provider factory that always returns the same mock instance.

    Captures the slug the client passed so tests can verify alias
    resolution worked end-to-end.
    """
    received: list[str | None] = []

    def make(slug: str | None) -> MockLLM:
        received.append(slug)
        return scripted_provider

    make.received = received  # type: ignore[attr-defined]
    return make


@pytest.fixture
def client(repo: Path, factory) -> LyraClient:
    """A client wired to the scripted mock provider."""
    return LyraClient(repo_root=repo, provider_factory=factory)


# ---------------------------------------------------------------------------
# Basic chat
# ---------------------------------------------------------------------------


def test_chat_with_string_prompt_returns_text(client: LyraClient) -> None:
    """The most ergonomic call shape — pass a raw prompt — must work."""
    resp = client.chat("how do you do")
    assert isinstance(resp, ChatResponse)
    assert resp.text == "hello, embedded world"
    assert resp.error is None
    assert resp.session_id  # non-empty


def test_chat_with_request_object_uses_explicit_session_id(
    client: LyraClient,
) -> None:
    """Caller-provided ``session_id`` is honoured, not overwritten."""
    sid = "fixed-session-id"
    resp = client.chat(ChatRequest(prompt="hi", session_id=sid))
    assert resp.session_id == sid


def test_chat_persists_user_and_assistant_rows(
    client: LyraClient, repo: Path
) -> None:
    """Each ``chat()`` writes two JSONL rows: user, then assistant."""
    resp = client.chat("ping")
    log = repo / ".lyra" / "sessions" / resp.session_id / "turns.jsonl"
    assert log.is_file(), "turns.jsonl was not created"
    rows = [json.loads(line) for line in log.read_text().splitlines() if line]
    assert len(rows) == 2
    assert rows[0]["role"] == "user"
    assert rows[0]["content"] == "ping"
    assert rows[1]["role"] == "assistant"
    assert rows[1]["content"] == "hello, embedded world"
    # Same timestamp = same turn => Phase M aggregator buckets correctly.
    assert rows[0]["ts"] == rows[1]["ts"]


def test_chat_creates_session_lazily(client: LyraClient, repo: Path) -> None:
    """No session file should exist until a turn is recorded."""
    sessions_root = repo / ".lyra" / "sessions"
    assert sessions_root.is_dir()
    # Empty before chat.
    assert list(sessions_root.iterdir()) == []
    resp = client.chat("first")
    children = list(sessions_root.iterdir())
    assert len(children) == 1
    assert children[0].name == resp.session_id


def test_chat_appends_to_existing_session_history(
    repo: Path, scripted_provider: MockLLM
) -> None:
    """A second turn should see the first turn in the message list."""
    # Two scripted replies so the second ``chat()`` doesn't fall through
    # to MockLLM's default ``done`` placeholder.
    provider = MockLLM(scripted_outputs=["reply-1", "reply-2"])

    def factory(_slug):
        return provider

    c = LyraClient(repo_root=repo, provider_factory=factory)
    sid = "multi-turn"
    c.chat(ChatRequest(prompt="first", session_id=sid))
    c.chat(ChatRequest(prompt="second", session_id=sid))

    # Second call's message list must include both prior turns.
    messages_for_second = provider.calls[-1]
    contents = [m.content for m in messages_for_second]
    assert "first" in contents
    assert "reply-1" in contents
    assert "second" in contents


def test_chat_forwards_system_prompt(
    repo: Path, scripted_provider: MockLLM
) -> None:
    """A non-empty ``system_prompt`` must show up as the first message."""

    def factory(_slug):
        return scripted_provider

    c = LyraClient(repo_root=repo, provider_factory=factory)
    c.chat(ChatRequest(prompt="hi", system_prompt="be terse"))

    sent = scripted_provider.calls[-1]
    assert sent[0].role == "system"
    assert sent[0].content == "be terse"


def test_chat_records_canonical_slug_after_alias_resolution(
    repo: Path, scripted_provider: MockLLM
) -> None:
    """``opus`` should resolve to the canonical slug in ``turns.jsonl``.

    Phase M's aggregator filters/groups by model slug; recording the
    raw alias would bucket ``opus`` separately from
    ``claude-opus-4.5`` and break ``lyra burn compare``.
    """
    received: list[str | None] = []

    def factory(slug):
        received.append(slug)
        return scripted_provider

    c = LyraClient(repo_root=repo, provider_factory=factory)
    resp = c.chat(ChatRequest(prompt="hi", model="opus"))
    assert resp.model == "claude-opus-4.5"
    assert received == ["claude-opus-4.5"]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


def test_chat_handles_provider_error_gracefully(repo: Path) -> None:
    """A raising provider must not crash the client."""

    class Boom:
        def generate(self, _messages: list[Message]) -> Message:
            raise RuntimeError("kaboom")

    c = LyraClient(repo_root=repo, provider_factory=lambda _slug: Boom())
    resp = c.chat("anything")

    assert resp.error is not None and "kaboom" in resp.error
    assert resp.text == ""
    # Errored turns are still persisted so the user can see what failed.
    log = repo / ".lyra" / "sessions" / resp.session_id / "turns.jsonl"
    rows = [json.loads(line) for line in log.read_text().splitlines() if line]
    assert rows[1]["error"] is not None
    assert "kaboom" in rows[1]["error"]


def test_chat_rejects_non_string_non_request(client: LyraClient) -> None:
    """Misuse should fail loudly; we only accept ``str`` or ``ChatRequest``."""
    with pytest.raises(TypeError):
        client.chat(42)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------


def test_stream_yields_delta_then_complete(client: LyraClient) -> None:
    """MVP stream path: one ``delta`` carrying the full reply, one ``complete``."""
    events = list(client.stream("hi"))
    assert len(events) == 2
    assert events[0].kind == "delta"
    assert events[0].payload == "hello, embedded world"
    assert events[1].kind == "complete"
    assert events[1].payload == "hello, embedded world"


def test_stream_yields_error_event_on_failure(repo: Path) -> None:
    """Provider failure must collapse to a single ``error`` event."""

    class Boom:
        def generate(self, _messages: list[Message]) -> Message:
            raise ValueError("bad provider")

    c = LyraClient(repo_root=repo, provider_factory=lambda _slug: Boom())
    events = list(c.stream("hi"))
    assert len(events) == 1
    assert events[0].kind == "error"
    assert "bad provider" in events[0].payload


# ---------------------------------------------------------------------------
# Listings
# ---------------------------------------------------------------------------


def test_list_models_returns_canonical_sorted_slugs(client: LyraClient) -> None:
    """The model list must dedupe aliases and be sorted for stable output."""
    models = client.list_models()
    assert models == sorted(set(models))
    # A handful of slugs we know live in DEFAULT_ALIASES.
    assert "claude-opus-4.5" in models
    assert "claude-sonnet-4.5" in models
    assert "deepseek-chat" in models


def test_list_sessions_reflects_completed_turns(client: LyraClient) -> None:
    """After one chat we should see one session row with ``turn_count > 0``."""
    assert client.list_sessions() == []
    resp = client.chat("hi")
    sessions = client.list_sessions()
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == resp.session_id
    assert sessions[0]["turn_count"] >= 1


def test_list_skills_returns_serialisable_dicts(client: LyraClient) -> None:
    """Result must be plain dicts with at least ``id``/``description``/``path``."""
    skills = client.list_skills()
    assert isinstance(skills, list)
    for s in skills:
        assert isinstance(s, dict)
        assert {"id", "description", "path"} <= s.keys()
        # Must be JSON-serialisable (N.6 streams this over HTTP).
        json.dumps(s)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_close_is_idempotent(client: LyraClient) -> None:
    """Multiple ``close()`` calls must be safe."""
    client.close()
    client.close()


def test_context_manager_calls_close(repo: Path, factory) -> None:
    """``with LyraClient(...) as c:`` must close on exit (no exception)."""
    closes: list[int] = []

    class Tracking(LyraClient):
        def close(self) -> None:
            closes.append(1)

    with Tracking(repo_root=repo, provider_factory=factory) as c:
        assert isinstance(c, LyraClient)
    assert closes == [1]
