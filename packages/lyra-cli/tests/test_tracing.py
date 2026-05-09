"""Tests for :mod:`lyra_cli.tracing`."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from harness_core.messages import Message
from harness_core.models import MockLLM

from lyra_cli.client import ChatRequest, LyraClient
from lyra_cli.tracing import (
    LangfuseCallback,
    LangSmithCallback,
    TracingCallback,
    TracingHub,
    TurnTrace,
)


# ---------------------------------------------------------------------------
# Hub primitives
# ---------------------------------------------------------------------------


class _Recorder:
    """Tiny callback that captures the trace lifecycle for assertion."""

    def __init__(self) -> None:
        self.starts: list[TurnTrace] = []
        self.ends: list[TurnTrace] = []

    def on_turn_start(self, trace: TurnTrace) -> None:
        self.starts.append(trace)

    def on_turn_end(self, trace: TurnTrace) -> None:
        self.ends.append(trace)


def test_hub_dispatches_start_and_end_in_order() -> None:
    hub = TracingHub()
    rec = _Recorder()
    hub.add(rec)

    trace = hub.start_turn(session_id="s1", model="m", prompt="hi")
    assert trace in rec.starts
    assert rec.ends == []

    out = hub.end_turn(trace, text="ok")
    assert out is trace
    assert rec.ends == [trace]
    assert trace.latency_ms is not None and trace.latency_ms >= 0.0


def test_hub_swallows_callback_exceptions() -> None:
    """A misbehaving observer must not break the chat loop."""

    class Bomb:
        def on_turn_start(self, trace: TurnTrace) -> None:
            raise RuntimeError("on_start blew up")

        def on_turn_end(self, trace: TurnTrace) -> None:
            raise RuntimeError("on_end blew up")

    hub = TracingHub()
    rec = _Recorder()
    hub.add(Bomb())
    hub.add(rec)

    trace = hub.start_turn(session_id="s1", model="m", prompt="p")
    hub.end_turn(trace, text="ok")
    # The recorder still saw both events despite Bomb raising.
    assert rec.starts and rec.ends


def test_hub_rejects_invalid_callback() -> None:
    hub = TracingHub()
    with pytest.raises(TypeError):
        hub.add("not-a-callback")  # type: ignore[arg-type]


def test_hub_dedups_same_callback() -> None:
    hub = TracingHub()
    rec = _Recorder()
    hub.add(rec)
    hub.add(rec)
    assert len(hub) == 1


def test_hub_remove_is_idempotent() -> None:
    hub = TracingHub()
    rec = _Recorder()
    hub.add(rec)
    hub.remove(rec)
    hub.remove(rec)  # second call is a silent no-op
    assert len(hub) == 0


def test_turn_trace_to_dict_is_json_serialisable() -> None:
    import json

    trace = TurnTrace(
        session_id="s", model="m", prompt="p",
        system_prompt="be terse", metadata={"trace_id_user": "abc"},
    )
    payload = trace.to_dict()
    json.dumps(payload)  # must not raise


# ---------------------------------------------------------------------------
# LyraClient integration
# ---------------------------------------------------------------------------


def test_client_chat_emits_start_and_end_to_hub(tmp_path: Path) -> None:
    provider = MockLLM(scripted_outputs=["traced reply"])
    hub = TracingHub()
    rec = _Recorder()
    hub.add(rec)

    c = LyraClient(repo_root=tmp_path, provider_factory=lambda _slug: provider, tracing=hub)
    c.chat(ChatRequest(prompt="hi", model="opus"))

    assert len(rec.starts) == 1
    assert len(rec.ends) == 1
    end = rec.ends[0]
    assert end.text == "traced reply"
    assert end.error is None
    assert end.model == "claude-opus-4.5"
    assert end.latency_ms is not None and end.latency_ms >= 0


def test_client_chat_emits_error_trace_when_provider_fails(tmp_path: Path) -> None:
    class Boom:
        def generate(self, _msgs: list[Message]) -> Message:
            raise RuntimeError("nope")

    hub = TracingHub()
    rec = _Recorder()
    hub.add(rec)

    c = LyraClient(repo_root=tmp_path, provider_factory=lambda _slug: Boom(), tracing=hub)
    resp = c.chat("p")

    assert resp.error is not None
    assert rec.ends and rec.ends[0].error and "nope" in rec.ends[0].error


# ---------------------------------------------------------------------------
# LangSmithCallback
# ---------------------------------------------------------------------------


class _FakeLSClient:
    """Stand-in for ``langsmith.Client`` recording calls."""

    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []
        self.updated: list[tuple[str, dict[str, Any]]] = []

    def create_run(self, **kwargs: Any) -> dict[str, Any]:
        self.created.append(kwargs)
        rid = f"run-{len(self.created)}"
        return {"id": rid}

    def update_run(self, run_id: str, **kwargs: Any) -> None:
        self.updated.append((run_id, kwargs))


def test_langsmith_callback_records_create_and_update() -> None:
    fake = _FakeLSClient()
    cb = LangSmithCallback(project="proj", api_key="k", client=fake)
    assert cb.enabled is True

    hub = TracingHub()
    hub.add(cb)
    trace = hub.start_turn(session_id="s", model="m", prompt="hi")
    hub.end_turn(trace, text="ok", usage={"input_tokens": 1, "output_tokens": 2})

    assert len(fake.created) == 1
    assert fake.created[0]["project_name"] == "proj"
    assert fake.created[0]["inputs"]["prompt"] == "hi"
    assert len(fake.updated) == 1
    run_id, payload = fake.updated[0]
    assert run_id == "run-1"
    assert payload["outputs"]["text"] == "ok"
    assert payload["error"] is None


def test_langsmith_callback_disabled_without_credentials(monkeypatch) -> None:
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    cb = LangSmithCallback(project="p")
    assert cb.enabled is False
    # Calling the protocol methods must not raise.
    trace = TurnTrace(session_id="s", model="m", prompt="p")
    cb.on_turn_start(trace)
    cb.on_turn_end(trace)


def test_langsmith_callback_swallows_sdk_errors() -> None:
    class BoomClient:
        def create_run(self, **_kw: Any) -> Any:
            raise RuntimeError("ls is down")

        def update_run(self, *_a: Any, **_kw: Any) -> None:
            raise RuntimeError("ls is down")

    cb = LangSmithCallback(api_key="k", client=BoomClient())
    trace = TurnTrace(session_id="s", model="m", prompt="p")
    cb.on_turn_start(trace)
    cb.on_turn_end(trace)


# ---------------------------------------------------------------------------
# LangfuseCallback
# ---------------------------------------------------------------------------


class _FakeLfTrace:
    def __init__(self) -> None:
        self.updates: list[dict[str, Any]] = []

    def update(self, **kwargs: Any) -> None:
        self.updates.append(kwargs)


class _FakeLfClient:
    def __init__(self) -> None:
        self.traces: list[tuple[dict[str, Any], _FakeLfTrace]] = []
        self.flushed = 0

    def trace(self, **kwargs: Any) -> _FakeLfTrace:
        handle = _FakeLfTrace()
        self.traces.append((kwargs, handle))
        return handle

    def flush(self) -> None:
        self.flushed += 1


def test_langfuse_callback_opens_and_updates_trace() -> None:
    fake = _FakeLfClient()
    cb = LangfuseCallback(public_key="pk", secret_key="sk", client=fake)
    assert cb.enabled is True

    hub = TracingHub()
    hub.add(cb)
    trace = hub.start_turn(session_id="s", model="m", prompt="hello")
    hub.end_turn(trace, text="ok", usage={"input_tokens": 3, "output_tokens": 4})

    assert len(fake.traces) == 1
    kwargs, handle = fake.traces[0]
    assert kwargs["session_id"] == "s"
    assert kwargs["input"]["prompt"] == "hello"
    assert handle.updates == [
        {
            "output": {"text": "ok", "usage": {"input_tokens": 3, "output_tokens": 4}},
            "level": "DEFAULT",
            "status_message": None,
            "end_time": trace.ended_at,
        }
    ]
    assert fake.flushed >= 1


def test_langfuse_callback_disabled_without_credentials(monkeypatch) -> None:
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    cb = LangfuseCallback()
    assert cb.enabled is False
    # No-op safe calls.
    trace = TurnTrace(session_id="s", model="m", prompt="p")
    cb.on_turn_start(trace)
    cb.on_turn_end(trace)


def test_langfuse_callback_marks_error_level_on_failure() -> None:
    fake = _FakeLfClient()
    cb = LangfuseCallback(public_key="pk", secret_key="sk", client=fake)

    hub = TracingHub()
    hub.add(cb)
    trace = hub.start_turn(session_id="s", model="m", prompt="hi")
    hub.end_turn(trace, text="", error="boom")

    _, handle = fake.traces[0]
    assert handle.updates[0]["level"] == "ERROR"
    assert handle.updates[0]["status_message"] == "boom"
