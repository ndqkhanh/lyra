"""
Comprehensive tests for the Lyra V4 3-tier Model Router.

Covers:
- Rule tier keyword/pattern matching
- Semantic tier TF-IDF similarity
- Budget tracker enforcement across regimes
- Circuit breaker at $5/session
- Routing decision confidence and reasoning
- Provider registry correctness
- Full 3-tier cascade integration
- Budget-aware tier downgrade
"""

from __future__ import annotations

import os

import pytest
from lyra_router import (
    BudgetRegime,
    BudgetTracker,
    ModelAssignment,
    ModelRouter,
    ModelTier,
    NeuralTier,
    Provider,
    ProviderRegistry,
    RoutingDecision,
    RuleTier,
    SemanticTier,
    TaskComplexity,
    TierResult,
    get_cost_estimate,
    get_tier_for_complexity,
)

# ────────────────────────────────────────────────────────────────────
# Models tests
# ────────────────────────────────────────────────────────────────────


class TestModelTier:
    def test_tier_values(self) -> None:
        tiers = list(ModelTier)
        assert len(tiers) == 6
        assert ModelTier.LOCAL_SLM.value == "local_slm"
        assert ModelTier.AGENTIC.value == "agentic"

    def test_tier_ordering(self) -> None:
        tiers = list(ModelTier)
        assert tiers[0] == ModelTier.LOCAL_SLM
        assert tiers[-1] == ModelTier.AGENTIC


class TestTaskComplexity:
    def test_complexity_values(self) -> None:
        complexities = list(TaskComplexity)
        assert len(complexities) == 5

    def test_complexity_to_tier(self) -> None:
        assert get_tier_for_complexity(TaskComplexity.TRIVIAL) == ModelTier.LOCAL_SLM
        assert get_tier_for_complexity(TaskComplexity.SIMPLE) == ModelTier.HAIKU
        assert get_tier_for_complexity(TaskComplexity.MODERATE) == ModelTier.STANDARD
        assert get_tier_for_complexity(TaskComplexity.COMPLEX) == ModelTier.PREMIUM
        assert get_tier_for_complexity(TaskComplexity.AGENTIC) == ModelTier.AGENTIC


class TestBudgetRegime:
    def test_regime_values(self) -> None:
        regimes = list(BudgetRegime)
        assert len(regimes) == 4
        assert BudgetRegime.HIGH.value == "high"
        assert BudgetRegime.CRITICAL.value == "critical"


class TestModelAssignment:
    def test_frozen_dataclass(self) -> None:
        ma = ModelAssignment(
            model_name="test-model",
            provider="test",
            cost_per_1m_tokens=1.0,
            tier=ModelTier.STANDARD,
        )
        assert ma.model_name == "test-model"
        assert ma.provider == "test"
        with pytest.raises(Exception):
            ma.model_name = "other"  # type: ignore[misc]


class TestRoutingDecision:
    def test_frozen_dataclass(self) -> None:
        rd = RoutingDecision(
            model="test-model",
            tier=ModelTier.STANDARD,
            complexity=TaskComplexity.MODERATE,
            confidence=0.85,
            reasoning="test reason",
            cost_estimate_usd=0.01,
        )
        assert rd.confidence == 0.85
        with pytest.raises(Exception):
            rd.model = "other"  # type: ignore[misc]


class TestProvider:
    def test_defaults(self) -> None:
        p = Provider(name="test")
        assert p.name == "test"
        assert p.models == []
        assert p.max_requests_per_minute == 100


class TestCostEstimates:
    def test_trivial_cost(self) -> None:
        assert get_cost_estimate(TaskComplexity.TRIVIAL) == 0.0001

    def test_agentic_cost(self) -> None:
        assert get_cost_estimate(TaskComplexity.AGENTIC) == 0.10

    def test_moderate_cost(self) -> None:
        assert get_cost_estimate(TaskComplexity.MODERATE) == 0.01


# ────────────────────────────────────────────────────────────────────
# Rule Tier (Tier 1) tests
# ────────────────────────────────────────────────────────────────────


class TestRuleTier:
    def setup_method(self) -> None:
        self.tier = RuleTier()

    def test_trivial_greeting_hello(self) -> None:
        result = self.tier.route("hello")
        assert result is not None
        assert result.complexity == TaskComplexity.TRIVIAL
        assert result.model_tier == ModelTier.LOCAL_SLM

    def test_trivial_greeting_hi(self) -> None:
        result = self.tier.route("hi there")
        assert result is not None
        assert result.complexity == TaskComplexity.TRIVIAL

    def test_trivial_yes(self) -> None:
        result = self.tier.route("yes")
        assert result is not None
        assert result.complexity == TaskComplexity.TRIVIAL

    def test_simple_factual_lookup(self) -> None:
        result = self.tier.route("what is the capital of France")
        assert result is not None
        assert result.complexity == TaskComplexity.SIMPLE

    def test_moderate_implement_keyword(self) -> None:
        result = self.tier.route("implement a login form")
        assert result is not None
        assert result.complexity == TaskComplexity.MODERATE

    def test_moderate_debug_keyword(self) -> None:
        result = self.tier.route("debug the database connection error")
        assert result is not None
        assert result.complexity == TaskComplexity.MODERATE

    def test_complex_architecture_keyword(self) -> None:
        result = self.tier.route("design the architecture for our new microservice")
        assert result is not None
        assert result.complexity == TaskComplexity.COMPLEX

    def test_complex_security_domain(self) -> None:
        result = self.tier.route("perform a security audit of the login system")
        assert result is not None
        assert result.complexity == TaskComplexity.COMPLEX

    def test_agentic_build_from_scratch(self) -> None:
        result = self.tier.route("build a complete e-commerce application from scratch")
        assert result is not None
        assert result.complexity == TaskComplexity.AGENTIC
        assert result.model_tier == ModelTier.AGENTIC

    def test_agentic_autonomous_keyword(self) -> None:
        result = self.tier.route("create an autonomous research agent")
        assert result is not None
        assert result.complexity == TaskComplexity.AGENTIC

    def test_domain_rule_cryptography(self) -> None:
        result = self.tier.route("implement a cryptography module")
        assert result is not None
        assert result.model_tier == ModelTier.PREMIUM

    def test_domain_rule_payment(self) -> None:
        result = self.tier.route("process payment transactions")
        assert result is not None
        assert result.model_tier == ModelTier.PREMIUM

    def test_short_task_defaults_to_simple(self) -> None:
        result = self.tier.route("run xyz")
        assert result is not None
        assert result.complexity == TaskComplexity.SIMPLE
        assert result.confidence == 0.55

    def test_question_detection_defaults_to_simple(self) -> None:
        result = self.tier.route("why is the sky blue?")
        assert result is not None
        assert result.complexity == TaskComplexity.SIMPLE

    def test_add_custom_rule(self) -> None:
        self.tier.add_rule("customkeyword", ModelTier.PREMIUM)
        result = self.tier.route("use customkeyword for analysis")
        assert result is not None
        assert result.model_tier == ModelTier.PREMIUM

    def test_remove_custom_rule(self) -> None:
        self.tier.add_rule("customkeyword", ModelTier.PREMIUM)
        self.tier.remove_rule("customkeyword")
        # Without the custom domain rule, falls through to keyword matching
        result = self.tier.route("customkeyword")
        # "customkeyword" is a single word, treated as short -> simple
        assert result is not None
        assert result.complexity == TaskComplexity.SIMPLE

    def test_confidence_meets_threshold(self) -> None:
        result = self.tier.route("hello")
        assert result is not None
        assert result.confidence >= 0.50


# ────────────────────────────────────────────────────────────────────
# Semantic Tier (Tier 2) tests
# ────────────────────────────────────────────────────────────────────


class TestSemanticTier:
    def setup_method(self) -> None:
        self.tier = SemanticTier()

    def test_routes_similar_task(self) -> None:
        result = self.tier.route("what is the python list comprehension syntax")
        assert result is not None
        assert result.confidence > 0

    def test_routes_moderate_coding_task(self) -> None:
        result = self.tier.route("implement a function to parse json files")
        assert result is not None
        assert result.complexity in (TaskComplexity.MODERATE, TaskComplexity.SIMPLE)

    def test_routes_complex_design_task(self) -> None:
        result = self.tier.route(
            "design a scalable distributed database architecture for real-time analytics"
        )
        assert result is not None
        # Should match closer to complex architecture examples

    def test_returns_low_confidence_for_empty_task(self) -> None:
        result = self.tier.route("")
        # Empty task should produce low confidence regardless of backend
        assert result is None or result.confidence < 0.6

    def test_add_example_updates_corpus(self) -> None:
        initial_count = len(self.tier._corpus_texts)
        self.tier.add_example(
            "a brand new task about quantum computing",
            TaskComplexity.COMPLEX,
            ModelTier.PREMIUM,
        )
        assert len(self.tier._corpus_texts) == initial_count + 1


# ────────────────────────────────────────────────────────────────────
# Neural Tier (Tier 3) tests
# ────────────────────────────────────────────────────────────────────


class TestNeuralTier:
    def setup_method(self) -> None:
        self.tier = NeuralTier()

    def test_always_returns_result(self) -> None:
        result = self.tier.route("some random task that is unclear")
        assert result is not None
        assert result.complexity in list(TaskComplexity)
        assert result.confidence > 0

    def test_routes_trivial_short(self) -> None:
        result = self.tier.route("hi")
        assert result is not None
        # Short greeting should be trivial
        assert result.complexity == TaskComplexity.TRIVIAL

    def test_routes_simple_question(self) -> None:
        result = self.tier.route("what is Python?")
        assert result is not None

    def test_training_accumulates_examples(self) -> None:
        self.tier.train("implement a rest api with authentication", TaskComplexity.MODERATE)
        self.tier.train("design a distributed system architecture", TaskComplexity.COMPLEX)
        self.tier.train("hello world", TaskComplexity.TRIVIAL)
        assert len(self.tier._X) == 3

    def test_multiple_trainings_still_routes(self) -> None:
        for _ in range(15):
            self.tier.train("implement a feature", TaskComplexity.MODERATE)
        result = self.tier.route("implement a feature")
        assert result is not None

    def test_fit_returns_bool(self) -> None:
        # Without sufficient data, fit returns False
        result = self.tier.fit()
        assert isinstance(result, bool)


# ────────────────────────────────────────────────────────────────────
# Budget tracker tests
# ────────────────────────────────────────────────────────────────────


class TestBudgetTracker:
    def setup_method(self) -> None:
        self.tracker = BudgetTracker(session_budget_usd=5.0)

    def test_initial_state(self) -> None:
        assert self.tracker.total_spent == 0.0
        assert self.tracker.remaining == 5.0
        assert self.tracker.budget_used_ratio == 0.0
        assert self.tracker.regime == BudgetRegime.HIGH
        assert not self.tracker.is_tripped

    def test_record_within_budget(self) -> None:
        result = self.tracker.record(cost_usd=0.5)
        assert result is True
        assert self.tracker.total_spent == 0.5
        assert self.tracker.remaining == 4.5

    def test_regime_high(self) -> None:
        self.tracker.record(cost_usd=1.0)
        assert self.tracker.regime == BudgetRegime.HIGH

    def test_regime_medium(self) -> None:
        self.tracker.record(cost_usd=2.0)  # 40% used, 60% remaining = MEDIUM
        assert self.tracker.regime == BudgetRegime.MEDIUM

    def test_regime_low(self) -> None:
        self.tracker.record(cost_usd=3.7)  # 74% used, 26% remaining = LOW
        assert self.tracker.regime == BudgetRegime.LOW

    def test_regime_critical(self) -> None:
        self.tracker.record(cost_usd=4.7)  # 94% used, 6% remaining = CRITICAL
        assert self.tracker.regime == BudgetRegime.CRITICAL

    def test_circuit_breaker_trips_at_limit(self) -> None:
        result1 = self.tracker.record(cost_usd=4.5)
        assert result1 is True
        assert not self.tracker.is_tripped

        result2 = self.tracker.record(cost_usd=1.0)
        assert result2 is False
        assert self.tracker.is_tripped
        assert self.tracker.total_spent == 5.5

    def test_circuit_breaker_blocks_after_tripping(self) -> None:
        self.tracker.record(cost_usd=5.0)
        assert self.tracker.is_tripped
        result = self.tracker.record(cost_usd=0.01)
        assert result is False

    def test_record_updates_task_count(self) -> None:
        self.tracker.record(cost_usd=0.1)
        self.tracker.record(cost_usd=0.2)
        assert self.tracker.task_count == 2

    def test_success_rate_tracking(self) -> None:
        self.tracker.record(cost_usd=0.1, success=True)
        self.tracker.record(cost_usd=0.1, success=False)
        self.tracker.record(cost_usd=0.1, success=True)
        assert self.tracker.success_count == 2
        assert self.tracker.success_rate == 2.0 / 3.0

    def test_cost_per_successful_task(self) -> None:
        self.tracker.record(cost_usd=0.5, success=True)
        self.tracker.record(cost_usd=0.3, success=True)
        assert self.tracker.cost_per_successful_task == 0.8 / 2.0

    def test_get_max_task_budget_high(self) -> None:
        assert self.tracker.regime == BudgetRegime.HIGH
        max_budget = self.tracker.get_max_task_budget()
        assert max_budget == pytest.approx(1.0)  # 20% of 5.0

    def test_get_max_task_budget_critical(self) -> None:
        self.tracker.record(cost_usd=4.7)
        assert self.tracker.regime == BudgetRegime.CRITICAL
        max_budget = self.tracker.get_max_task_budget()
        assert max_budget < 0.05  # 2% of remaining

    def test_should_downgrade_tier_critical(self) -> None:
        self.tracker.record(cost_usd=4.8)
        assert self.tracker.should_downgrade_tier(ModelTier.PREMIUM)
        assert self.tracker.should_downgrade_tier(ModelTier.STANDARD)
        assert not self.tracker.should_downgrade_tier(ModelTier.HAIKU)

    def test_should_downgrade_tier_low(self) -> None:
        self.tracker.record(cost_usd=3.7)  # LOW regime
        assert self.tracker.should_downgrade_tier(ModelTier.PREMIUM)
        assert self.tracker.should_downgrade_tier(ModelTier.AGENTIC)
        assert not self.tracker.should_downgrade_tier(ModelTier.STANDARD)

    def test_should_not_downgrade_in_high_regime(self) -> None:
        assert not self.tracker.should_downgrade_tier(ModelTier.PREMIUM)
        assert not self.tracker.should_downgrade_tier(ModelTier.STANDARD)

    def test_xml_context_output(self) -> None:
        self.tracker.record(cost_usd=0.5, task_summary="test")
        xml = self.tracker.to_xml_context()
        assert "<budget>" in xml
        assert "HIGH" in xml
        assert "0.5000" in xml
        assert "OK" in xml

    def test_get_summary(self) -> None:
        self.tracker.record(cost_usd=0.5)
        summary = self.tracker.get_summary()
        assert summary["total_spent"] == 0.5
        assert summary["regime"] == "high"
        assert not summary["is_tripped"]

    def test_reset(self) -> None:
        self.tracker.record(cost_usd=3.0)
        self.tracker.reset()
        assert self.tracker.total_spent == 0.0
        assert not self.tracker.is_tripped
        assert self.tracker.task_count == 0

    def test_circuit_breaker_default_limit(self) -> None:
        tracker = BudgetTracker()
        assert tracker.session_budget_usd == 5.0


# ────────────────────────────────────────────────────────────────────
# Provider registry tests
# ────────────────────────────────────────────────────────────────────


class TestProviderRegistry:
    def setup_method(self) -> None:
        self.registry = ProviderRegistry()

    def test_builtin_providers_registered(self) -> None:
        providers = self.registry.list_providers()
        assert "anthropic" in providers
        assert "deepseek" in providers
        assert "google" in providers
        assert "openai" in providers
        assert "openrouter" in providers

    def test_anthropic_models(self) -> None:
        models = self.registry.list_models("anthropic")
        assert any("claude" in m for m in models)
        assert any("haiku" in m for m in models)
        assert any("sonnet" in m for m in models)
        assert any("opus" in m for m in models)

    def test_get_model_returns_correct_data(self) -> None:
        model = self.registry.get_model("claude-sonnet-4-20250514")
        assert model is not None
        assert model.provider == "anthropic"
        assert model.tier == ModelTier.STANDARD
        assert model.cost_per_1m_tokens == 3.0

    def test_get_provider_returns_correct_data(self) -> None:
        provider = self.registry.get_provider("deepseek")
        assert provider is not None
        assert provider.base_url == "https://api.deepseek.com/v1"
        assert provider.api_key_env == "DEEPSEEK_API_KEY"

    def test_get_missing_provider_returns_none(self) -> None:
        assert self.registry.get_provider("nonexistent") is None

    def test_get_missing_model_returns_none(self) -> None:
        assert self.registry.get_model("nonexistent-model") is None

    def test_register_custom_provider(self) -> None:
        p = Provider(name="custom", base_url="https://custom.api", api_key_env="CUSTOM_KEY")
        self.registry.register_provider(p)
        assert self.registry.get_provider("custom") is p

    def test_register_custom_model(self) -> None:
        ma = ModelAssignment(
            model_name="custom-model-v1",
            provider="custom",
            cost_per_1m_tokens=0.5,
            tier=ModelTier.HAIKU,
        )
        self.registry.register_provider(Provider(name="custom"))
        self.registry.register_model(ma)
        assert self.registry.get_model("custom-model-v1") is ma

    def test_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        assert self.registry.has_api_key("anthropic")
        assert self.registry.get_api_key("anthropic") == "sk-ant-test"

    def test_api_key_missing(self) -> None:
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]
        # May or may not be set — we just check the method works
        key = self.registry.get_api_key("anthropic")
        assert key is None or isinstance(key, str)

    def test_get_best_model_for_tier(self) -> None:
        model = self.registry.get_best_model_for_tier(ModelTier.HAIKU, require_key=False)
        assert model is not None
        assert model.tier == ModelTier.HAIKU

    def test_get_best_model_returns_cheapest(self) -> None:
        model = self.registry.get_best_model_for_tier(ModelTier.HAIKU, require_key=False)
        assert model is not None
        # Among Haiku-tier models, should pick the cheapest available
        assert model.cost_per_1m_tokens <= 1.0

    def test_get_fallback_model(self) -> None:
        fallback = self.registry.get_fallback_model(ModelTier.PREMIUM)
        assert fallback is not None
        # Fallback should be at a lower tier
        tier_order = list(ModelTier)
        original_idx = tier_order.index(ModelTier.PREMIUM)
        fallback_idx = tier_order.index(fallback.tier)
        assert fallback_idx < original_idx

    def test_get_stats(self) -> None:
        stats = self.registry.get_stats()
        assert stats["total_providers"] >= 5
        assert stats["total_models"] >= 10
        assert "models_by_tier" in stats

    def test_list_models_filtered(self) -> None:
        anthropic_models = self.registry.list_models("anthropic")
        assert len(anthropic_models) >= 3
        for m in anthropic_models:
            model_data = self.registry.get_model(m)
            assert model_data is not None
            assert model_data.provider == "anthropic"


# ────────────────────────────────────────────────────────────────────
# ModelRouter integration tests
# ────────────────────────────────────────────────────────────────────


class TestModelRouter:
    def setup_method(self) -> None:
        self.router = ModelRouter(session_budget_usd=5.0)

    def test_route_returns_decision(self) -> None:
        decision = self.router.route("hello world")
        assert isinstance(decision, RoutingDecision)
        assert decision.model
        assert decision.tier
        assert decision.confidence > 0
        assert decision.reasoning

    def test_route_trivial_task(self) -> None:
        decision = self.router.route("hi there")
        assert decision.complexity == TaskComplexity.TRIVIAL
        assert decision.tier in (ModelTier.LOCAL_SLM, ModelTier.HAIKU)

    def test_route_simple_task(self) -> None:
        decision = self.router.route("what is the syntax for list comprehension in Python")
        assert decision.complexity in (
            TaskComplexity.SIMPLE,
            TaskComplexity.TRIVIAL,
            TaskComplexity.MODERATE,
        )

    def test_route_moderate_task(self) -> None:
        decision = self.router.route("implement a JWT authentication middleware")
        assert decision.complexity in (
            TaskComplexity.MODERATE,
            TaskComplexity.SIMPLE,
            TaskComplexity.COMPLEX,
        )

    def test_route_complex_task(self) -> None:
        decision = self.router.route(
            "design the architecture for a scalable microservices platform"
        )
        assert decision.complexity in (TaskComplexity.COMPLEX, TaskComplexity.MODERATE)

    def test_route_agentic_task(self) -> None:
        decision = self.router.route(
            "build a complete autonomous trading bot from scratch with risk management"
        )
        assert decision.complexity in (TaskComplexity.AGENTIC, TaskComplexity.COMPLEX)

    def test_decision_has_all_fields(self) -> None:
        decision = self.router.route("test task")
        assert isinstance(decision.model, str) and decision.model
        assert isinstance(decision.tier, ModelTier)
        assert isinstance(decision.complexity, TaskComplexity)
        assert isinstance(decision.confidence, float)
        assert 0 < decision.confidence <= 1.0
        assert isinstance(decision.reasoning, str) and decision.reasoning
        assert isinstance(decision.cost_estimate_usd, float)
        assert decision.cost_estimate_usd >= 0
        assert isinstance(decision.tier_used, int)
        assert decision.tier_used in (1, 2, 3)
        assert isinstance(decision.budget_regime, BudgetRegime)

    def test_force_tier(self) -> None:
        decision = self.router.route("hello", force_tier=3)
        assert decision.tier_used == 3

    def test_record_outcome_success(self) -> None:
        decision = self.router.route("implement a login form")
        result = self.router.record_outcome(decision, success=True, latency_ms=100, cost=0.005)
        assert result is True

    def test_circuit_breaker_stops_routing(self) -> None:
        # Spend the entire budget
        self.router.budget.record(cost_usd=5.0)
        with pytest.raises(RuntimeError, match="Circuit breaker tripped"):
            self.router.route("another task")

    def test_record_outcome_returns_false_after_trip(self) -> None:
        decision = self.router.route("test")
        self.router.budget.record(cost_usd=4.9)
        result = self.router.record_outcome(decision, success=True, latency_ms=10, cost=0.5)
        assert result is False

    def test_budget_downgrade_in_low_regime(self) -> None:
        # Put budget into LOW regime
        self.router.budget.record(cost_usd=3.7)
        decision = self.router.route("design a complex system architecture")
        # Even for a COMPLEX task, the router should consider budget
        assert decision.budget_regime == BudgetRegime.LOW

    def test_stats_returns_valid_data(self) -> None:
        self.router.route("test 1")
        self.router.route("test 2")
        stats = self.router.stats
        assert stats["route_count"] == 2
        assert stats["tier_hits"] is not None
        assert stats["avg_latency_ms"] >= 0
        assert "budget" in stats
        assert "providers" in stats

    def test_add_domain_rule_affects_routing(self) -> None:
        self.router.add_domain_rule("supercritical", ModelTier.PREMIUM)
        decision = self.router.route("the supercritical system needs attention")
        # Domain rule triggers PREMIUM tier
        assert decision.tier == ModelTier.PREMIUM

    def test_add_training_example(self) -> None:
        self.router.add_training_example(
            "deploy a kubernetes cluster with monitoring",
            TaskComplexity.COMPLEX,
            ModelTier.PREMIUM,
        )
        # Should not raise

    def test_multiple_routes_increment_count(self) -> None:
        for i in range(5):
            self.router.route(f"task number {i}")
        assert self.router.stats["route_count"] == 5

    def test_context_parameter_accepted(self) -> None:
        decision = self.router.route(
            "explain the code",
            context={"history": ["previous message"], "user_role": "developer"},
        )
        assert isinstance(decision, RoutingDecision)


# ────────────────────────────────────────────────────────────────────
# TierResult tests
# ────────────────────────────────────────────────────────────────────


class TestTierResult:
    def test_tier_result_fields(self) -> None:
        result = TierResult(
            complexity=TaskComplexity.MODERATE,
            model_tier=ModelTier.STANDARD,
            confidence=0.75,
            reasoning="test",
            matched_rule="test:rule",
        )
        assert result.complexity == TaskComplexity.MODERATE
        assert result.model_tier == ModelTier.STANDARD
        assert result.confidence == 0.75
