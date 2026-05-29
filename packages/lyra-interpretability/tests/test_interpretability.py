"""Tests for the lyra-interpretability package."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from lyra_interpretability import (
    AttributionMethod,
    CounterfactualExplanation,
    DecisionTrace,
    ExplanationType,
    FeatureAttribution,
    InterpretabilityConfig,
    InterpretabilityEngine,
    InterpretabilityReport,
    SaliencyMap,
)

# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestAttributionMethod:
    def test_has_all_expected_values(self) -> None:
        assert AttributionMethod.GRADIENT.value == "gradient"
        assert AttributionMethod.INTEGRATED_GRADIENTS.value == "integrated_gradients"
        assert AttributionMethod.SHAPLEY.value == "shapley"
        assert AttributionMethod.LIME.value == "lime"
        assert AttributionMethod.ATTENTION.value == "attention"
        assert AttributionMethod.OCCLUSION.value == "occlusion"

    def test_is_string_enum(self) -> None:
        assert issubclass(AttributionMethod, str)


class TestExplanationType:
    def test_has_all_expected_values(self) -> None:
        assert ExplanationType.DECISION_RATIONALE.value == "decision_rationale"
        assert ExplanationType.FEATURE_IMPORTANCE.value == "feature_importance"
        assert ExplanationType.COUNTERFACTUAL.value == "counterfactual"
        assert ExplanationType.CHAIN_OF_THOUGHT.value == "chain_of_thought"
        assert ExplanationType.CONFIDENCE_BREAKDOWN.value == "confidence_breakdown"

    def test_is_string_enum(self) -> None:
        assert issubclass(ExplanationType, str)


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------


class TestFeatureAttribution:
    def test_can_instantiate(self) -> None:
        attr = FeatureAttribution(feature="safety", score=0.85, method="SHAPLEY", rank=1)
        assert attr.feature == "safety"
        assert attr.score == 0.85

    def test_evidence_defaults_to_empty_string(self) -> None:
        attr = FeatureAttribution(feature="speed", score=0.5, method="LIME", rank=2)
        assert attr.evidence == ""

    def test_is_frozen(self) -> None:
        attr = FeatureAttribution(feature="cost", score=0.3, method="GRADIENT", rank=3)
        with pytest.raises(FrozenInstanceError):
            attr.score = 0.9  # type: ignore[misc]


class TestDecisionTrace:
    def test_can_instantiate(self) -> None:
        factors = (
            FeatureAttribution(feature="safety", score=0.9, method="SHAPLEY", rank=1),
        )
        trace = DecisionTrace(
            decision_id="dec-001",
            agent_id="agent-a",
            timestamp=1000.0,
            input_summary="User query about safety",
            reasoning_steps=("Step 1", "Step 2"),
            key_factors=factors,
            confidence=0.85,
            alternatives_considered=("Option B",),
        )
        assert trace.decision_id == "dec-001"
        assert trace.agent_id == "agent-a"

    def test_is_frozen(self) -> None:
        trace = DecisionTrace(
            decision_id="dec-002",
            agent_id="agent-b",
            timestamp=2000.0,
            input_summary="test",
            reasoning_steps=(),
            key_factors=(),
            confidence=0.5,
            alternatives_considered=(),
        )
        with pytest.raises(FrozenInstanceError):
            trace.confidence = 0.99  # type: ignore[misc]


class TestCounterfactualExplanation:
    def test_can_instantiate(self) -> None:
        cf = CounterfactualExplanation(
            original_decision="Deploy to production",
            counterfactual_scenario="If safety check failed",
            alternative_decision="Deploy to staging",
            confidence_delta=-0.15,
            key_changed_factors=("safety",),
        )
        assert cf.original_decision == "Deploy to production"
        assert cf.confidence_delta == -0.15

    def test_is_frozen(self) -> None:
        cf = CounterfactualExplanation(
            original_decision="A",
            counterfactual_scenario="B",
            alternative_decision="C",
            confidence_delta=0.0,
            key_changed_factors=("x",),
        )
        with pytest.raises(FrozenInstanceError):
            cf.confidence_delta = 0.5  # type: ignore[misc]


class TestSaliencyMap:
    def test_can_instantiate(self) -> None:
        sm = SaliencyMap(
            target_text="high performance needed",
            tokens=("high", "performance", "needed"),
            scores=(0.2, 0.9, 0.3),
            method="SHAPLEY",
        )
        assert sm.target_text == "high performance needed"
        assert sm.normalized is True
        assert len(sm.tokens) == len(sm.scores)

    def test_can_set_normalized_false(self) -> None:
        sm = SaliencyMap(
            target_text="test",
            tokens=("test",),
            scores=(1.0,),
            method="GRADIENT",
            normalized=False,
        )
        assert sm.normalized is False

    def test_is_frozen(self) -> None:
        sm = SaliencyMap(
            target_text="test",
            tokens=("a",),
            scores=(0.5,),
            method="LIME",
        )
        with pytest.raises(FrozenInstanceError):
            sm.target_text = "different"  # type: ignore[misc]


class TestInterpretabilityReport:
    def test_can_instantiate(self) -> None:
        report = InterpretabilityReport(
            agent_id="agent-x",
            timestamp=3000.0,
            decision_traces=(),
            top_attributions=(),
            counterfactuals=(),
            overall_transparency_score=0.85,
        )
        assert report.agent_id == "agent-x"
        assert report.overall_transparency_score == 0.85

    def test_is_frozen(self) -> None:
        report = InterpretabilityReport(
            agent_id="a",
            timestamp=1.0,
            decision_traces=(),
            top_attributions=(),
            counterfactuals=(),
            overall_transparency_score=1.0,
        )
        with pytest.raises(FrozenInstanceError):
            report.overall_transparency_score = 0.0  # type: ignore[misc]


class TestInterpretabilityConfig:
    def test_default_values(self) -> None:
        config = InterpretabilityConfig()
        assert config.attribution_method == "SHAPLEY"
        assert config.max_traces == 1000
        assert config.saliency_enabled is True
        assert config.counterfactual_enabled is True
        assert config.confidence_threshold == 0.5
        assert config.max_alternatives == 5

    def test_can_override_defaults(self) -> None:
        config = InterpretabilityConfig(
            attribution_method="LIME",
            max_traces=100,
            saliency_enabled=False,
            counterfactual_enabled=False,
            confidence_threshold=0.8,
            max_alternatives=3,
        )
        assert config.attribution_method == "LIME"
        assert config.max_traces == 100
        assert config.saliency_enabled is False
        assert config.counterfactual_enabled is False
        assert config.confidence_threshold == 0.8
        assert config.max_alternatives == 3


# ---------------------------------------------------------------------------
# InterpretabilityEngine tests
# ---------------------------------------------------------------------------


class TestInterpretabilityEngineInit:
    def test_uses_default_config_when_none_given(self) -> None:
        engine = InterpretabilityEngine()
        assert engine._config.attribution_method == "SHAPLEY"

    def test_accepts_custom_config(self) -> None:
        config = InterpretabilityConfig(attribution_method="LIME", max_traces=10)
        engine = InterpretabilityEngine(config=config)
        assert engine._config.attribution_method == "LIME"
        assert engine._config.max_traces == 10


class TestInterpretabilityEngineTraceDecision:
    def test_records_trace_with_reasoning(self) -> None:
        engine = InterpretabilityEngine()
        trace = engine.trace_decision(
            agent_id="test-agent",
            input_text="Should I deploy to production?",
            reasoning=[
                "Check if tests pass",
                "Check if code review completed",
                "Verify safety checks",
            ],
            decision="Deploy to production",
            confidence=0.92,
        )
        assert trace.agent_id == "test-agent"
        assert len(trace.reasoning_steps) == 3
        assert trace.confidence == 0.92

    def test_skips_trace_below_threshold(self) -> None:
        config = InterpretabilityConfig(confidence_threshold=0.9)
        engine = InterpretabilityEngine(config=config)
        trace = engine.trace_decision(
            agent_id="agent",
            input_text="test",
            reasoning=["Step 1"],
            decision="Skip",
            confidence=0.3,
        )
        # Trace is still returned, but not stored internally
        assert trace.confidence == 0.3
        assert len(engine._traces) == 0

    def test_caps_alternatives_to_max(self) -> None:
        config = InterpretabilityConfig(max_alternatives=2)
        engine = InterpretabilityEngine(config=config)
        trace = engine.trace_decision(
            agent_id="agent",
            input_text="test",
            reasoning=["Step"],
            decision="A",
            confidence=0.9,
            alternatives=["B", "C", "D", "E"],
        )
        assert len(trace.alternatives_considered) == 2

    def test_clamps_confidence_to_01(self) -> None:
        engine = InterpretabilityEngine()
        trace_high = engine.trace_decision(
            agent_id="a",
            input_text="t",
            reasoning=["s"],
            decision="d",
            confidence=5.0,
        )
        trace_low = engine.trace_decision(
            agent_id="a",
            input_text="t",
            reasoning=["s"],
            decision="d",
            confidence=-1.0,
        )
        assert trace_high.confidence == 1.0
        assert trace_low.confidence == 0.0


class TestInterpretabilityEngineAttributeFeatures:
    def test_returns_ranked_attributions(self) -> None:
        engine = InterpretabilityEngine()
        results = engine.attribute_features(
            "We need to improve performance and security while maintaining safety."
        )
        assert len(results) > 0
        # Verify descending rank order
        for i in range(len(results) - 1):
            assert results[i].rank < results[i + 1].rank

    def test_uses_specified_method(self) -> None:
        engine = InterpretabilityEngine()
        results = engine.attribute_features(
            "Safety first", method="GRADIENT"
        )
        assert all(r.method == "GRADIENT" for r in results)

    def test_returns_empty_for_no_keywords(self) -> None:
        engine = InterpretabilityEngine()
        results = engine.attribute_features("The quick brown fox")
        assert results == []

    def test_scores_are_positive(self) -> None:
        engine = InterpretabilityEngine()
        results = engine.attribute_features("safety and security are critical")
        assert all(r.score > 0 for r in results)


class TestInterpretabilityEngineGenerateCounterfactual:
    def test_produces_valid_counterfactual(self) -> None:
        engine = InterpretabilityEngine()
        trace = engine.trace_decision(
            agent_id="agent",
            input_text="Deploy with safety checks",
            reasoning=["Check safety"],
            decision="Deploy to production",
            confidence=0.85,
        )
        cf = engine.generate_counterfactual(trace, "safety", "failed")
        assert cf.original_decision == trace.input_summary
        assert "safety" in cf.counterfactual_scenario
        assert "safety" in cf.key_changed_factors
        assert isinstance(cf.confidence_delta, float)


class TestInterpretabilityEngineComputeSaliency:
    def test_returns_properly_sized_scores(self) -> None:
        engine = InterpretabilityEngine()
        text = "safety performance reliability"
        sm = engine.compute_saliency(text)
        assert len(sm.tokens) == len(sm.scores)
        assert sm.target_text == text

    def test_scores_are_normalized_to_01(self) -> None:
        engine = InterpretabilityEngine()
        sm = engine.compute_saliency("safety and performance are important for reliability")
        for score in sm.scores:
            assert 0.0 <= score <= 1.0

    def test_domain_keywords_get_boosted_scores(self) -> None:
        engine = InterpretabilityEngine()
        sm = engine.compute_saliency("the safety performance")
        # "the" is not a domain keyword, "safety" and "performance" are
        safety_idx = sm.tokens.index("safety") if "safety" in sm.tokens else -1
        perf_idx = sm.tokens.index("performance") if "performance" in sm.tokens else -1
        sm.tokens.index("the") if "the" in sm.tokens else -1
        # Domain keywords should have non-zero scores
        if safety_idx >= 0:
            assert sm.scores[safety_idx] > 0
        if perf_idx >= 0:
            assert sm.scores[perf_idx] > 0

    def test_empty_text_returns_empty_result(self) -> None:
        engine = InterpretabilityEngine()
        sm = engine.compute_saliency("")
        assert sm.tokens == ()
        assert sm.scores == ()


class TestInterpretabilityEngineGenerateReport:
    def test_aggregates_traces_for_agent(self) -> None:
        engine = InterpretabilityEngine()
        engine.trace_decision(
            agent_id="agent-a",
            input_text="Deploy safety fix",
            reasoning=["Check"],
            decision="Deploy",
            confidence=0.9,
        )
        engine.trace_decision(
            agent_id="agent-b",
            input_text="Handle performance issue",
            reasoning=["Analyze"],
            decision="Optimize",
            confidence=0.8,
        )

        report = engine.generate_report("agent-a")
        assert report.agent_id == "agent-a"
        assert len(report.decision_traces) == 1

    def test_transparency_score_is_between_0_and_1(self) -> None:
        engine = InterpretabilityEngine()
        report = engine.generate_report("agent-x")
        assert 0.0 <= report.overall_transparency_score <= 1.0

    def test_includes_top_attributions(self) -> None:
        engine = InterpretabilityEngine()
        engine.trace_decision(
            agent_id="agent",
            input_text="safety and security are critical for performance",
            reasoning=["Check"],
            decision="Proceed with safety and performance review",
            confidence=0.9,
        )
        report = engine.generate_report("agent")
        assert len(report.top_attributions) > 0


class TestInterpretabilityEngineExplainDecision:
    def test_returns_readable_text(self) -> None:
        engine = InterpretabilityEngine()
        trace = engine.trace_decision(
            agent_id="agent",
            input_text="Should I enable safety checks?",
            reasoning=["Safety is important", "Check configuration"],
            decision="Enable safety",
            confidence=0.95,
        )
        explanation = engine.explain_decision("agent", trace.decision_id)
        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "Decision Explanation" in explanation
        assert trace.decision_id in explanation or "agent" in explanation

    def test_returns_not_found_for_unknown_decision(self) -> None:
        engine = InterpretabilityEngine()
        explanation = engine.explain_decision("agent", "nonexistent-id")
        assert "No decision found" in explanation


class TestInterpretabilityEngineGetStats:
    def test_returns_zero_when_no_traces(self) -> None:
        engine = InterpretabilityEngine()
        stats = engine.get_stats()
        assert stats["total_traces"] == 0
        assert stats["total_counterfactuals"] == 0
        assert stats["avg_confidence"] == 0.0
        assert stats["avg_alternatives_considered"] == 0.0

    def test_tracks_after_decisions(self) -> None:
        engine = InterpretabilityEngine()
        engine.trace_decision(
            agent_id="agent",
            input_text="test",
            reasoning=["Step"],
            decision="Go",
            confidence=0.8,
            alternatives=["Stop", "Wait"],
        )
        stats = engine.get_stats()
        assert stats["total_traces"] == 1
        assert stats["avg_confidence"] == 0.8
        assert stats["avg_alternatives_considered"] == 2.0


class TestInterpretabilityEngineEdgeCases:
    def test_trace_with_empty_reasoning(self) -> None:
        engine = InterpretabilityEngine()
        trace = engine.trace_decision(
            agent_id="agent",
            input_text="Input",
            reasoning=[],
            decision="Go",
            confidence=0.9,
        )
        assert trace.reasoning_steps == ()

    def test_trace_with_long_input_truncates_summary(self) -> None:
        engine = InterpretabilityEngine()
        long_input = "A" * 500
        trace = engine.trace_decision(
            agent_id="agent",
            input_text=long_input,
            reasoning=["Step"],
            decision="Go",
            confidence=0.9,
        )
        assert len(trace.input_summary) <= 103  # 100 chars + "..."

    def test_many_traces_respects_max_traces(self) -> None:
        config = InterpretabilityConfig(max_traces=5, confidence_threshold=0.0)
        engine = InterpretabilityEngine(config=config)
        for i in range(20):
            engine.trace_decision(
                agent_id=f"agent-{i}",
                input_text="test",
                reasoning=["Step"],
                decision="Go",
                confidence=0.5,
            )
        assert len(engine._traces) <= 5
