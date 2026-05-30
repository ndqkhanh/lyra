"""Tests for Task-Phase-Aware Model Routing (P3-B5)."""
from __future__ import annotations

import pytest

from lyra_harness_core.providers import ProviderKind
from lyra_harness_core.routing.effort_router import EffortTier
from lyra_harness_core.routing.phase_router import (
    AgentPhase,
    PhaseConfig,
    PhaseDecision,
    PhaseRouter,
    infer_phase,
)


# ---------------------------------------------------------------------------
# AgentPhase
# ---------------------------------------------------------------------------


class TestAgentPhase:
    def test_five_phases(self):
        assert len(AgentPhase) == 5

    def test_values(self):
        assert AgentPhase.PLANNING.value == "planning"
        assert AgentPhase.EXECUTION.value == "execution"
        assert AgentPhase.REVIEW.value == "review"
        assert AgentPhase.RESEARCH.value == "research"
        assert AgentPhase.ORCHESTRATION.value == "orchestration"


# ---------------------------------------------------------------------------
# PhaseConfig
# ---------------------------------------------------------------------------


class TestPhaseConfig:
    def test_defaults_has_all_phases(self):
        configs = PhaseConfig.defaults()
        assert set(configs.keys()) == set(AgentPhase)

    def test_planning_prefers_anthropic_high(self):
        configs = PhaseConfig.defaults()
        cfg = configs[AgentPhase.PLANNING]
        assert cfg.provider == ProviderKind.ANTHROPIC
        assert cfg.effort == EffortTier.HIGH

    def test_execution_prefers_anthropic_medium(self):
        configs = PhaseConfig.defaults()
        cfg = configs[AgentPhase.EXECUTION]
        assert cfg.provider == ProviderKind.ANTHROPIC
        assert cfg.effort == EffortTier.MEDIUM

    def test_research_effort_xhigh(self):
        configs = PhaseConfig.defaults()
        cfg = configs[AgentPhase.RESEARCH]
        assert cfg.effort == EffortTier.XHIGH

    def test_orchestration_effort_low(self):
        configs = PhaseConfig.defaults()
        cfg = configs[AgentPhase.ORCHESTRATION]
        assert cfg.effort == EffortTier.LOW

    def test_custom_config(self):
        cfg = PhaseConfig(
            phase=AgentPhase.PLANNING,
            provider=ProviderKind.OPENAI,
            effort=EffortTier.MAX,
            description="custom",
        )
        assert cfg.provider == ProviderKind.OPENAI
        assert cfg.effort == EffortTier.MAX

    def test_frozen(self):
        cfg = PhaseConfig.defaults()[AgentPhase.PLANNING]
        with pytest.raises(Exception):
            cfg.provider = ProviderKind.MOCK  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PhaseDecision
# ---------------------------------------------------------------------------


class TestPhaseDecision:
    def test_decision_fields(self):
        d = PhaseDecision(
            phase=AgentPhase.EXECUTION,
            provider=ProviderKind.ANTHROPIC,
            effort=EffortTier.MEDIUM,
            max_tokens=4096,
            reason="test",
        )
        assert d.phase == AgentPhase.EXECUTION
        assert d.max_tokens == 4096
        assert not d.is_fallback

    def test_fallback_decision(self):
        d = PhaseDecision(
            phase=AgentPhase.PLANNING,
            provider=ProviderKind.DEEPSEEK,
            effort=EffortTier.HIGH,
            max_tokens=8192,
            is_fallback=True,
            reason="anthropic unavailable",
        )
        assert d.is_fallback

    def test_frozen(self):
        d = PhaseDecision(
            phase=AgentPhase.EXECUTION,
            provider=ProviderKind.ANTHROPIC,
            effort=EffortTier.MEDIUM,
            max_tokens=4096,
        )
        with pytest.raises(Exception):
            d.max_tokens = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PhaseRouter
# ---------------------------------------------------------------------------


class TestPhaseRouter:
    @pytest.fixture
    def router(self):
        return PhaseRouter()

    def test_route_planning(self, router):
        d = router.route(AgentPhase.PLANNING)
        assert d.phase == AgentPhase.PLANNING
        assert d.effort == EffortTier.HIGH
        assert d.max_tokens == 8192

    def test_route_execution(self, router):
        d = router.route(AgentPhase.EXECUTION)
        assert d.effort == EffortTier.MEDIUM
        assert d.max_tokens == 4096

    def test_route_review(self, router):
        d = router.route(AgentPhase.REVIEW)
        assert d.effort == EffortTier.HIGH

    def test_route_research(self, router):
        d = router.route(AgentPhase.RESEARCH)
        assert d.effort == EffortTier.XHIGH
        assert d.max_tokens == 16384

    def test_route_orchestration(self, router):
        d = router.route(AgentPhase.ORCHESTRATION)
        assert d.effort == EffortTier.LOW
        assert d.max_tokens == 1024

    def test_fallback_on_unavailable_provider(self, router):
        router.effort_router.mark_unavailable(ProviderKind.ANTHROPIC)
        d = router.route(AgentPhase.PLANNING)
        assert d.is_fallback
        assert d.provider != ProviderKind.ANTHROPIC

    def test_set_phase_config(self, router):
        router.set_phase_config(
            AgentPhase.PLANNING,
            PhaseConfig(
                phase=AgentPhase.PLANNING,
                provider=ProviderKind.QWEN,
                effort=EffortTier.MAX,
            ),
        )
        d = router.route(AgentPhase.PLANNING)
        assert d.provider == ProviderKind.QWEN
        assert d.max_tokens == 32768

    def test_get_config(self, router):
        cfg = router.get_config(AgentPhase.EXECUTION)
        assert cfg is not None
        assert cfg.phase == AgentPhase.EXECUTION

    def test_get_config_unknown(self, router):
        cfg = router.get_config(AgentPhase.EXECUTION)
        assert cfg is not None

    def test_from_policy_dict(self):
        policy = {
            "phases": {
                "planning": {"provider": "deepseek", "effort": "max"},
                "execution": {"provider": "qwen", "effort": "low"},
            }
        }
        router = PhaseRouter.from_policy_dict(policy)

        d_plan = router.route(AgentPhase.PLANNING)
        assert d_plan.provider == ProviderKind.DEEPSEEK
        assert d_plan.max_tokens == 32768

        d_exec = router.route(AgentPhase.EXECUTION)
        assert d_exec.provider == ProviderKind.QWEN
        assert d_exec.max_tokens == 1024

    def test_from_policy_dict_unknown_phase_skipped(self):
        policy = {"phases": {"nonexistent_phase": {"provider": "openai"}}}
        router = PhaseRouter.from_policy_dict(policy)
        # Should not crash; unknown phases are skipped
        d = router.route(AgentPhase.PLANNING)
        assert d.provider == ProviderKind.ANTHROPIC  # default

    def test_from_policy_dict_invalid_effort_defaults(self):
        policy = {"phases": {"planning": {"provider": "anthropic", "effort": "invalid"}}}
        router = PhaseRouter.from_policy_dict(policy)
        d = router.route(AgentPhase.PLANNING)
        assert d.effort == EffortTier.MEDIUM  # fallback to medium

    def test_all_phases_routable(self, router):
        for phase in AgentPhase:
            d = router.route(phase)
            assert d.phase == phase
            assert d.max_tokens > 0


# ---------------------------------------------------------------------------
# infer_phase
# ---------------------------------------------------------------------------


class TestInferPhase:
    def test_design_is_planning(self):
        assert infer_phase("design a new caching architecture") == AgentPhase.PLANNING

    def test_plan_is_planning(self):
        assert infer_phase("plan the microservices migration") == AgentPhase.PLANNING

    def test_implement_is_execution(self):
        assert infer_phase("implement user authentication") == AgentPhase.EXECUTION

    def test_refactor_is_execution(self):
        assert infer_phase("refactor the database layer") == AgentPhase.EXECUTION

    def test_fix_is_execution(self):
        assert infer_phase("fix the login bug") == AgentPhase.EXECUTION

    def test_review_is_review(self):
        assert infer_phase("review the pull request for issues") == AgentPhase.REVIEW

    def test_audit_is_review(self):
        assert infer_phase("audit the codebase for vulnerabilities") == AgentPhase.REVIEW

    def test_research_is_research(self):
        assert infer_phase("research best practices for microservices") == AgentPhase.RESEARCH

    def test_investigate_is_research(self):
        assert infer_phase("investigate the performance regression") == AgentPhase.RESEARCH

    def test_orchestrate_is_orchestration(self):
        assert infer_phase("orchestrate the multi-agent deployment") == AgentPhase.ORCHESTRATION

    def test_delegate_is_orchestration(self):
        assert infer_phase("delegate tasks to the worker agents") == AgentPhase.ORCHESTRATION

    def test_short_defaults_execution(self):
        assert infer_phase("run tests") == AgentPhase.EXECUTION

    def test_long_defaults_planning(self):
        assert infer_phase("create a comprehensive strategy for migrating the entire "
                          "monolith to microservices") == AgentPhase.PLANNING

    def test_mixed_keywords_execution_wins_tiebreak(self):
        # "fix" (execution) + "review" (review) → execution wins tiebreak
        assert infer_phase("fix the code and review it") == AgentPhase.EXECUTION
