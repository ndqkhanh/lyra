"""Tracing protocol + hub.

A :class:`TracingCallback` is anything with ``on_turn_start`` and
``on_turn_end`` methods; the :class:`TracingHub` fans turn events
out to every registered callback and swallows their exceptions so
a broken observer can't break the chat path.

The :class:`TurnTrace` payload is a small JSON-serialisable dict so
HTTP-based tracers (LangSmith, Langfuse) can ship it without an
adapter. Keep new fields *append-only* and document defaults — old
observers must keep parsing newer payloads.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@dataclass
class TurnTrace:
    """Mutable trace context shared across ``on_turn_start`` / ``on_turn_end``.

    Created by the hub at ``start_turn``, threaded through whatever
    layer drove the turn (client, REPL, HTTP server), then handed
    back to ``end_turn`` so observers can correlate the two events
    via ``trace_id``.

    Attributes:
        trace_id: UUID4 hex identifying the turn. Stable across
            ``start``/``end`` and emitted by every callback.
        session_id: Lyra session id (matches ``turns.jsonl``).
        model: Canonical model slug used for the turn.
        prompt: User prompt text (truncated by individual observers
            if their backend has a payload limit — the hub itself
            never trims).
        system_prompt: System prompt forwarded to the provider.
        metadata: Free-form caller metadata (mirrored from
            :class:`ChatRequest`).
        started_at: Wall-clock seconds since epoch when the turn
            started.
        ended_at: Wall-clock seconds when the turn ended; ``None``
            until ``end_turn`` runs.
        text: Assistant reply text (empty on error).
        usage: Provider usage block, ``None`` when unknown.
        error: Diagnostic string when the turn failed.
        latency_ms: Convenience field set by the hub at end time.
    """

    session_id: str
    model: str
    prompt: str
    system_prompt: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    started_at: float = field(default_factory=time.time)
    ended_at: float | None = None
    text: str = ""
    usage: Mapping[str, Any] | None = None
    error: str | None = None
    latency_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Project the trace into a JSON-friendly dict."""
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "model": self.model,
            "prompt": self.prompt,
            "system_prompt": self.system_prompt,
            "metadata": dict(self.metadata or {}),
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "text": self.text,
            "usage": dict(self.usage) if self.usage else None,
            "error": self.error,
            "latency_ms": self.latency_ms,
        }


@runtime_checkable
class TracingCallback(Protocol):
    """Anything that wants to observe a Lyra turn.

    Implementations should be cheap and exception-tolerant — the
    :class:`TracingHub` already swallows raised exceptions, but
    that's a *safety net*, not an excuse. A callback that raises on
    every turn just floods the hub's debug log.
    """

    def on_turn_start(self, trace: TurnTrace) -> None:  # pragma: no cover - protocol
        """Called once before the provider is invoked."""

    def on_turn_end(self, trace: TurnTrace) -> None:  # pragma: no cover - protocol
        """Called once after the provider returns (success or error)."""


class TracingHub:
    """Fan-out registry for :class:`TracingCallback` instances.

    The hub is the only thing :class:`LyraClient` (and N.6's HTTP
    server) talks to: callers register concrete observers
    (``LangSmithCallback``, ``LangfuseCallback``, project-local
    custom shims) and the hub forwards every turn event to all of
    them. Adding/removing callbacks is mutex-free because tracing
    is single-threaded per client.

    The hub also owns the :class:`TurnTrace` lifecycle: ``start_turn``
    builds a fresh trace and dispatches ``on_turn_start``;
    ``end_turn`` stamps the result and dispatches ``on_turn_end``.
    Callers don't construct ``TurnTrace`` themselves so we can add
    fields without breaking the call sites.
    """

    def __init__(self) -> None:
        self._callbacks: list[TracingCallback] = []

    # ---------------- registration ---------------- #

    def add(self, callback: TracingCallback) -> None:
        """Register *callback*. Duplicate adds are no-ops."""
        if not isinstance(callback, TracingCallback):
            # Protocol check is structural — but enforce that the
            # required methods exist anyway so we fail at register
            # time rather than per-turn.
            raise TypeError(
                "tracing callback must implement on_turn_start / on_turn_end"
            )
        if callback in self._callbacks:
            return
        self._callbacks.append(callback)

    def remove(self, callback: TracingCallback) -> None:
        """Drop *callback* if registered; silent on miss."""
        try:
            self._callbacks.remove(callback)
        except ValueError:
            pass

    def __len__(self) -> int:
        return len(self._callbacks)

    @property
    def callbacks(self) -> tuple[TracingCallback, ...]:
        """Snapshot of registered callbacks (read-only)."""
        return tuple(self._callbacks)

    # ---------------- lifecycle ------------------- #

    def start_turn(
        self,
        *,
        session_id: str,
        model: str,
        prompt: str,
        system_prompt: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> TurnTrace:
        """Build a :class:`TurnTrace` and notify all callbacks."""
        trace = TurnTrace(
            session_id=session_id,
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            metadata=dict(metadata or {}),
        )
        for cb in self._callbacks:
            self._safe_call(cb, "on_turn_start", trace)
        return trace

    def end_turn(
        self,
        trace: TurnTrace,
        *,
        text: str,
        usage: Mapping[str, Any] | None = None,
        error: str | None = None,
    ) -> TurnTrace:
        """Stamp the result, set ``latency_ms``, and notify all callbacks.

        Returns the same trace so callers can chain logging.
        """
        trace.text = text
        trace.usage = dict(usage) if usage else None
        trace.error = error
        trace.ended_at = time.time()
        if trace.started_at is not None:
            trace.latency_ms = max(0.0, (trace.ended_at - trace.started_at) * 1000.0)
        for cb in self._callbacks:
            self._safe_call(cb, "on_turn_end", trace)
        return trace

    # ---------------- internals ------------------- #

    def _safe_call(self, cb: TracingCallback, method: str, trace: TurnTrace) -> None:
        """Invoke *method* on *cb*, swallowing any exception.

        We log the failure at debug level so a developer running with
        ``LYRA_LOG=DEBUG`` can see which observer is misbehaving
        without leaking the noise into a production session.
        """
        fn = getattr(cb, method, None)
        if fn is None:
            return
        try:
            fn(trace)
        except Exception:  # noqa: BLE001 — observer must never crash a turn
            logger.debug("tracing callback %s.%s raised", cb, method, exc_info=True)


__all__ = ["TracingCallback", "TracingHub", "TurnTrace"]
