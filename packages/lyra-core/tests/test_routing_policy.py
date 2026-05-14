"""Tests for Phase B: 3-tier routing policy + BAAR budget ledger."""
from __future__ import annotations

from lyra_core.routing.policy import (
    RoutingConfig,
    RoutingSignals,
    TrajectoryBudget,
    TrajectoryRouter,
    route_step,
)


# ------------------------------------------------------------------ #
# RoutingSignals validation                                            #
# ------------------------------------------------------------------ #

class TestRoutingSignals:
    def test_defaults_are_zero(self):
        s = RoutingSignals()
        assert s.task_ambiguity == 0.0
        assert s.tool_risk == 0.0
        assert not s.evidence_conflict
        assert not s.repeated_failure

    def test_out_of_range_raises(self):
        import pytest
        with pytest.raises(ValueError):
            RoutingSignals(task_ambiguity=1.5)
        with pytest.raises(ValueError):
            RoutingSignals(tool_risk=-0.1)


# ------------------------------------------------------------------ #
# TrajectoryBudget                                                     #
# ------------------------------------------------------------------ #

class TestTrajectoryBudget:
    def test_initial_state(self):
        b = TrajectoryBudget(max_cost_usd=10.0, max_advisor_calls=3)
        assert b.cost_spent_usd == 0.0
        assert b.budget_pressure == 0.0
        assert not b.advisor_budget_exhausted

    def test_record_updates_counts(self):
        b = TrajectoryBudget()
        b.record("fast", 0.01)
        b.record("reasoning", 0.05)
        b.record("advisor", 0.20)
        assert b.fast_calls == 1
        assert b.reasoning_calls == 1
        assert b.advisor_calls == 1
        assert b.total_turns == 3

    def test_budget_pressure_clamped(self):
        b = TrajectoryBudget(max_cost_usd=1.0)
        b.record("advisor", 5.0)
        assert b.budget_pressure == 1.0

    def test_advisor_exhausted(self):
        b = TrajectoryBudget(max_advisor_calls=2)
        b.record("advisor")
        b.record("advisor")
        assert b.advisor_budget_exhausted


# ------------------------------------------------------------------ #
# route_step — fast path                                               #
# ------------------------------------------------------------------ #

class TestRouteStepFast:
    def test_defaults_route_fast(self):
        decision = route_step(RoutingSignals(), TrajectoryBudget())
        assert decision.tier == "fast"
        assert not decision.escalated

    def test_low_signals_stay_fast(self):
        s = RoutingSignals(task_ambiguity=0.1, tool_risk=0.3, context_pressure=0.5)
        d = route_step(s, TrajectoryBudget())
        assert d.tier == "fast"


# ------------------------------------------------------------------ #
# route_step — reasoning escalation                                    #
# ------------------------------------------------------------------ #

class TestRouteStepReasoning:
    def test_high_ambiguity_escalates(self):
        s = RoutingSignals(task_ambiguity=0.8)
        d = route_step(s, TrajectoryBudget())
        assert d.tier == "reasoning"
        assert d.escalated
        assert "ambiguity" in d.reason

    def test_evidence_conflict_escalates(self):
        s = RoutingSignals(evidence_conflict=True)
        d = route_step(s, TrajectoryBudget())
        assert d.tier == "reasoning"

    def test_high_context_pressure_escalates(self):
        s = RoutingSignals(context_pressure=0.80)
        d = route_step(s, TrajectoryBudget())
        assert d.tier == "reasoning"
        assert "context_pressure" in d.reason

    def test_repeated_failure_escalates(self):
        s = RoutingSignals(repeated_failure=True)
        d = route_step(s, TrajectoryBudget())
        assert d.tier == "reasoning"
        assert "repeated_failure" in d.reason

    def test_high_uncertainty_escalates(self):
        s = RoutingSignals(uncertainty=0.6)
        d = route_step(s, TrajectoryBudget())
        assert d.tier == "reasoning"


# ------------------------------------------------------------------ #
# route_step — advisor escalation                                      #
# ------------------------------------------------------------------ #

class TestRouteStepAdvisor:
    def test_high_risk_plus_uncertainty_triggers_advisor(self):
        s = RoutingSignals(tool_risk=0.9, uncertainty=0.8)
        d = route_step(s, TrajectoryBudget())
        assert d.tier == "advisor"

    def test_high_risk_plus_evidence_conflict_triggers_advisor(self):
        s = RoutingSignals(tool_risk=0.9, evidence_conflict=True)
        d = route_step(s, TrajectoryBudget())
        assert d.tier == "advisor"

    def test_advisor_suppressed_when_budget_exhausted(self):
        b = TrajectoryBudget(max_advisor_calls=0)
        s = RoutingSignals(tool_risk=1.0, uncertainty=1.0)
        d = route_step(s, b)
        # Cannot use advisor; falls to reasoning
        assert d.tier == "reasoning"

    def test_advisor_suppressed_when_budget_pressure_high(self):
        b = TrajectoryBudget(max_cost_usd=1.0)
        b.record("advisor", 0.90)   # 90% spent — above 85% cap
        s = RoutingSignals(tool_risk=1.0, uncertainty=1.0)
        d = route_step(s, b)
        assert d.tier in ("reasoning", "fast")

    def test_custom_config_raises_threshold(self):
        cfg = RoutingConfig(tool_risk_advisor_threshold=0.99)
        s = RoutingSignals(tool_risk=0.9, uncertainty=1.0)
        d = route_step(s, TrajectoryBudget(), config=cfg)
        # threshold not met → stays at reasoning
        assert d.tier == "reasoning"


# ------------------------------------------------------------------ #
# TrajectoryRouter                                                     #
# ------------------------------------------------------------------ #

class TestTrajectoryRouter:
    def test_decide_and_record(self):
        router = TrajectoryRouter(max_cost_usd=5.0, max_advisor_calls=3)
        d = router.decide(RoutingSignals())
        assert d.tier == "fast"
        router.record(d.tier, cost_usd=0.01)
        assert router.budget.fast_calls == 1
        assert router.budget.cost_spent_usd == 0.01

    def test_advisor_calls_counted(self):
        router = TrajectoryRouter(max_advisor_calls=2)
        for _ in range(2):
            router.decide(RoutingSignals(tool_risk=0.9, uncertainty=0.9))
            router.record("advisor", 0.10)
        assert router.budget.advisor_budget_exhausted

    def test_reset_clears_budget(self):
        router = TrajectoryRouter()
        router.record("fast", 0.05)
        router.reset()
        assert router.budget.cost_spent_usd == 0.0
        assert router.budget.total_turns == 0

    def test_advisor_blocked_after_exhaustion(self):
        router = TrajectoryRouter(max_advisor_calls=1)
        router.record("advisor", 0.10)
        # Next high-risk turn should fall back to reasoning
        d = router.decide(RoutingSignals(tool_risk=1.0, uncertainty=1.0))
        assert d.tier == "reasoning"
