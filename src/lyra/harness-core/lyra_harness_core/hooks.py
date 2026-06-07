"""Hook system: 50+ event pipeline with timeout decoupling, watchdog health
matrix, and crash-loop detection.

Backward-compatible with the original 3-event HookRegistry API.
"""
from __future__ import annotations

import enum
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from .messages import ToolCall, ToolResult


# ---------------------------------------------------------------------------
# Hook events — 50+ lifecycle events across 12 categories
# ---------------------------------------------------------------------------


class HookEvent(str, enum.Enum):
    """50+ hook events covering the full agent lifecycle."""

    # --- Session (4) ---
    SESSION_STARTED = "SessionStarted"
    SESSION_PAUSED = "SessionPaused"
    SESSION_RESUMED = "SessionResumed"
    SESSION_ENDED = "SessionEnded"

    # --- Tool (4) ---
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    TOOL_OUTPUT_STREAM = "ToolOutputStream"
    TOOL_TIMEOUT = "ToolTimeout"

    # --- Stop (1) ---
    STOP = "Stop"

    # --- Plan (3) ---
    PLAN_CREATED = "PlanCreated"
    PLAN_UPDATED = "PlanUpdated"
    PLAN_RECOVERY = "PlanRecovery"

    # --- Subagent (4) ---
    SUBAGENT_SPAWNED = "SubagentSpawned"
    SUBAGENT_COMPLETED = "SubagentCompleted"
    SUBAGENT_FAILED = "SubagentFailed"
    SUBAGENT_HEARTBEAT = "SubagentHeartbeat"

    # --- Memory (4) ---
    MEMORY_WRITE = "MemoryWrite"
    MEMORY_READ = "MemoryRead"
    MEMORY_CONSOLIDATION = "MemoryConsolidation"
    MEMORY_EXPIRY = "MemoryExpiry"

    # --- Context (2) ---
    CONTEXT_COMPACTION = "ContextCompaction"
    CONTEXT_WARNING = "ContextWarning"

    # --- Model routing (1) ---
    MODEL_ROUTER_DECISION = "ModelRouterDecision"

    # --- Verification (2) ---
    VERIFIER_PASS = "VerifierPass"
    VERIFIER_FAIL = "VerifierFail"

    # --- Skills (2) ---
    SKILL_LOAD = "SkillLoad"
    SKILL_UNLOAD = "SkillUnload"

    # --- Agent lifecycle (2) ---
    AGENT_HIBERNATE = "AgentHibernate"
    AGENT_WAKE = "AgentWake"

    # --- Checkpoint (2) ---
    CHECKPOINT_CREATE = "CheckpointCreate"
    CHECKPOINT_RESTORE = "CheckpointRestore"

    # --- Fleet / scaling (2) ---
    FLEET_SCALE_UP = "FleetScaleUp"
    FLEET_SCALE_DOWN = "FleetScaleDown"

    # --- Safety (1) ---
    SAFETY_VIOLATION = "SafetyViolation"

    # --- Provider (1) ---
    PROVIDER_FAILOVER = "ProviderFailover"

    # --- Plugin lifecycle (3) ---
    PLUGIN_LOADED = "PluginLoaded"
    PLUGIN_UNLOADED = "PluginUnloaded"
    PLUGIN_ERROR = "PluginError"

    # --- MCP (2) ---
    MCP_CONNECTED = "MCPConnected"
    MCP_DISCONNECTED = "MCPDisconnected"

    # --- Cron (1) ---
    CRON_TRIGGERED = "CronTriggered"

    # --- System (2) ---
    SYSTEM_STARTUP = "SystemStartup"
    SYSTEM_SHUTDOWN = "SystemShutdown"

    # --- Command (1) ---
    COMMAND_INVOKED = "CommandInvoked"

    # --- Pipeline (3) ---
    PIPELINE_STARTED = "PipelineStarted"
    PIPELINE_COMPLETED = "PipelineCompleted"
    PIPELINE_FAILED = "PipelineFailed"

    # --- Permission (2) ---
    PERMISSION_DENIED = "PermissionDenied"
    PERMISSION_GRANTED = "PermissionGranted"

    # --- Rate limiting (2) ---
    RATE_LIMIT_HIT = "RateLimitHit"
    RATE_LIMIT_CLEARED = "RateLimitCleared"

    # --- Heartbeat (1) ---
    HEARTBEAT = "Heartbeat"

    @classmethod
    def by_category(cls) -> dict[str, list[HookEvent]]:
        """Group events by their lifecycle category."""
        mapping: dict[str, list[HookEvent]] = defaultdict(list)
        categories = {
            "session": {"SESSION_STARTED", "SESSION_PAUSED", "SESSION_RESUMED", "SESSION_ENDED"},
            "tool": {"PRE_TOOL_USE", "POST_TOOL_USE", "TOOL_OUTPUT_STREAM", "TOOL_TIMEOUT"},
            "stop": {"STOP"},
            "plan": {"PLAN_CREATED", "PLAN_UPDATED", "PLAN_RECOVERY"},
            "subagent": {"SUBAGENT_SPAWNED", "SUBAGENT_COMPLETED", "SUBAGENT_FAILED", "SUBAGENT_HEARTBEAT"},
            "memory": {"MEMORY_WRITE", "MEMORY_READ", "MEMORY_CONSOLIDATION", "MEMORY_EXPIRY"},
            "context": {"CONTEXT_COMPACTION", "CONTEXT_WARNING"},
            "model": {"MODEL_ROUTER_DECISION"},
            "verifier": {"VERIFIER_PASS", "VERIFIER_FAIL"},
            "skill": {"SKILL_LOAD", "SKILL_UNLOAD"},
            "agent": {"AGENT_HIBERNATE", "AGENT_WAKE"},
            "checkpoint": {"CHECKPOINT_CREATE", "CHECKPOINT_RESTORE"},
            "fleet": {"FLEET_SCALE_UP", "FLEET_SCALE_DOWN"},
            "safety": {"SAFETY_VIOLATION"},
            "provider": {"PROVIDER_FAILOVER"},
            "plugin": {"PLUGIN_LOADED", "PLUGIN_UNLOADED", "PLUGIN_ERROR"},
            "mcp": {"MCP_CONNECTED", "MCP_DISCONNECTED"},
            "cron": {"CRON_TRIGGERED"},
            "system": {"SYSTEM_STARTUP", "SYSTEM_SHUTDOWN"},
            "command": {"COMMAND_INVOKED"},
            "pipeline": {"PIPELINE_STARTED", "PIPELINE_COMPLETED", "PIPELINE_FAILED"},
            "permission": {"PERMISSION_DENIED", "PERMISSION_GRANTED"},
            "rate_limit": {"RATE_LIMIT_HIT", "RATE_LIMIT_CLEARED"},
            "heartbeat": {"HEARTBEAT"},
        }
        for cat, names in categories.items():
            for name in names:
                mapping[cat].append(cls[name])
        return dict(mapping)


# ---------------------------------------------------------------------------
# Hook health / watchdog
# ---------------------------------------------------------------------------


class HookHealth(str, enum.Enum):
    """Health state for a single hook — alphaclaw watchdog matrix."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"  # some failures, still running
    UNSTABLE = "unstable"  # crash-loop suspected
    DISABLED = "disabled"  # auto-disabled after repeated crashes
    TIMED_OUT = "timed_out"  # last execution exceeded timeout


@dataclass
class HookWatchdog:
    """Tracks health state per hook with crash-loop detection.

    Crash-loop rule: 3+ failures within 5 minutes → UNSTABLE.
    5+ failures within 5 minutes → DISABLED (auto-shed).
    """

    max_failures_before_unstable: int = 3
    max_failures_before_disable: int = 5
    window_seconds: float = 300.0  # 5 minutes
    timeout_seconds: float = 120.0  # per-hook timeout

    # Per-hook state: hook_name → list of (timestamp, success)
    _history: dict[str, list[tuple[float, bool]]] = field(default_factory=dict)

    def record(self, hook_name: str, success: bool) -> None:
        now = time.monotonic()
        if hook_name not in self._history:
            self._history[hook_name] = []
        self._history[hook_name].append((now, success))
        self._prune(hook_name, now)

    def _prune(self, hook_name: str, now: float) -> None:
        if hook_name not in self._history:
            return
        cutoff = now - self.window_seconds
        self._history[hook_name] = [
            (ts, ok) for ts, ok in self._history[hook_name] if ts > cutoff
        ]

    def health(self, hook_name: str) -> HookHealth:
        """Evaluate current health state for a hook."""
        now = time.monotonic()
        entries = self._history.get(hook_name, [])
        self._prune(hook_name, now)
        entries = self._history.get(hook_name, [])

        if not entries:
            return HookHealth.HEALTHY

        recent_failures = sum(1 for _, ok in entries if not ok)
        total = len(entries)

        if total == 0:
            return HookHealth.HEALTHY

        failure_rate = recent_failures / total

        if recent_failures >= self.max_failures_before_disable:
            return HookHealth.DISABLED
        if recent_failures >= self.max_failures_before_unstable:
            return HookHealth.UNSTABLE
        if failure_rate > 0.2:
            return HookHealth.DEGRADED
        return HookHealth.HEALTHY

    def is_disabled(self, hook_name: str) -> bool:
        return self.health(hook_name) == HookHealth.DISABLED

    def reset(self, hook_name: str) -> None:
        self._history.pop(hook_name, None)


# ---------------------------------------------------------------------------
# Hook decision & handler type
# ---------------------------------------------------------------------------


@dataclass
class HookDecision:
    """Outcome of a hook invocation."""

    block: bool = False
    reason: str = ""
    annotation: str = ""


Handler = Callable[[ToolCall, ToolResult | None], HookDecision]

# Generic handler for non-tool events (no ToolCall/ToolResult context)
GenericHandler = Callable[[dict[str, object] | None], HookDecision]


# ---------------------------------------------------------------------------
# Hook definition
# ---------------------------------------------------------------------------


@dataclass
class Hook:
    """A registered hook with optional timeout and health tracking."""

    name: str
    event: HookEvent
    matcher: str = "*"  # fnmatch pattern on tool name / event context
    handler: Handler | GenericHandler | None = None
    timeout_seconds: float | None = None  # per-hook override (default: 120s)


# ---------------------------------------------------------------------------
# HookRegistry — expanded with timeout, watchdog, crash-loop detection
# ---------------------------------------------------------------------------


@dataclass
class HookExecution:
    """Record of a single hook execution for stats / debugging."""

    hook_name: str
    event: HookEvent
    started_at: float
    finished_at: float
    success: bool
    error: str = ""


@dataclass
class HookStats:
    """Aggregate statistics for the hook registry."""

    total_executions: int = 0
    total_blocks: int = 0
    total_timeouts: int = 0
    total_errors: int = 0
    disabled_hooks: int = 0
    recent_executions: list[HookExecution] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_executions == 0:
            return 1.0
        return (self.total_executions - self.total_errors) / self.total_executions


class HookRegistry:
    """Holds registered hooks; dispatches events with timeout and health gating.

    Backward-compatible with the original 3-event API.
    """

    def __init__(
        self,
        default_timeout: float = 120.0,
        max_recent_executions: int = 100,
    ) -> None:
        self._hooks: list[Hook] = []
        self._watchdog = HookWatchdog(timeout_seconds=default_timeout)
        self._default_timeout = default_timeout
        self._max_recent = max_recent_executions
        self._executions: list[HookExecution] = []
        self._block_count: int = 0

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, hook: Hook) -> None:
        if hook.handler is None:
            raise ValueError(f"Hook {hook.name!r} has no handler")
        self._hooks.append(hook)

    def unregister(self, name: str) -> None:
        self._hooks = [h for h in self._hooks if h.name != name]
        self._watchdog.reset(name)

    @property
    def hook_count(self) -> int:
        return len(self._hooks)

    def list_hooks(self) -> list[str]:
        return sorted(h.name for h in self._hooks)

    def hooks_for_event(self, event: HookEvent) -> list[Hook]:
        return [h for h in self._hooks if h.event == event]

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def run(
        self,
        event: HookEvent,
        call: ToolCall,
        result: ToolResult | None = None,
    ) -> HookDecision:
        """Run all hooks for an event in registration order. First block wins.

        Backward-compatible with the original 3-event signature.
        """
        import fnmatch

        combined = HookDecision(block=False, reason="", annotation="")
        timeout = self._default_timeout

        for h in self._hooks:
            if h.event != event:
                continue
            if not (fnmatch.fnmatchcase(call.name, h.matcher) or h.matcher == "*"):
                continue

            # Crash-loop gate
            if self._watchdog.is_disabled(h.name):
                self._executions.append(
                    HookExecution(
                        hook_name=h.name,
                        event=event,
                        started_at=time.monotonic(),
                        finished_at=time.monotonic(),
                        success=False,
                        error="hook disabled by watchdog (crash-loop detected)",
                    )
                )
                continue

            per_hook_timeout = h.timeout_seconds or timeout
            assert h.handler is not None

            started = time.monotonic()
            try:
                d = h.handler(call, result)  # type: ignore[call-arg]
                elapsed = time.monotonic() - started

                if elapsed > per_hook_timeout:
                    self._watchdog.record(h.name, False)
                    self._executions.append(
                        HookExecution(
                            hook_name=h.name,
                            event=event,
                            started_at=started,
                            finished_at=time.monotonic(),
                            success=False,
                            error=f"timeout ({elapsed:.1f}s > {per_hook_timeout}s)",
                        )
                    )
                    # Graceful degradation: skip timed-out hook, continue chain
                    continue

                self._watchdog.record(h.name, True)
                self._record_execution(h.name, event, started, success=True)

                if d.annotation:
                    combined.annotation = (
                        f"{combined.annotation}\n{d.annotation}".strip()
                    )
                if d.block:
                    self._block_count += 1
                    return HookDecision(
                        block=True,
                        reason=f"{h.name}: {d.reason}",
                        annotation=combined.annotation,
                    )
            except Exception as exc:
                self._watchdog.record(h.name, False)
                self._record_execution(
                    h.name, event, started, success=False, error=str(exc)
                )
                # Continue to next hook — don't let one bad handler break the chain

        self._prune_executions()
        return combined

    def run_generic(
        self,
        event: HookEvent,
        context: dict[str, object] | None = None,
    ) -> HookDecision:
        """Dispatch a non-tool event (session, memory, system, etc.) to registered
        hooks. Uses ``*`` matcher since there is no tool name.
        """
        combined = HookDecision(block=False, reason="", annotation="")
        timeout = self._default_timeout

        for h in self._hooks:
            if h.event != event:
                continue

            if self._watchdog.is_disabled(h.name):
                continue

            per_hook_timeout = h.timeout_seconds or timeout
            assert h.handler is not None

            started = time.monotonic()
            try:
                d = h.handler(context)  # type: ignore[call-arg]
                elapsed = time.monotonic() - started

                if elapsed > per_hook_timeout:
                    self._watchdog.record(h.name, False)
                    continue

                self._watchdog.record(h.name, True)
                self._record_execution(h.name, event, started, success=True)

                if d.annotation:
                    combined.annotation = (
                        f"{combined.annotation}\n{d.annotation}".strip()
                    )
                if d.block:
                    self._block_count += 1
                    return HookDecision(
                        block=True,
                        reason=f"{h.name}: {d.reason}",
                        annotation=combined.annotation,
                    )
            except Exception:
                self._watchdog.record(h.name, False)
                self._record_execution(
                    h.name, event, started, success=False, error="exception"
                )

        self._prune_executions()
        return combined

    # ------------------------------------------------------------------
    # Watchdog & health
    # ------------------------------------------------------------------

    @property
    def watchdog(self) -> HookWatchdog:
        return self._watchdog

    def health(self, hook_name: str) -> HookHealth:
        return self._watchdog.health(hook_name)

    def disabled_hooks(self) -> list[str]:
        return sorted(
            h.name for h in self._hooks if self._watchdog.is_disabled(h.name)
        )

    def reset_watchdog(self, hook_name: str | None = None) -> None:
        """Reset watchdog state. If hook_name is None, resets ALL hooks."""
        if hook_name is None:
            for h in self._hooks:
                self._watchdog.reset(h.name)
        else:
            self._watchdog.reset(hook_name)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> HookStats:
        self._prune_executions()
        return HookStats(
            total_executions=len(self._executions),
            total_blocks=self._block_count,
            total_timeouts=sum(
                1 for e in self._executions if "timeout" in e.error
            ),
            total_errors=sum(1 for e in self._executions if not e.success),
            disabled_hooks=len(self.disabled_hooks()),
            recent_executions=list(self._executions),
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _record_execution(
        self,
        hook_name: str,
        event: HookEvent,
        started_at: float,
        success: bool,
        error: str = "",
    ) -> None:
        self._executions.append(
            HookExecution(
                hook_name=hook_name,
                event=event,
                started_at=started_at,
                finished_at=time.monotonic(),
                success=success,
                error=error,
            )
        )

    def _prune_executions(self) -> None:
        if len(self._executions) > self._max_recent:
            self._executions = self._executions[-self._max_recent:]
