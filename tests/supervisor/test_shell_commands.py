"""Tests for src/lyra/supervisor/shell_commands.py — 85%+ coverage target.

Tests the CLI command functions and formatting helpers by mocking the
FleetOrchestrator and optional circuit breaker dependency.
"""

from __future__ import annotations

import datetime
from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from lyra.supervisor.fleet import AgentConfig, FleetOrchestrator, FleetStatus, SessionProgress
from lyra.supervisor.shell_commands import (
    _fmt_cost,
    _fmt_duration,
    _fmt_time,
    _session_state_char,
    _term_width,
    cmd_fleet_kill,
    cmd_fleet_list,
    cmd_fleet_logs,
    cmd_fleet_start,
    cmd_fleet_status,
    cmd_fleet_stop,
    cmd_fleet_top,
)
from lyra.supervisor.state import ProcessState, SessionInfo, SessionState


# =========================================================================
# Formatting helpers
# =========================================================================


class TestFmtTime:
    def test_none(self):
        assert _fmt_time(None) == " -- "

    def test_valid(self):
        dt = datetime.datetime(2025, 6, 1, 14, 30, 0, tzinfo=datetime.timezone.utc)
        result = _fmt_time(dt)
        assert "14:30:00" in result


class TestFmtDuration:
    def test_seconds(self):
        assert _fmt_duration(30) == "30s"

    def test_minutes(self):
        assert _fmt_duration(125) == "2m05s"

    def test_hours(self):
        assert _fmt_duration(3725) == "1h02m05s"


class TestFmtCost:
    def test_under_one(self):
        assert _fmt_cost(0.5) == "500m"

    def test_over_one(self):
        assert _fmt_cost(2.34) == "2.34"


class TestTermWidth:
    def test_normal(self):
        with patch("shutil.get_terminal_size") as mock:
            mock.return_value.columns = 100
            assert _term_width() == 100

    def test_fallback(self):
        with patch("shutil.get_terminal_size", side_effect=ImportError):
            assert _term_width() == 80

    def test_value_error(self):
        with patch("shutil.get_terminal_size", side_effect=ValueError):
            assert _term_width() == 80


# =========================================================================
# _session_state_char
# =========================================================================


class TestSessionStateChar:
    def _make_info(self, state: SessionState) -> SessionInfo:
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        return SessionInfo(
            session_id="s1", name="test", state=state,
            process_state=ProcessState.ALIVE,
            working_dir="/tmp", created_at=now, last_active=now,
        )

    def test_none(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = None
        assert _session_state_char(fleet, "unknown") == "?"

    def test_working(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = self._make_info(SessionState.WORKING)
        assert _session_state_char(fleet, "s1") == "R"

    def test_idle(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = self._make_info(SessionState.IDLE)
        assert _session_state_char(fleet, "s1") == "I"

    def test_stopped(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = self._make_info(SessionState.STOPPED)
        assert _session_state_char(fleet, "s1") == "S"

    def test_failed(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = self._make_info(SessionState.FAILED)
        assert _session_state_char(fleet, "s1") == "F"

    def test_completed(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = self._make_info(SessionState.COMPLETED)
        assert _session_state_char(fleet, "s1") == "C"

    def test_needs_input(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = self._make_info(SessionState.NEEDS_INPUT)
        assert _session_state_char(fleet, "s1") == "W"

    def test_unknown_state(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        info = MagicMock(spec=SessionInfo)
        info.session_id = "s1"
        info.name = "test"
        info.state = MagicMock()
        info.state.value = "MYSTERY"
        info.process_state = ProcessState.ALIVE
        info.working_dir = "/tmp"
        info.created_at = datetime.datetime.now(tz=datetime.timezone.utc)
        info.last_active = datetime.datetime.now(tz=datetime.timezone.utc)
        fleet.get_session_info.return_value = info
        assert _session_state_char(fleet, "s1") == "?"


# =========================================================================
# Helpers for creating test data
# =========================================================================


def _make_status(sessions: list[tuple[str, int, float, int]] | None = None) -> FleetStatus:
    if sessions is None:
        sessions = [("s1", 0, 0.0, 0)]
    return FleetStatus(
        total_sessions=len(sessions),
        active_count=sum(1 for _ in sessions),
        stagnant_count=0,
        gpu_allocated_count=0,
        sessions=tuple(
            SessionProgress(
                session_id=sid,
                checkpoint_count=ck,
                stagnation_level=stg,
                cost_estimate=cost,
            )
            for sid, ck, cost, stg in sessions
        ),
    )


def _make_info(
    session_id: str = "s1",
    name: str = "agent-1",
    state: SessionState = SessionState.WORKING,
) -> SessionInfo:
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    return SessionInfo(
        session_id=session_id, name=name, state=state,
        process_state=ProcessState.ALIVE,
        working_dir="/tmp/work", created_at=now, last_active=now,
    )


# =========================================================================
# cmd_fleet_start
# =========================================================================


class TestCmdFleetStart:
    def test_start_success(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.spawn_agent.return_value = "abc123"
        config = AgentConfig(name="test-agent", working_dir="/tmp")
        result = cmd_fleet_start(fleet, config)
        assert "spawned" in result
        assert "abc123" in result

    def test_start_runtime_error(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.spawn_agent.side_effect = RuntimeError("at capacity")
        config = AgentConfig(name="test-agent", working_dir="/tmp")
        result = cmd_fleet_start(fleet, config)
        assert "ERROR" in result
        assert "at capacity" in result

    def test_start_generic_error(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.spawn_agent.side_effect = ValueError("bad config")
        config = AgentConfig(name="test-agent", working_dir="/tmp")
        result = cmd_fleet_start(fleet, config)
        assert "ERROR" in result
        assert "bad config" in result


# =========================================================================
# cmd_fleet_stop
# =========================================================================


class TestCmdFleetStop:
    def test_stop_success(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_status([("s1", 0, 0.0, 0)])
        result = cmd_fleet_stop(fleet)
        assert "Stopped 1 session" in result

    def test_stop_no_sessions(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_status([])
        result = cmd_fleet_stop(fleet)
        assert "No active sessions" in result

    def test_stop_partial_failure(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_status([
            ("s1", 0, 0.0, 0), ("s2", 0, 0.0, 0),
        ])
        fleet.kill_session.side_effect = [None, RuntimeError("boom")]
        result = cmd_fleet_stop(fleet)
        assert "Stopped 1" in result

    def test_stop_status_raises(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.side_effect = RuntimeError("fleet down")
        result = cmd_fleet_stop(fleet)
        assert "ERROR" in result


# =========================================================================
# cmd_fleet_status
# =========================================================================


class TestCmdFleetStatus:
    def test_empty_fleet(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_status([])
        result = cmd_fleet_status(fleet)
        assert "empty" in result

    def test_status_raises(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.side_effect = RuntimeError("boom")
        result = cmd_fleet_status(fleet)
        assert "ERROR" in result

    def test_wide_terminal(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_status([("s1", 3, 1.5, 0)])
        fleet.get_session_info.return_value = _make_info("s1", "test-agent")
        with patch("lyra.supervisor.shell_commands._term_width", return_value=120):
            result = cmd_fleet_status(fleet)
            assert "SESSION ID" in result
            assert "s1" in result
            assert "test-agent" in result

    def test_narrow_terminal(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_status([("s1", 3, 1.5, 0)])
        fleet.get_session_info.return_value = _make_info("s1", "test-agent")
        with patch("lyra.supervisor.shell_commands._term_width", return_value=60):
            result = cmd_fleet_status(fleet)
            assert "SESSION" in result
            assert "s1" in result

    def test_narrow_terminal_stagnation(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_status([("s1", 3, 1.5, 2)])
        fleet.get_session_info.return_value = _make_info("s1")
        with patch("lyra.supervisor.shell_commands._term_width", return_value=60):
            result = cmd_fleet_status(fleet)
            assert "L2" in result

    def test_narrow_terminal_no_info(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_status([("s1", 0, 0.0, 0)])
        fleet.get_session_info.return_value = None
        with patch("lyra.supervisor.shell_commands._term_width", return_value=60):
            result = cmd_fleet_status(fleet)
            assert "s1" in result

    def test_wide_terminal_no_info(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_status([("s1", 0, 0.0, 0)])
        fleet.get_session_info.return_value = None
        with patch("lyra.supervisor.shell_commands._term_width", return_value=120):
            result = cmd_fleet_status(fleet)
            assert "s1" in result
            assert "UNKNOWN" in result


# =========================================================================
# cmd_fleet_kill
# =========================================================================


class TestCmdFleetKill:
    def test_kill_success(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = _make_info("s1", "agent-x")
        result = cmd_fleet_kill(fleet, "s1")
        assert "killed" in result
        fleet.kill_session.assert_called_once_with("s1")

    def test_kill_not_found(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = None
        result = cmd_fleet_kill(fleet, "s1")
        assert "not found" in result

    def test_kill_raises(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = _make_info("s1")
        fleet.kill_session.side_effect = RuntimeError("permission denied")
        result = cmd_fleet_kill(fleet, "s1")
        assert "ERROR" in result


# =========================================================================
# cmd_fleet_logs
# =========================================================================


class TestCmdFleetLogs:
    def test_logs_not_found(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = None
        result = cmd_fleet_logs(fleet, "s1")
        assert "not found" in result

    def test_logs_with_checkpoint_manager(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = _make_info("s1", "agent-y")

        # Simulate checkpoint manager
        cm = MagicMock()
        cm.list_checkpoints.return_value = [MagicMock(created_at=datetime.datetime.now(tz=datetime.timezone.utc))]
        cm.recover.return_value = {"step": "42", "result": "success", "extra": "data"}
        fleet._checkpoint_manager = cm

        result = cmd_fleet_logs(fleet, "s1")
        assert "Last Checkpoint" in result
        assert "step" in result
        assert "result" in result
        assert "extra" in result

    def test_logs_no_checkpoint_manager(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = _make_info("s1", "agent-z")
        fleet._checkpoint_manager = None

        result = cmd_fleet_logs(fleet, "s1")
        assert "No log data" in result

    def test_logs_checkpoint_manager_none_checkpoints(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = _make_info("s1")
        cm = MagicMock()
        cm.list_checkpoints.return_value = []
        fleet._checkpoint_manager = cm
        result = cmd_fleet_logs(fleet, "s1")
        assert "No log data" in result

    def test_logs_checkpoint_list_raises(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = _make_info("s1")
        cm = MagicMock()
        cm.list_checkpoints.side_effect = RuntimeError("ckpt fail")
        fleet._checkpoint_manager = cm
        result = cmd_fleet_logs(fleet, "s1")
        assert "No log data" in result

    def test_logs_with_tail_limit(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.get_session_info.return_value = _make_info("s1")
        cm = MagicMock()
        cm.list_checkpoints.return_value = [MagicMock(created_at=datetime.datetime.now(tz=datetime.timezone.utc))]
        cm.recover.return_value = {f"key_{i}": f"val_{i}" for i in range(50)}
        fleet._checkpoint_manager = cm
        result = cmd_fleet_logs(fleet, "s1", tail_lines=5)
        lines = result.split("\n")
        # Only count lines after "=== Last Checkpoint State ==="
        checkpoint_section = False
        kv_lines = 0
        for line in lines:
            if "=== Last Checkpoint State ===" in line:
                checkpoint_section = True
                continue
            if checkpoint_section and line.startswith("  "):
                kv_lines += 1
        # Should have at most 5 key-value lines
        assert kv_lines <= 5


# =========================================================================
# cmd_fleet_top
# =========================================================================


class TestCmdFleetTop:
    def test_top_empty(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_status([])
        fleet.daemon_status.side_effect = AttributeError("no daemon_status")
        result = cmd_fleet_top(fleet)
        assert "LYRA FLEET TOP" in result

    def test_top_with_daemon_health(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_status([("s1", 5, 2.0, 0)])
        fleet.get_session_info.return_value = _make_info("s1", "top-agent")

        health = MagicMock()
        health.uptime_seconds = 3600
        health.cpu_percent = 12.5
        health.memory_usage_mb = 256.0
        health.error_rate = 0.5
        fleet.daemon_status.return_value = health

        with patch("lyra.supervisor.shell_commands._term_width", return_value=120):
            result = cmd_fleet_top(fleet)
            assert "LYRA FLEET TOP" in result
            assert "Daemon uptime" in result
            assert "s1" in result
            assert "top-agent" in result

    def test_top_daemon_status_raises(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_status([("s1", 0, 0.0, 0)])
        fleet.get_session_info.return_value = _make_info("s1")
        fleet.daemon_status.side_effect = Exception("health error")
        result = cmd_fleet_top(fleet)
        assert "LYRA FLEET TOP" in result
        assert "Daemon" not in result

    def test_top_with_circuit_breaker(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_status([("s1", 0, 0.0, 0)])
        fleet.get_session_info.return_value = _make_info("s1")

        cb = MagicMock()
        health_cb = MagicMock()
        health_cb.circuit_state.value = "OPEN"
        cb.session_health.return_value = health_cb

        from lyra.supervisor.circuit_breaker import LoopHealth, CircuitState
        class FakeCBHealth:
            circuit_state = CircuitState.OPEN

        cb.session_health.return_value = FakeCBHealth()

        result = cmd_fleet_top(fleet, circuit_breaker=cb)
        assert "OPEN" in result

    def test_top_circuit_breaker_closed_no_indicator(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_status([("s1", 0, 0.0, 0)])
        fleet.get_session_info.return_value = _make_info("s1")

        from lyra.supervisor.circuit_breaker import CircuitState
        class FakeCBHealth:
            circuit_state = CircuitState.CLOSED

        cb = MagicMock()
        cb.session_health.return_value = FakeCBHealth()

        result = cmd_fleet_top(fleet, circuit_breaker=cb)
        assert "CLOSED" not in result

    def test_top_circuit_breaker_raises(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_status([("s1", 0, 0.0, 0)])
        fleet.get_session_info.return_value = _make_info("s1")

        cb = MagicMock()
        cb.session_health.side_effect = RuntimeError("cb error")

        result = cmd_fleet_top(fleet, circuit_breaker=cb)
        assert "LYRA FLEET TOP" in result  # doesn't crash

    def test_top_status_raises(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.side_effect = RuntimeError("no fleet")
        result = cmd_fleet_top(fleet)
        assert "ERROR" in result

    def test_top_no_info_fallback(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_status([("s1", 0, 0.0, 0)])
        fleet.get_session_info.return_value = None
        fleet.daemon_status.side_effect = AttributeError("no daemon")
        with patch("lyra.supervisor.shell_commands._term_width", return_value=120):
            result = cmd_fleet_top(fleet)
            assert "s1" in result
            assert "UNKNOWN" in result


# =========================================================================
# cmd_fleet_list
# =========================================================================


class TestCmdFleetList:
    def test_list_empty(self):
        fleet = MagicMock(spec=FleetOrchestrator)
        fleet.fleet_status.return_value = _make_status([])
        result = cmd_fleet_list(fleet)
        assert "empty" in result
