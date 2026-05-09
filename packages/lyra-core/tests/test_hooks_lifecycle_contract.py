"""Wave-D Task 11: full hooks lifecycle (``SessionStart`` … ``TurnRejected``).

The :class:`LifecycleBus` is the connective tissue between the agent
loop, the slash dispatcher, and external observers (HIR, telemetry,
CI hooks). Subscribers register against an :class:`LifecycleEvent`
name; the bus broadcasts every emitted event to all subscribers.

Six lifecycle events ship in v1.8:

* ``session_start`` — first user input received.
* ``turn_start`` — before the LLM call.
* ``turn_complete`` — LLM returned, tool calls (if any) executed.
* ``turn_rejected`` — a guard / hook blocked the turn before it
  produced output.
* ``tool_call`` — fired *after* a tool call returns.
* ``session_end`` — REPL is shutting down (or ``/exit``).

Six RED tests:

1. The bus has the documented event registry.
2. ``subscribe`` then ``emit`` calls the subscriber with the payload.
3. Multiple subscribers all fire for the same event.
4. A subscriber raising never breaks downstream subscribers.
5. ``unsubscribe`` removes a subscriber cleanly.
6. ``LifecycleEvent.TURN_REJECTED`` is emitted with a ``reason`` field.
"""
from __future__ import annotations

import pytest


def test_lifecycle_event_names() -> None:
    from lyra_core.hooks.lifecycle import LifecycleEvent

    names = {e.value for e in LifecycleEvent}
    assert {
        "session_start",
        "turn_start",
        "turn_complete",
        "turn_rejected",
        "tool_call",
        "session_end",
    } <= names


def test_subscribe_then_emit_fires() -> None:
    from lyra_core.hooks.lifecycle import LifecycleBus, LifecycleEvent

    bus = LifecycleBus()
    seen: list[dict] = []
    bus.subscribe(LifecycleEvent.SESSION_START, lambda payload: seen.append(payload))
    bus.emit(LifecycleEvent.SESSION_START, {"session_id": "s1"})
    assert seen == [{"session_id": "s1"}]


def test_multiple_subscribers_all_fire() -> None:
    from lyra_core.hooks.lifecycle import LifecycleBus, LifecycleEvent

    bus = LifecycleBus()
    a: list[int] = []
    b: list[int] = []
    bus.subscribe(LifecycleEvent.TURN_START, lambda p: a.append(p["n"]))
    bus.subscribe(LifecycleEvent.TURN_START, lambda p: b.append(p["n"]))
    bus.emit(LifecycleEvent.TURN_START, {"n": 1})
    bus.emit(LifecycleEvent.TURN_START, {"n": 2})
    assert a == [1, 2]
    assert b == [1, 2]


def test_subscriber_raising_does_not_break_others() -> None:
    from lyra_core.hooks.lifecycle import LifecycleBus, LifecycleEvent

    bus = LifecycleBus()
    seen: list[str] = []

    def boom(_: dict) -> None:
        raise RuntimeError("subscriber blew up")

    def ok(payload: dict) -> None:
        seen.append(payload["v"])

    bus.subscribe(LifecycleEvent.TOOL_CALL, boom)
    bus.subscribe(LifecycleEvent.TOOL_CALL, ok)
    bus.emit(LifecycleEvent.TOOL_CALL, {"v": "still-fires"})
    assert seen == ["still-fires"]


def test_unsubscribe_removes_subscriber() -> None:
    from lyra_core.hooks.lifecycle import LifecycleBus, LifecycleEvent

    bus = LifecycleBus()
    seen: list[int] = []

    def listener(payload: dict) -> None:
        seen.append(payload["n"])

    bus.subscribe(LifecycleEvent.TURN_COMPLETE, listener)
    bus.emit(LifecycleEvent.TURN_COMPLETE, {"n": 1})
    bus.unsubscribe(LifecycleEvent.TURN_COMPLETE, listener)
    bus.emit(LifecycleEvent.TURN_COMPLETE, {"n": 2})
    assert seen == [1]


def test_turn_rejected_carries_reason() -> None:
    from lyra_core.hooks.lifecycle import LifecycleBus, LifecycleEvent

    bus = LifecycleBus()
    seen: list[dict] = []
    bus.subscribe(LifecycleEvent.TURN_REJECTED, lambda p: seen.append(p))
    bus.emit(LifecycleEvent.TURN_REJECTED, {"reason": "secrets-scan: AWS key"})
    assert seen == [{"reason": "secrets-scan: AWS key"}]


def test_skills_activated_event_is_registered() -> None:
    """v3.5 (Phase O.2): the bus knows about ``skills_activated``.

    Plugins and observability collectors subscribe to this event by
    name to learn which progressive skills the model is about to
    receive. The enum value is stable contract surface — renaming
    the string would silently break every subscriber.
    """
    from lyra_core.hooks.lifecycle import LifecycleEvent

    assert LifecycleEvent.SKILLS_ACTIVATED.value == "skills_activated"


def test_skills_activated_carries_activated_skills() -> None:
    """The payload uses ``activated_skills`` as a list of dicts.

    Each entry has at minimum ``skill_id`` (str). ``reason`` (str) is
    optional but documents *why* the skill was activated (e.g.
    ``"keyword:tdd"`` or ``"forced"``).
    """
    from lyra_core.hooks.lifecycle import LifecycleBus, LifecycleEvent

    bus = LifecycleBus()
    seen: list[dict] = []
    bus.subscribe(LifecycleEvent.SKILLS_ACTIVATED, lambda p: seen.append(p))
    bus.emit(
        LifecycleEvent.SKILLS_ACTIVATED,
        {
            "session_id": "s1",
            "turn": 3,
            "activated_skills": [
                {"skill_id": "tdd-guide", "reason": "keyword:test"},
                {"skill_id": "code-reviewer", "reason": "forced"},
            ],
        },
    )
    assert len(seen) == 1
    payload = seen[0]
    assert payload["session_id"] == "s1"
    assert payload["turn"] == 3
    skills = payload["activated_skills"]
    assert len(skills) == 2
    assert skills[0]["skill_id"] == "tdd-guide"
    assert skills[1]["reason"] == "forced"
