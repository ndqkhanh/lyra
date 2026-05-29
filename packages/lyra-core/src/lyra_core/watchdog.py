"""Agent Watchdog — lifecycle × health state monitoring.

Inspired by alphaclaw's watchdog state machine:
  - Lifecycle × Health state matrix
  - Crash-loop detection (3 crashes in 300s → escalate)
  - Auto-repair pipeline: detect → diagnose → fix → verify → notify
  - Startup grace periods and expected-restart windows

Also incorporates cmux's agent hibernation lifecycle:
  - Only idle agents can hibernate
  - Whitelist-gated lifecycle reporting
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum

from lyra_core.events import EventBus, EventCategory
from lyra_core.protocol import AgentHealth, AgentLifecycle, AgentState

logger = logging.getLogger(__name__)


# ── Watchdog State ──────────────────────────────────────────────────────────


class WatchdogStatus(str, Enum):
    """Watchdog-level status combining lifecycle and health."""

    RUNNING_HEALTHY = "running/healthy"
    RUNNING_DEGRADED = "running/degraded"
    RUNNING_UNKNOWN = "running/unknown"
    CRASHED_UNHEALTHY = "crashed/unhealthy"
    CRASH_LOOP_UNHEALTHY = "crash_loop/unhealthy"
    RESTARTING_UNKNOWN = "restarting/unknown"
    STOPPED_UNKNOWN = "stopped/unknown"


@dataclass
class WatchdogConfig:
    """Configuration for agent watchdog monitoring."""

    startup_grace_seconds: float = 30.0
    expected_restart_window_seconds: float = 15.0
    crash_loop_threshold: int = 3
    crash_loop_window_seconds: float = 300.0
    health_poll_interval_seconds: float = 5.0
    bootstrap_health_poll_seconds: float = 5.0
    degraded_retry_interval_seconds: float = 10.0
    idle_hibernation_threshold_seconds: float = 600.0  # 10 min idle → hibernate
    allowed_agent_types: frozenset[str] = field(default_factory=frozenset)


# ── Crash Record ────────────────────────────────────────────────────────────


@dataclass
class CrashRecord:
    """Record of a single crash event."""

    timestamp: float
    agent_id: str
    exit_code: int
    error_message: str = ""


# ── Watchdog ────────────────────────────────────────────────────────────────


class AgentWatchdog:
    """Monitors an agent's lifecycle and health.

    Maintains a crash history for crash-loop detection. Emits events
    through the EventBus for subscribers (alerts, auto-repair, dashboards).
    """

    def __init__(
        self,
        agent_id: str,
        project_id: str,
        config: WatchdogConfig | None = None,
        bus: EventBus | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.project_id = project_id
        self.config = config or WatchdogConfig()
        self._bus = bus or EventBus.get()
        self._crash_history: list[CrashRecord] = []
        self._state_started_at: float = time.time()
        self._current_lifecycle = AgentLifecycle.REGISTERED
        self._current_health = AgentHealth.UNKNOWN
        self._last_activity: float = time.time()
        self._incident_open: bool = False

    # ── State Management ─────────────────────────────────────────────────

    @property
    def state(self) -> AgentState:
        return AgentState(
            lifecycle=self._current_lifecycle,
            health=self._current_health,
            since=self._state_started_at,
        )

    @property
    def watchdog_status(self) -> WatchdogStatus:
        """Compute the combined watchdog status."""
        if self._current_lifecycle == AgentLifecycle.TERMINATED:
            return WatchdogStatus.STOPPED_UNKNOWN
        if self._in_crash_loop():
            return WatchdogStatus.CRASH_LOOP_UNHEALTHY
        if self._current_health == AgentHealth.UNHEALTHY:
            return WatchdogStatus.CRASHED_UNHEALTHY
        if self._current_lifecycle == AgentLifecycle.INITIALIZING:
            return WatchdogStatus.RESTARTING_UNKNOWN

        lc = self._current_lifecycle
        h = self._current_health
        if h == AgentHealth.UNHEALTHY:
            return WatchdogStatus.CRASHED_UNHEALTHY
        if lc in (AgentLifecycle.ACTIVE, AgentLifecycle.READY, AgentLifecycle.IDLE,
                  AgentLifecycle.DEGRADED):
            if h == AgentHealth.HEALTHY:
                return WatchdogStatus.RUNNING_HEALTHY
            if h == AgentHealth.DEGRADED:
                return WatchdogStatus.RUNNING_DEGRADED
            return WatchdogStatus.RUNNING_UNKNOWN
        return WatchdogStatus.RUNNING_UNKNOWN

    def transition(self, lifecycle: AgentLifecycle, health: AgentHealth,
                   message: str = "") -> None:
        """Transition the agent to a new lifecycle/health state."""
        old_status = self.watchdog_status
        self._current_lifecycle = lifecycle
        self._current_health = health
        self._state_started_at = time.time()

        new_status = self.watchdog_status
        if old_status != new_status:
            self._bus.publish(
                category=EventCategory.LIFECYCLE,
                name="agent.state_changed",
                source_agent_id=self.agent_id,
                source_project_id=self.project_id,
                origin=__name__,
                payload={
                    "old_status": old_status.value,
                    "new_status": new_status.value,
                    "lifecycle": lifecycle.value,
                    "health": health.value,
                    "message": message,
                },
            )

    def record_activity(self) -> None:
        """Call this whenever the agent does something (heartbeat)."""
        self._last_activity = time.time()

    # ── Crash Handling ───────────────────────────────────────────────────

    def record_crash(self, exit_code: int, error_message: str = "") -> None:
        """Record a crash. Automatically detects crash loops."""
        record = CrashRecord(
            timestamp=time.time(),
            agent_id=self.agent_id,
            exit_code=exit_code,
            error_message=error_message,
        )
        self._crash_history.append(record)

        # Prune old crash records outside the window
        cutoff = time.time() - self.config.crash_loop_window_seconds
        self._crash_history = [c for c in self._crash_history if c.timestamp > cutoff]

        self.transition(AgentLifecycle.DEGRADED, AgentHealth.UNHEALTHY,
                        message=f"Crash recorded: exit_code={exit_code}")

        if self._in_crash_loop():
            logger.error("Agent %s entered crash loop (%d crashes in %ds)",
                         self.agent_id, len(self._crash_history),
                         self.config.crash_loop_window_seconds)
            self._bus.publish(
                category=EventCategory.LIFECYCLE,
                name="agent.crash_loop_detected",
                source_agent_id=self.agent_id,
                source_project_id=self.project_id,
                origin=__name__,
                payload={
                    "crash_count": len(self._crash_history),
                    "window_seconds": self.config.crash_loop_window_seconds,
                    "exit_code": exit_code,
                    "error_message": error_message,
                },
            )

    def should_restart(self) -> bool:
        """Check if the agent should be restarted (not in crash loop)."""
        if self._in_crash_loop():
            return False
        if self._current_lifecycle == AgentLifecycle.TERMINATED:
            return False
        return self._current_health == AgentHealth.UNHEALTHY

    def should_hibernate(self) -> bool:
        """Check if the agent should be hibernated (idle too long)."""
        if self._current_lifecycle != AgentLifecycle.IDLE:
            return False
        idle_duration = time.time() - self._last_activity
        return idle_duration >= self.config.idle_hibernation_threshold_seconds

    # ── Incident Management ──────────────────────────────────────────────

    def open_incident(self, title: str) -> None:
        """Open an incident. Deduplicates notifications."""
        if not self._incident_open:
            self._incident_open = True
            self._bus.publish(
                category=EventCategory.NOTIFICATION,
                name="incident.opened",
                source_agent_id=self.agent_id,
                source_project_id=self.project_id,
                origin=__name__,
                payload={"title": title},
            )

    def close_incident(self) -> None:
        """Close the current incident."""
        if self._incident_open:
            self._incident_open = False
            self._bus.publish(
                category=EventCategory.NOTIFICATION,
                name="incident.closed",
                source_agent_id=self.agent_id,
                source_project_id=self.project_id,
                origin=__name__,
                payload={},
            )

    # ── Internal ─────────────────────────────────────────────────────────

    def _in_crash_loop(self) -> bool:
        """Check if the agent is in a crash loop."""
        cutoff = time.time() - self.config.crash_loop_window_seconds
        recent_crashes = [c for c in self._crash_history if c.timestamp > cutoff]
        return len(recent_crashes) >= self.config.crash_loop_threshold

    def within_startup_grace(self) -> bool:
        """Check if we're still within the startup grace period."""
        elapsed = time.time() - self._state_started_at
        return self._current_lifecycle == AgentLifecycle.INITIALIZING and \
            elapsed < self.config.startup_grace_seconds

    def within_expected_restart(self) -> bool:
        """Check if we're still within the expected restart window."""
        elapsed = time.time() - self._state_started_at
        return self._current_lifecycle == AgentLifecycle.INITIALIZING and \
            elapsed < self.config.expected_restart_window_seconds
