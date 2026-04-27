"""Phase D.3/D.4 — LifecycleBus emission + plugin wiring.

These tests exercise the new lifecycle plumbing introduced in
v2.6.0:

* :func:`session._chat_with_llm` emits ``session_start``,
  ``turn_start``, ``turn_complete``, and ``turn_rejected`` at the
  expected moments.
* :func:`session._chat_with_tool_loop` emits ``tool_call`` after
  every tool result.
* :func:`driver._wire_plugins_to_lifecycle` walks plugins discovered
  via ``discover_plugins`` and subscribes their hooks to the bus.

The tests work with a scripted in-process LLM so no network is
involved. The chat-tools loop is *disabled* on most tests via
``session.chat_tools_enabled = False`` so the assertions stay
deterministic — the loop branch is exercised separately in
``test_chat_tool_loop.py``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from harness_core.messages import Message
from lyra_cli.interactive.driver import _wire_plugins_to_lifecycle
from lyra_cli.interactive.session import (
    InteractiveSession,
    _chat_with_llm,
    _ensure_lifecycle_bus,
    _emit_lifecycle,
)


class CannedLLM:
    """Minimal LLMProvider stub returning a fixed reply."""

    def __init__(self, *, reply: str = "ok", usage: dict[str, int] | None = None) -> None:
        self._reply = reply
        self.last_usage = usage or {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
        self.model = "stub-model"
        self.provider_name = "stub"

    def generate(
        self,
        messages: list[Any],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> Message:
        return Message.assistant(content=self._reply)


@pytest.fixture
def session(tmp_path: Path) -> InteractiveSession:
    s = InteractiveSession(repo_root=tmp_path, model="stub", mode="agent")
    # Disable the chat-tool loop so we exercise the simple generate
    # branch — the tool-loop branch has its own coverage in
    # ``test_chat_tool_loop.py`` and emits tool_call separately.
    s.chat_tools_enabled = False
    s._streaming_enabled = False
    return s


@pytest.fixture
def captured_events() -> dict[str, list[dict[str, Any]]]:
    """Empty buckets the tests fill in via the sub-helpers below."""
    return {
        "session_start": [],
        "turn_start": [],
        "turn_complete": [],
        "turn_rejected": [],
        "tool_call": [],
        "session_end": [],
    }


def _attach_listener(session: InteractiveSession, captured: dict[str, list[dict[str, Any]]]) -> None:
    """Subscribe one capture-fn per event onto the session bus."""
    from lyra_core.hooks.lifecycle import LifecycleEvent

    bus = _ensure_lifecycle_bus(session)
    assert bus is not None

    for ev in LifecycleEvent:
        def _make(name: str):
            def _sub(payload: dict[str, Any]) -> None:
                captured[name].append(dict(payload))
            return _sub
        bus.subscribe(ev, _make(ev.value))


def test_chat_emits_turn_start_and_turn_complete(
    session: InteractiveSession,
    captured_events: dict[str, list[dict[str, Any]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _attach_listener(session, captured_events)
    monkeypatch.setattr(
        "lyra_cli.interactive.session._ensure_llm",
        lambda _s: CannedLLM(reply="hi"),
    )

    ok, text = _chat_with_llm(session, "hello", system_prompt="be helpful")

    assert ok is True
    assert text == "hi"
    assert len(captured_events["session_start"]) == 1
    assert captured_events["session_start"][0]["model"] == session.model
    assert len(captured_events["turn_start"]) == 1
    assert captured_events["turn_start"][0]["input"] == "hello"
    assert len(captured_events["turn_complete"]) == 1
    assert captured_events["turn_complete"][0]["branch"] == "generate"
    assert captured_events["turn_complete"][0]["output_chars"] == 2


def test_chat_session_start_emitted_only_once(
    session: InteractiveSession,
    captured_events: dict[str, list[dict[str, Any]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _attach_listener(session, captured_events)
    monkeypatch.setattr(
        "lyra_cli.interactive.session._ensure_llm",
        lambda _s: CannedLLM(reply="hi"),
    )

    _chat_with_llm(session, "first", system_prompt="be helpful")
    _chat_with_llm(session, "second", system_prompt="be helpful")

    assert len(captured_events["session_start"]) == 1
    assert len(captured_events["turn_start"]) == 2
    assert len(captured_events["turn_complete"]) == 2


def test_chat_emits_turn_rejected_on_provider_failure(
    session: InteractiveSession,
    captured_events: dict[str, list[dict[str, Any]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _attach_listener(session, captured_events)

    def _boom(_s: InteractiveSession) -> Any:
        raise RuntimeError("no provider configured")

    monkeypatch.setattr(
        "lyra_cli.interactive.session._ensure_llm",
        _boom,
    )

    ok, msg = _chat_with_llm(session, "hello", system_prompt="be helpful")

    assert ok is False
    assert "no provider" in msg
    assert len(captured_events["turn_rejected"]) == 1
    assert captured_events["turn_rejected"][0]["reason"] == "provider_init_failed"
    assert captured_events["turn_complete"] == []


def test_chat_emits_turn_rejected_on_empty_response(
    session: InteractiveSession,
    captured_events: dict[str, list[dict[str, Any]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _attach_listener(session, captured_events)

    monkeypatch.setattr(
        "lyra_cli.interactive.session._ensure_llm",
        lambda _s: CannedLLM(reply="   "),
    )

    ok, msg = _chat_with_llm(session, "hi", system_prompt="be helpful")

    assert ok is False
    assert "empty response" in msg
    assert len(captured_events["turn_rejected"]) == 1
    assert captured_events["turn_rejected"][0]["reason"] == "empty_response"


def test_emit_lifecycle_no_op_when_event_unknown(session: InteractiveSession) -> None:
    """An unknown event name should be silently dropped, not raise."""
    captured: list[Any] = []
    bus = _ensure_lifecycle_bus(session)
    assert bus is not None

    from lyra_core.hooks.lifecycle import LifecycleEvent

    bus.subscribe(LifecycleEvent.TURN_START, lambda p: captured.append(p))

    _emit_lifecycle(session, "no_such_event_xyz", {"data": 1})
    assert captured == []


def test_emit_lifecycle_swallows_subscriber_errors(session: InteractiveSession) -> None:
    """A bad subscriber must not break the emit cascade."""
    bus = _ensure_lifecycle_bus(session)
    assert bus is not None

    from lyra_core.hooks.lifecycle import LifecycleEvent

    seen: list[dict[str, Any]] = []

    def _good(payload: dict[str, Any]) -> None:
        seen.append(payload)

    def _bad(_payload: dict[str, Any]) -> None:
        raise RuntimeError("hostile plugin")

    bus.subscribe(LifecycleEvent.TURN_START, _bad)
    bus.subscribe(LifecycleEvent.TURN_START, _good)

    _emit_lifecycle(session, "turn_start", {"x": 1})
    assert seen == [{"x": 1}]


# ---------------------------------------------------------------------------
# Plugin wiring — Phase D.4
# ---------------------------------------------------------------------------


class _PluginAllHooks:
    """Plugin that captures every named lifecycle hook."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def on_session_start(self, payload: dict[str, Any]) -> None:
        self.events.append(("session_start", dict(payload)))

    def on_turn_start(self, payload: dict[str, Any]) -> None:
        self.events.append(("turn_start", dict(payload)))

    def on_turn_complete(self, payload: dict[str, Any]) -> None:
        self.events.append(("turn_complete", dict(payload)))

    def on_turn_rejected(self, payload: dict[str, Any]) -> None:
        self.events.append(("turn_rejected", dict(payload)))

    def on_tool_call(self, payload: dict[str, Any]) -> None:
        self.events.append(("tool_call", dict(payload)))

    def on_session_end(self, payload: dict[str, Any]) -> None:
        self.events.append(("session_end", dict(payload)))


class _PluginUniversalSink:
    """Plugin that uses the universal ``on_lifecycle_event`` hook."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def on_lifecycle_event(self, event_name: str, payload: dict[str, Any]) -> None:
        self.events.append((event_name, dict(payload)))


class _PluginNoHooks:
    """A plugin with no hook methods is silently ignored."""


def test_wire_plugins_routes_events_to_named_hooks(
    session: InteractiveSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin = _PluginAllHooks()
    monkeypatch.setattr(
        "lyra_core.plugins.discover_plugins",
        lambda *, extra=None: [plugin] + list(extra or []),
    )

    _wire_plugins_to_lifecycle(session)
    monkeypatch.setattr(
        "lyra_cli.interactive.session._ensure_llm",
        lambda _s: CannedLLM(reply="hi"),
    )

    _chat_with_llm(session, "hello", system_prompt="be helpful")

    captured_names = [name for name, _ in plugin.events]
    assert "session_start" in captured_names
    assert "turn_start" in captured_names
    assert "turn_complete" in captured_names


def test_wire_plugins_routes_to_universal_sink(
    session: InteractiveSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin = _PluginUniversalSink()
    monkeypatch.setattr(
        "lyra_core.plugins.discover_plugins",
        lambda *, extra=None: [plugin] + list(extra or []),
    )

    _wire_plugins_to_lifecycle(session)
    monkeypatch.setattr(
        "lyra_cli.interactive.session._ensure_llm",
        lambda _s: CannedLLM(reply="hi"),
    )

    _chat_with_llm(session, "hello", system_prompt="be helpful")

    names = [n for n, _ in plugin.events]
    assert names.count("turn_start") == 1
    assert names.count("turn_complete") == 1


def test_wire_plugins_skips_plugins_without_hooks(
    session: InteractiveSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plugin = _PluginNoHooks()
    monkeypatch.setattr(
        "lyra_core.plugins.discover_plugins",
        lambda *, extra=None: [plugin] + list(extra or []),
    )

    _wire_plugins_to_lifecycle(session)
    monkeypatch.setattr(
        "lyra_cli.interactive.session._ensure_llm",
        lambda _s: CannedLLM(reply="hi"),
    )

    ok, _ = _chat_with_llm(session, "hello", system_prompt="be helpful")
    assert ok is True


def test_wire_plugins_isolates_buggy_subscriber(
    session: InteractiveSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Hostile:
        def on_turn_start(self, _payload: dict[str, Any]) -> None:
            raise RuntimeError("plugin exploded")

    good = _PluginAllHooks()
    monkeypatch.setattr(
        "lyra_core.plugins.discover_plugins",
        lambda *, extra=None: [_Hostile(), good],
    )

    _wire_plugins_to_lifecycle(session)
    monkeypatch.setattr(
        "lyra_cli.interactive.session._ensure_llm",
        lambda _s: CannedLLM(reply="hi"),
    )

    ok, text = _chat_with_llm(session, "hello", system_prompt="be helpful")

    assert ok is True
    assert text == "hi"
    assert any(name == "turn_start" for name, _ in good.events)
