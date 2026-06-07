"""Tests for autonomy loop."""
import asyncio
import pytest
from lyra.autonomy.loop import AutonomyLoop, LoopState, RunMode
from lyra.autonomy.recovery import CrashRecovery, RecoveryAction


class TestAutonomyLoop:
    def test_initial_state(self):
        loop = AutonomyLoop()
        assert loop.state == LoopState.IDLE
        assert loop.run_mode == RunMode.CONTINUOUS

    def test_run_mode_once(self):
        loop = AutonomyLoop(run_mode=RunMode.ONCE)
        assert loop.run_mode == RunMode.ONCE

    def test_run_mode_scheduled(self):
        loop = AutonomyLoop(run_mode=RunMode.SCHEDULED)
        assert loop.run_mode == RunMode.SCHEDULED

    def test_health_ok_initial(self):
        loop = AutonomyLoop()
        assert loop._health_ok() is True

    def test_health_fails_after_max_failures(self):
        loop = AutonomyLoop(max_consecutive_failures=3)
        loop._failure_count = 3
        assert loop._health_ok() is False

    def test_stop(self):
        loop = AutonomyLoop()
        loop.stop()
        assert loop.state == LoopState.STOPPED

    def test_stats(self):
        loop = AutonomyLoop()
        stats = loop.stats()
        assert stats["state"] == "idle"
        assert stats["tasks_completed"] == 0
        assert stats["failure_count"] == 0

    def test_is_idle_fresh(self):
        loop = AutonomyLoop(max_idle_seconds=1)
        assert loop.is_idle is False

    @pytest.mark.asyncio
    async def test_start_with_empty_queue_stops_on_idle(self):
        loop = AutonomyLoop(run_mode=RunMode.ONCE, max_idle_seconds=0)
        await loop.start(task_queue=None)
        assert loop.state in (LoopState.IDLE, LoopState.RUNNING)


class TestCrashRecovery:
    def test_initial_action_is_retry(self):
        cr = CrashRecovery()
        assert cr.current_action == RecoveryAction.RETRY

    def test_escalates_to_escalate(self):
        cr = CrashRecovery()
        for _ in range(10):
            cr.record_failure()
        assert cr.current_action == RecoveryAction.ESCALATE
        assert cr.should_escalate is True

    def test_record_success_resets(self):
        cr = CrashRecovery()
        cr.record_failure()
        cr.record_failure()
        cr.record_success()
        assert cr._recovery_index == 0
        assert cr.current_action == RecoveryAction.RETRY

    def test_stats(self):
        cr = CrashRecovery()
        cr.record_failure()
        stats = cr.stats()
        assert stats["total_failures"] == 1
        assert "recovery_level" in stats
        assert "current_action" in stats
