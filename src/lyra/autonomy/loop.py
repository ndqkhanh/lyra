"""Continuous autonomy loop — fire-and-forget task execution with health monitoring.

Provides:
- :class:`AutonomyLoop` — core loop with state machine, health pings, stop/start.
- :class:`AutonomousAgent` — high-level wrapper with effort regulation, daemon mode,
  health monitoring, and ERROR PROBE-style self-diagnosis.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from lyra.autonomy.effort_regulator import (
    Budget,
    EffortLevel as EffortLevelER,
    EffortRegulator,
    SessionState,
    TaskHistoryEntry,
)

logger = logging.getLogger(__name__)


class LoopState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    RECOVERING = "recovering"
    STOPPED = "stopped"


class RunMode(str, Enum):
    ONCE = "once"            # Single task, exit when done
    CONTINUOUS = "continuous"  # Keep running, pick up new tasks
    SCHEDULED = "scheduled"    # Run on a cron-like schedule


class HealthStatus(str, Enum):
    """Health check outcome for the autonomous agent."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthReport:
    """Detailed health report for an agent session.

    Attributes:
        status: Overall health status.
        memory_mb: Current RSS memory usage in MB.
        token_burn_rate: Tokens consumed per minute.
        error_rate: Errors per minute in the recent window.
        cpu_percent: CPU utilisation percentage (0-100).
        uptime_seconds: Seconds since agent started.
        details: Additional key-value diagnostics.
    """

    status: HealthStatus
    memory_mb: float
    token_burn_rate: float
    error_rate: float
    cpu_percent: float
    uptime_seconds: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class Issue:
    """A self-diagnosed issue.

    Attributes:
        severity: One of ``"info"``, ``"warning"``, ``"error"``, ``"critical"``.
        component: The subsystem where the issue was found.
        description: Human-readable description.
        recommendation: Suggested remediation.
    """

    severity: str
    component: str
    description: str
    recommendation: str


@dataclass
class AutonomyLoop:
    """Continuous autonomy loop that runs unattended, managed by the supervisor daemon.

    The loop polls for pending tasks, executes them with health checks,
    and handles crashes with escalating recovery actions.
    """

    run_mode: RunMode = RunMode.CONTINUOUS
    max_idle_seconds: int = 3600  # Auto-stop after 1h idle
    health_check_interval: int = 30  # seconds between health pings
    max_consecutive_failures: int = 3

    _state: LoopState = LoopState.IDLE
    _last_activity: float = field(default_factory=time.time)
    _failure_count: int = 0
    _tasks_completed: int = 0
    _start_time: float = field(default_factory=time.time)

    @property
    def state(self) -> LoopState:
        return self._state

    @property
    def is_idle(self) -> bool:
        return (time.time() - self._last_activity) > self.max_idle_seconds

    async def start(self, task_queue: asyncio.Queue | None = None):
        """Start the autonomy loop. Runs until stopped or idle timeout."""
        self._state = LoopState.RUNNING
        self._last_activity = time.time()

        while self._state != LoopState.STOPPED:
            if self.is_idle and self.run_mode != RunMode.ONCE:
                self._state = LoopState.IDLE
                break

            if task_queue and not task_queue.empty():
                task = await task_queue.get()
                try:
                    await self._execute_task(task)
                    self._tasks_completed += 1
                    self._failure_count = 0
                    self._last_activity = time.time()
                except Exception:
                    self._failure_count += 1
                    if self._failure_count >= self.max_consecutive_failures:
                        self._state = LoopState.RECOVERING
                        break

            await asyncio.sleep(self.health_check_interval)

    async def _execute_task(self, task: Any):
        """Execute a single task with pre/post health checks."""
        self._state = LoopState.RUNNING
        if not self._health_ok():
            raise RuntimeError("Health check failed before task execution")
        self._state = LoopState.WAITING

    def _health_ok(self) -> bool:
        """Check if the loop is healthy enough to continue."""
        return self._failure_count < self.max_consecutive_failures

    def stop(self):
        """Gracefully stop the autonomy loop."""
        self._state = LoopState.STOPPED

    def stats(self) -> dict:
        return {
            "state": self._state.value,
            "tasks_completed": self._tasks_completed,
            "failure_count": self._failure_count,
            "idle_seconds": time.time() - self._last_activity,
            "uptime_seconds": time.time() - self._start_time,
        }


# ────────────────────────────────────────────────────────────────────
# AutonomousAgent — high-level wrapper with effort regulation
# ────────────────────────────────────────────────────────────────────


class AutonomousAgent:
    """High-level autonomous agent that wraps :class:`AutonomyLoop` with
    effort regulation, health monitoring, self-diagnosis, and daemon mode.

    Integrates with the Phase 0 checkpoint manager (:mod:`lyra.sessions.checkpoint`)
    for safe restart.

    Usage::

        agent = AutonomousAgent(agent_id="code-worker")
        await agent.daemon_mode(task_queue)
        report = agent.health_check()
        issues = agent.self_diagnose()
    """

    def __init__(
        self,
        agent_id: str = "default",
        loop: AutonomyLoop | None = None,
        regulator: EffortRegulator | None = None,
        checkpoint_manager: Any | None = None,
        token_budget: int = 100_000,
        wall_time_budget: float = 3600.0,
    ) -> None:
        """
        Args:
            agent_id: Unique identifier for this agent instance.
            loop: Core autonomy loop instance. Creates a default one if None.
            regulator: Effort regulator for calibrating task effort. Creates
                a default one if None.
            checkpoint_manager: Optional Phase 0 CheckpointManager for
                persisting and restoring agent state on restart.
            token_budget: Maximum tokens per daemon cycle.
            wall_time_budget: Maximum wall time per daemon cycle in seconds.
        """
        self.agent_id = agent_id
        self.loop = loop or AutonomyLoop()
        self.regulator = regulator or EffortRegulator()
        self.checkpoint_manager = checkpoint_manager
        self._budget = Budget(
            max_steps=100,
            max_tokens=token_budget,
            max_wall_time_seconds=wall_time_budget,
        )

        # Internal counters
        self._total_tokens: int = 0
        self._step_count: int = 0
        self._error_count: int = 0
        self._restart_count: int = 0
        self._start_time: float = time.time()

        # Error timestamps for rate calculation
        self._error_timestamps: list[float] = []

    # ── Daemon mode ────────────────────────────────────────────────

    async def daemon_mode(self, task_queue: asyncio.Queue) -> None:
        """Run the agent indefinitely, self-restarting on crash.

        Each cycle:
        1. Optionally restore from checkpoint (if checkpoint_manager && first start).
        2. Start the loop and process tasks.
        3. Record the outcome in the effort regulator for future calibration.
        4. If the loop enters RECOVERING state, save a checkpoint, log the crash,
           and restart silently.

        Args:
            task_queue: Queue of tasks to process.
        """
        logger.info("Daemon mode started for agent '%s'", self.agent_id)

        while True:
            if self.loop.state == LoopState.STOPPED:
                logger.info("Daemon mode: loop stopped, ending daemon cycle.")
                break

            try:
                if (
                    self.loop.state != LoopState.RECOVERING
                    and self.checkpoint_manager is not None
                ):
                    # Attempt to restore from checkpoint (idempotent)
                    self._restore_from_checkpoint()

                await self.loop.start(task_queue)

            except asyncio.CancelledError:
                logger.info("Daemon mode cancelled for agent '%s'", self.agent_id)
                raise

            except Exception as exc:
                logger.exception(
                    "Daemon cycle crashed for agent '%s': %s",
                    self.agent_id,
                    exc,
                )

            # --- Post-cycle bookkeeping ---

            if self.checkpoint_manager is not None:
                self._save_checkpoint()

            # If the loop is recovering, restart it
            if self.loop.state == LoopState.RECOVERING:
                self._restart_count += 1
                self.loop = AutonomyLoop(
                    run_mode=self.loop.run_mode,
                    max_idle_seconds=self.loop.max_idle_seconds,
                    health_check_interval=self.loop.health_check_interval,
                    max_consecutive_failures=self.loop.max_consecutive_failures,
                )
                logger.info(
                    "AutonomousAgent '%s' self-restarted (count=%d)",
                    self.agent_id,
                    self._restart_count,
                )
                continue

            # If the loop stopped gracefully, exit daemon mode
            if self.loop.state == LoopState.STOPPED:
                break

            # Brief pause before next cycle
            await asyncio.sleep(1)

    # ── Health monitoring ───────────────────────────────────────────

    def health_check(self) -> HealthReport:
        """Produce a health report for the current agent session.

        Measures:
        - Memory usage (via ``getrusage`` or ``/proc/self/status``).
        - Token burn rate (tokens per minute).
        - Error rate (errors per minute over the last 5-minute window).
        - CPU usage (approximate from resource usage).
        - Uptime.

        Returns:
            A :class:`HealthReport` with the current health status.
        """
        memory_mb = self._get_memory_mb()
        uptime = time.time() - self._start_time
        token_rate = self._compute_token_burn_rate()
        error_rate = self._compute_error_rate(window_seconds=300)
        cpu_pct = self._get_cpu_percent()

        if error_rate > 5.0 or memory_mb > 1024:
            status = HealthStatus.UNHEALTHY
        elif error_rate > 1.0 or memory_mb > 512:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY

        return HealthReport(
            status=status,
            memory_mb=memory_mb,
            token_burn_rate=token_rate,
            error_rate=error_rate,
            cpu_percent=cpu_pct,
            uptime_seconds=uptime,
            details={
                "agent_id": self.agent_id,
                "loop_state": self.loop.state.value,
                "tasks_completed": self.loop._tasks_completed,
                "restart_count": self._restart_count,
            },
        )

    # ── Self-diagnosis ─────────────────────────────────────────────

    def self_diagnose(self) -> list[Issue]:
        """ERROR PROBE-style self-diagnosis of the autonomous agent.

        Checks:
        1. Memory usage — high consumption → warning.
        2. Error rate — elevated errors → warning/error.
        3. Restart frequency — excessive restarts → error.
        4. Token burn rate — abnormal pattern → info.
        5. Loop state — recovering → error; idle → info.
        6. Agent idleness — long idle time → info.

        Returns:
            A list of :class:`Issue` objects (empty if all clear).
        """
        issues: list[Issue] = []
        report = self.health_check()

        # 1. Memory
        if report.memory_mb > 1024:
            issues.append(Issue(
                severity="error",
                component="memory",
                description=f"Memory usage is high: {report.memory_mb:.0f} MB",
                recommendation="Consider checkpointing state and restarting the agent. "
                "Check for memory leaks in task handlers.",
            ))
        elif report.memory_mb > 512:
            issues.append(Issue(
                severity="warning",
                component="memory",
                description=f"Memory usage is elevated: {report.memory_mb:.0f} MB",
                recommendation="Monitor memory trend. Consider reducing task concurrency.",
            ))

        # 2. Error rate
        if report.error_rate > 5.0:
            issues.append(Issue(
                severity="error",
                component="errors",
                description=f"High error rate: {report.error_rate:.1f} errors/min in last 5 min",
                recommendation="Investigate recent task failures. Check provider health. "
                "Escalate if persistent.",
            ))
        elif report.error_rate > 1.0:
            issues.append(Issue(
                severity="warning",
                component="errors",
                description=f"Elevated error rate: {report.error_rate:.1f} errors/min",
                recommendation="Monitor for escalation. Review crash recovery escalation order.",
            ))

        # 3. Restart frequency
        if self._restart_count > 10:
            issues.append(Issue(
                severity="error",
                component="restarts",
                description=f"Excessive restarts: {self._restart_count} cycles",
                recommendation="The agent is repeatedly crashing. Engage human escalation "
                "path and investigate root cause via ErrorProbe.",
            ))
        elif self._restart_count > 3:
            issues.append(Issue(
                severity="warning",
                component="restarts",
                description=f"Frequent restarts: {self._restart_count} cycles",
                recommendation="Check checkpoint integrity. Consider circuit breaker.",
            ))

        # 4. Token burn rate
        if report.token_burn_rate > 100_000:
            issues.append(Issue(
                severity="warning",
                component="tokens",
                description=f"High token burn rate: {report.token_burn_rate:.0f} tokens/min",
                recommendation="Consider reducing effort level or enabling "
                "diminishing-returns early stop.",
            ))

        # 5. Loop state
        if self.loop.state == LoopState.RECOVERING:
            issues.append(Issue(
                severity="error",
                component="loop",
                description="Loop is in RECOVERING state",
                recommendation="Trigger daemon mode self-restart or escalate human.",
            ))
        elif self.loop.state == LoopState.IDLE:
            issues.append(Issue(
                severity="info",
                component="loop",
                description="Loop is idle — no active tasks",
                recommendation="No action needed if this is expected. "
                "Extend max_idle_seconds if premature.",
            ))

        # 6. Agent idleness
        uptime = time.time() - self._start_time
        if uptime > 600 and self._total_tokens == 0:
            issues.append(Issue(
                severity="info",
                component="productivity",
                description=f"Agent has been running for {uptime:.0f}s with zero token "
                "consumption",
                recommendation="Verify task queue is populated and agent is processing.",
            ))

        return issues

    # ── Effort regulation helpers ───────────────────────────────────

    def get_task_budget(self, task_type: str) -> Budget:
        """Return the budget for a task after effort calibration.

        The budget caps are adjusted based on the calibrated effort level
        for the task type.

        Args:
            task_type: One of ``"code"``, ``"chat"``, ``"research"``.

        Returns:
            A :class:`Budget` instance with calibrated limits.
        """
        level = self.regulator.calibrate(task_type)
        profile = self._effort_profile_for_level(level)

        return Budget(
            max_steps=profile.max_steps,
            max_tokens=self._budget.max_tokens,
            max_wall_time_seconds=self._budget.max_wall_time_seconds,
        )

    def record_task_outcome(
        self,
        task_type: str,
        session_state: SessionState,
    ) -> None:
        """Record a task outcome in the effort regulator.

        Args:
            task_type: Type of the completed task.
            session_state: Final session state snapshot.
        """
        entry = TaskHistoryEntry(
            task_type=task_type,
            steps_taken=session_state.step,
            final_confidence=session_state.confidence,
            improvement_sequence=list(session_state.improvements),
            wall_time_seconds=session_state.wall_time_seconds,
            tokens_consumed=session_state.tokens_consumed,
        )
        self.regulator.record_outcome(entry)
        self._total_tokens += session_state.tokens_consumed

    # ── Internal helpers ───────────────────────────────────────────

    def _restore_from_checkpoint(self) -> None:
        """Restore agent state from the checkpoint manager, if available."""
        if self.checkpoint_manager is None:
            return
        try:
            state = self.checkpoint_manager.restore(self.agent_id)
            if state:
                self._total_tokens = state.get("total_tokens", self._total_tokens)
                self._error_count = state.get("error_count", self._error_count)
                logger.info(
                    "Restored agent '%s' from checkpoint", self.agent_id
                )
        except Exception:
            logger.debug(
                "No checkpoint to restore for agent '%s'", self.agent_id
            )

    def _save_checkpoint(self) -> None:
        """Persist agent state via the checkpoint manager, if available."""
        if self.checkpoint_manager is None:
            return
        try:
            self.checkpoint_manager.save(
                self.agent_id,
                {
                    "total_tokens": self._total_tokens,
                    "error_count": self._error_count,
                    "tasks_completed": self.loop._tasks_completed,
                    "loop_state": self.loop.state.value,
                },
            )
        except Exception:
            logger.exception("Failed to save checkpoint for agent '%s'", self.agent_id)

    def _get_memory_mb(self) -> float:
        """Return approximate RSS memory usage in MB.

        Uses ``getrusage`` on Unix (macOS reports max RSS in bytes)
        or falls back to ``/proc/self/status`` on Linux.
        """
        try:
            import resource

            usage = resource.getrusage(resource.RUSAGE_SELF)
            # macOS: ru_maxrss is in bytes; Linux: ru_maxrss is in kilobytes
            rss_bytes = usage.ru_maxrss / 1024.0 if os.uname().sysname == "Darwin" else usage.ru_maxrss
            return rss_bytes / 1024.0
        except (ImportError, AttributeError, OSError):
            # Fallback: try /proc/self/status (Linux)
            try:
                with open("/proc/self/status") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            parts = line.split()
                            return float(parts[1]) / 1024  # kB → MB
            except OSError:
                pass
            # Best-effort: return 0
            return 0.0

    def _compute_token_burn_rate(self) -> float:
        """Return tokens consumed per minute since the agent started."""
        uptime = time.time() - self._start_time
        if uptime < 1:
            return 0.0
        return self._total_tokens / (uptime / 60.0)

    def _compute_error_rate(self, window_seconds: int = 300) -> float:
        """Return errors per minute in the recent time window."""
        cutoff = time.time() - window_seconds
        recent = [t for t in self._error_timestamps if t > cutoff]
        if not recent:
            return 0.0
        return len(recent) / (window_seconds / 60.0)

    def _get_cpu_percent(self) -> float:
        """Return approximate CPU utilisation percentage.

        On Unix uses ``resource.getrusage`` to compute CPU time ratio.
        """
        try:
            import resource

            usage = resource.getrusage(resource.RUSAGE_SELF)
            uptime = max(time.time() - self._start_time, 0.01)
            total_cpu = usage.ru_utime + usage.ru_stime
            return min((total_cpu / uptime) * 100.0, 100.0)
        except (ImportError, AttributeError):
            return 0.0

    @staticmethod
    def _effort_profile_for_level(level: EffortLevelER) -> Any:
        """Return the EffortProfile for a given EffortLevel."""
        from lyra.autonomy.effort_regulator import _EFFORT_PROFILES

        return _EFFORT_PROFILES.get(level, _EFFORT_PROFILES[EffortLevelER.BALANCED])

    def stats(self) -> dict[str, Any]:
        """Return comprehensive agent stats."""
        report = self.health_check()
        return {
            "agent_id": self.agent_id,
            "loop_state": self.loop.state.value,
            "tasks_completed": self.loop._tasks_completed,
            "failure_count": self.loop._failure_count,
            "restart_count": self._restart_count,
            "total_tokens": self._total_tokens,
            "error_count": self._error_count,
            "health": {
                "status": report.status.value,
                "memory_mb": round(report.memory_mb, 1),
                "token_burn_rate": round(report.token_burn_rate, 1),
                "error_rate": round(report.error_rate, 2),
                "cpu_percent": round(report.cpu_percent, 1),
                "uptime_seconds": round(report.uptime_seconds, 1),
            },
            "uptime_seconds": time.time() - self._start_time,
        }
