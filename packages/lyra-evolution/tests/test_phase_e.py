"""Tests for Phase E: closed-loop controller, Voyager, Reflexion, stability."""
from __future__ import annotations

import pytest

from lyra_evolution.stability import BudgetViolation, StabilityBudget, StabilityState
from lyra_evolution.control_record import ControlRecord, new_control_record
from lyra_evolution.voyager import SkillCandidate, SkillLibrary, VoyagerAccumulator
from lyra_evolution.reflexion import ReflexionEngine, ReflexionLesson
from lyra_evolution.controller import ClosedLoopController, ControllerConfig, HaltSignal


# ------------------------------------------------------------------ #
# StabilityBudget / StabilityState                                     #
# ------------------------------------------------------------------ #

class TestStabilityBudget:
    def test_defaults_no_violations(self):
        state = StabilityState()
        violations = state.check(StabilityBudget())
        assert violations == []

    def test_cost_violation(self):
        budget = StabilityBudget(max_cost_usd=1.0)
        state = StabilityState()
        state.record_cost(2.0)
        violations = state.check(budget)
        names = {v.budget_name for v in violations}
        assert "cost_usd" in names

    def test_retry_violation(self):
        budget = StabilityBudget(max_retry_count=2)
        state = StabilityState()
        state.record_retry()
        state.record_retry()
        state.record_retry()
        violations = state.check(budget)
        assert any(v.budget_name == "retry_count" for v in violations)

    def test_unsafe_action_violation(self):
        budget = StabilityBudget(max_unsafe_actions=0)
        state = StabilityState()
        state.record_unsafe_action()
        violations = state.check(budget)
        assert any(v.budget_name == "unsafe_actions" for v in violations)

    def test_failed_tests_violation(self):
        budget = StabilityBudget(max_failed_tests=2)
        state = StabilityState()
        for _ in range(3):
            state.record_failed_test()
        violations = state.check(budget)
        assert any(v.budget_name == "failed_tests" for v in violations)

    def test_behavior_drift_violation(self):
        budget = StabilityBudget(max_behavior_drift=0.2)
        state = StabilityState()
        state.set_behavior_drift(0.5)
        violations = state.check(budget)
        assert any(v.budget_name == "behavior_drift" for v in violations)

    def test_excess_is_positive(self):
        v = BudgetViolation("cost_usd", 3.0, 1.0)
        assert v.excess == pytest.approx(2.0)


# ------------------------------------------------------------------ #
# ControlRecord                                                        #
# ------------------------------------------------------------------ #

class TestControlRecord:
    def test_factory_sets_identity(self):
        rec = new_control_record("sess-1", "run-1", 3, "span-99")
        assert rec.session_id == "sess-1"
        assert rec.run_id == "run-1"
        assert rec.turn_index == 3
        assert rec.aer_span_id == "span-99"

    def test_defaults_all_zero(self):
        rec = new_control_record("s", "r", 0)
        assert rec.token_retry_count == 0
        assert rec.step_tool_retries == 0
        assert not rec.hitl_pending
        assert rec.fleet_sre_alert == ""

    def test_to_dict_includes_all_fields(self):
        rec = new_control_record("s", "r", 0)
        d = rec.to_dict()
        assert "session_id" in d
        assert "episode_lesson" in d
        assert "skill_verified" in d


# ------------------------------------------------------------------ #
# VoyagerAccumulator                                                   #
# ------------------------------------------------------------------ #

class _AlwaysPassVerifier:
    def verify(self, candidate):
        return True, "looks good"

class _AlwaysFailVerifier:
    def verify(self, candidate):
        return False, "test failed"


class TestVoyagerAccumulator:
    def test_accepted_skill_in_library(self):
        lib = SkillLibrary()
        acc = VoyagerAccumulator(lib, _AlwaysPassVerifier())
        cand = SkillCandidate("greet", "def greet(): return 'hi'")
        passed, _ = acc.submit(cand)
        assert passed
        assert lib.get("greet") is not None
        assert lib.size == 1

    def test_rejected_skill_not_in_library(self):
        lib = SkillLibrary()
        acc = VoyagerAccumulator(lib, _AlwaysFailVerifier())
        cand = SkillCandidate("bad", "def bad(): raise ValueError()")
        passed, feedback = acc.submit(cand)
        assert not passed
        assert lib.size == 0
        assert "test failed" in feedback

    def test_acceptance_rate(self):
        lib = SkillLibrary()
        acc = VoyagerAccumulator(lib, _AlwaysPassVerifier())
        for i in range(3):
            acc.submit(SkillCandidate(f"s{i}", "pass"))
        assert acc.acceptance_rate == pytest.approx(1.0)

    def test_zero_attempts_rate(self):
        acc = VoyagerAccumulator(SkillLibrary(), _AlwaysPassVerifier())
        assert acc.acceptance_rate == 0.0

    def test_library_list(self):
        lib = SkillLibrary()
        acc = VoyagerAccumulator(lib, _AlwaysPassVerifier())
        acc.submit(SkillCandidate("a", "pass"))
        acc.submit(SkillCandidate("b", "pass"))
        assert len(lib.list()) == 2


# ------------------------------------------------------------------ #
# ReflexionEngine                                                      #
# ------------------------------------------------------------------ #

class TestReflexionEngine:
    def test_record_and_retrieve(self):
        engine = ReflexionEngine()
        lesson = ReflexionLesson(
            aer_span_id="span-1",
            session_id="sess-1",
            turn_index=2,
            lesson="always validate input",
            improvement_actions=["add guard"],
        )
        engine.record(lesson)
        lessons = engine.lessons_for_session("sess-1")
        assert len(lessons) == 1
        assert lessons[0].lesson == "always validate input"

    def test_empty_span_id_raises(self):
        with pytest.raises(ValueError, match="aer_span_id"):
            ReflexionLesson(aer_span_id="", session_id="s", turn_index=0, lesson="ok")

    def test_empty_lesson_raises(self):
        with pytest.raises(ValueError, match="lesson"):
            ReflexionLesson(aer_span_id="span-1", session_id="s", turn_index=0, lesson="  ")

    def test_lessons_for_span(self):
        engine = ReflexionEngine()
        engine.record(ReflexionLesson("span-A", "sess-1", 0, "lesson A"))
        engine.record(ReflexionLesson("span-B", "sess-1", 1, "lesson B"))
        assert len(engine.lessons_for_span("span-A")) == 1

    def test_all_improvement_actions(self):
        engine = ReflexionEngine()
        engine.record(ReflexionLesson("s1", "sess-1", 0, "L1", ["action-1", "action-2"]))
        engine.record(ReflexionLesson("s2", "sess-1", 1, "L2", ["action-3"]))
        actions = engine.all_improvement_actions("sess-1")
        assert len(actions) == 3

    def test_total_lessons(self):
        engine = ReflexionEngine()
        engine.record(ReflexionLesson("s1", "sess-1", 0, "L1"))
        engine.record(ReflexionLesson("s2", "sess-2", 0, "L2"))
        assert engine.total_lessons == 2


# ------------------------------------------------------------------ #
# ClosedLoopController                                                 #
# ------------------------------------------------------------------ #

class TestClosedLoopController:
    def test_healthy_turn_no_halt(self):
        ctrl = ClosedLoopController("sess-1", "run-1")
        rec, halt = ctrl.on_turn(0, aer_span_id="span-0", tool_cost_usd=0.01)
        assert isinstance(rec, ControlRecord)
        assert halt is None

    def test_cost_violation_triggers_halt(self):
        budget = StabilityBudget(max_cost_usd=0.5)
        ctrl = ClosedLoopController("sess-1", "run-1", budget=budget)
        rec, halt = ctrl.on_turn(0, tool_cost_usd=1.0)
        assert halt is not None
        assert isinstance(halt, HaltSignal)
        assert "cost_usd" in halt.reason

    def test_unsafe_action_halt(self):
        budget = StabilityBudget(max_unsafe_actions=0)
        ctrl = ClosedLoopController("sess-1", "run-1", budget=budget)
        rec, halt = ctrl.on_turn(0, policy_blocked=True)
        assert halt is not None

    def test_halt_disabled_by_config(self):
        budget = StabilityBudget(max_cost_usd=0.0)
        cfg = ControllerConfig(halt_on_violation=False)
        ctrl = ClosedLoopController("sess-1", "run-1", budget=budget, config=cfg)
        rec, halt = ctrl.on_turn(0, tool_cost_usd=100.0)
        assert halt is None

    def test_record_lesson_stored(self):
        ctrl = ClosedLoopController("sess-1", "run-1")
        ctrl.record_lesson(ReflexionLesson("span-1", "sess-1", 0, "be careful"))
        assert len(ctrl.lessons) == 1

    def test_records_accumulate(self):
        ctrl = ClosedLoopController("sess-1", "run-1")
        ctrl.on_turn(0)
        ctrl.on_turn(1)
        assert len(ctrl.records) == 2

    def test_halt_signal_reason_string(self):
        budget = StabilityBudget(max_cost_usd=1.0)
        ctrl = ClosedLoopController("sess-1", "run-1", budget=budget)
        _, halt = ctrl.on_turn(0, tool_cost_usd=5.0)
        assert halt is not None
        assert "cost_usd" in halt.reason
        assert ">" in halt.reason
