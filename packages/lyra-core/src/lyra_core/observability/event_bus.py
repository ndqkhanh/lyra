"""Unified EventBus for Lyra process transparency (Phase 1).

Every background process, agent call, LLM request, tool invocation, cron
routine, subagent worker, and async task emits a typed event here.  Nothing
runs silently.

Architecture:
  - ``emit(event)`` is always synchronous and non-blocking.  It never raises
    even if a subscriber fails (best-effort delivery, same contract as
    ``LifecycleBus``).
  - Sync listeners (``add_listener``) are called inline on ``emit``.  Use
    these for low-latency writers such as ``ProcessStateWriter``.
  - Async queues (``subscribe``/``unsubscribe``) receive events via
    ``asyncio.Queue.put_nowait`` for live display consumers (Rich ``Live()``,
    harness-tui transport).
  - A global singleton is available via ``get_event_bus()``.

Research grounding: LangChain ``CallbackManager`` (run_id + parent_run_id
correlation), Claude Code 12 hook types, OpenAI Responses API SSE per-step
usage reporting, ``disler/claude-code-hooks-multi-agent-observability``.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Typed event dataclasses
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


@dataclass(frozen=True)
class LLMCallStarted:
    session_id: str
    model: str
    prompt_tokens: int
    turn: int
    ts: str = field(default_factory=_now)


@dataclass(frozen=True)
class LLMTokenChunk:
    session_id: str
    delta_text: str
    cumulative_tokens: int
    turn: int
    ts: str = field(default_factory=_now)


@dataclass(frozen=True)
class LLMCallFinished:
    session_id: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    duration_ms: float
    model: str = ""
    turn: int = 0
    ts: str = field(default_factory=_now)


@dataclass(frozen=True)
class ToolCallStarted:
    session_id: str
    tool_name: str
    args_preview: str  # first 80 chars of JSON-serialised args
    span_id: str = ""
    ts: str = field(default_factory=_now)


@dataclass(frozen=True)
class ToolCallFinished:
    session_id: str
    tool_name: str
    duration_ms: float
    is_error: bool
    span_id: str = ""
    ts: str = field(default_factory=_now)


@dataclass(frozen=True)
class ToolCallBlocked:
    session_id: str
    tool_name: str
    reason: str
    hook_name: str = ""
    ts: str = field(default_factory=_now)


@dataclass(frozen=True)
class SubagentSpawned:
    session_id: str
    agent_id: str
    agent_role: str
    worktree: str = ""
    parent_agent_id: str = ""
    ts: str = field(default_factory=_now)


@dataclass(frozen=True)
class SubagentFinished:
    session_id: str
    agent_id: str
    status: str       # "done" | "failed" | "killed"
    duration_ms: float = 0.0
    cost_usd: float = 0.0
    ts: str = field(default_factory=_now)


@dataclass(frozen=True)
class StopHookFired:
    session_id: str
    reason: str
    extensions_used: int = 0
    ts: str = field(default_factory=_now)


@dataclass(frozen=True)
class PermissionDecision:
    session_id: str
    tool_name: str
    decision: str   # "ALLOWED" | "BLOCKED" | "ASK" | "ANNOTATED"
    mode: str = ""
    hook_name: str = ""
    ts: str = field(default_factory=_now)


@dataclass(frozen=True)
class CostThreshold:
    session_id: str
    cost_usd: float
    budget_usd: float
    pct_consumed: float
    ts: str = field(default_factory=_now)


@dataclass(frozen=True)
class CronJobFired:
    job_name: str
    next_fire_at: str = ""
    last_duration_ms: float = 0.0
    ts: str = field(default_factory=_now)


@dataclass(frozen=True)
class DaemonIteration:
    iteration: int
    budget_remaining_usd: float = 0.0
    wall_clock_elapsed_s: float = 0.0
    ts: str = field(default_factory=_now)


# Union of all event types (used for type hints)
AnyEvent = (
    LLMCallStarted
    | LLMTokenChunk
    | LLMCallFinished
    | ToolCallStarted
    | ToolCallFinished
    | ToolCallBlocked
    | SubagentSpawned
    | SubagentFinished
    | StopHookFired
    | PermissionDecision
    | CostThreshold
    | CronJobFired
    | DaemonIteration
)

# ---------------------------------------------------------------------------
# EventBus
# ---------------------------------------------------------------------------


class EventBus:
    """Thread-safe in-process pub/sub for transparency events.

    Usage::
        bus = get_event_bus()
        bus.emit(ToolCallStarted(session_id="s1", tool_name="bash", args_preview="ls -la"))

        # async consumer
        q: asyncio.Queue = asyncio.Queue()
        bus.subscribe(q)
        event = await q.get()

        # sync listener
        bus.add_listener(lambda e: print(type(e).__name__))
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._queues: list[asyncio.Queue] = []
        self._listeners: list[Callable[[Any], None]] = []

    def emit(self, event: Any) -> None:
        """Emit *event* to all subscribers.  Never raises.  Non-blocking."""
        with self._lock:
            queues = list(self._queues)
            listeners = list(self._listeners)

        for listener in listeners:
            try:
                listener(event)
            except Exception:
                _log.exception("EventBus sync listener error (demoted)")

        for q in queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                _log.debug("EventBus queue full — dropping %s", type(event).__name__)
            except Exception:
                _log.exception("EventBus queue put error")

    def subscribe(self, queue: asyncio.Queue) -> None:
        """Register an async queue to receive all future events."""
        with self._lock:
            if queue not in self._queues:
                self._queues.append(queue)

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove an async queue from the subscriber list."""
        with self._lock:
            try:
                self._queues.remove(queue)
            except ValueError:
                pass

    def add_listener(self, fn: Callable[[Any], None]) -> None:
        """Add a synchronous listener called inline on every emit."""
        with self._lock:
            if fn not in self._listeners:
                self._listeners.append(fn)

    def remove_listener(self, fn: Callable[[Any], None]) -> None:
        with self._lock:
            try:
                self._listeners.remove(fn)
            except ValueError:
                pass

    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._queues) + len(self._listeners)


_BUS: EventBus | None = None
_BUS_LOCK = threading.Lock()


def get_event_bus() -> EventBus:
    """Return the global singleton EventBus, creating it on first call."""
    global _BUS
    if _BUS is None:
        with _BUS_LOCK:
            if _BUS is None:
                _BUS = EventBus()
    return _BUS


def reset_event_bus() -> None:
    """Reset the global singleton (test isolation only)."""
    global _BUS
    with _BUS_LOCK:
        _BUS = None


# ---------------------------------------------------------------------------
# ProcessStateWriter — atomic .lyra/process_state.json
# ---------------------------------------------------------------------------

_STATE_BEARING_EVENTS = (
    LLMCallStarted,
    LLMCallFinished,
    ToolCallStarted,
    ToolCallFinished,
    ToolCallBlocked,
    SubagentSpawned,
    SubagentFinished,
    StopHookFired,
    PermissionDecision,
    DaemonIteration,
)


class ProcessStateWriter:
    """Sync EventBus listener that writes `.lyra/process_state.json` atomically.

    Updated on every state-bearing event so external tools (``lyra ps``,
    abtop-equivalents) can read current process state without a live connection.

    Usage::
        writer = ProcessStateWriter(lyra_dir=Path(".lyra"))
        writer.attach(get_event_bus())
    """

    def __init__(
        self,
        lyra_dir: Path = Path(".lyra"),
        session_id: str = "",
    ) -> None:
        self._lyra_dir = lyra_dir
        self._path = lyra_dir / "process_state.json"
        self._state: dict[str, Any] = {
            "session_id": session_id,
            "started_at": _now(),
            "status": "running",
            "agent_role": "",
            "permission_mode": "",
            "model_slot": "",
            "current_step": 0,
            "max_steps": 0,
            "cost_usd_so_far": 0.0,
            "token_in": 0,
            "token_out": 0,
            "cache_hit_tokens": 0,
            "last_tool": None,
            "worktree": "",
            "daemon_iteration": 0,
        }

    def attach(self, bus: EventBus) -> None:
        bus.add_listener(self._on_event)

    def detach(self, bus: EventBus) -> None:
        bus.remove_listener(self._on_event)

    def _on_event(self, event: Any) -> None:
        if not isinstance(event, _STATE_BEARING_EVENTS):
            return
        self._update_state(event)
        self._write()

    def _update_state(self, event: Any) -> None:
        s = self._state
        if isinstance(event, LLMCallStarted):
            s["model_slot"] = event.model
            s["current_step"] = event.turn
            s["status"] = "running"
        elif isinstance(event, LLMCallFinished):
            s["token_in"] += event.input_tokens
            s["token_out"] += event.output_tokens
            s["cache_hit_tokens"] += event.cache_read_tokens
        elif isinstance(event, ToolCallStarted):
            s["last_tool"] = {"name": event.tool_name, "status": "running", "duration_ms": None}
        elif isinstance(event, ToolCallFinished):
            s["last_tool"] = {
                "name": event.tool_name,
                "status": "error" if event.is_error else "done",
                "duration_ms": event.duration_ms,
            }
        elif isinstance(event, ToolCallBlocked):
            s["last_tool"] = {"name": event.tool_name, "status": "blocked", "reason": event.reason}
        elif isinstance(event, SubagentSpawned):
            s["agent_role"] = event.agent_role
            s["worktree"] = event.worktree
            s["status"] = "running"
        elif isinstance(event, SubagentFinished):
            s["status"] = event.status
            s["cost_usd_so_far"] += event.cost_usd
        elif isinstance(event, StopHookFired):
            s["status"] = "stopped"
        elif isinstance(event, PermissionDecision):
            s["permission_mode"] = event.mode
        elif isinstance(event, DaemonIteration):
            s["daemon_iteration"] = event.iteration

    def _write(self) -> None:
        try:
            self._lyra_dir.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self._lyra_dir, suffix=".tmp")
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(self._state, f, indent=2)
                os.replace(tmp, self._path)
            except Exception:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
        except Exception:
            _log.exception("ProcessStateWriter: failed to write %s", self._path)

    def read_state(self) -> dict[str, Any]:
        """Return a copy of the current in-memory state."""
        return dict(self._state)


__all__ = [
    # events
    "LLMCallStarted",
    "LLMTokenChunk",
    "LLMCallFinished",
    "ToolCallStarted",
    "ToolCallFinished",
    "ToolCallBlocked",
    "SubagentSpawned",
    "SubagentFinished",
    "StopHookFired",
    "PermissionDecision",
    "CostThreshold",
    "CronJobFired",
    "DaemonIteration",
    # bus
    "EventBus",
    "get_event_bus",
    "reset_event_bus",
    # writer
    "ProcessStateWriter",
]
