"""Tests for Relay Race — continuous autonomous operation with baton-pass checkpointing."""

import time

import pytest
from lyra_core.safety.relay_race import (
    Baton,
    LegResult,
    LegStatus,
    RelayConfig,
    RelayRace,
    RelayState,
)


class TestLegStatus:
    def test_status_values(self):
        assert LegStatus.PENDING.value == "pending"
        assert LegStatus.RUNNING.value == "running"
        assert LegStatus.COMPLETED.value == "completed"
        assert LegStatus.FAILED.value == "failed"
        assert LegStatus.TIMEOUT.value == "timeout"


class TestRelayState:
    def test_state_values(self):
        assert RelayState.IDLE.value == "idle"
        assert RelayState.RUNNING.value == "running"
        assert RelayState.PAUSED.value == "paused"
        assert RelayState.RECOVERING.value == "recovering"
        assert RelayState.COMPLETED.value == "completed"


class TestBaton:
    def test_baton_creation(self):
        baton = Baton(
            relay_id="relay-001",
            leg_index=0,
            state_snapshot=(("key", "value"),),
            progress=0.0,
            started_at=time.time(),
            handed_off_at=time.time(),
            accumulated_reward=0.0,
        )
        assert baton.relay_id == "relay-001"
        assert baton.leg_index == 0
        assert baton.progress == 0.0

    def test_baton_immutable(self):
        b = Baton(relay_id="r1", leg_index=0, state_snapshot=(), progress=0.0, started_at=0.0, handed_off_at=0.0, accumulated_reward=0.0)
        with pytest.raises(Exception):
            b.progress = 1.0


class TestLegResult:
    def test_leg_result_completed(self):
        baton = Baton("r1", 1, (("k", "v"),), 0.5, 0.0, 10.0, 5.0)
        result = LegResult(
            leg_index=1,
            status=LegStatus.COMPLETED,
            duration_sec=10.0,
            output="all done",
            error="",
            reward=5.0,
            baton=baton,
        )
        assert result.status == LegStatus.COMPLETED
        assert result.baton is not None
        assert result.output == "all done"

    def test_leg_result_failed(self):
        result = LegResult(
            leg_index=2,
            status=LegStatus.FAILED,
            duration_sec=5.0,
            output="",
            error="connection timeout",
            reward=0.0,
            baton=None,
        )
        assert result.status == LegStatus.FAILED
        assert result.baton is None
        assert "timeout" in result.error

    def test_leg_result_immutable(self):
        r = LegResult(0, LegStatus.COMPLETED, 1.0, "ok", "", 1.0, None)
        with pytest.raises(Exception):
            r.status = LegStatus.FAILED


class TestRelayConfig:
    def test_default_config(self):
        config = RelayConfig()
        assert config.max_leg_duration_sec == 1800.0
        assert config.max_legs == 16
        assert config.auto_recover is True

    def test_custom_config(self):
        config = RelayConfig(max_legs=10, max_leg_duration_sec=600.0, auto_recover=False)
        assert config.max_legs == 10
        assert config.auto_recover is False


class TestRelayRace:
    def test_initial_state(self):
        relay = RelayRace()
        assert relay.state == RelayState.IDLE
        assert len(relay.leg_results) == 0

    def test_start_race(self):
        relay = RelayRace()
        baton = relay.start({"task": "deploy"})
        assert relay.state == RelayState.RUNNING
        assert isinstance(baton, Baton)
        assert baton.relay_id is not None
        assert baton.leg_index == 0

    def test_run_leg_success(self):
        relay = RelayRace()
        baton = relay.start({"task": "test"})

        def execute(b):
            return "completed successfully", 10.0

        result = relay.run_leg(baton, execute)
        assert result.status == LegStatus.COMPLETED
        assert result.reward == 10.0
        assert result.baton is not None
        assert result.baton.leg_index == 1

    def test_run_leg_failure_with_recovery(self):
        relay = RelayRace()
        baton = relay.start({"task": "risky"})

        def fail_execute(_):
            raise RuntimeError("boom")

        result = relay.run_leg(baton, fail_execute)
        assert result.status == LegStatus.FAILED
        assert "boom" in result.error

    def test_run_leg_max_legs_reached(self):
        config = RelayConfig(max_legs=1)
        relay = RelayRace(config=config)
        baton = relay.start({"task": "single"})

        def ok(_):
            return "done", 1.0

        result = relay.run_leg(baton, ok)
        assert result.status == LegStatus.COMPLETED

    def test_get_checkpoint(self):
        relay = RelayRace()
        relay.start({"task": "cp"})
        cp = relay.get_checkpoint()
        assert cp is not None
        assert isinstance(cp, Baton)

    def test_pause_and_resume(self):
        relay = RelayRace()
        relay.start({"task": "pausable"})
        relay.pause()
        assert relay.state == RelayState.PAUSED
        baton = relay.resume()
        assert relay.state == RelayState.RUNNING
        assert baton is not None

    def test_cannot_resume_when_not_paused(self):
        relay = RelayRace()
        baton = relay.resume()
        assert baton is None

    def test_stats(self):
        relay = RelayRace()
        baton = relay.start({"task": "stats"})

        def ok(b):
            return "ok", 1.0

        relay.run_leg(baton, ok)
        stats = relay.stats()
        assert "state" in stats
        assert "total_legs" in stats
        assert "completed" in stats
        assert "failed" in stats
        assert "total_reward" in stats
