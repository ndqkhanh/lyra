"""Tests for lyra-model-router package (50+ tests)."""

from __future__ import annotations

import pytest

from lyra_model_router import (
    BudgetLimit,
    CapabilityAnalyzer,
    CostOptimizer,
    CrossModelVerifier,
    GapReport,
    KnowingDoingGapDetector,
    ModelCapability,
    ModelRouterError,
    RouterConfig,
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
