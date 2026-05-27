"""Tests for lyra-model-router package (100+ tests)."""

from __future__ import annotations

import time

import pytest

from lyra_model_router import (
    BudgetLimit,
    CapabilityAnalyzer,
    ClassificationResult,
    ComplexityEstimator,
    ConfidenceEscalator,
    CostOptimizer,
    CrossModelVerifier,
    GapReport,
    KnowingDoingGapDetector,
    ModelCapability,
    ModelProvider,
    ModelRouterError,
    ModelSpec,
    ModelTier,
    PerformanceHistory,
    PerformanceRecord,
    ProviderHealth,
    RouterConfig,
    RoutingDecision,
    RoutingStrategy,
    TaskCategory,
    TaskClassifier,
    TaskRequirements,
    UsageRecord,
    UsageStats,
    UsageTracker,
    VerificationResult,
    default_config,
)


# ═════════════════════════════════════════════════════════════════════════
# RouterConfig Tests
# ═════════════════════════════════════════════════════════════════════════


class TestModelCapability:
    def test_frozen_dataclass(self):
        cap = ModelCapability(
            model_id="test-model",
            provider="anthropic",
            tier=0,
            strengths=("reasoning",),
            cost_per_1k_tokens=0.075,
            max_tokens=200000,
            supports_thinking=True,
        )
        assert cap.model_id == "test-model"
        assert cap.provider == "anthropic"
        assert cap.tier == 0
        assert cap.strengths == ("reasoning",)
        assert cap.cost_per_1k_tokens == 0.075
        assert cap.max_tokens == 200000
        assert cap.supports_thinking

    def test_frozen_cannot_mutate(self):
        cap = ModelCapability(
            model_id="m", provider="p", tier=0,
            strengths=("s",), cost_per_1k_tokens=0.01,
            max_tokens=1000, supports_thinking=False,
        )
        with pytest.raises(AttributeError):
            cap.tier = 1  # type: ignore[misc]


class TestRouterConfig:
    def test_default_config_creates_registry(self):
        config = default_config()
        assert isinstance(config, RouterConfig)
        assert len(config.model_registry) == 5
        assert config.default_tier == 1
        assert len(config.routing_rules) == 4

    def test_default_registry_has_all_models(self):
        config = default_config()
        registry = config.model_registry
        assert "claude-opus-4-7" in registry
        assert "claude-sonnet-4-6" in registry
        assert "claude-haiku-4-5" in registry
        assert "deepseek-v4-pro" in registry
        assert "deepseek-v4-flash" in registry

    def test_opus_is_tier_0(self):
        config = default_config()
        opus = config.model_registry["claude-opus-4-7"]
        assert opus.tier == 0
        assert opus.provider == "anthropic"
        assert opus.supports_thinking

    def test_sonnet_is_tier_1(self):
        config = default_config()
        sonnet = config.model_registry["claude-sonnet-4-6"]
        assert sonnet.tier == 1
        assert sonnet.supports_thinking

    def test_haiku_is_tier_2(self):
        config = default_config()
        haiku = config.model_registry["claude-haiku-4-5"]
        assert haiku.tier == 2
        assert not haiku.supports_thinking

    def test_deepseek_pro_is_tier_0(self):
        config = default_config()
        pro = config.model_registry["deepseek-v4-pro"]
        assert pro.tier == 0
        assert pro.provider == "deepseek"

    def test_deepseek_flash_is_tier_2(self):
        config = default_config()
        flash = config.model_registry["deepseek-v4-flash"]
        assert flash.tier == 2
        assert flash.provider == "deepseek"
        assert not flash.supports_thinking

    def test_custom_config(self):
        registry = {
            "custom-model": ModelCapability(
                model_id="custom-model", provider="custom", tier=1,
                strengths=("custom",), cost_per_1k_tokens=0.01,
                max_tokens=10000, supports_thinking=False,
            ),
        }
        config = RouterConfig(
            model_registry=registry,
            default_tier=0,
            routing_rules=("custom rule",),
        )
        assert config.default_tier == 0
        assert config.routing_rules == ("custom rule",)
        assert "custom-model" in config.model_registry


# ═════════════════════════════════════════════════════════════════════════
# CapabilityAnalyzer Tests
# ═════════════════════════════════════════════════════════════════════════


class TestCapabilityAnalyzer:
    @pytest.mark.asyncio
    async def test_analyze_architecture_task(self):
        analyzer = CapabilityAnalyzer()
        req = await analyzer.analyze_task(
            "Design a distributed system architecture with microservices",
            context_tokens=50000,
            tools_required=3,
        )
        assert isinstance(req, TaskRequirements)
        assert req.category == "architecture"
        assert 0.0 <= req.complexity_score <= 1.0
        assert "reasoning" in req.required_capabilities

    @pytest.mark.asyncio
    async def test_analyze_coding_task(self):
        analyzer = CapabilityAnalyzer()
        req = await analyzer.analyze_task(
            "Write a Python function to sort a list of integers",
        )
        assert req.category == "coding"
        assert "coding" in req.required_capabilities

    @pytest.mark.asyncio
    async def test_analyze_review_task(self):
        analyzer = CapabilityAnalyzer()
        req = await analyzer.analyze_task(
            "Review this pull request for code quality issues",
        )
        assert req.category == "review"
        assert "review" in req.required_capabilities

    @pytest.mark.asyncio
    async def test_analyze_research_task(self):
        analyzer = CapabilityAnalyzer()
        req = await analyzer.analyze_task(
            "Research and analyze the latest transformer model advances",
            context_tokens=80000,
            tools_required=4,
        )
        assert req.category == "research"
        assert "research" in req.required_capabilities

    @pytest.mark.asyncio
    async def test_analyze_lookup_task(self):
        analyzer = CapabilityAnalyzer()
        req = await analyzer.analyze_task("Lookup the price of AAPL stock")
        assert req.category == "lookup"

    @pytest.mark.asyncio
    async def test_analyze_execution_task(self):
        analyzer = CapabilityAnalyzer()
        req = await analyzer.analyze_task("Translate this document to French")
        assert req.category == "execution"

    @pytest.mark.asyncio
    async def test_analyze_defaults_to_execution(self):
        analyzer = CapabilityAnalyzer()
        req = await analyzer.analyze_task("Hi")
        assert req.category == "execution"

    @pytest.mark.asyncio
    async def test_complexity_from_description_length(self):
        analyzer = CapabilityAnalyzer()
        short = await analyzer.analyze_task("Hi", context_tokens=0, tools_required=0)
        long_desc = "x " * 1000
        long_task = await analyzer.analyze_task(long_desc, context_tokens=0, tools_required=0)
        assert long_task.complexity_score > short.complexity_score

    @pytest.mark.asyncio
    async def test_complexity_from_context_tokens(self):
        analyzer = CapabilityAnalyzer()
        low = await analyzer.analyze_task("Do something", context_tokens=0, tools_required=0)
        high = await analyzer.analyze_task("Do something", context_tokens=200000, tools_required=0)
        assert high.complexity_score > low.complexity_score

    @pytest.mark.asyncio
    async def test_complexity_from_tools_required(self):
        analyzer = CapabilityAnalyzer()
        none = await analyzer.analyze_task("Do something", context_tokens=0, tools_required=0)
        many = await analyzer.analyze_task("Do something", context_tokens=0, tools_required=10)
        assert many.complexity_score > none.complexity_score

    @pytest.mark.asyncio
    async def test_capabilities_include_deep_reasoning_at_high_complexity(self):
        analyzer = CapabilityAnalyzer()
        req = await analyzer.analyze_task(
            "x " * 1000, context_tokens=100000, tools_required=10,
        )
        assert req.complexity_score >= 0.7
        assert "deep_reasoning" in req.required_capabilities

    @pytest.mark.asyncio
    async def test_task_requirements_is_frozen(self):
        req = TaskRequirements(category="coding", complexity_score=0.5, required_capabilities=("coding",))
        with pytest.raises(AttributeError):
            req.category = "research"  # type: ignore[misc]


# ═════════════════════════════════════════════════════════════════════════
# CostOptimizer Tests
# ═════════════════════════════════════════════════════════════════════════


class TestCostOptimizer:
    @pytest.mark.asyncio
    async def test_select_model_returns_model_capability(self):
        optimizer = CostOptimizer()
        req = TaskRequirements(category="coding", complexity_score=0.5, required_capabilities=("coding",))
        model = await optimizer.select_model(req)
        assert isinstance(model, ModelCapability)
        assert model.model_id

    @pytest.mark.asyncio
    async def test_select_model_respects_preferred_tier(self):
        optimizer = CostOptimizer()
        req = TaskRequirements(category="coding", complexity_score=0.5, required_capabilities=("coding",))
        budget = BudgetLimit(max_cost_per_task=float("inf"), max_tokens_per_task=100000, preferred_tier=0)
        model = await optimizer.select_model(req, budget_limit=budget)
        assert model.tier == 0

    @pytest.mark.asyncio
    async def test_select_model_economy_tier(self):
        optimizer = CostOptimizer()
        req = TaskRequirements(category="lookup", complexity_score=0.2, required_capabilities=("simple_query",))
        budget = BudgetLimit(max_cost_per_task=float("inf"), max_tokens_per_task=1000, preferred_tier=2)
        model = await optimizer.select_model(req, budget_limit=budget)
        assert model.tier >= 2

    @pytest.mark.asyncio
    async def test_select_model_for_architecture(self):
        optimizer = CostOptimizer()
        req = TaskRequirements(category="architecture", complexity_score=0.9, required_capabilities=("reasoning", "design"))
        model = await optimizer.select_model(req)
        assert model.tier == 0  # tier-0 for architecture

    @pytest.mark.asyncio
    async def test_select_model_for_research(self):
        optimizer = CostOptimizer()
        req = TaskRequirements(category="research", complexity_score=0.85, required_capabilities=("research", "reasoning"))
        model = await optimizer.select_model(req)
        assert model.tier == 0  # tier-0 for research

    @pytest.mark.asyncio
    async def test_select_model_for_lookup(self):
        optimizer = CostOptimizer()
        req = TaskRequirements(category="lookup", complexity_score=0.1, required_capabilities=("simple_query",))
        model = await optimizer.select_model(req)
        assert model.tier >= 2  # economy or higher

    @pytest.mark.asyncio
    async def test_select_model_for_execution(self):
        optimizer = CostOptimizer()
        req = TaskRequirements(category="execution", complexity_score=0.3, required_capabilities=("execution",))
        model = await optimizer.select_model(req)
        # execution should be tier 3, but may fall back if no tier-3 model available
        assert model.tier >= 2

    @pytest.mark.asyncio
    async def test_select_model_with_budget_constraint(self):
        optimizer = CostOptimizer()
        req = TaskRequirements(category="coding", complexity_score=0.5, required_capabilities=("coding",))
        budget = BudgetLimit(max_cost_per_task=0.001, max_tokens_per_task=10000, preferred_tier=1)
        model = await optimizer.select_model(req, budget_limit=budget)
        assert model.cost_per_1k_tokens <= 0.001 or model.tier >= 2

    @pytest.mark.asyncio
    async def test_select_model_with_custom_config(self):
        optimizer = CostOptimizer()
        registry = {
            "custom-opus": ModelCapability(
                model_id="custom-opus", provider="custom", tier=0,
                strengths=("reasoning",), cost_per_1k_tokens=0.10,
                max_tokens=200000, supports_thinking=True,
            ),
        }
        config = RouterConfig(model_registry=registry, default_tier=0, routing_rules=("test",))
        req = TaskRequirements(category="architecture", complexity_score=0.9, required_capabilities=("reasoning",))
        model = await optimizer.select_model(req, config=config)
        assert model.model_id == "custom-opus"


class TestBudgetLimit:
    def test_budget_limit_dataclass(self):
        bl = BudgetLimit(max_cost_per_task=0.05, max_tokens_per_task=10000, preferred_tier=1)
        assert bl.max_cost_per_task == 0.05
        assert bl.max_tokens_per_task == 10000
        assert bl.preferred_tier == 1

    def test_budget_limit_is_frozen(self):
        bl = BudgetLimit(max_cost_per_task=0.05, max_tokens_per_task=10000, preferred_tier=1)
        with pytest.raises(AttributeError):
            bl.preferred_tier = 2  # type: ignore[misc]


# ═════════════════════════════════════════════════════════════════════════
# KnowingDoingGapDetector Tests
# ═════════════════════════════════════════════════════════════════════════


class TestKnowingDoingGapDetector:
    @pytest.mark.asyncio
    async def test_detect_gap_no_tools_expected(self):
        detector = KnowingDoingGapDetector()
        gap = await detector.detect_gap("Hello, how are you?")
        assert isinstance(gap, GapReport)
        assert not gap.has_gap

    @pytest.mark.asyncio
    async def test_detect_gap_missing_tool(self):
        detector = KnowingDoingGapDetector()
        gap = await detector.detect_gap(
            "Search the web for the latest news",
            tool_calls_made=(),
            expected_tools=("web_search",),
        )
        assert gap.has_gap
        assert "web_search" in gap.missing_tools

    @pytest.mark.asyncio
    async def test_detect_gap_all_tools_called(self):
        detector = KnowingDoingGapDetector()
        gap = await detector.detect_gap(
            "Search the web for the latest news",
            tool_calls_made=("web_search",),
            expected_tools=("web_search",),
        )
        assert not gap.has_gap
        assert len(gap.missing_tools) == 0

    @pytest.mark.asyncio
    async def test_detect_gap_some_tools_missing(self):
        detector = KnowingDoingGapDetector()
        gap = await detector.detect_gap(
            "Search the web and query the database",
            tool_calls_made=("web_search",),
            expected_tools=("web_search", "data_query"),
        )
        assert gap.has_gap
        assert "data_query" in gap.missing_tools
        assert "web_search" not in gap.missing_tools

    @pytest.mark.asyncio
    async def test_infer_expected_tools_web_search(self):
        detector = KnowingDoingGapDetector()
        gap = await detector.detect_gap("Look up the latest stock price for Apple")
        assert gap.has_gap
        assert "web_search" in gap.missing_tools

    @pytest.mark.asyncio
    async def test_infer_expected_tools_code_execution(self):
        detector = KnowingDoingGapDetector()
        gap = await detector.detect_gap("Run this Python script and show the output")
        assert gap.has_gap
        assert "code_execution" in gap.missing_tools

    @pytest.mark.asyncio
    async def test_infer_expected_tools_data_query(self):
        detector = KnowingDoingGapDetector()
        gap = await detector.detect_gap("Query the database for all user records")
        assert gap.has_gap
        assert "data_query" in gap.missing_tools

    @pytest.mark.asyncio
    async def test_infer_expected_tools_verification(self):
        detector = KnowingDoingGapDetector()
        gap = await detector.detect_gap("Verify that the calculation is correct")
        assert gap.has_gap
        assert "verification" in gap.missing_tools

    @pytest.mark.asyncio
    async def test_infer_expected_tools_api_call(self):
        detector = KnowingDoingGapDetector()
        gap = await detector.detect_gap("Call the REST API to get user data")
        assert gap.has_gap
        assert "api_call" in gap.missing_tools

    @pytest.mark.asyncio
    async def test_infer_multiple_expected_tools(self):
        detector = KnowingDoingGapDetector()
        gap = await detector.detect_gap(
            "Search the web, run the script, and verify the results"
        )
        assert gap.has_gap
        assert "web_search" in gap.missing_tools
        assert "code_execution" in gap.missing_tools
        assert "verification" in gap.missing_tools

    @pytest.mark.asyncio
    async def test_recommendation_single_tool(self):
        detector = KnowingDoingGapDetector()
        gap = await detector.detect_gap(
            "Search the web",
            expected_tools=("web_search",),
        )
        assert "web_search" in gap.recommendation
        assert len(gap.recommendation) > 0

    @pytest.mark.asyncio
    async def test_recommendation_multiple_tools(self):
        detector = KnowingDoingGapDetector()
        gap = await detector.detect_gap(
            "Complex task",
            expected_tools=("web_search", "data_query", "code_execution"),
        )
        assert gap.has_gap
        assert len(gap.recommendation) > 0

    @pytest.mark.asyncio
    async def test_gap_report_frozen(self):
        report = GapReport(has_gap=True, missing_tools=("tool",), recommendation="Use tool")
        with pytest.raises(AttributeError):
            report.has_gap = False  # type: ignore[misc]


# ═════════════════════════════════════════════════════════════════════════
# CrossModelVerifier Tests
# ═════════════════════════════════════════════════════════════════════════


class TestCrossModelVerifier:
    @pytest.mark.asyncio
    async def test_verify_different_families(self):
        verifier = CrossModelVerifier()
        verifier_config = ModelCapability(
            model_id="deepseek-v4-pro", provider="deepseek", tier=0,
            strengths=("reasoning",), cost_per_1k_tokens=0.001,
            max_tokens=128000, supports_thinking=True,
        )
        result = await verifier.verify(
            output="some output",
            generator_model="claude-opus-4-7",
            verifier_model_config=verifier_config,
        )
        assert isinstance(result, VerificationResult)
        assert result.passed
        assert len(result.issues) == 0
        assert result.score > 0

    @pytest.mark.asyncio
    async def test_verify_same_family_anthropic(self):
        verifier = CrossModelVerifier()
        verifier_config = ModelCapability(
            model_id="claude-haiku-4-5", provider="anthropic", tier=2,
            strengths=("speed",), cost_per_1k_tokens=0.0025,
            max_tokens=50000, supports_thinking=False,
        )
        result = await verifier.verify(
            output="some output",
            generator_model="claude-opus-4-7",
            verifier_model_config=verifier_config,
        )
        assert not result.passed
        assert len(result.issues) > 0
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_verify_same_family_deepseek(self):
        verifier = CrossModelVerifier()
        verifier_config = ModelCapability(
            model_id="deepseek-v4-flash", provider="deepseek", tier=2,
            strengths=("speed",), cost_per_1k_tokens=0.0005,
            max_tokens=64000, supports_thinking=False,
        )
        result = await verifier.verify(
            output="test",
            generator_model="deepseek-v4-pro",
            verifier_model_config=verifier_config,
        )
        assert not result.passed
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_verify_anthropic_deepseek_high_diversity(self):
        verifier = CrossModelVerifier()
        verifier_config = ModelCapability(
            model_id="deepseek-v4-pro", provider="deepseek", tier=0,
            strengths=("reasoning",), cost_per_1k_tokens=0.001,
            max_tokens=128000, supports_thinking=True,
        )
        result = await verifier.verify(
            output="test",
            generator_model="claude-opus-4-7",
            verifier_model_config=verifier_config,
        )
        assert result.score == 0.85

    @pytest.mark.asyncio
    async def test_verify_unknown_family_lower_diversity(self):
        verifier = CrossModelVerifier()
        verifier_config = ModelCapability(
            model_id="custom-model", provider="other", tier=1,
            strengths=("custom",), cost_per_1k_tokens=0.01,
            max_tokens=10000, supports_thinking=False,
        )
        result = await verifier.verify(
            output="test",
            generator_model="claude-opus-4-7",
            verifier_model_config=verifier_config,
        )
        assert result.passed
        assert result.score == 0.5

    @pytest.mark.asyncio
    async def test_detect_family_anthropic(self):
        verifier = CrossModelVerifier()
        assert verifier._detect_family("claude-opus-4-7") == "anthropic"
        assert verifier._detect_family("claude-sonnet-4-6") == "anthropic"
        assert verifier._detect_family("claude-haiku-4-5") == "anthropic"

    @pytest.mark.asyncio
    async def test_detect_family_deepseek(self):
        verifier = CrossModelVerifier()
        assert verifier._detect_family("deepseek-v4-pro") == "deepseek"
        assert verifier._detect_family("deepseek-chat") == "deepseek"

    @pytest.mark.asyncio
    async def test_detect_family_openai(self):
        verifier = CrossModelVerifier()
        assert verifier._detect_family("gpt-4o") == "openai"
        assert verifier._detect_family("o1-preview") == "openai"

    @pytest.mark.asyncio
    async def test_detect_family_unknown(self):
        verifier = CrossModelVerifier()
        assert verifier._detect_family("unknown-model") == "other"

    @pytest.mark.asyncio
    async def test_verification_result_frozen(self):
        result = VerificationResult(passed=True, issues=(), score=0.85)
        with pytest.raises(AttributeError):
            result.passed = False  # type: ignore[misc]


# ═════════════════════════════════════════════════════════════════════════
# UsageTracker Tests
# ═════════════════════════════════════════════════════════════════════════


class TestUsageTracker:
    @pytest.mark.asyncio
    async def test_record_usage(self):
        tracker = UsageTracker()
        record = UsageRecord(
            model_id="opus", task_type="coding",
            tokens_in=500, tokens_out=200,
            latency_ms=3000.0, cost=0.05,
            timestamp=1000.0,
        )
        await tracker.record_usage(record)
        assert tracker.total_calls == 1

    @pytest.mark.asyncio
    async def test_record_multiple(self):
        tracker = UsageTracker()
        await tracker.record_usage(UsageRecord(
            model_id="m1", task_type="coding",
            tokens_in=100, tokens_out=50,
            latency_ms=100.0, cost=0.01,
            timestamp=1000.0,
        ))
        await tracker.record_usage(UsageRecord(
            model_id="m2", task_type="reasoning",
            tokens_in=200, tokens_out=100,
            latency_ms=200.0, cost=0.02,
            timestamp=1001.0,
        ))
        assert tracker.total_calls == 2

    @pytest.mark.asyncio
    async def test_get_stats_per_model(self):
        tracker = UsageTracker()
        await tracker.record_usage(UsageRecord(
            model_id="opus", task_type="reasoning",
            tokens_in=1000, tokens_out=500,
            latency_ms=5000.0, cost=0.075,
            timestamp=1000.0,
        ))
        await tracker.record_usage(UsageRecord(
            model_id="sonnet", task_type="coding",
            tokens_in=500, tokens_out=200,
            latency_ms=2000.0, cost=0.015,
            timestamp=1001.0,
        ))
        await tracker.record_usage(UsageRecord(
            model_id="opus", task_type="analysis",
            tokens_in=800, tokens_out=300,
            latency_ms=4000.0, cost=0.06,
            timestamp=1002.0,
        ))
        stats = await tracker.get_stats_per_model()
        assert "opus" in stats
        assert "sonnet" in stats
        assert stats["opus"].total_calls == 2
        assert stats["sonnet"].total_calls == 1

    @pytest.mark.asyncio
    async def test_get_stats_per_task(self):
        tracker = UsageTracker()
        await tracker.record_usage(UsageRecord(
            model_id="m1", task_type="coding",
            tokens_in=100, tokens_out=50,
            latency_ms=100.0, cost=0.01,
            timestamp=1000.0,
        ))
        await tracker.record_usage(UsageRecord(
            model_id="m1", task_type="reasoning",
            tokens_in=200, tokens_out=100,
            latency_ms=200.0, cost=0.02,
            timestamp=1001.0,
        ))
        await tracker.record_usage(UsageRecord(
            model_id="m2", task_type="coding",
            tokens_in=300, tokens_out=150,
            latency_ms=300.0, cost=0.03,
            timestamp=1002.0,
        ))
        stats = await tracker.get_stats_per_task()
        assert "coding" in stats
        assert "reasoning" in stats
        assert stats["coding"].total_calls == 2
        assert stats["reasoning"].total_calls == 1

    @pytest.mark.asyncio
    async def test_estimate_session_cost(self):
        tracker = UsageTracker()
        await tracker.record_usage(UsageRecord(
            model_id="opus", task_type="reasoning",
            tokens_in=1000, tokens_out=500,
            latency_ms=5000.0, cost=0.075,
            timestamp=1000.0,
        ))
        await tracker.record_usage(UsageRecord(
            model_id="haiku", task_type="lookup",
            tokens_in=100, tokens_out=50,
            latency_ms=500.0, cost=0.0025,
            timestamp=1001.0,
        ))
        total = await tracker.estimate_session_cost()
        assert total == pytest.approx(0.0775, rel=0.01)

    @pytest.mark.asyncio
    async def test_estimate_session_cost_empty(self):
        tracker = UsageTracker()
        total = await tracker.estimate_session_cost()
        assert total == 0.0

    @pytest.mark.asyncio
    async def test_total_calls_property(self):
        tracker = UsageTracker()
        assert tracker.total_calls == 0
        await tracker.record_usage(UsageRecord(
            model_id="m", task_type="t",
            tokens_in=1, tokens_out=1,
            latency_ms=1.0, cost=0.001,
            timestamp=1000.0,
        ))
        assert tracker.total_calls == 1

    @pytest.mark.asyncio
    async def test_stats_aggregation_values(self):
        tracker = UsageTracker()
        await tracker.record_usage(UsageRecord(
            model_id="m", task_type="t",
            tokens_in=100, tokens_out=50,
            latency_ms=200.0, cost=0.01,
            timestamp=1000.0,
        ))
        await tracker.record_usage(UsageRecord(
            model_id="m", task_type="t",
            tokens_in=200, tokens_out=100,
            latency_ms=400.0, cost=0.02,
            timestamp=1001.0,
        ))
        stats = await tracker.get_stats_per_model()
        model_stats = stats["m"]
        assert model_stats.total_tokens_in == 300
        assert model_stats.total_tokens_out == 150
        assert model_stats.total_cost == 0.03
        assert model_stats.total_latency_ms == 600.0
        assert model_stats.avg_latency_ms == 300.0
        assert model_stats.avg_cost_per_call == 0.015

    @pytest.mark.asyncio
    async def test_usage_record_frozen(self):
        record = UsageRecord(
            model_id="m", task_type="t",
            tokens_in=1, tokens_out=1,
            latency_ms=1.0, cost=0.001,
            timestamp=1000.0,
        )
        with pytest.raises(AttributeError):
            record.model_id = "other"  # type: ignore[misc]

    @pytest.mark.asyncio
    async def test_usage_stats_empty_aggregate(self):
        tracker = UsageTracker()
        stats = await tracker.get_stats_per_model()
        assert len(stats) == 0

    @pytest.mark.asyncio
    async def test_get_stats_per_task_empty(self):
        tracker = UsageTracker()
        stats = await tracker.get_stats_per_task()
        assert len(stats) == 0


# ═════════════════════════════════════════════════════════════════════════
# Exceptions Tests
# ═════════════════════════════════════════════════════════════════════════


class TestExceptions:
    def test_model_router_error_is_base(self):
        assert issubclass(ModelRouterError, Exception)

    def test_model_router_error_can_be_raised(self):
        with pytest.raises(ModelRouterError, match="test error"):
            raise ModelRouterError("test error")

    def test_model_router_error_message(self):
        err = ModelRouterError("something went wrong")
        assert str(err) == "something went wrong"


# ═════════════════════════════════════════════════════════════════════════
# Integration Tests
# ═════════════════════════════════════════════════════════════════════════


class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_analysis_to_selection_pipeline(self):
        """Test the full pipeline: analyze task -> select model."""
        analyzer = CapabilityAnalyzer()
        optimizer = CostOptimizer()

        req = await analyzer.analyze_task(
            "Design a distributed microservices architecture with Kubernetes",
            context_tokens=60000,
            tools_required=5,
        )
        assert req.category == "architecture"
        assert req.complexity_score >= 0.5

        model = await optimizer.select_model(req)
        assert model.tier == 0  # architecture gets tier 0
        assert model.provider in ("anthropic", "deepseek")

    @pytest.mark.asyncio
    async def test_verification_with_usage_tracking(self):
        """Test cross-model verification with usage tracking."""
        verifier = CrossModelVerifier()
        tracker = UsageTracker()

        opus = ModelCapability(
            model_id="claude-opus-4-7", provider="anthropic", tier=0,
            strengths=("reasoning",), cost_per_1k_tokens=0.075,
            max_tokens=200000, supports_thinking=True,
        )
        deepseek = ModelCapability(
            model_id="deepseek-v4-pro", provider="deepseek", tier=0,
            strengths=("reasoning",), cost_per_1k_tokens=0.001,
            max_tokens=128000, supports_thinking=True,
        )

        result = await verifier.verify(
            output="analysis result",
            generator_model="claude-opus-4-7",
            verifier_model_config=deepseek,
        )
        assert result.passed
        assert result.score > 0

        await tracker.record_usage(UsageRecord(
            model_id="claude-opus-4-7", task_type="research",
            tokens_in=5000, tokens_out=2000,
            latency_ms=10000.0, cost=0.525,
            timestamp=1000.0,
        ))
        await tracker.record_usage(UsageRecord(
            model_id="deepseek-v4-pro", task_type="verification",
            tokens_in=2000, tokens_out=500,
            latency_ms=3000.0, cost=0.0025,
            timestamp=1001.0,
        ))

        assert tracker.total_calls == 2
        cost = await tracker.estimate_session_cost()
        assert cost > 0

    @pytest.mark.asyncio
    async def test_gap_detection_leads_to_cost_optimization(self):
        """Test that gap detection informs model selection."""
        detector = KnowingDoingGapDetector()
        optimizer = CostOptimizer()

        gap = await detector.detect_gap(
            "Search the web and run data analysis on the results",
            tool_calls_made=("web_search",),  # missing code_execution
        )
        assert gap.has_gap
        assert "code_execution" in gap.missing_tools

        req = TaskRequirements(
            category="research",
            complexity_score=0.7,
            required_capabilities=("research", "reasoning"),
        )
        model = await optimizer.select_model(req)
        # Research tasks should get tier 0
        assert model.tier == 0

    @pytest.mark.asyncio
    async def test_multi_model_usage_tracking(self):
        """Test usage tracking across multiple models."""
        tracker = UsageTracker()

        records = [
            UsageRecord(model_id="opus", task_type="research",
                        tokens_in=5000, tokens_out=2000,
                        latency_ms=10000.0, cost=0.525, timestamp=1000.0),
            UsageRecord(model_id="sonnet", task_type="coding",
                        tokens_in=2000, tokens_out=800,
                        latency_ms=4000.0, cost=0.042, timestamp=1001.0),
            UsageRecord(model_id="haiku", task_type="lookup",
                        tokens_in=500, tokens_out=200,
                        latency_ms=1000.0, cost=0.00175, timestamp=1002.0),
        ]
        for r in records:
            await tracker.record_usage(r)

        assert tracker.total_calls == 3
        model_stats = await tracker.get_stats_per_model()
        assert set(model_stats.keys()) == {"opus", "sonnet", "haiku"}
        assert model_stats["opus"].total_cost == 0.525
        task_stats = await tracker.get_stats_per_task()
        assert set(task_stats.keys()) == {"research", "coding", "lookup"}
        total = await tracker.estimate_session_cost()
        assert total == pytest.approx(0.56875, rel=0.01)

    @pytest.mark.asyncio
    async def test_budget_constrained_selection(self):
        """Test model selection respects budget constraints."""
        optimizer = CostOptimizer()
        req = TaskRequirements(
            category="coding",
            complexity_score=0.5,
            required_capabilities=("coding",),
        )
        # Very tight budget
        budget = BudgetLimit(
            max_cost_per_task=0.001,
            max_tokens_per_task=5000,
            preferred_tier=2,
        )
        model = await optimizer.select_model(req, budget_limit=budget)
        assert model.cost_per_1k_tokens <= 0.001 or model.tier >= 2


# ═════════════════════════════════════════════════════════════════════════
# V3 — TaskClassifier Tests (15 categories)
# ═════════════════════════════════════════════════════════════════════════


class TestTaskClassifier:
    """Tests for the 15-category task classifier."""

    def test_all_categories_exist(self):
        assert len(TaskCategory) == 15

    def test_classify_architecture(self):
        classifier = TaskClassifier()
        result = classifier.classify("Design a microservice architecture with trade-off analysis")
        assert result.primary == TaskCategory.ARCHITECTURE
        assert result.confidence > 0.3

    def test_classify_code_implementation(self):
        classifier = TaskClassifier()
        result = classifier.classify("Implement a new API endpoint for user authentication")
        assert result.primary == TaskCategory.CODE_IMPLEMENTATION

    def test_classify_code_review(self):
        classifier = TaskClassifier()
        result = classifier.classify("Review this PR for code quality and approve if it passes the quality gate")
        assert result.primary == TaskCategory.CODE_REVIEW

    def test_classify_debugging(self):
        classifier = TaskClassifier()
        result = classifier.classify("Debug this stack trace and find the root cause of the crash")
        assert result.primary == TaskCategory.DEBUGGING

    def test_classify_refactoring(self):
        classifier = TaskClassifier()
        result = classifier.classify("Refactor this module to extract method and decouple dependencies")
        assert result.primary == TaskCategory.REFACTORING

    def test_classify_testing(self):
        classifier = TaskClassifier()
        result = classifier.classify("Write unit tests and integration tests for the e2e coverage")
        assert result.primary == TaskCategory.TESTING

    def test_classify_research(self):
        classifier = TaskClassifier()
        result = classifier.classify("Research the latest papers and do a deep dive survey on AGI")
        assert result.primary == TaskCategory.RESEARCH

    def test_classify_data_analysis(self):
        classifier = TaskClassifier()
        result = classifier.classify("Write an ETL pipeline with SQL queries and an analytics dashboard")
        assert result.primary == TaskCategory.DATA_ANALYSIS

    def test_classify_documentation(self):
        classifier = TaskClassifier()
        result = classifier.classify("Write API docs, README, and changelog documentation")
        assert result.primary == TaskCategory.DOCUMENTATION

    def test_classify_security_audit(self):
        classifier = TaskClassifier()
        result = classifier.classify("Run OWASP security vulnerability and penetration audit")
        assert result.primary == TaskCategory.SECURITY_AUDIT

    def test_classify_devops(self):
        classifier = TaskClassifier()
        result = classifier.classify("Set up CI/CD pipeline with Docker and Kubernetes deployment")
        assert result.primary == TaskCategory.DEVOPS

    def test_classify_simple_lookup(self):
        classifier = TaskClassifier()
        result = classifier.classify("Find where the config file is and list the settings")
        assert result.primary == TaskCategory.SIMPLE_LOOKUP

    def test_classify_batch_processing(self):
        classifier = TaskClassifier()
        result = classifier.classify("Batch process all files and bulk migrate the data")
        assert result.primary == TaskCategory.BATCH_PROCESSING

    def test_classify_creative_generation(self):
        classifier = TaskClassifier()
        result = classifier.classify("Brainstorm creative copywriting ideas for the logo design")
        assert result.primary == TaskCategory.CREATIVE_GENERATION

    def test_classify_conversation(self):
        classifier = TaskClassifier()
        result = classifier.classify("Hello! How are you? Can you help clarify something?")
        assert result.primary == TaskCategory.CONVERSATION

    def test_top_categories_are_returned(self):
        classifier = TaskClassifier()
        result = classifier.classify("Refactor the API and add unit tests")
        assert len(result.top_categories) == 3

    def test_all_scores_dict_is_complete(self):
        classifier = TaskClassifier()
        result = classifier.classify("Write documentation")
        assert len(result.all_scores) == 15

    def test_classification_result_is_frozen(self):
        result = ClassificationResult(primary=TaskCategory.CODE_IMPLEMENTATION, confidence=0.9)
        with pytest.raises(Exception):
            result.confidence = 0.5

    def test_classify_batch(self):
        classifier = TaskClassifier()
        results = classifier.classify_batch([
            "Debug this bug", "Write documentation", "Deploy to Kubernetes",
        ])
        assert len(results) == 3
        assert results[0].primary == TaskCategory.DEBUGGING
        assert results[1].primary == TaskCategory.DOCUMENTATION
        assert results[2].primary == TaskCategory.DEVOPS

    def test_classification_counts(self):
        classifier = TaskClassifier()
        classifier.classify("Debug this")
        classifier.classify("Debug that")
        classifier.classify("Research AI")
        counts = classifier.classification_counts
        assert counts[TaskCategory.DEBUGGING] == 2
        assert counts[TaskCategory.RESEARCH] == 1

    def test_reset_counts(self):
        classifier = TaskClassifier()
        classifier.classify("Debug this")
        classifier.reset_counts()
        assert all(v == 0 for v in classifier.classification_counts.values())


# ═════════════════════════════════════════════════════════════════════════
# V3 — ComplexityEstimator Tests (1-10 scale)
# ═════════════════════════════════════════════════════════════════════════


class TestComplexityEstimator:
    """Tests for the 1-10 complexity estimator."""

    def test_trivial_task_scores_low(self):
        estimator = ComplexityEstimator()
        result = estimator.estimate("Fix a typo in the README")
        assert result.score < 3.0

    def test_complex_task_scores_high(self):
        estimator = ComplexityEstimator()
        result = estimator.estimate(
            "Design a distributed recursive consensus protocol with encryption "
            "and real-time performance critical optimizations for a multi-threaded "
            "compiler with neural network integration",
            context_tokens=120_000,
            tools_required=15,
        )
        assert result.score >= 7.0

    def test_score_in_1_to_10_range(self):
        estimator = ComplexityEstimator()
        for desc in ["x", "a" * 2000]:
            result = estimator.estimate(desc)
            assert 1.0 <= result.score <= 10.0

    def test_factors_are_returned(self):
        estimator = ComplexityEstimator()
        result = estimator.estimate("Write a function", context_tokens=5000, tools_required=3)
        assert "description" in result.factors
        assert "context" in result.factors
        assert "tools" in result.factors

    def test_reasoning_string(self):
        estimator = ComplexityEstimator()
        result = estimator.estimate("Write code")
        assert "Complexity" in result.reasoning
        assert "tier" in result.reasoning

    def test_recommended_tier_range(self):
        estimator = ComplexityEstimator()
        result = estimator.estimate("Simple task")
        assert 0 <= result.recommended_tier <= 3

    def test_high_complexity_signal_boosts_score(self):
        estimator = ComplexityEstimator()
        simple = estimator.estimate("Write a function")
        complex = estimator.estimate("Write a compiler with recursive descent parser")
        assert complex.score > simple.score

    def test_context_tokens_influence_score(self):
        estimator = ComplexityEstimator()
        low_ctx = estimator.estimate("task", context_tokens=1000)
        high_ctx = estimator.estimate("task", context_tokens=150_000)
        assert high_ctx.score > low_ctx.score

    def test_tools_count_influences_score(self):
        estimator = ComplexityEstimator()
        few = estimator.estimate("task", tools_required=1)
        many = estimator.estimate("task", tools_required=15)
        assert many.score > few.score

    def test_dependencies_influence_score(self):
        estimator = ComplexityEstimator()
        no_deps = estimator.estimate("task", dependency_count=0)
        many_deps = estimator.estimate("task", dependency_count=10)
        assert many_deps.score > no_deps.score

    def test_domain_difficulty(self):
        estimator = ComplexityEstimator()
        compiler = estimator.estimate("task", domain="compiler")
        docs = estimator.estimate("task", domain="documentation")
        assert compiler.score > docs.score

    def test_estimate_is_frozen(self):
        estimator = ComplexityEstimator()
        result = estimator.estimate("task")
        with pytest.raises(Exception):
            result.score = 5.0

    def test_recommend_tier_for_very_complex(self):
        estimator = ComplexityEstimator()
        result = estimator.estimate(
            "Design a distributed OS kernel with real-time constraints",
            context_tokens=150_000, tools_required=20, domain="os_kernel",
        )
        assert result.recommended_tier == 0

    def test_recommend_tier_for_simple(self):
        estimator = ComplexityEstimator()
        result = estimator.estimate("Fix a typo")
        assert result.recommended_tier == 3


# ═════════════════════════════════════════════════════════════════════════
# V3 — PerformanceHistory Tests
# ═════════════════════════════════════════════════════════════════════════


class TestPerformanceHistory:
    """Tests for learned performance history tracking."""

    def test_record_and_retrieve(self):
        history = PerformanceHistory()
        history.record(PerformanceRecord(
            model_id="claude-sonnet-4-6", category=TaskCategory.CODE_IMPLEMENTATION,
            complexity=5.0, success=True,
        ))
        assert history.record_count == 1

    def test_get_model_performance(self):
        history = PerformanceHistory()
        for i in range(5):
            history.record(PerformanceRecord(
                model_id="claude-sonnet-4-6", category=TaskCategory.CODE_IMPLEMENTATION,
                complexity=5.0, success=(i < 4),
            ))
        perf = history.get_model_performance("claude-sonnet-4-6", TaskCategory.CODE_IMPLEMENTATION)
        assert perf.total_attempts == 5
        assert perf.success_count == 4
        assert perf.success_rate == pytest.approx(0.8, rel=0.01)

    def test_cold_start_performance(self):
        history = PerformanceHistory()
        perf = history.get_model_performance("unknown-model", TaskCategory.CODE_IMPLEMENTATION)
        assert perf.is_cold
        assert perf.total_attempts == 0

    def test_recommend_model_with_history(self):
        history = PerformanceHistory()
        for _ in range(10):
            history.record(PerformanceRecord(
                model_id="claude-opus-4.7", category=TaskCategory.ARCHITECTURE,
                complexity=8.0, success=True,
            ))
        for _ in range(10):
            history.record(PerformanceRecord(
                model_id="claude-sonnet-4-6", category=TaskCategory.ARCHITECTURE,
                complexity=8.0, success=False,
            ))
        rec = history.recommend_model(
            TaskCategory.ARCHITECTURE, ["claude-opus-4.7", "claude-sonnet-4-6"],
        )
        assert rec is not None
        assert rec.model_id == "claude-opus-4.7"

    def test_recommend_requires_min_attempts(self):
        history = PerformanceHistory()
        history.record(PerformanceRecord(
            model_id="claude-opus-4.7", category=TaskCategory.CODE_IMPLEMENTATION,
            complexity=5.0, success=True,
        ))
        rec = history.recommend_model(
            TaskCategory.CODE_IMPLEMENTATION, ["claude-opus-4.7"], min_attempts=3,
        )
        assert rec is None

    def test_category_leaderboard(self):
        history = PerformanceHistory()
        for _ in range(5):
            history.record(PerformanceRecord(
                model_id="model-a", category=TaskCategory.CODE_IMPLEMENTATION,
                complexity=5.0, success=True,
            ))
        for _ in range(5):
            history.record(PerformanceRecord(
                model_id="model-b", category=TaskCategory.CODE_IMPLEMENTATION,
                complexity=5.0, success=False,
            ))
        board = history.get_category_leaderboard(TaskCategory.CODE_IMPLEMENTATION)
        assert len(board) == 2
        assert board[0].model_id == "model-a"

    def test_global_stats(self):
        history = PerformanceHistory()
        history.record(PerformanceRecord(
            model_id="m1", category=TaskCategory.CODE_IMPLEMENTATION, complexity=5.0, success=True,
        ))
        history.record(PerformanceRecord(
            model_id="m2", category=TaskCategory.RESEARCH, complexity=7.0, success=False,
        ))
        stats = history.get_global_stats()
        assert stats["total_decisions"] == 2
        assert stats["global_success_rate"] == 0.5
        assert stats["unique_models"] == 2

    def test_prune_old_records(self):
        history = PerformanceHistory()
        history.record(PerformanceRecord(
            model_id="old-model", category=TaskCategory.CODE_IMPLEMENTATION,
            complexity=5.0, success=True,
            timestamp=time.time() - 100 * 86400,
        ))
        history.record(PerformanceRecord(
            model_id="new-model", category=TaskCategory.CODE_IMPLEMENTATION,
            complexity=5.0, success=True,
            timestamp=time.time(),
        ))
        removed = history.prune_old_records(max_age_days=50.0)
        assert removed == 1
        assert history.record_count == 1

    def test_performance_record_is_frozen(self):
        record = PerformanceRecord(
            model_id="m1", category=TaskCategory.CODE_IMPLEMENTATION,
            complexity=5.0, success=True,
        )
        with pytest.raises(Exception):
            record.success = False

    def test_recommendation_confidence_scales(self):
        history = PerformanceHistory()
        for _ in range(20):
            history.record(PerformanceRecord(
                model_id="m1", category=TaskCategory.CODE_IMPLEMENTATION,
                complexity=5.0, success=True,
            ))
        rec = history.recommend_model(TaskCategory.CODE_IMPLEMENTATION, ["m1"])
        assert rec is not None
        assert rec.confidence >= 0.9


# ═════════════════════════════════════════════════════════════════════════
# V3 — ConfidenceEscalator Tests
# ═════════════════════════════════════════════════════════════════════════


class TestConfidenceEscalator:
    """Tests for confidence-thresholded escalation with fallback chains."""

    @staticmethod
    def _mk_decision(name="claude-haiku-4-5", confidence=0.6):
        return RoutingDecision(
            model=ModelSpec(
                name=name, provider=ModelProvider.ANTHROPIC, tier=ModelTier.FAST,
                cost_per_1k_tokens=0.001, latency_ms=100.0, accuracy_estimate=confidence,
            ),
            confidence=confidence,
            estimated_cost=0.0005,
            strategy=RoutingStrategy.BALANCED,
        )

    @staticmethod
    def _mk_model(name, provider, tier, accuracy, cost=0.003):
        return ModelSpec(
            name=name, provider=provider, tier=tier,
            cost_per_1k_tokens=cost, latency_ms=300.0, accuracy_estimate=accuracy,
        )

    def test_low_confidence_triggers_escalation(self):
        escalator = ConfidenceEscalator(confidence_threshold=0.75)
        assert escalator.should_escalate(self._mk_decision(confidence=0.5))

    def test_high_confidence_no_escalation(self):
        escalator = ConfidenceEscalator(confidence_threshold=0.75)
        assert not escalator.should_escalate(self._mk_decision(confidence=0.9))

    def test_degraded_provider_triggers_escalation(self):
        escalator = ConfidenceEscalator(confidence_threshold=0.75)
        for _ in range(3):
            escalator.record_failure(ModelProvider.ANTHROPIC)
        assert escalator.should_escalate(self._mk_decision(confidence=0.9))

    def test_escalation_finds_alternative(self):
        escalator = ConfidenceEscalator(confidence_threshold=0.75)
        decision = self._mk_decision("claude-haiku-4-5", confidence=0.5)
        available = [
            self._mk_model("claude-haiku-4-5", ModelProvider.ANTHROPIC, ModelTier.FAST, 0.8),
            self._mk_model("gpt-5.4-nano", ModelProvider.OPENAI, ModelTier.FAST, 0.78),
            self._mk_model("claude-sonnet-4-6", ModelProvider.ANTHROPIC, ModelTier.STANDARD, 0.88),
            self._mk_model("deepseek-v4-pro", ModelProvider.LITELLM, ModelTier.REASONING, 0.92),
        ]
        result = escalator.escalate(decision, available)
        assert result.escalated
        assert result.final_decision is not None

    def test_no_escalation_if_confident(self):
        escalator = ConfidenceEscalator(confidence_threshold=0.75)
        decision = self._mk_decision("claude-sonnet-4-6", confidence=0.88)
        result = escalator.escalate(decision, [decision.model])
        assert not result.escalated
        assert result.final_decision == decision

    def test_provider_health_tracking(self):
        escalator = ConfidenceEscalator()
        assert escalator.is_provider_healthy(ModelProvider.ANTHROPIC)
        escalator.record_failure(ModelProvider.ANTHROPIC)
        escalator.record_failure(ModelProvider.ANTHROPIC)
        assert escalator.is_provider_healthy(ModelProvider.ANTHROPIC)
        escalator.record_failure(ModelProvider.ANTHROPIC)
        assert not escalator.is_provider_healthy(ModelProvider.ANTHROPIC)
        escalator.record_success(ModelProvider.ANTHROPIC)
        assert escalator.is_provider_healthy(ModelProvider.ANTHROPIC)

    def test_escalation_result_steps_are_tuple(self):
        escalator = ConfidenceEscalator(confidence_threshold=0.75)
        decision = self._mk_decision(confidence=0.9)
        result = escalator.escalate(decision, [decision.model])
        assert isinstance(result.steps, tuple)


class TestProviderHealth:
    """Tests for provider health tracking."""

    def test_initial_state(self):
        health = ProviderHealth(provider=ModelProvider.ANTHROPIC)
        assert not health.is_degraded
        assert health.success_rate == 1.0

    def test_record_success_resets(self):
        health = ProviderHealth(provider=ModelProvider.ANTHROPIC)
        health.record_failure()
        health.record_success()
        assert health.consecutive_failures == 0

    def test_degraded_after_multiple_failures(self):
        health = ProviderHealth(provider=ModelProvider.ANTHROPIC)
        for _ in range(3):
            health.record_failure()
        assert health.is_degraded
