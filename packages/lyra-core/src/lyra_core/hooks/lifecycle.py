"""Wave-D Task 11: full lifecycle event bus.

Seven events span the agent loop's user-visible touch points:

* ``session_start`` — first user input received in this REPL run.
* ``turn_start`` — about to call the LLM for the next round.
* ``skills_activated`` — Phase O.2 (v3.5): one or more progressive
  skills were activated for the upcoming turn. Payload carries the
  per-turn ``activated_skills`` list (each entry has ``skill_id``
  and ``reason``) plus ``session_id`` and ``turn``. Fires *after*
  ``turn_start`` and *before* the LLM call so observers see what
  knowledge the model is about to receive.
* ``turn_complete`` — the LLM call returned and tool calls (if any)
  were dispatched.
* ``turn_rejected`` — a guard, plugin, or hook stopped the turn
  before it produced output. Payload carries ``reason``.
* ``tool_call`` — a tool just returned (success or error). Payload
  carries ``tool``, ``args``, ``result``.
* ``session_end`` — user typed ``/exit`` or the REPL is shutting
  down.

Why a typed Enum instead of free-form strings? So a third-party
plugin (or unit test) can ``from lyra_core.hooks.lifecycle import
LifecycleEvent`` and tab-complete the names instead of guessing.
A misspelled string would silently never fire.

The bus is best-effort: a subscriber that raises is logged once and
demoted from the broadcast for that emit, but every other
subscriber still receives the event. Telemetry must never break the
caller's cascade.
"""
from __future__ import annotations

import enum
from collections import defaultdict
from typing import Any, Callable, Dict, List


class LifecycleEvent(str, enum.Enum):
    """Names every agent-loop seam emits."""

    SESSION_START = "session_start"
    TURN_START = "turn_start"
    SKILLS_ACTIVATED = "skills_activated"
    TURN_COMPLETE = "turn_complete"
    TURN_REJECTED = "turn_rejected"
    TOOL_CALL = "tool_call"
    SESSION_END = "session_end"


Subscriber = Callable[[Dict[str, Any]], None]


class LifecycleBus:
    """Per-process pub/sub for :class:`LifecycleEvent` notifications."""

    def __init__(self) -> None:
        self._subs: Dict[LifecycleEvent, List[Subscriber]] = defaultdict(list)

    # ---- subscription -----------------------------------------------

    def subscribe(self, event: LifecycleEvent, subscriber: Subscriber) -> None:
        if subscriber not in self._subs[event]:
            self._subs[event].append(subscriber)

    def unsubscribe(self, event: LifecycleEvent, subscriber: Subscriber) -> None:
        try:
            self._subs[event].remove(subscriber)
        except ValueError:
            pass

    def clear(self) -> None:
        self._subs.clear()

    # ---- emission ----------------------------------------------------

    def emit(self, event: LifecycleEvent, payload: Dict[str, Any] | None = None) -> None:
        """Best-effort broadcast; subscriber errors are swallowed.

        We snapshot the subscriber list before iterating so a
        subscriber that calls :meth:`unsubscribe` mid-broadcast can't
        race the iteration.
        """
        payload = payload or {}
        for sub in tuple(self._subs.get(event, ())):
            try:
                sub(payload)
            except Exception:
                # Telemetry must never break the caller's cascade —
                # swallow + continue is the standard contract.
                continue


__all__ = ["LifecycleBus", "LifecycleEvent", "Subscriber"]
