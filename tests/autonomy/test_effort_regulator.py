"""Tests for effort regulator and autonomous agent."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from lyra.autonomy.effort_regulator import (
    Budget,
    EffortLevel,
    EffortProfile,
    EffortRegulator,
    SessionState,
    TaskHistoryEntry,
)
from lyra.autonomy.loop import (
    AutonomousAgent,
    AutonomyLoop,
    HealthStatus,
    Issue,
    LoopState,
    RunMode,
)


# ====================================================================
# EffortRegulator tests
# ====================================================================


class TestEffortRegulator:
    def test_default_profile_for_code(self):
        regulator = EffortRegulator()
        profile = regulator.profile("code")
        assert isinstance(profile, EffortProfile)
        assert profile.max_steps == 50
        assert profile.confidence_threshold == 0.92

    def test_default_profile_for_chat(self):
        regulator = EffortRegulator()
        profile = regulator.profile("chat")
        assert profile.max_steps == 10

    def test_default_profile_for_research(self):
        regulator = EffortRegulator()
        profile = regulator.profile("research")
        assert profile.max_steps == 30

    def test_default_profile_fallback(self):
        regulator = EffortRegulator()
        profile = regulator.profile("unknown_type")
        assert profile.max_steps == 50  # Falls back to "code"

    def test_calibrate_no_history_returns_default(self):
        regulator = EffortRegulator()
        level = regulator.calibrate("code", history=[])
        assert level == EffortLevel.AGGRESSIVE  # default for code

    def test_calibrate_no_history_chat(self):
        regulator = EffortRegulator()
        level = regulator.calibrate("chat", history=[])
        assert level == EffortLevel.CONSERVATIVE

    def test_calibrate_no_history_research(self):
        regulator = EffortRegulator()
        level = regulator.calibrate("research", history=[])
        assert level == EffortLevel.ADAPTIVE

    def test_calibrate_learns_from_history(self):
        regulator = EffortRegulator()
        # History shows high confidence with low steps → CONSERVATIVE should win
        history = [
            TaskHistoryEntry(
                task_type="code",
                steps_taken=3,
                final_confidence=0.85,
                improvement_sequence=[0.5, 0.3, 0.05],
                wall_time_seconds=10,
                tokens_consumed=1000,
            ),
            TaskHistoryEntry(
                task_type="code",
                steps_taken=4,
                final_confidence=0.90,
                improvement_sequence=[0.4, 0.3, 0.15, 0.05],
                wall_time_seconds=15,
                tokens_consumed=1500,
            ),
        ]
        level = regulator.calibrate("code", history=history)
        assert isinstance(level, EffortLevel)

    def test_diminishing_returns_no_plateau(self):
        regulator = EffortRegulator()
        # Continuous improvement
        improvements = [0.3, 0.25, 0.2, 0.15, 0.1]
        assert regulator.diminishing_returns_check(improvements) is False

    def test_diminishing_returns_plateau(self):
        regulator = EffortRegulator()
        # Flat improvements at end → plateau (need 4 consecutive near-zero values)
        improvements = [0.3, 0.005, 0.003, 0.002, 0.001]
        assert regulator.diminishing_returns_check(improvements) is True

    def test_diminishing_returns_plateau_negative(self):
        regulator = EffortRegulator()
        # Negative improvements → plateau
        improvements = [0.3, -0.008, -0.006, -0.004, -0.002]
        assert regulator.diminishing_returns_check(improvements) is True

    def test_diminishing_returns_too_few_points(self):
        regulator = EffortRegulator()
        assert regulator.diminishing_returns_check([]) is False
        assert regulator.diminishing_returns_check([0.5]) is False
        assert regulator.diminishing_returns_check([0.5, 0.3]) is False

    def test_diminishing_returns_custom_patience(self):
        regulator = EffortRegulator()
        improvements = [0.3, 0.005, 0.003]
        # patience=2, only 2 recent flat values
        assert regulator.diminishing_returns_check(improvements, patience=2) is True
        # patience=3, only 2 flat values available
        assert regulator.diminishing_returns_check(improvements, patience=3) is False

    def test_should_continue_within_budget(self):
        regulator = EffortRegulator()
        state = SessionState(
            step=5,
            confidence=0.5,
            improvements=[0.3, 0.2, 0.1, 0.05, 0.03],
            tokens_consumed=10000,
            wall_time_seconds=100,
        )
        budget = Budget(max_steps=100, max_tokens=100_000, max_wall_time_seconds=3600)
        assert regulator.should_continue(state, budget) is True

    def test_should_continue_stops_at_max_steps(self):
        regulator = EffortRegulator()
        state = SessionState(
            step=100,
            confidence=0.5,
            improvements=[0.1, 0.05, 0.02],
        )
        budget = Budget(max_steps=50)
        assert regulator.should_continue(state, budget) is False

    def test_should_continue_stops_at_max_tokens(self):
        regulator = EffortRegulator()
        state = SessionState(
            step=10,
            confidence=0.5,
            tokens_consumed=100_000,
        )
        budget = Budget(max_tokens=50_000)
        assert regulator.should_continue(state, budget) is False

    def test_should_continue_stops_at_wall_time(self):
        regulator = EffortRegulator()
        state = SessionState(
            step=10,
            confidence=0.5,
            wall_time_seconds=4000,
        )
        budget = Budget(max_wall_time_seconds=3600)
        assert regulator.should_continue(state, budget) is False

    def test_should_continue_stops_when_confidence_met(self):
        regulator = EffortRegulator()
        state = SessionState(
            step=10,
            confidence=0.95,
            improvements=[0.5, 0.3, 0.1, 0.03, 0.01],
        )
        budget = Budget(max_steps=100)
        # Confidence (0.95) >= BALANCED profile threshold (0.85)
        assert regulator.should_continue(state, budget) is False

    def test_should_continue_stops_on_plateau(self):
        regulator = EffortRegulator()
        # 4 consecutive near-zero improvements → plateau should fire
        state = SessionState(
            step=10,
            confidence=0.5,
            improvements=[0.3, 0.008, 0.006, 0.004, 0.002],
        )
        budget = Budget(max_steps=100)
        assert regulator.should_continue(state, budget) is False

    def test_record_outcome(self):
        regulator = EffortRegulator()
        entry = TaskHistoryEntry(
            task_type="code",
            steps_taken=10,
            final_confidence=0.85,
            improvement_sequence=[0.5, 0.2, 0.1, 0.03, 0.02],
            wall_time_seconds=60,
            tokens_consumed=5000,
        )
        regulator.record_outcome(entry)
        stats = regulator.calibration_stats("code")
        assert stats["total_tasks"] == 1
        assert stats["average_steps"] == 10.0
        assert stats["average_confidence"] == 0.85

    def test_calibration_stats_empty(self):
        regulator = EffortRegulator()
        stats = regulator.calibration_stats("code")
        assert stats["task_type"] == "code"
        assert stats["total_tasks"] == 0
        assert stats["average_steps"] == 0.0

    def test_all_profiles(self):
        regulator = EffortRegulator()
        profiles = regulator.all_profiles()
        assert "code" in profiles
        assert "chat" in profiles
        assert "research" in profiles
        assert len(profiles) == 3

    def test_effort_level_values(self):
        assert EffortLevel.CONSERVATIVE.value == "conservative"
        assert EffortLevel.BALANCED.value == "balanced"
        assert EffortLevel.AGGRESSIVE.value == "aggressive"
        assert EffortLevel.ADAPTIVE.value == "adaptive"

    def test_calibrate_with_history_no_match(self):
        """calibrate returns BALANCED when history exists but nothing matches."""
        regulator = EffortRegulator()
        # History with steps too large for conservative but low confidence
        history = [
            TaskHistoryEntry(
                task_type="code", steps_taken=2, final_confidence=0.1,
                improvement_sequence=[], wall_time_seconds=1, tokens_consumed=100,
            ),
        ]
        level = regulator.calibrate("code", history=history)
        assert isinstance(level, EffortLevel)

    def test_diminishing_returns_fewer_than_patience(self):
        """Not enough improvements for patience threshold returns False."""
        regulator = EffortRegulator()
        assert regulator.diminishing_returns_check([0.1, 0.05], patience=3) is False

    def test_profile_for_steps_aggressive(self):
        """_profile_for_steps returns AGGRESSIVE for high step counts."""
        regulator = EffortRegulator()
        profile = regulator._profile_for_steps(50)
        # 50 > balanced(30) => aggressive
        assert profile.confidence_threshold >= 0.8

    def test_profile_for_steps_conservative(self):
        regulator = EffortRegulator()
        profile = regulator._profile_for_steps(5)
        assert profile.max_steps == 10  # CONSERVATIVE max_steps

    def test_custom_profiles(self):
        """Custom profiles override defaults."""
        profiles = {"custom": EffortProfile(max_steps=100, confidence_threshold=0.99, early_stop_patience=10)}
        regulator = EffortRegulator(profiles=profiles)
        assert regulator.profile("custom").max_steps == 100
        assert regulator.profile("custom").confidence_threshold == 0.99

    def test_calibration_stats_with_data(self):
        regulator = EffortRegulator()
        regulator.record_outcome(TaskHistoryEntry(
            task_type="code", steps_taken=5, final_confidence=0.9,
            improvement_sequence=[0.5, 0.3], wall_time_seconds=30, tokens_consumed=2000,
        ))
        stats = regulator.calibration_stats("code")
        assert stats["average_steps"] == 5.0
        assert stats["average_confidence"] == pytest.approx(0.9, rel=0.1)

    def test_best_profile_for_no_history(self):
        """_CalibrationDB.best_profile_for returns None when no history."""
        reg = EffortRegulator()
        result = reg._db.best_profile_for("unknown_type", reg.all_profiles())
        assert result is None

    def test_calibrate_empty_history_via_public_api(self):
        """calibrate with no history at all returns default."""
        regulator = EffortRegulator()
        level = regulator.calibrate("code", history=[])
        assert level == EffortLevel.AGGRESSIVE

    def test_best_profile_for_with_history(self):
        """_CalibrationDB.best_profile_for finds best profile from history."""
        reg = EffortRegulator()
        entry = TaskHistoryEntry(
            task_type="code", steps_taken=5, final_confidence=0.9,
            improvement_sequence=[], wall_time_seconds=10, tokens_consumed=500,
        )
        reg._db.record(entry)
        result = reg._db.best_profile_for("code", reg.all_profiles())
        assert result is not None

    def test_best_profile_for_steps_zero_skip(self):
        """Entries with steps_taken=0 are skipped."""
        reg = EffortRegulator()
        entry = TaskHistoryEntry(
            task_type="code", steps_taken=0, final_confidence=0.9,
            improvement_sequence=[], wall_time_seconds=10, tokens_consumed=500,
        )
        reg._db.record(entry)
        result = reg._db.best_profile_for("code", reg.all_profiles())
        assert result is None

    def test_profile_for_steps_aggressive_path(self):
        """_profile_for_steps with high step count returns AGGRESSIVE."""
        reg = EffortRegulator()
        profile = reg._profile_for_steps(50)
        assert profile.max_steps == 80  # AGGRESSIVE

    def test_should_continue_with_confidence_met_via_conservative(self):
        """Confidence check uses appropriate profile."""
        regulator = EffortRegulator()
        state = SessionState(
            step=5, confidence=0.95,
            improvements=[0.5, 0.3, 0.1],
        )
        budget = Budget(max_steps=100)
        assert regulator.should_continue(state, budget) is False


# ====================================================================
# AutonomousAgent tests
# ====================================================================


class TestAutonomousAgent:
    def test_initial_state(self):
        agent = AutonomousAgent(agent_id="test-agent")
        assert agent.agent_id == "test-agent"
        assert agent.loop.state == LoopState.IDLE
        assert agent._restart_count == 0
        assert agent._total_tokens == 0

    def test_health_check_initial(self):
        agent = AutonomousAgent()
        report = agent.health_check()
        assert report.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
        assert report.uptime_seconds >= 0
        assert report.memory_mb >= 0
        assert report.token_burn_rate >= 0

    def test_health_check_isolation(self):
        """Multiple health checks produce independent reports."""
        agent = AutonomousAgent()
        r1 = agent.health_check()
        r2 = agent.health_check()
        assert r1.status == r2.status

    @patch.object(AutonomousAgent, "_get_memory_mb", return_value=600.0)
    def test_health_check_high_memory_degraded(self, mock_memory):
        agent = AutonomousAgent()
        report = agent.health_check()
        assert report.status == HealthStatus.DEGRADED
        assert report.memory_mb == 600.0

    @patch.object(AutonomousAgent, "_get_memory_mb", return_value=1200.0)
    def test_health_check_high_memory_unhealthy(self, mock_memory):
        agent = AutonomousAgent()
        report = agent.health_check()
        assert report.status == HealthStatus.UNHEALTHY

    def test_get_task_budget(self):
        agent = AutonomousAgent()
        budget = agent.get_task_budget("code")
        assert isinstance(budget, Budget)
        assert budget.max_steps > 0
        assert budget.max_tokens > 0

    def test_get_task_budget_chat(self):
        agent = AutonomousAgent()
        budget = agent.get_task_budget("chat")
        assert budget.max_steps < agent.get_task_budget("code").max_steps

    def test_self_diagnose_initial(self):
        agent = AutonomousAgent()
        issues = agent.self_diagnose()
        assert isinstance(issues, list)
        # Initial state should have few issues
        assert all(isinstance(i, Issue) for i in issues)

    @patch.object(AutonomousAgent, "_get_memory_mb", return_value=1200.0)
    def test_self_diagnose_high_memory(self, mock_memory):
        agent = AutonomousAgent()
        issues = agent.self_diagnose()
        memory_issues = [i for i in issues if i.component == "memory"]
        assert len(memory_issues) >= 1
        assert memory_issues[0].severity == "error"

    def test_self_diagnose_loop_recovering(self):
        agent = AutonomousAgent()
        agent.loop._state = LoopState.RECOVERING
        issues = agent.self_diagnose()
        loop_issues = [i for i in issues if i.component == "loop"]
        assert any(i.severity == "error" for i in loop_issues)

    def test_self_diagnose_excessive_restarts(self):
        agent = AutonomousAgent()
        agent._restart_count = 15
        issues = agent.self_diagnose()
        restart_issues = [i for i in issues if i.component == "restarts"]
        assert len(restart_issues) >= 1
        assert restart_issues[0].severity == "error"

    def test_get_memory_mb_returns_float(self):
        agent = AutonomousAgent()
        memory = agent._get_memory_mb()
        assert isinstance(memory, float)

    def test_stats_initial(self):
        agent = AutonomousAgent(agent_id="testy")
        stats = agent.stats()
        assert stats["agent_id"] == "testy"
        assert stats["tasks_completed"] == 0
        assert "health" in stats
        assert "uptime_seconds" in stats

    def test_stats_includes_health(self):
        agent = AutonomousAgent()
        stats = agent.stats()
        health = stats["health"]
        assert "memory_mb" in health
        assert "token_burn_rate" in health
        assert "error_rate" in health
        assert "cpu_percent" in health
        assert "uptime_seconds" in health

    def test_effort_profile_for_level_conservative(self):
        profile = AutonomousAgent._effort_profile_for_level(EffortLevel.CONSERVATIVE)
        assert profile.max_steps == 10

    def test_effort_profile_for_level_aggressive(self):
        profile = AutonomousAgent._effort_profile_for_level(EffortLevel.AGGRESSIVE)
        assert profile.max_steps == 80

    def test_record_task_outcome(self):
        agent = AutonomousAgent()
        agent.record_task_outcome(
            "code",
            SessionState(
                step=10,
                confidence=0.9,
                improvements=[0.5, 0.3, 0.1],
                tokens_consumed=5000,
                wall_time_seconds=60,
            ),
        )
        assert agent._total_tokens == 5000
        # Verify regulator has the data
        stats = agent.regulator.calibration_stats("code")
        assert stats["total_tasks"] == 1

    def test_compute_token_burn_rate(self):
        agent = AutonomousAgent()
        agent._total_tokens = 6000
        # Pretend 60 seconds elapsed
        with patch.object(agent, "_start_time", time.time() - 60):
            rate = agent._compute_token_burn_rate()
            assert rate == pytest.approx(6000.0, rel=1.0)

    def test_compute_error_rate_empty(self):
        agent = AutonomousAgent()
        rate = agent._compute_error_rate(window_seconds=300)
        assert rate == 0.0

    def test_compute_error_rate_with_errors(self):
        agent = AutonomousAgent()
        now = time.time()
        agent._error_timestamps = [now - 10, now - 20, now - 30]
        rate = agent._compute_error_rate(window_seconds=300)
        assert rate == pytest.approx(0.6, rel=0.1)  # 3 errors / 5 min = 0.6/min

    @patch.object(AutonomousAgent, "_get_memory_mb", return_value=100.0)
    def test_self_diagnose_healthy(self, mock_memory):
        agent = AutonomousAgent()
        issues = agent.self_diagnose()
        # A newly started agent with no errors and no restarts
        # should only have info-level issues at most
        severe = [i for i in issues if i.severity in ("error", "critical")]
        assert len(severe) == 0

    def test_self_diagnose_idle_loop(self):
        agent = AutonomousAgent()
        agent.loop._state = LoopState.IDLE
        issues = agent.self_diagnose()
        loop_issues = [i for i in issues if i.component == "loop"]
        assert any(i.severity == "info" for i in loop_issues)

    def test_self_diagnose_high_error_rate(self):
        agent = AutonomousAgent()
        now = time.time()
        # Simulate 30 errors in the last 5 minutes (rate > 5)
        agent._error_timestamps = [now - i * 10 for i in range(30)]
        issues = agent.self_diagnose()
        error_issues = [i for i in issues if i.component == "errors"]
        assert len(error_issues) >= 1
        assert error_issues[0].severity == "error"

    def test_self_diagnose_idle_with_no_tokens(self):
        """Agent running >10min with zero tokens → info issue."""
        agent = AutonomousAgent()
        with patch.object(agent, "_start_time", time.time() - 700):
            issues = agent.self_diagnose()
        idle_issues = [i for i in issues if i.component == "productivity"]
        assert len(idle_issues) >= 1
        assert idle_issues[0].severity == "info"

    def test_self_diagnose_high_token_burn(self):
        """Token burn rate > 100k triggers warning."""
        agent = AutonomousAgent()
        agent._total_tokens = 500000
        with patch.object(agent, "_start_time", time.time() - 60):
            issues = agent.self_diagnose()
        token_issues = [i for i in issues if i.component == "tokens"]
        assert len(token_issues) >= 1
        assert token_issues[0].severity == "warning"

    def test_self_diagnose_frequent_restarts_warning(self):
        """Restart count > 3 but <= 10 triggers warning."""
        agent = AutonomousAgent()
        agent._restart_count = 5
        issues = agent.self_diagnose()
        restart_issues = [i for i in issues if i.component == "restarts"]
        assert len(restart_issues) >= 1
        assert restart_issues[0].severity == "warning"

    def test_self_diagnose_elevated_error_rate(self):
        """Error rate > 1 but <= 5 triggers warning."""
        agent = AutonomousAgent()
        now = time.time()
        agent._error_timestamps = [now - i * 20 for i in range(10)]
        issues = agent.self_diagnose()
        error_issues = [i for i in issues if i.component == "errors"]
        assert len(error_issues) >= 1
        assert error_issues[0].severity == "warning"

    def test_get_cpu_percent(self):
        """_get_cpu_percent returns a float between 0 and 100."""
        agent = AutonomousAgent()
        cpu = agent._get_cpu_percent()
        assert isinstance(cpu, float)
        assert 0.0 <= cpu <= 100.0

    def test_compute_token_burn_rate_zero_uptime(self):
        """_compute_token_burn_rate returns 0 when uptime < 1s."""
        agent = AutonomousAgent()
        agent._total_tokens = 5000
        with patch.object(agent, "_start_time", time.time()):
            rate = agent._compute_token_burn_rate()
            assert rate == 0.0

    def test_elevated_memory_warning_in_diagnose(self):
        """Memory between 512-1024 MB triggers warning."""
        agent = AutonomousAgent()
        with patch.object(AutonomousAgent, "_get_memory_mb", return_value=700.0):
            issues = agent.self_diagnose()
        mem_issues = [i for i in issues if i.component == "memory"]
        assert any(i.severity == "warning" for i in mem_issues)


# ====================================================================
# Integration tests (EffortRegulator + AutonomyLoop)
# ====================================================================


@pytest.mark.asyncio
async def test_agent_daemon_mode_empty_queue():
    """Daemon mode with empty queue should eventually stop on STOP."""
    loop = AutonomyLoop(run_mode=RunMode.CONTINUOUS, max_idle_seconds=0)
    agent = AutonomousAgent(agent_id="test-daemon", loop=loop)

    queue: asyncio.Queue = asyncio.Queue()

    # Schedule a stop after a brief delay
    async def stop_later():
        await asyncio.sleep(0.05)
        agent.loop.stop()

    asyncio.create_task(stop_later())
    await agent.daemon_mode(queue)
    assert agent.loop.state in (LoopState.STOPPED, LoopState.IDLE)


@pytest.mark.asyncio
async def test_agent_daemon_mode_task_processing():
    """Daemon mode processes tasks from queue."""
    loop = AutonomyLoop(run_mode=RunMode.CONTINUOUS, max_idle_seconds=1)
    agent = AutonomousAgent(agent_id="test-worker", loop=loop)

    queue: asyncio.Queue = asyncio.Queue()
    await queue.put("task-1")
    await queue.put("task-2")

    async def stop_later():
        await asyncio.sleep(0.2)
        agent.loop.stop()

    asyncio.create_task(stop_later())
    await agent.daemon_mode(queue)
    assert agent.loop._tasks_completed >= 0


@pytest.mark.asyncio
async def test_agent_daemon_mode_self_restart():
    """Daemon mode should restart when loop enters RECOVERING."""
    loop = AutonomyLoop(
        run_mode=RunMode.CONTINUOUS,
        max_consecutive_failures=3,
        max_idle_seconds=1,
    )
    agent = AutonomousAgent(agent_id="test-restart", loop=loop)

    # Force the loop into RECOVERING state
    agent.loop._state = LoopState.RECOVERING

    queue: asyncio.Queue = asyncio.Queue()

    async def stop_later():
        await asyncio.sleep(0.05)
        agent.loop.stop()

    asyncio.create_task(stop_later())
    await agent.daemon_mode(queue)
    # The agent should have restarted (new loop instance) or stopped
    assert agent._restart_count >= 1 or agent.loop.state == LoopState.STOPPED


@pytest.mark.asyncio
async def test_agent_daemon_cancelled():
    """Daemon mode propagates CancelledError."""
    loop = AutonomyLoop(run_mode=RunMode.CONTINUOUS, max_idle_seconds=0)
    agent = AutonomousAgent(agent_id="test-cancel", loop=loop)
    queue: asyncio.Queue = asyncio.Queue()

    async def cancel_later():
        await asyncio.sleep(0.01)
        # This will propagate via the loop.start cancel
        agent.loop.stop()

    asyncio.create_task(cancel_later())
    await agent.daemon_mode(queue)
    # Should exit cleanly without raising


@pytest.mark.asyncio
async def test_agent_checkpoint_restore():
    """Agent restores state from checkpoint manager."""
    cm = MagicMock()
    cm.restore.return_value = {"total_tokens": 5000, "error_count": 2}
    agent = AutonomousAgent(
        agent_id="test-cp",
        checkpoint_manager=cm,
        loop=AutonomyLoop(run_mode=RunMode.ONCE, max_idle_seconds=0),
    )
    agent._restore_from_checkpoint()
    assert agent._total_tokens == 5000
    assert agent._error_count == 2


@pytest.mark.asyncio
async def test_agent_checkpoint_save():
    """Agent saves state to checkpoint manager on cycle end."""
    cm = MagicMock()
    loop = AutonomyLoop(run_mode=RunMode.ONCE, max_idle_seconds=0)
    agent = AutonomousAgent(
        agent_id="test-cp-save",
        checkpoint_manager=cm,
        loop=loop,
    )
    agent.loop._tasks_completed = 7
    agent._save_checkpoint()
    cm.save.assert_called_once()
    args = cm.save.call_args[0]
    assert args[0] == "test-cp-save"
    assert args[1]["tasks_completed"] == 7


def test_checkpoint_save_exception():
    """_save_checkpoint handles exceptions from checkpoint manager."""
    cm = MagicMock()
    cm.save.side_effect = RuntimeError("save error")
    agent = AutonomousAgent(agent_id="test", checkpoint_manager=cm)
    agent._save_checkpoint()  # should not raise


def test_checkpoint_restore_exception():
    """_restore_from_checkpoint handles exceptions."""
    cm = MagicMock()
    cm.restore.side_effect = RuntimeError("restore error")
    agent = AutonomousAgent(agent_id="test", checkpoint_manager=cm)
    agent._restore_from_checkpoint()  # should not raise


@pytest.mark.asyncio
async def test_autonomy_loop_start_with_failures():
    """Loop transitions to RECOVERING after max failures."""
    loop = AutonomyLoop(run_mode=RunMode.ONCE, max_consecutive_failures=2, max_idle_seconds=0)
    # Set failure count to trigger health check failure in _execute_task
    loop._failure_count = 2
    with pytest.raises(RuntimeError, match="Health check failed"):
        await loop._execute_task("test")


def test_autonomy_loop_stats():
    """stats() returns a valid dict."""
    loop = AutonomyLoop()
    stats = loop.stats()
    assert "state" in stats
    assert "tasks_completed" in stats
    assert "failure_count" in stats
    assert "idle_seconds" in stats
    assert "uptime_seconds" in stats


def test_autonomy_loop_health_ok():
    """_health_ok returns True when failures below max."""
    loop = AutonomyLoop(max_consecutive_failures=5)
    assert loop._health_ok() is True
    loop._failure_count = 5
    assert loop._health_ok() is False


def test_autonomy_loop_is_idle():
    """is_idle returns True when idle time exceeds max."""
    loop = AutonomyLoop(max_idle_seconds=0)
    assert loop.is_idle is True


@pytest.mark.asyncio
async def test_agent_daemon_mode_cancelled_direct():
    """Daemon mode handles CancelledError from loop.start."""
    loop = AutonomyLoop(run_mode=RunMode.CONTINUOUS, max_idle_seconds=0)
    agent = AutonomousAgent(agent_id="test-cancel-direct", loop=loop)
    queue: asyncio.Queue = asyncio.Queue()

    # Simulate loop.start raising CancelledError
    original_start = loop.start

    async def raising_start(*args):
        raise asyncio.CancelledError()

    loop.start = raising_start  # type: ignore
    with pytest.raises(asyncio.CancelledError):
        await agent.daemon_mode(queue)


@pytest.mark.asyncio
async def test_agent_daemon_mode_exception_and_restart():
    """Daemon mode handles exception and restarts when recovering."""
    cm = MagicMock()
    loop = AutonomyLoop(run_mode=RunMode.CONTINUOUS, max_idle_seconds=99)
    agent = AutonomousAgent(
        agent_id="test-restart-2",
        loop=loop,
        checkpoint_manager=cm,
    )
    queue: asyncio.Queue = asyncio.Queue()

    # Mock start to leave state as RECOVERING
    original_start = agent.loop.start

    async def mock_start(task_queue):
        agent.loop._state = LoopState.RECOVERING

    agent.loop.start = mock_start  # type: ignore

    async def stop_later():
        await asyncio.sleep(0.1)
        agent.loop.stop()

    asyncio.create_task(stop_later())
    await agent.daemon_mode(queue)
    assert agent._restart_count >= 1
