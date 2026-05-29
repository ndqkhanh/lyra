"""Hardening tests for AgentWatchdog — crash-loop detection, lifecycle/health matrix."""

from __future__ import annotations

import time

from lyra_core.watchdog import (
    AgentWatchdog,
    CrashRecord,
    WatchdogConfig,
    WatchdogStatus,
)

# ── WatchdogConfig ──────────────────────────────────────────────────────


class TestWatchdogConfig:
    def test_default_config(self):
        cfg = WatchdogConfig()
        assert cfg.startup_grace_seconds == 30.0
        assert cfg.crash_loop_threshold == 3
        assert cfg.crash_loop_window_seconds == 300.0
        assert cfg.idle_hibernation_threshold_seconds == 600.0

    def test_custom_config(self):
        cfg = WatchdogConfig(
            startup_grace_seconds=10.0,
            crash_loop_threshold=5,
            crash_loop_window_seconds=120.0,
            idle_hibernation_threshold_seconds=300.0,
        )
        assert cfg.crash_loop_threshold == 5
        assert cfg.crash_loop_window_seconds == 120.0


# ── CrashRecord ─────────────────────────────────────────────────────────


class TestCrashRecord:
    def test_crash_record_fields(self):
        now = time.time()
        cr = CrashRecord(timestamp=now, agent_id="agent-1", exit_code=1, error_message="OOM")
        assert cr.agent_id == "agent-1"
        assert cr.exit_code == 1
        assert cr.error_message == "OOM"

    def test_crash_record_default_message(self):
        cr = CrashRecord(timestamp=time.time(), agent_id="a1", exit_code=0)
        assert cr.error_message == ""


# ── AgentWatchdog Construction ──────────────────────────────────────────


class TestAgentWatchdogConstruction:
    def test_create_watchdog(self):
        wd = AgentWatchdog(agent_id="a1", project_id="p1")
        assert wd.agent_id == "a1"
        assert wd.project_id == "p1"

    def test_default_watchdog_status_is_running_unknown(self):
        wd = AgentWatchdog(agent_id="a1", project_id="p1")
        assert wd.watchdog_status == WatchdogStatus.RUNNING_UNKNOWN

    def test_custom_config_applied(self):
        cfg = WatchdogConfig(startup_grace_seconds=5.0)
        wd = AgentWatchdog(agent_id="a1", project_id="p1", config=cfg)
        assert wd.config.startup_grace_seconds == 5.0

    def test_state_property_returns_agent_state(self):
        wd = AgentWatchdog(agent_id="a1", project_id="p1")
        state = wd.state
        assert state is not None


# ── Lifecycle Transitions ───────────────────────────────────────────────


class TestLifecycleTransitions:
    def test_transition_updates_status(self):
        from lyra_core.protocol import AgentHealth, AgentLifecycle

        wd = AgentWatchdog(agent_id="a1", project_id="p1")
        wd.transition(AgentLifecycle.ACTIVE, AgentHealth.HEALTHY)
        assert wd.watchdog_status == WatchdogStatus.RUNNING_HEALTHY

    def test_transition_to_degraded(self):
        from lyra_core.protocol import AgentHealth, AgentLifecycle

        wd = AgentWatchdog(agent_id="a1", project_id="p1")
        wd.transition(AgentLifecycle.ACTIVE, AgentHealth.DEGRADED)
        assert wd.watchdog_status == WatchdogStatus.RUNNING_DEGRADED

    def test_transition_to_terminated(self):
        from lyra_core.protocol import AgentHealth, AgentLifecycle

        wd = AgentWatchdog(agent_id="a1", project_id="p1")
        wd.transition(AgentLifecycle.TERMINATED, AgentHealth.UNKNOWN)
        assert wd.watchdog_status == WatchdogStatus.STOPPED_UNKNOWN

    def test_transition_to_restarting_unknown(self):
        from lyra_core.protocol import AgentHealth, AgentLifecycle

        wd = AgentWatchdog(agent_id="a1", project_id="p1")
        wd.transition(AgentLifecycle.INITIALIZING, AgentHealth.UNKNOWN)
        assert wd.watchdog_status == WatchdogStatus.RESTARTING_UNKNOWN


# ── Crash Loop Detection ────────────────────────────────────────────────


class TestCrashLoopDetection:
    def test_single_crash_no_loop(self):
        wd = AgentWatchdog(agent_id="a1", project_id="p1")
        wd.record_crash(exit_code=1, error_message="test crash")
        assert wd.watchdog_status == WatchdogStatus.CRASHED_UNHEALTHY

    def test_three_crashes_in_window_triggers_loop(self):
        cfg = WatchdogConfig(crash_loop_threshold=3, crash_loop_window_seconds=3600.0)
        wd = AgentWatchdog(agent_id="a1", project_id="p1", config=cfg)
        wd.record_crash(1)
        wd.record_crash(1)
        wd.record_crash(1)
        assert wd.watchdog_status == WatchdogStatus.CRASH_LOOP_UNHEALTHY

    def test_two_crashes_below_threshold_no_loop(self):
        cfg = WatchdogConfig(crash_loop_threshold=3, crash_loop_window_seconds=3600.0)
        wd = AgentWatchdog(agent_id="a1", project_id="p1", config=cfg)
        wd.record_crash(1)
        wd.record_crash(1)
        assert wd.watchdog_status != WatchdogStatus.CRASH_LOOP_UNHEALTHY

    def test_custom_threshold_respected(self):
        cfg = WatchdogConfig(crash_loop_threshold=2, crash_loop_window_seconds=3600.0)
        wd = AgentWatchdog(agent_id="a1", project_id="p1", config=cfg)
        wd.record_crash(1)
        wd.record_crash(1)
        assert wd.watchdog_status == WatchdogStatus.CRASH_LOOP_UNHEALTHY

    def test_crash_history_pruned_outside_window(self):
        cfg = WatchdogConfig(
            crash_loop_threshold=3, crash_loop_window_seconds=0.0
        )  # immediate prune
        wd = AgentWatchdog(agent_id="a1", project_id="p1", config=cfg)
        wd.record_crash(1)
        wd.record_crash(1)
        wd.record_crash(1)
        # With window=0, only the most recent crash survives pruning
        assert wd.watchdog_status != WatchdogStatus.CRASH_LOOP_UNHEALTHY


# ── Restart Logic ───────────────────────────────────────────────────────


class TestRestartLogic:
    def test_should_restart_when_unhealthy_not_in_loop(self):
        from lyra_core.protocol import AgentHealth, AgentLifecycle

        wd = AgentWatchdog(agent_id="a1", project_id="p1")
        wd.transition(AgentLifecycle.DEGRADED, AgentHealth.UNHEALTHY)
        assert wd.should_restart() is True

    def test_should_not_restart_in_crash_loop(self):
        cfg = WatchdogConfig(crash_loop_threshold=2, crash_loop_window_seconds=3600.0)
        wd = AgentWatchdog(agent_id="a1", project_id="p1", config=cfg)
        wd.record_crash(1)
        wd.record_crash(1)
        assert wd.should_restart() is False

    def test_should_not_restart_when_healthy(self):
        from lyra_core.protocol import AgentHealth, AgentLifecycle

        wd = AgentWatchdog(agent_id="a1", project_id="p1")
        wd.transition(AgentLifecycle.ACTIVE, AgentHealth.HEALTHY)
        assert wd.should_restart() is False

    def test_should_not_restart_when_terminated(self):
        from lyra_core.protocol import AgentHealth, AgentLifecycle

        wd = AgentWatchdog(agent_id="a1", project_id="p1")
        wd.transition(AgentLifecycle.TERMINATED, AgentHealth.UNKNOWN)
        assert wd.should_restart() is False


# ── Hibernation Logic ───────────────────────────────────────────────────


class TestHibernationLogic:
    def test_should_not_hibernate_when_active(self):
        from lyra_core.protocol import AgentHealth, AgentLifecycle

        wd = AgentWatchdog(agent_id="a1", project_id="p1")
        wd.transition(AgentLifecycle.ACTIVE, AgentHealth.HEALTHY)
        assert wd.should_hibernate() is False

    def test_should_not_hibernate_when_recently_active(self):
        from lyra_core.protocol import AgentHealth, AgentLifecycle

        wd = AgentWatchdog(agent_id="a1", project_id="p1")
        wd.transition(AgentLifecycle.IDLE, AgentHealth.HEALTHY)
        wd.record_activity()  # just now
        assert wd.should_hibernate() is False

    def test_should_hibernate_when_idle_long_enough(self):
        from lyra_core.protocol import AgentHealth, AgentLifecycle

        cfg = WatchdogConfig(idle_hibernation_threshold_seconds=0.0)  # immediate
        wd = AgentWatchdog(agent_id="a1", project_id="p1", config=cfg)
        wd.transition(AgentLifecycle.IDLE, AgentHealth.HEALTHY)
        assert wd.should_hibernate() is True


# ── Grace Periods ───────────────────────────────────────────────────────


class TestGracePeriods:
    def test_within_startup_grace(self):
        from lyra_core.protocol import AgentHealth, AgentLifecycle

        cfg = WatchdogConfig(startup_grace_seconds=3600.0)
        wd = AgentWatchdog(agent_id="a1", project_id="p1", config=cfg)
        wd.transition(AgentLifecycle.INITIALIZING, AgentHealth.UNKNOWN)
        assert wd.within_startup_grace() is True

    def test_outside_startup_grace_when_not_initializing(self):
        from lyra_core.protocol import AgentHealth, AgentLifecycle

        wd = AgentWatchdog(agent_id="a1", project_id="p1")
        wd.transition(AgentLifecycle.ACTIVE, AgentHealth.HEALTHY)
        assert wd.within_startup_grace() is False

    def test_within_expected_restart(self):
        from lyra_core.protocol import AgentHealth, AgentLifecycle

        cfg = WatchdogConfig(expected_restart_window_seconds=3600.0)
        wd = AgentWatchdog(agent_id="a1", project_id="p1", config=cfg)
        wd.transition(AgentLifecycle.INITIALIZING, AgentHealth.UNKNOWN)
        assert wd.within_expected_restart() is True


# ── Incident Management ─────────────────────────────────────────────────


class TestIncidentManagement:
    def test_open_incident_sets_flag(self):
        wd = AgentWatchdog(agent_id="a1", project_id="p1")
        assert wd._incident_open is False
        wd.open_incident("test incident")
        assert wd._incident_open is True

    def test_duplicate_open_is_noop(self):
        wd = AgentWatchdog(agent_id="a1", project_id="p1")
        wd.open_incident("first")
        wd.open_incident("second")  # should be deduplicated
        assert wd._incident_open is True

    def test_close_incident_clears_flag(self):
        wd = AgentWatchdog(agent_id="a1", project_id="p1")
        wd.open_incident("test")
        wd.close_incident()
        assert wd._incident_open is False

    def test_close_without_open_is_noop(self):
        wd = AgentWatchdog(agent_id="a1", project_id="p1")
        wd.close_incident()  # should not raise
        assert wd._incident_open is False
