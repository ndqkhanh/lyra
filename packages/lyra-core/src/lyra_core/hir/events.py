"""Fire-and-forget HIR event hub.

Provides a single module-level callable :func:`emit` that fans out to
zero-or-more registered subscribers. Subscribers receive the event
``name`` plus arbitrary keyword attributes; they MUST be cheap and
non-throwing (any exception is swallowed so a misbehaving subscriber
cannot break the LLM factory cascade).

Tests typically patch :data:`emit` directly via ``monkeypatch.setattr``
to capture events; production code registers subscribers via
:func:`subscribe`.

v1.7.5 (Wave-C Task 4) adds :class:`RingBuffer` — a drop-oldest in-memory
sink that auto-attaches at construction time and powers the new
``/trace`` slash without bolting REPL state onto the global hub.
"""
from __future__ import annotations

from collections import deque
from threading import RLock
from typing import Any, Callable, Deque, Dict, List


Subscriber = Callable[..., None]
_subscribers: List[Subscriber] = []


def subscribe(fn: Subscriber) -> None:
    """Register a subscriber. Subscribers are called in registration order."""
    if fn not in _subscribers:
        _subscribers.append(fn)


def unsubscribe(fn: Subscriber) -> None:
    """Remove a previously-registered subscriber."""
    try:
        _subscribers.remove(fn)
    except ValueError:
        pass


def clear_subscribers() -> None:
    """Remove all subscribers. Test-only helper."""
    _subscribers.clear()


def emit(name: str, /, **attrs: Any) -> None:
    """Broadcast an event to every subscriber. Best-effort, never raises.

    The event ``name`` is *positional-only* so callers can pass an
    attribute also called ``name`` (e.g.
    ``emit("provider.selected", name="anthropic")``) without collision.
    """
    for fn in tuple(_subscribers):
        try:
            fn(name, **attrs)
        except Exception:
            # Telemetry must never break the caller's cascade.
            pass


class RingBuffer:
    """Bounded, drop-oldest in-memory event sink.

    Constructing one auto-subscribes it to the module's :func:`emit`
    hub; calling :meth:`detach` cleanly unsubscribes (tests should
    always do this in a ``try / finally`` to avoid leaks across the
    suite). :meth:`snapshot` returns a list of ``{"name", "attrs"}``
    dicts in arrival order — newest last.

    Thread-safety: a single :class:`RLock` guards the deque so a
    background tracer can :meth:`snapshot` while a foreground emitter
    is appending.
    """

    def __init__(self, cap: int = 1024) -> None:
        if cap <= 0:
            raise ValueError("RingBuffer cap must be > 0")
        self._buf: Deque[Dict[str, Any]] = deque(maxlen=cap)
        self._lock = RLock()
        self._attached = True
        subscribe(self._on_event)

    def _on_event(self, name: str, /, **attrs: Any) -> None:
        with self._lock:
            self._buf.append({"name": name, "attrs": dict(attrs)})

    def snapshot(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._buf)

    def clear(self) -> None:
        with self._lock:
            self._buf.clear()

    def detach(self) -> None:
        """Stop receiving events. Idempotent."""
        if self._attached:
            unsubscribe(self._on_event)
            self._attached = False


# Global, eagerly-installed ring used by ``/trace`` so any code path
# that emits an HIR event (factory cascade, plugin runtime, …) is
# observable without touching call sites — even events fired before
# the user runs the slash for the first time.
_GLOBAL_RING: "RingBuffer | None" = None


def global_ring() -> RingBuffer:
    """Return the process-wide RingBuffer (installed at import)."""
    global _GLOBAL_RING
    if _GLOBAL_RING is None:
        _GLOBAL_RING = RingBuffer(cap=1024)
    return _GLOBAL_RING


def reset_global_ring(*, cap: int = 1024) -> RingBuffer:
    """Replace the global ring (test-only helper)."""
    global _GLOBAL_RING
    if _GLOBAL_RING is not None:
        _GLOBAL_RING.detach()
    _GLOBAL_RING = RingBuffer(cap=cap)
    return _GLOBAL_RING


# Install the global ring at module import so the very first ``emit``
# in the process is captured. The cost is one tiny deque + one
# subscriber registration — both are O(1).
global_ring()


__all__ = [
    "emit",
    "subscribe",
    "unsubscribe",
    "clear_subscribers",
    "Subscriber",
    "RingBuffer",
    "global_ring",
    "reset_global_ring",
]
