"""Auto-capture: bind LifecycleBus events to memory writes.

agentmemory captures every UserPromptSubmit / PreToolUse / PostToolUse
turn through 12 hooks. Lyra has the equivalent in
:class:`~lyra_core.hooks.lifecycle.LifecycleBus` (7 typed events). This
module wires the bus into :class:`~lyra_core.memory.memory_tools.MemoryToolset`
so the agent doesn't have to remember to remember.

Design choices:

* **Policy is configurable.** Auto-writes are noisy if everything
  qualifies. Each subscriber takes a small ``CapturePolicy`` that
  decides what to keep. Defaults are conservative: only capture
  failed tool calls (as ``feedback``) and session ends with a
  summary (as ``project``).
* **Writes route through MemoryToolset.remember.** That guarantees
  the redactor + HIR audit emit fire on every captured row.
* **Subscribers self-detach on toolset destroy.** The
  :meth:`MemoryAutoCapture.unbind` method removes every subscription
  it registered so tests + multi-session REPLs can roll up cleanly.

Bright-line: ``LBL-MEMORY-AUTO-CAPTURE`` — every auto-captured row
records its source ``LifecycleEvent`` in ``MemoryEntry.extra`` so
audit can distinguish agent-driven from user-driven writes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..hooks.lifecycle import LifecycleBus, LifecycleEvent
from .auto_memory import MemoryKind
from .memory_tools import MemoryToolset


# A predicate that decides whether to capture a given lifecycle payload.
# Returning ``None`` means "skip"; returning a ``CaptureDirective`` means
# "write this entry".
CaptureFilter = Callable[[dict[str, Any]], Optional["CaptureDirective"]]


@dataclass(frozen=True)
class CaptureDirective:
    """Output of a :data:`CaptureFilter` — describes one write."""

    kind: MemoryKind
    title: str
    body: str
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class CapturePolicy:
    """Per-event capture policy — three filters, each optional.

    Defaults shipped here are conservative; tune per-deployment.
    """

    on_tool_call: Optional[CaptureFilter] = None
    on_turn_complete: Optional[CaptureFilter] = None
    on_session_end: Optional[CaptureFilter] = None


def _default_tool_call_filter(payload: dict[str, Any]) -> Optional[CaptureDirective]:
    """Default policy: capture failed tool calls as `feedback` entries.

    Successful calls are skipped — the procedural memory + reasoning
    bank already absorb success patterns through the distillation path.
    Failures are the high-signal events: the agent's "what went wrong"
    record should land somewhere durable.
    """
    result = payload.get("result")
    if not isinstance(result, dict):
        return None
    # Lyra's tool result shape carries `error` / `is_error` flags.
    if not (result.get("is_error") or result.get("error")):
        return None
    tool = str(payload.get("tool", "tool"))
    args_preview = repr(payload.get("args", {}))[:200]
    err = result.get("error") or "tool returned is_error=True"
    return CaptureDirective(
        kind=MemoryKind.FEEDBACK,
        title=f"tool failed: {tool}",
        body=f"args={args_preview}\nerror={err}",
        extra={"source_event": "tool_call"},
    )


def _default_session_end_filter(payload: dict[str, Any]) -> Optional[CaptureDirective]:
    """Default policy: capture a one-line session summary as `project`.

    Only fires when the host harness has populated a ``summary`` field
    on the session_end payload — we don't synthesise summaries here
    (that's the host's call).
    """
    summary = payload.get("summary")
    if not summary or not isinstance(summary, str):
        return None
    return CaptureDirective(
        kind=MemoryKind.PROJECT,
        title=f"session: {payload.get('session_id', 'unknown')}",
        body=str(summary),
        extra={"source_event": "session_end"},
    )


@dataclass
class MemoryAutoCapture:
    """Bind a :class:`MemoryToolset` to a :class:`LifecycleBus`.

    Construction subscribes the toolset to the configured events;
    :meth:`unbind` removes the subscriptions. Calling
    :meth:`bind` twice is idempotent — the same subscriber object is
    deduped by the bus.
    """

    toolset: MemoryToolset
    bus: LifecycleBus
    policy: CapturePolicy = field(default_factory=CapturePolicy)

    captured_count: int = field(default=0, init=False)
    _bound: bool = field(default=False, init=False)
    _handlers: list[tuple[LifecycleEvent, Callable[[dict[str, Any]], None]]] = \
        field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        # Default to the conservative policy if the caller passed an
        # empty CapturePolicy. Explicit None on the policy slots stays
        # None so callers can opt out of any single event.
        if self.policy.on_tool_call is None and \
           self.policy.on_turn_complete is None and \
           self.policy.on_session_end is None:
            self.policy = CapturePolicy(
                on_tool_call=_default_tool_call_filter,
                on_session_end=_default_session_end_filter,
            )

    def bind(self) -> "MemoryAutoCapture":
        """Subscribe to the bus. Idempotent."""
        if self._bound:
            return self
        if self.policy.on_tool_call is not None:
            handler = self._make_handler(self.policy.on_tool_call)
            self.bus.subscribe(LifecycleEvent.TOOL_CALL, handler)
            self._handlers.append((LifecycleEvent.TOOL_CALL, handler))
        if self.policy.on_turn_complete is not None:
            handler = self._make_handler(self.policy.on_turn_complete)
            self.bus.subscribe(LifecycleEvent.TURN_COMPLETE, handler)
            self._handlers.append((LifecycleEvent.TURN_COMPLETE, handler))
        if self.policy.on_session_end is not None:
            handler = self._make_handler(self.policy.on_session_end)
            self.bus.subscribe(LifecycleEvent.SESSION_END, handler)
            self._handlers.append((LifecycleEvent.SESSION_END, handler))
        self._bound = True
        return self

    def unbind(self) -> None:
        for event, handler in self._handlers:
            self.bus.unsubscribe(event, handler)
        self._handlers.clear()
        self._bound = False

    def _make_handler(
        self, capture_filter: CaptureFilter,
    ) -> Callable[[dict[str, Any]], None]:
        def handler(payload: dict[str, Any]) -> None:
            directive = capture_filter(payload)
            if directive is None:
                return
            extra = dict(directive.extra)
            extra.setdefault("bright_line", "LBL-MEMORY-AUTO-CAPTURE")
            self.toolset.remember(
                directive.body,
                scope="auto",
                kind=directive.kind,
                title=directive.title,
                extra=extra,
            )
            self.captured_count += 1
        return handler


__all__ = [
    "CaptureDirective",
    "CaptureFilter",
    "CapturePolicy",
    "MemoryAutoCapture",
]
