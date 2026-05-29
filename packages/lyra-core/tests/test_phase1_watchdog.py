"""Comprehensive tests for AgentWatchdog."""

from __future__ import annotations

from lyra_core.events import EventBus
from lyra_core.protocol import AgentHealth, AgentLifecycle
from lyra_core.watchdog import (
    AgentWatchdog,
    CrashRecord,
    WatchdogConfig,
    WatchdogStatus,
)


class TestWatchdogConfig:
    def test_defaults(self):
        c = WatchdogConfig()
        assert c.startup_grace_seconds == 30.0
        assert c.crash_loop_threshold == 3
        assert c.crash_loop_window_seconds == 300.0

    def test_custom(self):
        c = WatchdogConfig(
            startup_grace_seconds=10.0,
            crash_loop_threshold=5,
            crash_loop_window_seconds=120.0,
        )
        assert c.startup_grace_seconds == 10.0
        assert c.crash_loop_threshold == 5


class TestCrashRecord:
    def test_create(self):
        r = CrashRecord(timestamp=1000.0, agent_id="a1", exit_code=1)
        assert r.agent_id == "a1"
        assert r.exit_code == 1


class TestAgentWatchdog:
    def test_initial_state(self):
        w = AgentWatchdog("a1", "p1")
        assert w.state.lifecycle == AgentLifecycle.REGISTERED
        assert w.state.health == AgentHealth.UNKNOWN

    def test_transition(self):
        w = AgentWatchdog("a1", "p1")
        w.transition(AgentLifecycle.ACTIVE, AgentHealth.HEALTHY,
                     message="agent ready")
        assert w.state.lifecycle == AgentLifecycle.ACTIVE
        assert w.state.health == AgentHealth.HEALTHY
        assert w.watchdog_status == WatchdogStatus.RUNNING_HEALTHY

    def test_transition_emits_event(self):
        bus = EventBus()
        w = AgentWatchdog("a1", "p1", bus=bus)
        prev_seq = bus.sequence
        w.transition(AgentLifecycle.ACTIVE, AgentHealth.HEALTHY)
        assert bus.sequence > prev_seq

    def test_record_activity(self):
        w = AgentWatchdog("a1", "p1")
        w.transition(AgentLifecycle.IDLE, AgentHealth.HEALTHY)
        w.record_activity()
        # Activity recorded, no state change
        assert w.state.lifecycle == AgentLifecycle.IDLE

    def test_should_not_hibernate_when_active(self):
        w = AgentWatchdog("a1", "p1")
        w.transition(AgentLifecycle.ACTIVE, AgentHealth.HEALTHY)
        assert not w.should_hibernate()

    def test_crash_recording(self):
        w = AgentWatchdog("a1", "p1")
        w.record_crash(exit_code=1, error_message="oops")
        assert w.state.health == AgentHealth.UNHEALTHY

    def test_single_crash_no_crash_loop(self):
        w = AgentWatchdog("a1", "p1")
        w.record_crash(exit_code=1)
        assert w.watchdog_status != WatchdogStatus.CRASH_LOOP_UNHEALTHY

    def test_crash_loop_detection(self):
        w = AgentWatchdog("a1", "p1", config=WatchdogConfig(
            crash_loop_threshold=3,
            crash_loop_window_seconds=3600,
        ))
        for i in range(3):
            w.record_crash(exit_code=1)
        assert w.watchdog_status == WatchdogStatus.CRASH_LOOP_UNHEALTHY

    def test_should_not_restart_in_crash_loop(self):
        w = AgentWatchdog("a1", "p1", config=WatchdogConfig(
            crash_loop_threshold=2,
            crash_loop_window_seconds=3600,
        ))
        w.record_crash(exit_code=1)
        w.record_crash(exit_code=1)
        assert w.watchdog_status == WatchdogStatus.CRASH_LOOP_UNHEALTHY
        assert not w.should_restart()

    def test_should_restart_after_single_crash(self):
        w = AgentWatchdog("a1", "p1")
        w.record_crash(exit_code=1)
        assert w.should_restart()

    def test_startup_grace_period(self):
        w = AgentWatchdog("a1", "p1", config=WatchdogConfig(
            startup_grace_seconds=60.0,
        ))
        w.transition(AgentLifecycle.INITIALIZING, AgentHealth.UNKNOWN)
        assert w.within_startup_grace()

    def test_expected_restart_window(self):
        w = AgentWatchdog("a1", "p1", config=WatchdogConfig(
            expected_restart_window_seconds=30.0,
        ))
        w.transition(AgentLifecycle.INITIALIZING, AgentHealth.UNKNOWN)
        assert w.within_expected_restart()

    def test_incident_deduplication(self):
        bus = EventBus()
        w = AgentWatchdog("a1", "p1", bus=bus)
        prev_seq = bus.sequence
        w.open_incident("test incident")
        first_seq = bus.sequence
        assert first_seq > prev_seq

        # Second open should NOT emit (dedup)
        w.open_incident("test incident again")
        assert bus.sequence == first_seq

        # Close and reopen should emit
        w.close_incident()
        w.open_incident("new incident")
        assert bus.sequence > first_seq

    def test_all_watchdog_statuses(self):
        """Verify all status values are defined."""
        for status in WatchdogStatus:
            assert isinstance(status.value, str)

    def test_full_lifecycle_monitoring(self):
        """Monitor an agent through its full lifecycle."""
        w = AgentWatchdog("a1", "p1")

        # Register
        assert w.state.lifecycle == AgentLifecycle.REGISTERED

        # Initialize
        w.transition(AgentLifecycle.INITIALIZING, AgentHealth.UNKNOWN)
        assert w.within_startup_grace()

        # Ready
        w.transition(AgentLifecycle.READY, AgentHealth.HEALTHY)
        assert w.watchdog_status == WatchdogStatus.RUNNING_HEALTHY

        # Active
        w.transition(AgentLifecycle.ACTIVE, AgentHealth.HEALTHY)
        w.record_activity()
        assert w.watchdog_status == WatchdogStatus.RUNNING_HEALTHY

        # Degraded
        w.transition(AgentLifecycle.DEGRADED, AgentHealth.DEGRADED,
                     message="high latency")
        assert w.watchdog_status == WatchdogStatus.RUNNING_DEGRADED

        # Crash
        w.record_crash(exit_code=1)
        assert w.state.health == AgentHealth.UNHEALTHY

        # Terminate
        w.transition(AgentLifecycle.TERMINATED, AgentHealth.HEALTHY)
        assert w.watchdog_status == WatchdogStatus.STOPPED_UNKNOWN
