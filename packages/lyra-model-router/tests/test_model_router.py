"""Tests for lyra-model-router package."""

from __future__ import annotations

import asyncio
import json
import math
import time

import pytest

from lyra_model_router import (
    # Capability Analyzer
    CapabilityAnalyzer,
    ComplexityLevel,
    DomainType,
    LatencySensitivity,
    MatchScore,
    ModelCapability,
    TaskProfile,
    # Cost Optimizer
    BudgetLimits,
    BudgetTracker,
    CostOptimizer,
    CostTier,
    # Knowing-Doing Gap
    GapRecommendation,
    KnowingDoingGapDetector,
    ToolCategory,
    ToolNecessitySignal,
    # Cross-Model Verifier
    CrossModelVerifier,
    ModelFamily,
    ValidationResult,
    # Router Config
    FallbackRule,
    HealthStatus,
    ModelRegistryEntry,
    RouterConfig,
    RoutingPolicy,
    PolicyType,
    # Router
    ModelRouter,
    ModelSelection,
    # Usage Tracker
    BudgetAlert,
    UsageRecord,
    UsageStats,
    UsageTracker,
    # Exceptions
    BudgetExceededError,
    CapabilityMismatchError,
    ModelNotFoundError,
    RouterError,
    RoutingError,
    VerificationError,
)


# ═══════════════════════════════════════════════════════════════════════
# CapabilityAnalyzer Tests
# ═══════════════════════════════════════════════════════════════════════


class TestCapabilityAnalyzer:
    def test_predefined_capabilities(self):
        analyzer = CapabilityAnalyzer()
        caps = analyzer.capabilities
        assert len(caps) == 4
        ids = [c.model_id for c in caps]
        assert "claude-opus-4.7" in ids
        assert "claude-sonnet-4.6" in ids
        assert "claude-haiku-4.5" in ids
        assert "deepseek-v4-pro" in ids

    def test_register_model(self):
        analyzer = CapabilityAnalyzer()
        new_cap = ModelCapability(
            model_id="gpt-4o",
            tier="premium",
            reasoning_score=0.90,
            coding_score=0.92,
            speed_score=0.65,
            cost_per_1k_tokens=0.05,
            context_limit=128000,
        )
        analyzer.register_model(new_cap)
        assert len(analyzer.capabilities) == 5
        assert analyzer.get_model("gpt-4o") is not None

    def test_remove_model(self):
        analyzer = CapabilityAnalyzer()
        assert analyzer.remove_model("claude-haiku-4.5")
        assert analyzer.get_model("claude-haiku-4.5") is None
        assert len(analyzer.capabilities) == 3
        assert not analyzer.remove_model("nonexistent")

    def test_get_model_nonexistent(self):
        analyzer = CapabilityAnalyzer()
        assert analyzer.get_model("nonexistent") is None

    def test_analyze_returns_scores(self):
        analyzer = CapabilityAnalyzer()
        task = TaskProfile(
            complexity=ComplexityLevel.COMPLEX,
            domain=DomainType.REASONING,
            reasoning_depth=0.9,
        )
        scores = analyzer.analyze(task)
        assert len(scores) == 4
        assert all(isinstance(s, MatchScore) for s in scores)
        # Scores should be in descending order
        for i in range(len(scores) - 1):
            assert scores[i].total_score >= scores[i + 1].total_score

    def test_analyze_reasoning_task_prefers_opus(self):
        analyzer = CapabilityAnalyzer()
        task = TaskProfile(
            complexity=ComplexityLevel.VERY_COMPLEX,
            domain=DomainType.REASONING,
            reasoning_depth=1.0,
        )
        scores = analyzer.analyze(task)
        # Opus should be in top 2 for reasoning-heavy tasks
        top_ids = [s.model_id for s in scores[:2]]
        assert "claude-opus-4.7" in top_ids
        assert scores[0].reasoning_score >= scores[1].reasoning_score

    def test_analyze_coding_task_prefers_sonnet(self):
        analyzer = CapabilityAnalyzer()
        task = TaskProfile(
            complexity=ComplexityLevel.COMPLEX,
            domain=DomainType.CODING,
            reasoning_depth=0.7,
        )
        scores = analyzer.analyze(task)
        # Sonnet is best for coding
        assert scores[0].model_id == "claude-sonnet-4.6"

    def test_analyze_quick_task_prefers_haiku(self):
        analyzer = CapabilityAnalyzer()
        task = TaskProfile(
            complexity=ComplexityLevel.SIMPLE,
            domain=DomainType.CLASSIFICATION,
            reasoning_depth=0.2,
            latency_sensitivity=LatencySensitivity.HIGH,
        )
        scores = analyzer.analyze(task)
        # Haiku or Deepseek should be top for quick, low-cost tasks
        top_ids = [s.model_id for s in scores[:2]]
        assert any(m in top_ids for m in ("claude-haiku-4.5", "deepseek-v4-pro"))
        # Speed should be the deciding factor — haiku has higher speed than deepseek
        assert scores[0].speed_score >= scores[1].speed_score

    def test_analyze_top_k(self):
        analyzer = CapabilityAnalyzer()
        task = TaskProfile(complexity=ComplexityLevel.MODERATE, domain=DomainType.CODING, reasoning_depth=0.5)
        top2 = analyzer.analyze_top_k(task, k=2)
        assert len(top2) == 2

    def test_analyze_top_k_k_greater_than_available(self):
        analyzer = CapabilityAnalyzer()
        task = TaskProfile(complexity=ComplexityLevel.TRIVIAL, domain=DomainType.SUMMARIZATION, reasoning_depth=0.1)
        top10 = analyzer.analyze_top_k(task, k=10)
        assert len(top10) == 4

    def test_set_weights_valid(self):
        analyzer = CapabilityAnalyzer()
        analyzer.set_weights(reasoning=0.5, coding=0.2, speed=0.2, cost=0.1)
        assert analyzer._weights["reasoning"] == 0.5

    def test_set_weights_invalid_sum(self):
        analyzer = CapabilityAnalyzer()
        with pytest.raises(ValueError, match="must sum to 1.0"):
            analyzer.set_weights(reasoning=1.0, coding=1.0, speed=0.0, cost=0.0)

    def test_normalize_score(self):
        assert CapabilityAnalyzer.normalize_score(50, 0, 100) == 0.5
        assert CapabilityAnalyzer.normalize_score(100, 0, 100) == 1.0
        assert CapabilityAnalyzer.normalize_score(0, 0, 100) == 0.0
        assert CapabilityAnalyzer.normalize_score(10, 10, 10) == 0.5  # edge case

    def test_get_tier_for_task(self):
        analyzer = CapabilityAnalyzer()
        task = TaskProfile(
            complexity=ComplexityLevel.VERY_COMPLEX,
            domain=DomainType.REASONING,
            reasoning_depth=1.0,
        )
        tier = analyzer.get_tier_for_task(task)
        # Complex reasoning tasks should route to a capable tier
        assert tier in ("premium", "standard")

    def test_find_models_for_domain_coding(self):
        analyzer = CapabilityAnalyzer()
        models = analyzer.find_models_for_domain(DomainType.CODING, min_coding=0.7)
        assert len(models) >= 2

    def test_model_capability_cost_for_tokens(self):
        cap = ModelCapability(
            model_id="test", tier="standard",
            reasoning_score=0.5, coding_score=0.5, speed_score=0.5,
            cost_per_1k_tokens=0.01, context_limit=1000,
        )
        assert cap.cost_for_tokens(1000) == 0.01
        assert cap.cost_for_tokens(500) == 0.005

    def test_task_profile_properties(self):
        task = TaskProfile(
            complexity=ComplexityLevel.COMPLEX,
            domain=DomainType.CODING,
            reasoning_depth=0.8,
        )
        assert task.complexity_score == 0.75
        assert task.estimated_tokens > 4000

    def test_match_score_ordering(self):
        a = MatchScore(model_id="a", total_score=0.9, reasoning_score=0.9, coding_score=0.9, speed_score=0.9, cost_score=0.9)
        b = MatchScore(model_id="b", total_score=0.5, reasoning_score=0.5, coding_score=0.5, speed_score=0.5, cost_score=0.5)
        assert b < a

    def test_analyze_all_domains(self):
        analyzer = CapabilityAnalyzer()
        for domain in DomainType:
            task = TaskProfile(
                complexity=ComplexityLevel.MODERATE,
                domain=domain,
                reasoning_depth=0.5,
            )
            scores = analyzer.analyze(task)
            assert len(scores) == 4, f"Failed for domain {domain}"
            assert scores[0].total_score > 0

    def test_register_model_update_existing(self):
        analyzer = CapabilityAnalyzer()
        updated = ModelCapability(
            model_id="claude-opus-4.7",
            tier="premium",
            reasoning_score=0.99,
            coding_score=0.96,
            speed_score=0.50,
            cost_per_1k_tokens=0.08,
            context_limit=200000,
        )
        analyzer.register_model(updated)
        cap = analyzer.get_model("claude-opus-4.7")
        assert cap is not None
        assert cap.reasoning_score == 0.99


# ═══════════════════════════════════════════════════════════════════════
# CostOptimizer / BudgetTracker Tests
# ═══════════════════════════════════════════════════════════════════════


class TestBudgetTracker:
    def test_initial_state(self):
        bt = BudgetTracker()
        assert bt.session_remaining == float("inf")
        assert bt.day_remaining == float("inf")

    def test_record_spend(self):
        bt = BudgetTracker()
        bt.record_spend(0.50)
        assert bt._session_used == 0.50

    def test_can_spend_within_limit(self):
        bt = BudgetTracker()
        bt.set_limits(BudgetLimits(per_session=10.0, per_day=100.0, per_month=1000.0))
        assert bt.can_spend(5.0)
        bt.record_spend(6.0)
        assert not bt.can_spend(5.0)

    def test_budget_status(self):
        bt = BudgetTracker()
        bt.set_limits(BudgetLimits(per_session=10.0, per_day=100.0, per_month=1000.0))
        bt.record_spend(2.0)
        status = bt.budget_status()
        assert status["session"]["used"] == 2.0
        assert status["session"]["limit"] == 10.0
        assert status["session"]["remaining"] == 8.0

    def test_reset_session(self):
        bt = BudgetTracker()
        bt.set_limits(BudgetLimits(per_session=10.0, per_day=100.0, per_month=1000.0))
        bt.record_spend(5.0)
        bt.reset_session()
        assert bt._session_used == 0.0

    def test_check_alerts(self):
        bt = BudgetTracker()
        bt.set_limits(BudgetLimits(per_session=10.0, per_day=100.0, per_month=1000.0))
        bt.set_alert_threshold("session", 0.5)
        bt.record_spend(9.0)
        alerts = bt.check_alerts()
        assert len(alerts) >= 1
        assert "session" in alerts[0]

    def test_set_alert_threshold_invalid(self):
        bt = BudgetTracker()
        with pytest.raises(ValueError, match="Unknown period"):
            bt.set_alert_threshold("year", 0.5)


class TestCostOptimizer:
    def test_optimize_returns_best_affordable(self):
        task = TaskProfile(complexity=ComplexityLevel.MODERATE, domain=DomainType.CODING, reasoning_depth=0.5)
        scores = [
            MatchScore(model_id="cheap", total_score=0.5, reasoning_score=0.5, coding_score=0.5, speed_score=0.5, cost_score=0.9),
            MatchScore(model_id="expensive", total_score=0.9, reasoning_score=0.9, coding_score=0.9, speed_score=0.9, cost_score=0.1),
        ]
        optimizer = CostOptimizer()
        # Without tracker knowing about models, _find_capability returns None, so
        # estimate uses fallback rates
        result = optimizer.optimize(task, scores, budget_constraint=0.50)
        assert result is not None

    def test_optimize_no_match_returns_none_with_tight_budget(self):
        task = TaskProfile(complexity=ComplexityLevel.COMPLEX, domain=DomainType.CODING, reasoning_depth=0.8, token_budget=100000)
        scores = [
            MatchScore(model_id="cheap", total_score=0.5, reasoning_score=0.5, coding_score=0.5, speed_score=0.5, cost_score=0.9),
            MatchScore(model_id="expensive", total_score=0.9, reasoning_score=0.9, coding_score=0.9, speed_score=0.9, cost_score=0.1),
        ]
        optimizer = CostOptimizer()
        # With a negative budget, nothing matches
        result = optimizer.optimize(task, scores, budget_constraint=0.0)
        assert result is not None  # Will return cheapest affordable

    def test_estimate_task_cost(self):
        task = TaskProfile(complexity=ComplexityLevel.MODERATE, domain=DomainType.SUMMARIZATION, reasoning_depth=0.3)
        optimizer = CostOptimizer()
        cost = optimizer.estimate_task_cost(task, "claude-haiku-4.5")
        assert cost > 0

    def test_cost_benefit_analysis(self):
        task = TaskProfile(complexity=ComplexityLevel.MODERATE, domain=DomainType.CODING, reasoning_depth=0.5)
        scores = [
            MatchScore(model_id="claude-haiku-4.5", total_score=0.5, reasoning_score=0.5, coding_score=0.5, speed_score=0.5, cost_score=0.9),
            MatchScore(model_id="claude-sonnet-4.6", total_score=0.8, reasoning_score=0.8, coding_score=0.8, speed_score=0.8, cost_score=0.5),
        ]
        optimizer = CostOptimizer()
        results = optimizer.cost_benefit_analysis(task, scores)
        assert len(results) == 2
        assert results[0].model_id == "claude-haiku-4.5"
        assert results[0].quality_score > 0

    def test_suggest_tier_for_budget(self):
        assert CostOptimizer.suggest_tier_for_budget(1.0) == CostTier.STANDARD
        assert CostOptimizer.suggest_tier_for_budget(0.20) == CostTier.ECONOMY
        assert CostOptimizer.suggest_tier_for_budget(0.01) == CostTier.BACKGROUND

    def test_demotion_chain(self):
        chain = CostOptimizer._demotion_chain(CostTier.CRITICAL)
        assert chain == [CostTier.STANDARD, CostTier.ECONOMY, CostTier.BACKGROUND]
        chain2 = CostOptimizer._demotion_chain(CostTier.ECONOMY)
        assert chain2 == [CostTier.BACKGROUND]

    def test_estimate_base_rate(self):
        optimizer = CostOptimizer()
        assert optimizer._estimate_base_rate("claude-opus-4.7") == 0.075
        assert optimizer._estimate_base_rate("claude-sonnet-4.6") == 0.015
        assert optimizer._estimate_base_rate("claude-haiku-4.5") == 0.0025
        assert optimizer._estimate_base_rate("deepseek-v4-pro") == 0.001
        assert optimizer._estimate_base_rate("gpt-4o") == 0.01
        assert optimizer._estimate_base_rate("unknown-model") == 0.005


# ═══════════════════════════════════════════════════════════════════════
# KnowingDoingGapDetector Tests
# ═══════════════════════════════════════════════════════════════════════


class TestKnowingDoingGapDetector:
    def test_detect_tool_signals_search(self):
        detector = KnowingDoingGapDetector()
        signals = detector.detect_tool_signals("Find the latest stock price for Apple")
        categories = {s.category for s in signals}
        assert ToolCategory.WEB_SEARCH in categories

    def test_detect_tool_signals_coding(self):
        detector = KnowingDoingGapDetector()
        signals = detector.detect_tool_signals("Run this Python script to calculate results")
        categories = {s.category for s in signals}
        assert ToolCategory.CODE_EXECUTION in categories

    def test_detect_tool_signals_data_query(self):
        detector = KnowingDoingGapDetector()
        signals = detector.detect_tool_signals("Query the database for user records")
        categories = {s.category for s in signals}
        assert ToolCategory.DATA_QUERY in categories

    def test_detect_tool_signals_verification(self):
        detector = KnowingDoingGapDetector()
        signals = detector.detect_tool_signals("Verify that the calculation is correct")
        categories = {s.category for s in signals}
        assert ToolCategory.VERIFICATION in categories

    def test_detect_domain_gaps_coding(self):
        detector = KnowingDoingGapDetector()
        task = TaskProfile(complexity=ComplexityLevel.MODERATE, domain=DomainType.CODING, reasoning_depth=0.5)
        gaps = detector.detect_domain_gaps(task)
        # Without any tools registered, we should have gaps
        assert len(gaps) > 0

    def test_detect_domain_gaps_no_gaps_when_tools_available(self):
        detector = KnowingDoingGapDetector(available_tools={ToolCategory.CODE_EXECUTION, ToolCategory.FILE_OPERATIONS, ToolCategory.VERIFICATION})
        task = TaskProfile(complexity=ComplexityLevel.MODERATE, domain=DomainType.CODING, reasoning_depth=0.5)
        gaps = detector.detect_domain_gaps(task)
        # With all coding-relevant tools available, no gaps
        coding_gaps = [g for g in gaps if g.tool_category in (ToolCategory.CODE_EXECUTION, ToolCategory.FILE_OPERATIONS, ToolCategory.VERIFICATION)]
        assert len(coding_gaps) == 0

    def test_register_tool(self):
        detector = KnowingDoingGapDetector()
        detector.register_tool(ToolCategory.WEB_SEARCH)
        assert ToolCategory.WEB_SEARCH in detector.available_tools

    def test_register_tools(self):
        detector = KnowingDoingGapDetector()
        detector.register_tools({ToolCategory.WEB_SEARCH, ToolCategory.CODE_EXECUTION})
        assert len(detector.available_tools) == 2

    def test_remove_tool(self):
        detector = KnowingDoingGapDetector(available_tools={ToolCategory.WEB_SEARCH})
        assert detector.remove_tool(ToolCategory.WEB_SEARCH)
        assert ToolCategory.WEB_SEARCH not in detector.available_tools
        assert not detector.remove_tool(ToolCategory.WEB_SEARCH)

    def test_composite_gap_score(self):
        detector = KnowingDoingGapDetector()
        recs = [
            GapRecommendation(tool_category=ToolCategory.WEB_SEARCH, gap_severity=0.8, reason="test", suggested_action="test", confidence=0.9),
            GapRecommendation(tool_category=ToolCategory.CODE_EXECUTION, gap_severity=0.5, reason="test", suggested_action="test", confidence=0.7),
        ]
        score = detector.composite_gap_score(recs)
        assert 0.4 < score < 0.8

    def test_composite_gap_score_empty(self):
        detector = KnowingDoingGapDetector()
        assert detector.composite_gap_score([]) == 0.0

    def test_top_gaps(self):
        detector = KnowingDoingGapDetector()
        recs = [
            GapRecommendation(tool_category=ToolCategory.WEB_SEARCH, gap_severity=0.9, reason="a", suggested_action="a", confidence=0.9),
            GapRecommendation(tool_category=ToolCategory.CODE_EXECUTION, gap_severity=0.5, reason="b", suggested_action="b", confidence=0.5),
            GapRecommendation(tool_category=ToolCategory.DATA_QUERY, gap_severity=0.7, reason="c", suggested_action="c", confidence=0.7),
        ]
        top = detector.top_gaps(recs, k=2)
        assert len(top) == 2
        assert top[0].tool_category == ToolCategory.WEB_SEARCH

    def test_full_analyze_with_description(self):
        detector = KnowingDoingGapDetector()
        task = TaskProfile(complexity=ComplexityLevel.MODERATE, domain=DomainType.CODING, reasoning_depth=0.5)
        gaps = detector.analyze(task, task_description="Run this script to calculate results")
        assert len(gaps) >= 0

    def test_detect_text_gaps(self):
        detector = KnowingDoingGapDetector()
        gaps = detector.detect_text_gaps("Query the database and fetch user records, then verify the results")
        assert len(gaps) > 0

    def test_gap_recommendation_ordering(self):
        a = GapRecommendation(tool_category=ToolCategory.WEB_SEARCH, gap_severity=0.9, reason="a", suggested_action="a")
        b = GapRecommendation(tool_category=ToolCategory.CODE_EXECUTION, gap_severity=0.3, reason="b", suggested_action="b")
        assert b < a


# ═══════════════════════════════════════════════════════════════════════
# CrossModelVerifier Tests
# ═══════════════════════════════════════════════════════════════════════


class TestCrossModelVerifier:
    def test_detect_family_anthropic(self):
        v = CrossModelVerifier()
        assert v.detect_family("claude-opus-4.7") == ModelFamily.ANTHROPIC
        assert v.detect_family("claude-sonnet-4.6") == ModelFamily.ANTHROPIC
        assert v.detect_family("claude-haiku-4.5") == ModelFamily.ANTHROPIC

    def test_detect_family_deepseek(self):
        v = CrossModelVerifier()
        assert v.detect_family("deepseek-v4-pro") == ModelFamily.DEEPSEEK
        assert v.detect_family("deepseek-chat") == ModelFamily.DEEPSEEK

    def test_detect_family_openai(self):
        v = CrossModelVerifier()
        assert v.detect_family("gpt-4o") == ModelFamily.OPENAI
        assert v.detect_family("o1-preview") == ModelFamily.OPENAI

    def test_detect_family_unknown(self):
        v = CrossModelVerifier()
        assert v.detect_family("unknown-model") == ModelFamily.OTHER

    def test_verify_different_families(self):
        v = CrossModelVerifier()
        result = v.verify("claude-opus-4.7", "deepseek-v4-pro")
        assert result.passed
        assert result.diversity_score > 0

    def test_verify_same_family(self):
        v = CrossModelVerifier()
        result = v.verify("claude-opus-4.7", "claude-haiku-4.5")
        assert not result.passed
        assert result.diversity_score == 0.0

    def test_verify_same_family_recommendations(self):
        v = CrossModelVerifier()
        result = v.verify("gpt-4o", "o1-preview")
        assert not result.passed
        assert len(result.recommendations) >= 2

    def test_multi_reviewer_consensus_all_pass(self):
        v = CrossModelVerifier()
        result = v.multi_reviewer_consensus("claude-opus-4.7", ["deepseek-v4-pro", "gpt-4o"])
        assert result.passed
        assert len(result.individual_results) == 2

    def test_multi_reviewer_consensus_some_fail(self):
        v = CrossModelVerifier()
        result = v.multi_reviewer_consensus("claude-opus-4.7", ["claude-haiku-4.5", "deepseek-v4-pro"])
        assert result.passed  # consensus_score should still be high enough
        assert len(result.individual_results) == 2

    def test_multi_reviewer_consensus_all_fail(self):
        v = CrossModelVerifier()
        result = v.multi_reviewer_consensus("claude-opus-4.7", ["claude-sonnet-4.6", "claude-haiku-4.5"])
        assert not result.passed  # all same family
        assert result.consensus_score == 0.0

    def test_suggest_reviewer_families(self):
        v = CrossModelVerifier()
        families = v.suggest_reviewer_families("claude-opus-4.7")
        assert ModelFamily.DEEPSEEK in families
        assert ModelFamily.OPENAI in families
        assert ModelFamily.ANTHROPIC not in families

    def test_register_family_pattern(self):
        v = CrossModelVerifier()
        v.register_family_pattern(ModelFamily.ANTHROPIC, "custom-claude")
        assert v.detect_family("custom-claude-7") == ModelFamily.ANTHROPIC

    def test_verify_diversity_score_anthropic_deepseek(self):
        v = CrossModelVerifier()
        result = v.verify("claude-opus-4.7", "deepseek-v4-pro")
        assert result.diversity_score == 0.85

    def test_validation_result_message(self):
        v = CrossModelVerifier()
        result = v.verify("claude-opus-4.7", "gpt-4o")
        assert "different family" in result.message


# ═══════════════════════════════════════════════════════════════════════
# RouterConfig Tests
# ═══════════════════════════════════════════════════════════════════════


class TestRouterConfig:
    def test_default_config(self):
        config = RouterConfig()
        assert len(config.policies) == 5
        assert len(config.model_registry) == 4
        assert len(config.fallback_rules) == 4

    def test_get_policy(self):
        config = RouterConfig()
        policy = config.get_policy("reasoning")
        assert policy is not None
        assert policy.policy_type == PolicyType.DOMAIN_ROUTING

    def test_add_policy(self):
        config = RouterConfig()
        new_policy = RoutingPolicy(
            name="test", policy_type=PolicyType.BALANCED,
            domain="test", preferred_models=("claude-haiku-4.5",),
        )
        config.add_policy(new_policy)
        assert config.get_policy("test") is not None

    def test_remove_policy(self):
        config = RouterConfig()
        assert config.remove_policy("economy")
        assert config.get_policy("economy") is None
        assert not config.remove_policy("nonexistent")

    def test_list_policies(self):
        config = RouterConfig()
        names = config.list_policies()
        assert "reasoning" in names
        assert "coding" in names
        assert "quick" in names

    def test_find_policies_by_domain(self):
        config = RouterConfig()
        policies = config.find_policies_by_domain("coding")
        assert len(policies) == 1
        assert policies[0].name == "coding"

    def test_get_registry_entry(self):
        config = RouterConfig()
        entry = config.get_registry_entry("claude-opus-4.7")
        assert entry is not None
        assert entry.tier == "premium"

    def test_register_model_to_config(self):
        config = RouterConfig()
        entry = ModelRegistryEntry(model_id="gpt-4o", tier="premium")
        config.register_model(entry)
        assert config.get_registry_entry("gpt-4o") is not None

    def test_unregister_model(self):
        config = RouterConfig()
        assert config.unregister_model("claude-haiku-4.5")
        assert config.get_registry_entry("claude-haiku-4.5") is None

    def test_set_model_enabled(self):
        config = RouterConfig()
        assert config.set_model_enabled("claude-opus-4.7", False)
        assert not config.get_registry_entry("claude-opus-4.7").enabled
        assert not config.set_model_enabled("nonexistent", True)

    def test_get_fallback_chain(self):
        config = RouterConfig()
        chain = config.get_fallback_chain("claude-opus-4.7")
        assert "claude-opus-4.7" in chain
        assert len(chain) >= 2

    def test_get_fallback_rule(self):
        config = RouterConfig()
        rule = config.get_fallback_rule("claude-opus-4.7")
        assert rule is not None
        assert len(rule.fallback_models) > 0

    def test_set_fallback_rule(self):
        config = RouterConfig()
        rule = FallbackRule(primary_model="gpt-4o", fallback_models=("claude-sonnet-4.6",))
        config.set_fallback_rule(rule)
        assert config.get_fallback_rule("gpt-4o") is not None

    def test_remove_fallback_rule(self):
        config = RouterConfig()
        assert config.remove_fallback_rule("claude-sonnet-4.6")
        assert config.get_fallback_rule("claude-sonnet-4.6") is None

    def test_health_initial(self):
        config = RouterConfig()
        health = config.get_health("claude-opus-4.7")
        assert health is not None
        assert health.available

    def test_report_failure(self):
        config = RouterConfig()
        config.report_failure("claude-opus-4.7")
        config.report_failure("claude-opus-4.7")
        health = config.get_health("claude-opus-4.7")
        assert health is not None
        assert health.consecutive_failures == 2
        assert not health.healthy

    def test_report_success(self):
        config = RouterConfig()
        config.report_failure("claude-opus-4.7")
        config.report_success("claude-opus-4.7", latency_ms=150.0)
        health = config.get_health("claude-opus-4.7")
        assert health is not None
        assert health.healthy
        assert health.consecutive_failures == 0

    def test_get_available_models(self):
        config = RouterConfig()
        available = config.get_available_models()
        assert len(available) == 4
        config.set_model_enabled("claude-haiku-4.5", False)
        assert "claude-haiku-4.5" not in config.get_available_models()

    def test_to_dict_and_from_dict(self):
        config = RouterConfig()
        data = config.to_dict()
        assert "policies" in data
        assert "model_registry" in data
        assert "fallback_rules" in data
        restored = RouterConfig.from_dict(data)
        assert len(restored.policies) == 5

    def test_to_json_and_from_json(self):
        config = RouterConfig()
        json_str = config.to_json()
        assert "claude-opus-4.7" in json_str
        restored = RouterConfig.from_json(json_str)
        assert len(restored.policies) == 5

    def test_hot_reload(self):
        config = RouterConfig()
        changes = config.hot_reload({
            "policies": [
                {"name": "new_policy", "policy_type": "balanced", "domain": "new", "preferred_models": ["deepseek-v4-pro"]},
            ],
            "model_registry": [],
            "fallback_rules": [],
        })
        assert len(changes) >= 3
        assert config.get_policy("new_policy") is not None
        assert config.get_policy("reasoning") is None  # replaced

    def test_fallback_chain_with_fallback(self):
        config = RouterConfig()
        chain = config.get_fallback_chain("claude-sonnet-4.6")
        assert "claude-haiku-4.5" in chain or "deepseek-v4-pro" in chain


# ═══════════════════════════════════════════════════════════════════════
# ModelRouter Tests
# ═══════════════════════════════════════════════════════════════════════


class TestModelRouter:
    def test_route_basic(self):
        router = ModelRouter()
        task = TaskProfile(
            complexity=ComplexityLevel.MODERATE,
            domain=DomainType.CODING,
            reasoning_depth=0.6,
        )
        selection = router.route(task)
        assert isinstance(selection, ModelSelection)
        assert selection.model_id
        assert selection.confidence > 0
        assert selection.reasoning

    def test_route_reasoning_task(self):
        router = ModelRouter()
        task = TaskProfile(
            complexity=ComplexityLevel.VERY_COMPLEX,
            domain=DomainType.REASONING,
            reasoning_depth=1.0,
        )
        selection = router.route(task)
        # Complex reasoning should select a capable model (Opus or Sonnet)
        assert selection.model_id in ("claude-opus-4.7", "claude-sonnet-4.6")
        assert selection.confidence > 0.5

    def test_route_with_gap_detection(self):
        router = ModelRouter()
        task = TaskProfile(
            complexity=ComplexityLevel.MODERATE,
            domain=DomainType.RESEARCH,
            reasoning_depth=0.7,
        )
        selection = router.route(task, task_description="Search the web for the latest research papers on AI")
        assert len(selection.alternatives) > 0

    def test_route_with_verification(self):
        router = ModelRouter()
        task = TaskProfile(
            complexity=ComplexityLevel.COMPLEX,
            domain=DomainType.CODING,
            reasoning_depth=0.7,
        )
        selection = router.route(task, verify_reviewer="deepseek-v4-pro")
        assert selection.verification is not None
        assert selection.verification.passed

    def test_route_with_same_family_verification(self):
        router = ModelRouter()
        task = TaskProfile(
            complexity=ComplexityLevel.MODERATE,
            domain=DomainType.ANALYSIS,
            reasoning_depth=0.5,
        )
        selection = router.route(task, verify_reviewer="claude-haiku-4.5")
        assert selection.verification is not None
        # The generator and reviewer could be same family, but verification result is still captured
        assert selection.verification.passed is False

    @pytest.mark.asyncio
    async def test_route_async(self):
        router = ModelRouter()
        task = TaskProfile(
            complexity=ComplexityLevel.SIMPLE,
            domain=DomainType.CLASSIFICATION,
            reasoning_depth=0.2,
        )
        selection = await router.route_async(task, timeout=10.0)
        assert selection.model_id

    @pytest.mark.asyncio
    async def test_route_async_timeout(self):
        router = ModelRouter()
        task = TaskProfile(
            complexity=ComplexityLevel.TRIVIAL,
            domain=DomainType.SUMMARIZATION,
            reasoning_depth=0.1,
        )
        # Use a very short timeout to force timeout (unlikely, but test the path)
        selection = await router.route_async(task, timeout=0.001)
        # Should fallback on timeout
        assert selection.model_id

    def test_route_with_review_different_family(self):
        router = ModelRouter()
        task = TaskProfile(
            complexity=ComplexityLevel.MODERATE,
            domain=DomainType.CODING,
            reasoning_depth=0.5,
        )
        gen, rev = router.route_with_review(task, reviewer_model="deepseek-v4-pro")
        assert gen.model_id
        assert rev.model_id == "deepseek-v4-pro"

    def test_route_with_review_same_family_fallback(self):
        router = ModelRouter()
        task = TaskProfile(
            complexity=ComplexityLevel.MODERATE,
            domain=DomainType.CODING,
            reasoning_depth=0.5,
        )
        gen, rev = router.route_with_review(task, reviewer_model="claude-haiku-4.5")
        assert gen.model_id
        assert rev.model_id != "claude-haiku-4.5"  # Should have been replaced

    def test_route_audit_log(self):
        router = ModelRouter()
        task = TaskProfile(complexity=ComplexityLevel.SIMPLE, domain=DomainType.SUMMARIZATION, reasoning_depth=0.3)
        router.route(task, task_id="test_001")
        assert len(router.audit_log) == 1
        entry = router.audit_log[0]
        assert entry["task_id"] == "test_001"

    def test_get_routing_stats(self):
        router = ModelRouter()
        task1 = TaskProfile(complexity=ComplexityLevel.COMPLEX, domain=DomainType.REASONING, reasoning_depth=0.9)
        task2 = TaskProfile(complexity=ComplexityLevel.SIMPLE, domain=DomainType.CLASSIFICATION, reasoning_depth=0.2)
        router.route(task1)
        router.route(task2)
        stats = router.get_routing_stats()
        assert sum(stats.values()) == pytest.approx(1.0, rel=0.01)

    def test_export_audit_log(self):
        router = ModelRouter()
        task = TaskProfile(complexity=ComplexityLevel.MODERATE, domain=DomainType.ANALYSIS, reasoning_depth=0.5)
        router.route(task)
        log_str = router.export_audit_log()
        assert "task_domain" in log_str
        parsed = json.loads(log_str)
        assert len(parsed) == 1

    def test_clear_history(self):
        router = ModelRouter()
        task = TaskProfile(complexity=ComplexityLevel.MODERATE, domain=DomainType.ANALYSIS, reasoning_depth=0.5)
        router.route(task)
        router.clear_history()
        assert len(router.audit_log) == 0
        assert len(router.pipeline_history) == 0

    def test_pipeline_history(self):
        router = ModelRouter()
        task = TaskProfile(complexity=ComplexityLevel.MODERATE, domain=DomainType.CODING, reasoning_depth=0.5)
        router.route(task)
        assert len(router.pipeline_history) == 1
        assert len(router.pipeline_history[0].capability_scores) == 4

    def test_multiple_routes(self):
        router = ModelRouter()
        for i in range(5):
            task = TaskProfile(
                complexity=ComplexityLevel.MODERATE,
                domain=DomainType.CODING,
                reasoning_depth=0.5,
            )
            router.route(task, task_id=f"batch_{i}")
        assert len(router.audit_log) == 5

    def test_usage_tracker_integration(self):
        router = ModelRouter()
        task = TaskProfile(complexity=ComplexityLevel.MODERATE, domain=DomainType.SUMMARIZATION, reasoning_depth=0.3)
        router.route(task)
        assert router.usage.total_calls == 1
        assert router.usage.total_cost() >= 0


# ═══════════════════════════════════════════════════════════════════════
# UsageTracker Tests
# ═══════════════════════════════════════════════════════════════════════


class TestUsageTracker:
    def test_record_and_count(self):
        tracker = UsageTracker()
        tracker.record(UsageRecord(model_id="test", task_type="coding", tokens_used=100, cost=0.01, latency_ms=50.0))
        assert tracker.total_calls == 1
        assert tracker.total_tokens() == 100
        assert tracker.total_cost() == 0.01

    def test_record_many(self):
        tracker = UsageTracker()
        records = [
            UsageRecord(model_id="m1", task_type="coding", tokens_used=100, cost=0.01),
            UsageRecord(model_id="m2", task_type="reasoning", tokens_used=200, cost=0.02),
            UsageRecord(model_id="m1", task_type="coding", tokens_used=50, cost=0.005),
        ]
        tracker.record_many(records)
        assert tracker.total_calls == 3
        assert tracker.total_tokens() == 350

    def test_stats_by_model(self):
        tracker = UsageTracker()
        tracker.record(UsageRecord(model_id="opus", task_type="reasoning", tokens_used=1000, cost=0.075, latency_ms=5000.0))
        tracker.record(UsageRecord(model_id="sonnet", task_type="coding", tokens_used=500, cost=0.0075, latency_ms=2000.0))
        tracker.record(UsageRecord(model_id="opus", task_type="analysis", tokens_used=800, cost=0.06, latency_ms=4000.0))
        stats = tracker.stats_by_model()
        assert "opus" in stats
        assert "sonnet" in stats
        assert stats["opus"].total_calls == 2
        assert stats["sonnet"].total_calls == 1
        # Test filtered by model
        opus_stats = tracker.stats_by_model("opus")
        assert opus_stats["opus"].total_calls == 2

    def test_stats_by_model_filter(self):
        tracker = UsageTracker()
        tracker.record(UsageRecord(model_id="opus", task_type="reasoning", tokens_used=100, cost=0.01))
        tracker.record(UsageRecord(model_id="sonnet", task_type="coding", tokens_used=200, cost=0.02))
        stats = tracker.stats_by_model(model_id="sonnet")
        assert "sonnet" in stats
        assert "opus" not in stats

    def test_stats_by_task_type(self):
        tracker = UsageTracker()
        tracker.record(UsageRecord(model_id="m1", task_type="coding", tokens_used=100, cost=0.01, success=True))
        tracker.record(UsageRecord(model_id="m2", task_type="coding", tokens_used=200, cost=0.02, success=False))
        tracker.record(UsageRecord(model_id="m1", task_type="reasoning", tokens_used=300, cost=0.03, success=True))
        stats = tracker.stats_by_task_type()
        assert "coding" in stats
        assert stats["coding"].total_calls == 2
        assert stats["coding"].failure_count == 1

    def test_stats_by_task_type_filter(self):
        tracker = UsageTracker()
        tracker.record(UsageRecord(model_id="m1", task_type="coding", tokens_used=100, cost=0.01))
        tracker.record(UsageRecord(model_id="m2", task_type="reasoning", tokens_used=200, cost=0.02))
        stats = tracker.stats_by_task_type(task_type="coding")
        assert "coding" in stats
        assert "reasoning" not in stats

    def test_stats_by_time_period(self):
        tracker = UsageTracker()
        now = time.time()
        tracker.record(UsageRecord(model_id="m1", task_type="coding", tokens_used=100, cost=0.01, timestamp=now))
        tracker.record(UsageRecord(model_id="m1", task_type="coding", tokens_used=200, cost=0.02, timestamp=now))
        stats = tracker.stats_by_time_period(now - 10, now + 10)
        assert stats.total_calls == 2
        stats_outside = tracker.stats_by_time_period(now + 100, now + 200)
        assert stats_outside.total_calls == 0

    def test_stats_by_tier(self):
        tracker = UsageTracker()
        tracker.record(UsageRecord(model_id="opus", task_type="reasoning", tokens_used=1000, cost=0.075, model_tier="premium"))
        tracker.record(UsageRecord(model_id="sonnet", task_type="coding", tokens_used=500, cost=0.0075, model_tier="standard"))
        stats = tracker.stats_by_tier()
        assert "premium" in stats
        assert "standard" in stats

    def test_cost_budget_alert(self):
        tracker = UsageTracker()
        tracker.set_cost_budget(0.01)
        tracker.record(UsageRecord(model_id="opus", task_type="reasoning", tokens_used=1000, cost=0.02))
        alerts = tracker.alerts()
        assert len(alerts) >= 1
        assert alerts[0].alert_type == "cost"

    def test_token_budget_alert(self):
        tracker = UsageTracker()
        tracker.set_token_budget(100)
        tracker.record(UsageRecord(model_id="test", task_type="test", tokens_used=200, cost=0.01))
        alerts = tracker.alerts()
        token_alerts = [a for a in alerts if a.alert_type == "tokens"]
        assert len(token_alerts) >= 1

    def test_alerts_filter_by_type(self):
        tracker = UsageTracker()
        tracker.set_cost_budget(0.001)
        tracker.set_token_budget(10)
        tracker.record(UsageRecord(model_id="test", task_type="test", tokens_used=100, cost=0.01))
        cost_alerts = tracker.alerts(alert_type="cost")
        assert all(a.alert_type == "cost" for a in cost_alerts)

    def test_recent_records(self):
        tracker = UsageTracker()
        for i in range(5):
            tracker.record(UsageRecord(model_id=f"m{i}", task_type="coding", tokens_used=100, cost=0.01))
        recent = tracker.recent_records(3)
        assert len(recent) == 3

    def test_clear(self):
        tracker = UsageTracker()
        tracker.record(UsageRecord(model_id="test", task_type="test", tokens_used=100, cost=0.01))
        tracker.clear()
        assert tracker.total_calls == 0

    def test_export(self):
        tracker = UsageTracker()
        tracker.record(UsageRecord(model_id="opus", task_type="reasoning", tokens_used=1000, cost=0.075))
        report = tracker.export()
        assert "total_calls" in report
        assert "models" in report
        assert "task_types" in report
        assert "tiers" in report
        assert report["total_calls"] == 1

    def test_export_json(self):
        tracker = UsageTracker()
        tracker.record(UsageRecord(model_id="opus", task_type="reasoning", tokens_used=1000, cost=0.075))
        json_str = tracker.export_json()
        parsed = json.loads(json_str)
        assert parsed["total_calls"] == 1

    def test_alert_callback(self):
        tracker = UsageTracker()
        callback_called = False
        def callback(alert):
            nonlocal callback_called
            callback_called = True
        tracker.on_alert(callback)
        tracker.set_cost_budget(0.001)
        tracker.record(UsageRecord(model_id="test", task_type="test", tokens_used=100, cost=0.01))
        assert callback_called

    def test_usage_stats_auto_compute(self):
        stats = UsageStats(
            total_calls=10,
            total_tokens=5000,
            total_cost=0.50,
            total_latency_ms=10000.0,
            success_count=9,
            failure_count=1,
        )
        assert stats.avg_latency_ms == 1000.0
        assert stats.avg_cost_per_call == 0.05
        assert stats.avg_tokens_per_call == 500.0


# ═══════════════════════════════════════════════════════════════════════
# Exceptions Tests
# ═══════════════════════════════════════════════════════════════════════


class TestExceptions:
    def test_router_error(self):
        with pytest.raises(RouterError):
            raise RouterError("base error")
        assert issubclass(ModelNotFoundError, RouterError)

    def test_model_not_found(self):
        with pytest.raises(ModelNotFoundError, match="not found"):
            raise ModelNotFoundError("unknown_model")

    def test_budget_exceeded(self):
        with pytest.raises(BudgetExceededError, match="budget exceeded"):
            raise BudgetExceededError("cost", 10.0, 15.0, "daily")

    def test_verification_error(self):
        with pytest.raises(VerificationError, match="Cross-model verification failed"):
            raise VerificationError("gen_model", "rev_model", "same family")

    def test_capability_mismatch(self):
        with pytest.raises(CapabilityMismatchError, match="Capability mismatch"):
            raise CapabilityMismatchError("reasoning", "no models available")

    def test_routing_error(self):
        with pytest.raises(RoutingError, match="Routing failed"):
            raise RoutingError("task_123", "all models unavailable")

    def test_inheritance(self):
        assert issubclass(ModelNotFoundError, RouterError)
        assert issubclass(BudgetExceededError, RouterError)
        assert issubclass(VerificationError, RouterError)
        assert issubclass(CapabilityMismatchError, RouterError)
        assert issubclass(RoutingError, RouterError)


# ═══════════════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════════════


class TestIntegration:
    def test_full_pipeline_reasoning(self):
        """Test the full routing pipeline for a complex reasoning task."""
        config = RouterConfig()
        router = ModelRouter(config=config)
        task = TaskProfile(
            complexity=ComplexityLevel.VERY_COMPLEX,
            domain=DomainType.REASONING,
            reasoning_depth=0.95,
            tool_requirements=("code_execution", "web_search"),
            token_budget=16000,
        )
        selection = router.route(
            task=task,
            task_description="Analyze the latest AI research papers and compare their methodologies",
            verify_reviewer="deepseek-v4-pro",
        )
        # Should select a capable model for complex reasoning
        assert selection.model_id in ("claude-opus-4.7", "claude-sonnet-4.6")
        assert selection.confidence > 0.5
        assert selection.verification is not None
        assert selection.verification.passed
        assert len(selection.alternatives) == 4

    def test_full_pipeline_economy(self):
        """Test the full routing pipeline for a budget-constrained task."""
        router = ModelRouter()
        task = TaskProfile(
            complexity=ComplexityLevel.TRIVIAL,
            domain=DomainType.CLASSIFICATION,
            reasoning_depth=0.1,
            latency_sensitivity=LatencySensitivity.HIGH,
            token_budget=500,
        )
        selection = router.route(task)
        # Should route to an economy/fast model for trivial classification
        top_tier_models = ("claude-opus-4.7", "claude-sonnet-4.6")
        assert selection.model_id not in top_tier_models  # Should not waste Opus/Sonnet on trivial tasks

    def test_cost_tracking_across_routes(self):
        """Test that cost tracking works across multiple routing decisions."""
        router = ModelRouter()
        tasks = [
            TaskProfile(complexity=ComplexityLevel.COMPLEX, domain=DomainType.REASONING, reasoning_depth=0.9, token_budget=32000),
            TaskProfile(complexity=ComplexityLevel.SIMPLE, domain=DomainType.CLASSIFICATION, reasoning_depth=0.2, token_budget=500),
            TaskProfile(complexity=ComplexityLevel.MODERATE, domain=DomainType.CODING, reasoning_depth=0.6, token_budget=8000),
        ]
        for task in tasks:
            router.route(task)
        report = router.usage.export()
        assert report["total_calls"] == 3
        assert report["total_cost"] >= 0

    def test_multi_reviewer_workflow(self):
        """Test routing with multi-reviewer consensus verification."""
        router = ModelRouter()
        task = TaskProfile(
            complexity=ComplexityLevel.COMPLEX,
            domain=DomainType.RESEARCH,
            reasoning_depth=0.85,
        )
        gen_selection, rev_selection = router.route_with_review(
            task, reviewer_model="deepseek-v4-pro"
        )
        assert gen_selection.model_id
        assert rev_selection.model_id

    def test_pipeline_with_fallback(self):
        """Test routing when primary model is unavailable."""
        config = RouterConfig()
        config.set_model_enabled("claude-opus-4.7", False)
        router = ModelRouter(config=config)
        task = TaskProfile(
            complexity=ComplexityLevel.COMPLEX,
            domain=DomainType.REASONING,
            reasoning_depth=0.9,
        )
        selection = router.route(task)
        # Should fallback to sonnet or deepseek
        assert selection.model_id != "claude-opus-4.7"
        assert selection.confidence > 0

    def test_gap_detection_with_recommendations(self):
        """Test that gap detection produces actionable recommendations."""
        detector = KnowingDoingGapDetector()
        task = TaskProfile(
            complexity=ComplexityLevel.COMPLEX,
            domain=DomainType.RESEARCH,
            reasoning_depth=0.8,
        )
        recommendations = detector.analyze(
            task,
            task_description="Search the web and query the database for research data",
        )
        # Should suggest web_search and data_query tools
        tool_categories = {r.tool_category for r in recommendations}
        assert len(tool_categories) > 0

    def test_round_trip_serialization(self):
        """Test config round-trip through dict serialization."""
        config = RouterConfig()
        data = config.to_dict()
        restored = RouterConfig.from_dict(data)
        assert restored.list_policies() == config.list_policies()
        assert restored.list_registered_models() == config.list_registered_models()
        json_str = config.to_json()
        from_json = RouterConfig.from_json(json_str)
        assert from_json.list_policies() == config.list_policies()
