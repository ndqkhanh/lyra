"""Tests for Phase F — SLIM skill lifecycle management."""
import pytest

from lyra_skills.lifecycle import (
    LifecycleConfig,
    LifecycleDecision,
    LifecycleManager,
    SkillFitness,
)


def make_manager(**kwargs) -> LifecycleManager:
    return LifecycleManager(config=LifecycleConfig(**kwargs))


class TestSkillFitness:
    def test_success_rate_zero_uses(self):
        f = SkillFitness("s1")
        assert f.success_rate == 0.0

    def test_success_rate_mixed(self):
        f = SkillFitness("s1", use_count=5, success_count=3, failure_count=2)
        assert f.success_rate == pytest.approx(0.6)

    def test_is_exercised_false(self):
        f = SkillFitness("s1")
        assert not f.is_exercised

    def test_is_exercised_true(self):
        f = SkillFitness("s1", use_count=1)
        assert f.is_exercised


class TestLifecycleManagerRegistration:
    def test_register_returns_fitness(self):
        mgr = LifecycleManager()
        f = mgr.register("skill-a")
        assert isinstance(f, SkillFitness)
        assert f.skill_id == "skill-a"

    def test_record_outcome_auto_registers(self):
        mgr = LifecycleManager()
        mgr.record_outcome("skill-b", success=True)
        assert mgr.fitness("skill-b") is not None

    def test_record_outcome_increments_counts(self):
        mgr = LifecycleManager()
        mgr.record_outcome("s", success=True)
        mgr.record_outcome("s", success=True)
        mgr.record_outcome("s", success=False)
        f = mgr.fitness("s")
        assert f is not None
        assert f.use_count == 3
        assert f.success_count == 2
        assert f.failure_count == 1

    def test_context_tracking(self):
        mgr = LifecycleManager()
        mgr.record_outcome("s", success=True, context="web")
        mgr.record_outcome("s", success=True, context="cli")
        mgr.record_outcome("s", success=True, context="web")  # duplicate ignored
        f = mgr.fitness("s")
        assert f is not None
        assert sorted(f.contexts_applied) == ["cli", "web"]


class TestLifecycleEvaluationRetain:
    def test_unregistered_skill_retains(self):
        mgr = LifecycleManager()
        ev = mgr.evaluate("unknown")
        assert ev.decision == LifecycleDecision.RETAIN
        assert "not yet registered" in ev.reason

    def test_too_few_uses_retains(self):
        mgr = make_manager(min_uses_before_evaluation=5)
        for _ in range(4):
            mgr.record_outcome("s", success=True)
        mgr.set_marginal_contribution("s", 0.0)
        ev = mgr.evaluate("s")
        assert ev.decision == LifecycleDecision.RETAIN
        assert "4 uses" in ev.reason

    def test_healthy_skill_retains(self):
        mgr = make_manager(min_uses_before_evaluation=2)
        for _ in range(3):
            mgr.record_outcome("s", success=True)
        mgr.set_marginal_contribution("s", 0.10)
        ev = mgr.evaluate("s")
        assert ev.decision == LifecycleDecision.RETAIN


class TestLifecycleEvaluationRetire:
    def test_low_marginal_contribution_retires(self):
        mgr = make_manager(
            min_uses_before_evaluation=2,
            retire_marginal_threshold=0.05,
            retire_success_rate_floor=0.10,
        )
        for _ in range(5):
            mgr.record_outcome("s", success=True)
        mgr.set_marginal_contribution("s", 0.01)  # below threshold
        ev = mgr.evaluate("s")
        assert ev.decision == LifecycleDecision.RETIRE

    def test_low_success_rate_retires(self):
        mgr = make_manager(
            min_uses_before_evaluation=2,
            retire_success_rate_floor=0.50,
            expand_failure_streak=100,  # disable expand trigger for this test
        )
        for _ in range(5):
            mgr.record_outcome("s", success=False)
        mgr.set_marginal_contribution("s", 0.99)  # high contribution but bad success
        ev = mgr.evaluate("s")
        assert ev.decision == LifecycleDecision.RETIRE


class TestLifecycleEvaluationExpand:
    def test_failure_streak_triggers_expand(self):
        mgr = make_manager(
            min_uses_before_evaluation=2,
            expand_failure_streak=3,
        )
        for _ in range(5):
            mgr.record_outcome("s", success=False)
        mgr.set_marginal_contribution("s", 0.50)
        ev = mgr.evaluate("s")
        assert ev.decision == LifecycleDecision.EXPAND

    def test_success_resets_failure_streak(self):
        mgr = make_manager(
            min_uses_before_evaluation=2,
            expand_failure_streak=3,
            retire_marginal_threshold=0.01,
        )
        for _ in range(3):
            mgr.record_outcome("s", success=False)
        mgr.record_outcome("s", success=True)  # resets streak
        mgr.set_marginal_contribution("s", 0.50)
        ev = mgr.evaluate("s")
        # After streak reset, should not be EXPAND
        assert ev.decision != LifecycleDecision.EXPAND


class TestBulkEvaluation:
    def test_evaluate_all_returns_all_skills(self):
        mgr = make_manager(min_uses_before_evaluation=1)
        mgr.record_outcome("s1", success=True)
        mgr.record_outcome("s2", success=True)
        evals = mgr.evaluate_all()
        ids = {e.skill_id for e in evals}
        assert {"s1", "s2"} <= ids

    def test_skills_to_retire_filters(self):
        mgr = make_manager(
            min_uses_before_evaluation=1,
            retire_marginal_threshold=0.05,
            retire_success_rate_floor=0.10,
        )
        mgr.record_outcome("keep", success=True)
        mgr.set_marginal_contribution("keep", 0.50)
        mgr.record_outcome("drop", success=True)
        mgr.set_marginal_contribution("drop", 0.001)
        retire_list = mgr.skills_to_retire()
        assert "drop" in retire_list
        assert "keep" not in retire_list
