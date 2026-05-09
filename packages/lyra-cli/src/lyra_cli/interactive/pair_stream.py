"""Wave-D Task 15: live-streaming substrate for ``/pair``.

Wave-C shipped the ``/pair`` flag; this is the substrate that
actually surfaces the agent's heartbeat in a paired terminal.

The stream subscribes to every :class:`LifecycleEvent` and pushes a
single line per event into a sink (typically ``console.print`` in
the REPL, or ``list.append`` in tests). ``set_enabled(False)``
mutes the sink without losing the subscriptions — handy when the
user toggles ``/pair off`` mid-session.

Why a sink callable instead of a hard-coded ``print``? The REPL's
prompt-toolkit application owns the terminal; trying to ``print``
into it from a background subscriber would corrupt the prompt
state. The driver wires the sink to a thread-safe ``console.print``
that knows how to redraw the prompt afterwards.
"""
from __future__ import annotations

from typing import Callable, Dict

from lyra_core.hooks.lifecycle import LifecycleBus, LifecycleEvent


Sink = Callable[[str], None]


def _format(event: LifecycleEvent, payload: Dict) -> str:
    """Render one lifecycle event as a single user-visible line.

    Keep it boring on purpose — paired terminals are a "watch the
    agent think" view, not an analytics dashboard. The format is
    ``[event_name] key=value …`` so it greps cleanly when piped to
    a log file.
    """
    parts = []
    for key, value in payload.items():
        if isinstance(value, dict):
            value = ",".join(f"{k}={v}" for k, v in value.items())
        parts.append(f"{key}={value}")
    summary = " ".join(parts) if parts else ""
    if event == LifecycleEvent.TOOL_CALL:
        tool = payload.get("tool", "?")
        return f"[tool_call] {tool} {summary}".rstrip()
    return f"[{event.value}] {summary}".rstrip()


class PairStream:
    """Pipe every :class:`LifecycleEvent` into a sink while attached."""

    def __init__(self, *, sink: Sink, bus: LifecycleBus) -> None:
        self._sink = sink
        self._bus = bus
        self._enabled = True
        self._attached = False
        self._subs: list[tuple[LifecycleEvent, Callable[[Dict], None]]] = []

    # ---- lifecycle ---------------------------------------------------

    def attach(self) -> None:
        if self._attached:
            return
        for event in LifecycleEvent:
            handler = self._make_handler(event)
            self._bus.subscribe(event, handler)
            self._subs.append((event, handler))
        self._attached = True

    def detach(self) -> None:
        for event, handler in self._subs:
            self._bus.unsubscribe(event, handler)
        self._subs.clear()
        self._attached = False

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def attached(self) -> bool:
        return self._attached

    # ---- internals ---------------------------------------------------

    def _make_handler(
        self, event: LifecycleEvent
    ) -> Callable[[Dict], None]:
        def _handle(payload: Dict) -> None:
            if not self._enabled:
                return
            try:
                line = _format(event, payload or {})
                self._sink(line)
            except Exception:
                # Telemetry must never break the caller's cascade.
                return

        return _handle


__all__ = ["PairStream", "Sink"]
