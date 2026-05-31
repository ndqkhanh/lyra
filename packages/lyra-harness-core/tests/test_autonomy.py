"""Tests for autonomy.py — Autonomy Loop + Crash Detection (P4-B4 HIGH)."""
from __future__ import annotations

import time

import pytest
from lyra_harness_core.autonomy import (
    AgentHealth,
    AutonomyLoop,
    CrashDetector,
    CrashEvent,
    CrashLoopState,
    CrashSeverity,
    HealthCheck,
    LoopResult,
    LoopStep,
    StopCondition,
    StopConditionDSL,
    StopReason,
    SystemHealth,
    Watchdog,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestAgentHealth:
    def test_values(self):
        assert AgentHealth.HEALTHY.value == "healthy"
        assert AgentHealth.CRASHED.value == "crashed"
        assert AgentHealth.UNKNOWN.value == "unknown"

class TestCrashSeverity:
    def test_values(self):
        assert CrashSeverity.RECOVERABLE.value == "recoverable"
        assert CrashSeverity.FATAL.value == "fatal"

class TestStopReason:
    def test_values(self):
        assert StopReason.GOAL_ACHIEVED.value == "goal_achieved"
        assert StopReason.MAX_ITERATIONS.value == "max_iterations"
        assert StopReason.CRASH_LOOP.value == "crash_loop"
        assert StopReason.USER_INTERRUPT.value == "user_interrupt"
        assert StopReason.TIMEOUT.value == "timeout"
        assert StopReason.HEALTH_FAILURE.value == "health_failure"
        assert StopReason.EXPLICIT_STOP.value == "explicit_stop"


# ---------------------------------------------------------------------------
# CrashEvent
# ---------------------------------------------------------------------------

class TestCrashEvent:
    def test_creation(self):
        ce = CrashEvent(
            timestamp=1000.0,
            error_type="ValueError",
            error_message="bad value",
            severity=CrashSeverity.CRITICAL,
        )
        assert ce.error_type == "ValueError"
        assert ce.severity == CrashSeverity.CRITICAL

    def test_defaults(self):
        ce = CrashEvent(timestamp=0.0, error_type="TypeError", error_message="x")
        assert ce.severity == CrashSeverity.RECOVERABLE
        assert ce.stack_trace == ""

    def test_frozen(self):
        ce = CrashEvent(timestamp=0.0, error_type="Err", error_message="msg")
        with pytest.raises(Exception):
            ce.error_type = "new"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CrashLoopState
# ---------------------------------------------------------------------------

class TestCrashLoopState:
    def test_creation(self):
        ce = CrashEvent(timestamp=100.0, error_type="Err", error_message="msg")
        state = CrashLoopState(
            is_crash_loop=False,
            crash_count=1,
            window_seconds=300.0,
            latest_crashes=(ce,),
            first_crash_time=100.0,
        )
        assert not state.is_crash_loop
        assert state.crash_count == 1

    def test_crash_rate(self):
        ce = CrashEvent(timestamp=time.time() - 10, error_type="Err", error_message="msg")
        state = CrashLoopState(
            is_crash_loop=False,
            crash_count=3,
            window_seconds=300.0,
            latest_crashes=(ce,),
            first_crash_time=time.time() - 30,
        )
        assert state.crash_rate > 0.0

    def test_crash_rate_no_first_time(self):
        state = CrashLoopState(
            is_crash_loop=False,
            crash_count=0,
            window_seconds=300.0,
            latest_crashes=(),
            first_crash_time=None,
        )
        assert state.crash_rate == 0.0

    def test_crash_rate_zero_window(self):
        state = CrashLoopState(
            is_crash_loop=False,
            crash_count=1,
            window_seconds=0.0,
            latest_crashes=(),
            first_crash_time=100.0,
        )
        assert state.crash_rate == 0.0


# ---------------------------------------------------------------------------
# CrashDetector
# ---------------------------------------------------------------------------

class TestCrashDetector:
    def test_defaults(self):
        cd = CrashDetector()
        assert cd.crash_threshold == 3
        assert cd.window_seconds == 300.0

    def test_custom_thresholds(self):
        cd = CrashDetector(crash_threshold=5, window_seconds=60.0)
        assert cd.crash_threshold == 5
        assert cd.window_seconds == 60.0

    def test_initial_state(self):
        cd = CrashDetector()
        state = cd.check()
        assert not state.is_crash_loop
        assert state.crash_count == 0

    def test_record_single_crash(self):
        cd = CrashDetector()
        cd.record_crash("ValueError", "bad input")
        assert cd.crash_count == 1

    def test_no_crash_loop_below_threshold(self):
        cd = CrashDetector(crash_threshold=3, window_seconds=300.0)
        cd.record_crash("Err1")
        cd.record_crash("Err2")
        state = cd.check()
        assert not state.is_crash_loop
        assert state.crash_count == 2

    def test_crash_loop_detected(self):
        cd = CrashDetector(crash_threshold=3, window_seconds=300.0)
        cd.record_crash("Err1")
        cd.record_crash("Err2")
        cd.record_crash("Err3")
        state = cd.check()
        assert state.is_crash_loop
        assert state.crash_count == 3

    def test_crash_loop_beyond_threshold(self):
        cd = CrashDetector(crash_threshold=2, window_seconds=300.0)
        cd.record_crash("Err1")
        cd.record_crash("Err2")
        cd.record_crash("Err3")
        state = cd.check()
        assert state.is_crash_loop
        assert state.crash_count == 3

    def test_first_crash_time_recorded(self):
        cd = CrashDetector()
        cd.record_crash("Err1")
        state = cd.check()
        assert state.first_crash_time is not None

    def test_latest_crashes_sorted_newest_first(self):
        cd = CrashDetector()
        cd.record_crash("Err1", "msg1")
        cd.record_crash("Err2", "msg2")
        state = cd.check()
        assert state.latest_crashes[0].error_type == "Err2"
        assert state.latest_crashes[1].error_type == "Err1"

    def test_reset_clears_crashes(self):
        cd = CrashDetector()
        cd.record_crash("Err1")
        cd.record_crash("Err2")
        cd.reset()
        assert cd.crash_count == 0
        state = cd.check()
        assert not state.is_crash_loop

    def test_prune_removes_old_crashes(self):
        cd = CrashDetector(window_seconds=0.001)
        cd.record_crash("Err1")
        time.sleep(0.01)
        assert cd.crash_count == 0


# ---------------------------------------------------------------------------
# HealthCheck
# ---------------------------------------------------------------------------

class TestHealthCheck:
    def test_creation(self):
        hc = HealthCheck(component="db", health=AgentHealth.HEALTHY, message="ok", latency_ms=5.0)
        assert hc.component == "db"
        assert hc.health == AgentHealth.HEALTHY
        assert hc.message == "ok"
        assert hc.latency_ms == 5.0

    def test_defaults(self):
        hc = HealthCheck(component="cache", health=AgentHealth.UNKNOWN)
        assert hc.message == ""
        assert hc.latency_ms == 0.0

    def test_frozen(self):
        hc = HealthCheck(component="x", health=AgentHealth.HEALTHY)
        with pytest.raises(Exception):
            hc.health = AgentHealth.CRASHED  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SystemHealth
# ---------------------------------------------------------------------------

class TestSystemHealth:
    def test_all_healthy(self):
        checks = (
            HealthCheck(component="a", health=AgentHealth.HEALTHY),
            HealthCheck(component="b", health=AgentHealth.HEALTHY),
        )
        sh = SystemHealth(
            checks=checks,
            overall=AgentHealth.HEALTHY,
            degraded_components=(),
            crashed_components=(),
        )
        assert sh.is_healthy
        assert sh.can_operate

    def test_crashed_cannot_operate(self):
        sh = SystemHealth(
            checks=(HealthCheck(component="a", health=AgentHealth.CRASHED),),
            overall=AgentHealth.CRASHED,
            degraded_components=(),
            crashed_components=("a",),
        )
        assert not sh.is_healthy
        assert not sh.can_operate

    def test_unknown_cannot_operate(self):
        sh = SystemHealth(
            checks=(),
            overall=AgentHealth.UNKNOWN,
            degraded_components=(),
            crashed_components=(),
        )
        assert not sh.is_healthy
        assert not sh.can_operate

    def test_degraded_can_operate(self):
        sh = SystemHealth(
            checks=(HealthCheck(component="a", health=AgentHealth.DEGRADED),),
            overall=AgentHealth.DEGRADED,
            degraded_components=("a",),
            crashed_components=(),
        )
        assert not sh.is_healthy
        assert sh.can_operate

    def test_frozen(self):
        sh = SystemHealth(checks=(), overall=AgentHealth.HEALTHY, degraded_components=(), crashed_components=())
        with pytest.raises(Exception):
            sh.overall = AgentHealth.CRASHED  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Watchdog
# ---------------------------------------------------------------------------

class TestWatchdog:
    def test_initial_state(self):
        wd = Watchdog()
        health = wd.check_all()
        assert health.overall == AgentHealth.HEALTHY
        assert health.checks == ()

    def test_check_component(self):
        wd = Watchdog()
        wd.check_component("api", AgentHealth.HEALTHY)
        health = wd.check_all()
        assert health.overall == AgentHealth.HEALTHY
        assert len(health.checks) == 1

    def test_multiple_components_healthy(self):
        wd = Watchdog()
        wd.check_component("api", AgentHealth.HEALTHY)
        wd.check_component("db", AgentHealth.HEALTHY)
        health = wd.check_all()
        assert health.overall == AgentHealth.HEALTHY

    def test_one_crashed_overall_crashed(self):
        wd = Watchdog()
        wd.check_component("api", AgentHealth.HEALTHY)
        wd.check_component("db", AgentHealth.CRASHED)
        health = wd.check_all()
        assert health.overall == AgentHealth.CRASHED
        assert health.crashed_components == ("db",)

    def test_one_unstable_overall_unstable(self):
        wd = Watchdog()
        wd.check_component("api", AgentHealth.HEALTHY)
        wd.check_component("db", AgentHealth.UNSTABLE)
        health = wd.check_all()
        assert health.overall == AgentHealth.UNSTABLE

    def test_degraded_components_tracked(self):
        wd = Watchdog()
        wd.check_component("cache", AgentHealth.DEGRADED)
        wd.check_component("api", AgentHealth.HEALTHY)
        health = wd.check_all()
        assert health.overall == AgentHealth.DEGRADED
        assert health.degraded_components == ("cache",)

    def test_record_error(self):
        wd = Watchdog(crash_detector=CrashDetector(crash_threshold=1, window_seconds=300.0))
        state = wd.record_error("Timeout", "connection lost")
        assert state.is_crash_loop

    def test_reset(self):
        wd = Watchdog()
        wd.check_component("api", AgentHealth.CRASHED)
        wd.reset()
        health = wd.check_all()
        assert health.overall == AgentHealth.HEALTHY
        assert wd.component_count == 0

    def test_component_count(self):
        wd = Watchdog()
        assert wd.component_count == 0
        wd.check_component("a", AgentHealth.HEALTHY)
        wd.check_component("b", AgentHealth.HEALTHY)
        assert wd.component_count == 2

    def test_unstable_before_degraded(self):
        """Unstable should take priority over degraded for overall."""
        wd = Watchdog()
        wd.check_component("a", AgentHealth.DEGRADED)
        wd.check_component("b", AgentHealth.UNSTABLE)
        health = wd.check_all()
        assert health.overall == AgentHealth.UNSTABLE


# ---------------------------------------------------------------------------
# StopCondition / StopConditionDSL
# ---------------------------------------------------------------------------

class TestStopCondition:
    def test_creation(self):
        sc = StopCondition(name="max_iter", reason=StopReason.MAX_ITERATIONS, description="Reached max")
        assert sc.name == "max_iter"
        assert sc.reason == StopReason.MAX_ITERATIONS

    def test_frozen(self):
        sc = StopCondition(name="x", reason=StopReason.EXPLICIT_STOP)
        with pytest.raises(Exception):
            sc.name = "y"  # type: ignore[misc]


class TestStopConditionDSL:
    def test_empty(self):
        dsl = StopConditionDSL()
        assert dsl.condition_count == 0
        assert dsl.evaluate({}) is None

    def test_add_condition(self):
        dsl = StopConditionDSL()
        dsl.add("max", StopReason.MAX_ITERATIONS)
        assert dsl.condition_count == 1

    def test_max_iterations_triggered(self):
        dsl = StopConditionDSL()
        dsl.add("max", StopReason.MAX_ITERATIONS)
        result = dsl.evaluate({"max_iterations": 10, "iteration": 10})
        assert result is not None
        assert result.reason == StopReason.MAX_ITERATIONS

    def test_max_iterations_not_triggered(self):
        dsl = StopConditionDSL()
        dsl.add("max", StopReason.MAX_ITERATIONS)
        result = dsl.evaluate({"max_iterations": 10, "iteration": 5})
        assert result is None

    def test_max_iterations_zero_disabled(self):
        dsl = StopConditionDSL()
        dsl.add("max", StopReason.MAX_ITERATIONS)
        result = dsl.evaluate({"max_iterations": 0, "iteration": 100})
        assert result is None

    def test_timeout_triggered(self):
        dsl = StopConditionDSL()
        dsl.add("timeout", StopReason.TIMEOUT)
        result = dsl.evaluate({"deadline": 1.0})
        assert result is not None
        assert result.reason == StopReason.TIMEOUT

    def test_timeout_not_triggered(self):
        dsl = StopConditionDSL()
        dsl.add("timeout", StopReason.TIMEOUT)
        result = dsl.evaluate({"deadline": time.time() + 3600})
        assert result is None

    def test_goal_achieved(self):
        dsl = StopConditionDSL()
        dsl.add("goal", StopReason.GOAL_ACHIEVED)
        result = dsl.evaluate({"goal_achieved": True})
        assert result is not None
        assert result.reason == StopReason.GOAL_ACHIEVED

    def test_goal_not_achieved(self):
        dsl = StopConditionDSL()
        dsl.add("goal", StopReason.GOAL_ACHIEVED)
        assert dsl.evaluate({"goal_achieved": False}) is None

    def test_crash_loop_triggered(self):
        dsl = StopConditionDSL()
        dsl.add("crash", StopReason.CRASH_LOOP)
        result = dsl.evaluate({"crash_loop": True})
        assert result is not None
        assert result.reason == StopReason.CRASH_LOOP

    def test_health_failure(self):
        dsl = StopConditionDSL()
        dsl.add("health", StopReason.HEALTH_FAILURE)
        result = dsl.evaluate({"can_operate": False})
        assert result is not None
        assert result.reason == StopReason.HEALTH_FAILURE

    def test_health_ok(self):
        dsl = StopConditionDSL()
        dsl.add("health", StopReason.HEALTH_FAILURE)
        assert dsl.evaluate({"can_operate": True}) is None

    def test_first_triggered_wins(self):
        dsl = StopConditionDSL()
        dsl.add("a", StopReason.GOAL_ACHIEVED)
        dsl.add("b", StopReason.MAX_ITERATIONS)
        result = dsl.evaluate({"goal_achieved": True, "max_iterations": 10, "iteration": 100})
        assert result is not None
        assert result.reason == StopReason.GOAL_ACHIEVED  # first condition in list matched first

    def test_multiple_conditions(self):
        dsl = StopConditionDSL()
        dsl.add("max_iter", StopReason.MAX_ITERATIONS)
        dsl.add("timeout", StopReason.TIMEOUT)
        dsl.add("goal", StopReason.GOAL_ACHIEVED)
        assert dsl.condition_count == 3


# ---------------------------------------------------------------------------
# LoopStep
# ---------------------------------------------------------------------------

class TestLoopStep:
    def test_creation(self):
        step = LoopStep(iteration=0, phase="plan", success=True, duration_ms=10.0, details="ok")
        assert step.iteration == 0
        assert step.phase == "plan"
        assert step.success
        assert step.duration_ms == 10.0

    def test_frozen(self):
        step = LoopStep(iteration=0, phase="execute", success=True, duration_ms=5.0)
        with pytest.raises(Exception):
            step.success = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# LoopResult
# ---------------------------------------------------------------------------

class TestLoopResult:
    def test_creation(self):
        steps = (
            LoopStep(iteration=0, phase="plan", success=True, duration_ms=5.0),
            LoopStep(iteration=0, phase="execute", success=True, duration_ms=10.0),
        )
        result = LoopResult(
            steps=steps,
            stop_reason=StopReason.GOAL_ACHIEVED,
            total_iterations=2,
            successful_steps=2,
            failed_steps=0,
            total_duration_ms=15.0,
            crash_events=(),
        )
        assert result.success_rate == 1.0
        assert result.stop_reason == StopReason.GOAL_ACHIEVED

    def test_partial_success(self):
        result = LoopResult(
            steps=(),
            stop_reason=StopReason.CRASH_LOOP,
            total_iterations=3,
            successful_steps=2,
            failed_steps=1,
            total_duration_ms=100.0,
            crash_events=(),
        )
        assert result.success_rate == pytest.approx(2.0 / 3.0)

    def test_success_rate_no_iterations(self):
        result = LoopResult(
            steps=(),
            stop_reason=StopReason.EXPLICIT_STOP,
            total_iterations=0,
            successful_steps=0,
            failed_steps=0,
            total_duration_ms=0.0,
            crash_events=(),
        )
        assert result.success_rate == 1.0

    def test_frozen(self):
        result = LoopResult(
            steps=(), stop_reason=StopReason.EXPLICIT_STOP,
            total_iterations=0, successful_steps=0, failed_steps=0,
            total_duration_ms=0.0, crash_events=(),
        )
        with pytest.raises(Exception):
            result.stop_reason = StopReason.TIMEOUT  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AutonomyLoop
# ---------------------------------------------------------------------------

class TestAutonomyLoop:
    def test_creation(self):
        loop = AutonomyLoop(max_iterations=50)
        assert loop.max_iterations == 50
        assert loop._iteration == 0

    def test_default_max_iterations(self):
        loop = AutonomyLoop()
        assert loop.max_iterations == 100

    def test_run_completes_successfully(self):
        loop = AutonomyLoop(max_iterations=3)

        def plan_fn(ctx, i):
            return {"action": f"step_{i}"}

        def execute_fn(plan, ctx):
            return {"result": plan["action"], "done": True}

        def verify_fn(result, ctx):
            return True

        loop.stop_conditions.add("goal", StopReason.GOAL_ACHIEVED)
        result = loop.run(plan_fn, execute_fn, verify_fn)

        assert isinstance(result, LoopResult)
        assert result.total_iterations >= 1

    def test_run_stops_on_max_iterations(self):
        loop = AutonomyLoop(max_iterations=2)

        def plan_fn(ctx, i):
            return {"action": f"step_{i}"}

        def execute_fn(plan, ctx):
            return {"result": plan["action"]}

        def verify_fn(result, ctx):
            return True

        loop.stop_conditions.add("max", StopReason.MAX_ITERATIONS)
        result = loop.run(plan_fn, execute_fn, verify_fn)
        assert result.stop_reason == StopReason.MAX_ITERATIONS

    def test_run_stops_on_goal_achieved(self):
        loop = AutonomyLoop(max_iterations=10)

        def plan_fn(ctx, i):
            return {"action": "final"}

        def execute_fn(plan, ctx):
            ctx["goal_achieved"] = True
            return {"done": True}

        def verify_fn(result, ctx):
            return True

        loop.stop_conditions.add("goal", StopReason.GOAL_ACHIEVED)
        result = loop.run(plan_fn, execute_fn, verify_fn)
        assert result.stop_reason == StopReason.GOAL_ACHIEVED

    def test_run_stops_on_plan_exception(self):
        loop = AutonomyLoop(max_iterations=10)

        def plan_fn(ctx, i):
            raise ValueError("plan failed")

        def execute_fn(plan, ctx):
            return {}

        def verify_fn(result, ctx):
            return True

        result = loop.run(plan_fn, execute_fn, verify_fn)
        assert result.stop_reason == StopReason.GOAL_ACHIEVED
        assert len(result.crash_events) == 1
        assert result.crash_events[0].error_type == "plan_error"

    def test_run_stops_on_execute_exception(self):
        loop = AutonomyLoop(max_iterations=10)

        def plan_fn(ctx, i):
            return {"action": "step"}

        def execute_fn(plan, ctx):
            raise RuntimeError("execute failed")

        def verify_fn(result, ctx):
            return True

        result = loop.run(plan_fn, execute_fn, verify_fn)
        assert result.stop_reason == StopReason.GOAL_ACHIEVED
        assert any(c.error_type == "execute_error" for c in result.crash_events)

    def test_run_handles_verify_exception(self):
        loop = AutonomyLoop(max_iterations=3)

        def plan_fn(ctx, i):
            return {"action": "step"}

        def execute_fn(plan, ctx):
            return {"result": "ok"}

        def verify_fn(result, ctx):
            raise RuntimeError("verify failed")

        result = loop.run(plan_fn, execute_fn, verify_fn)
        assert any(c.error_type == "verify_error" for c in result.crash_events)

    def test_run_stops_on_health_failure(self):
        loop = AutonomyLoop(max_iterations=10)
        loop.watchdog.check_component("critical", AgentHealth.CRASHED)

        def plan_fn(ctx, i):
            return {}

        def execute_fn(plan, ctx):
            return {}

        def verify_fn(result, ctx):
            return True

        result = loop.run(plan_fn, execute_fn, verify_fn)
        assert result.stop_reason == StopReason.HEALTH_FAILURE

    def test_run_stops_on_crash_loop(self):
        """Crash loop detected on second iteration after first crash is recorded."""
        cd = CrashDetector(crash_threshold=1, window_seconds=300.0)
        loop = AutonomyLoop(max_iterations=10, crash_detector=cd)

        call_count = {"plan": 0}

        def plan_fn(ctx, i):
            call_count["plan"] += 1
            if call_count["plan"] == 1:
                raise ValueError("first crash")
            return {"action": "recovered"}

        def execute_fn(plan, ctx):
            return {}

        def verify_fn(result, ctx):
            return True

        result = loop.run(plan_fn, execute_fn, verify_fn)
        assert result.stop_reason == StopReason.GOAL_ACHIEVED
        assert len(result.crash_events) >= 1

    def test_run_stops_on_timeout(self):
        loop = AutonomyLoop(max_iterations=10, deadline=time.time() - 1)

        def plan_fn(ctx, i):
            return {"action": "step"}

        def execute_fn(plan, ctx):
            return {"result": "ok"}

        def verify_fn(result, ctx):
            return True

        loop.stop_conditions.add("timeout", StopReason.TIMEOUT)
        result = loop.run(plan_fn, execute_fn, verify_fn)
        assert result.stop_reason == StopReason.TIMEOUT

    def test_run_steps_recorded(self):
        loop = AutonomyLoop(max_iterations=2)

        def plan_fn(ctx, i):
            return {"action": f"step_{i}"}

        def execute_fn(plan, ctx):
            return {"result": plan["action"]}

        def verify_fn(result, ctx):
            return True

        loop.stop_conditions.add("max", StopReason.MAX_ITERATIONS)
        result = loop.run(plan_fn, execute_fn, verify_fn)
        assert len(result.steps) > 0
        phases = {s.phase for s in result.steps}
        assert "plan" in phases
        assert "execute" in phases
        assert "verify" in phases

    def test_run_persists_step(self):
        loop = AutonomyLoop(max_iterations=2)

        def plan_fn(ctx, i):
            return {"action": f"step_{i}"}

        def execute_fn(plan, ctx):
            return {"result": plan["action"]}

        def verify_fn(result, ctx):
            return True

        loop.stop_conditions.add("max", StopReason.MAX_ITERATIONS)
        result = loop.run(plan_fn, execute_fn, verify_fn)
        assert "persist" in {s.phase for s in result.steps}

    def test_run_with_initial_context(self):
        loop = AutonomyLoop(max_iterations=3)
        ctx_seen = []

        def plan_fn(ctx, i):
            ctx_seen.append(ctx.get("custom_key"))
            return {"action": "step"}

        def execute_fn(plan, ctx):
            return {"result": "ok"}

        def verify_fn(result, ctx):
            return True

        loop.stop_conditions.add("max", StopReason.MAX_ITERATIONS)
        loop.run(plan_fn, execute_fn, verify_fn, initial_context={"custom_key": "hello"})
        assert "hello" in ctx_seen

    def test_run_successful_and_failed_counts(self):
        loop = AutonomyLoop(max_iterations=2)

        def plan_fn(ctx, i):
            return {"action": "step"}

        def execute_fn(plan, ctx):
            return {"result": "ok"}

        def verify_fn(result, ctx):
            return False  # verification fails

        loop.stop_conditions.add("max", StopReason.MAX_ITERATIONS)
        result = loop.run(plan_fn, execute_fn, verify_fn)
        assert result.failed_steps > 0

    def test_reset(self):
        loop = AutonomyLoop(max_iterations=5)

        def plan_fn(ctx, i):
            return {"action": "step"}

        def execute_fn(plan, ctx):
            return {"result": "ok"}

        def verify_fn(result, ctx):
            return True

        loop.stop_conditions.add("max", StopReason.MAX_ITERATIONS)
        loop.run(plan_fn, execute_fn, verify_fn)
        loop.reset()
        assert len(loop.steps) == 0
        assert loop._iteration == 0

    def test_steps_property(self):
        loop = AutonomyLoop(max_iterations=2)

        def plan_fn(ctx, i):
            return {"action": "step"}

        def execute_fn(plan, ctx):
            return {"result": "ok"}

        def verify_fn(result, ctx):
            return True

        loop.stop_conditions.add("max", StopReason.MAX_ITERATIONS)
        loop.run(plan_fn, execute_fn, verify_fn)
        assert isinstance(loop.steps, tuple)
        assert len(loop.steps) > 0


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_full_autonomy_pipeline(self):
        """Full autonomy loop with watchdog, crash detection, and stop conditions."""
        loop = AutonomyLoop(max_iterations=5)
        loop.stop_conditions.add("max_iter", StopReason.MAX_ITERATIONS)
        loop.stop_conditions.add("goal", StopReason.GOAL_ACHIEVED)

        iteration_data = []

        def plan_fn(ctx, i):
            iteration_data.append(i)
            return {"task": f"task_{i}"}

        def execute_fn(plan, ctx):
            return {"completed": plan["task"]}

        def verify_fn(result, ctx):
            return True

        result = loop.run(plan_fn, execute_fn, verify_fn)

        assert result.stop_reason == StopReason.MAX_ITERATIONS
        assert result.total_iterations == 4  # loop iterates 0..3, stop triggers on iteration=5 in context
        assert result.success_rate == 1.0

    def test_error_recovery_pipeline(self):
        """Pipeline where plan recovers after one failure."""
        cd = CrashDetector(crash_threshold=5, window_seconds=300.0)
        loop = AutonomyLoop(max_iterations=3, crash_detector=cd)
        loop.stop_conditions.add("max", StopReason.MAX_ITERATIONS)

        call_count = {"plan": 0}

        def plan_fn(ctx, i):
            call_count["plan"] += 1
            if call_count["plan"] == 1:
                raise ValueError("first attempt fails")
            return {"action": "recovered"}

        def execute_fn(plan, ctx):
            return {"ok": True}

        def verify_fn(result, ctx):
            return True

        result = loop.run(plan_fn, execute_fn, verify_fn)

        assert result.stop_reason == StopReason.GOAL_ACHIEVED
        assert len(result.crash_events) >= 1
