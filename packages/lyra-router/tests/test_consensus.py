"""Tests for Consensus Router, Verdict Combiner, and Dissent Detector."""
from __future__ import annotations

import pytest

from lyra_router.verdict_combiner import (
    CombinedVerdict,
    CombineStrategy,
    ModelVerdict,
    VerdictCombiner,
)
from lyra_router.dissent_detector import (
    DissentDetector,
    DissentReport,
    DissentSeverity,
    DissentType,
)
from lyra_router.consensus_router import (
    ConsensusMode,
    ConsensusOutcome,
    ConsensusRouter,
    ConsensusResult,
)


# ── Fixtures ───────────────────────────────────────────────────────


def make_verdict(
    model_name: str = "sonnet",
    model_tier: str = "standard",
    output: str = "Use JWT with refresh tokens",
    confidence: float = 0.9,
    latency_ms: float = 150.0,
    cost_usd: float = 0.01,
    success: bool = True,
    error_message: str = "",
) -> ModelVerdict:
    return ModelVerdict(
        model_name=model_name,
        model_tier=model_tier,
        output=output,
        confidence=confidence,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        success=success,
        error_message=error_message,
    )


# ── VerdictCombiner Tests ──────────────────────────────────────────


class TestVerdictCombiner:
    def test_combine_empty_verdicts(self):
        combiner = VerdictCombiner()
        result = combiner.combine([])
        assert result.participating_models == 0
        assert result.confidence == 0.0

    def test_combine_single_verdict(self):
        combiner = VerdictCombiner()
        v = make_verdict()
        result = combiner.combine([v])
        assert result.participating_models == 1
        assert result.confidence > 0.0

    def test_majority_vote_selects_most_common(self):
        combiner = VerdictCombiner()
        verdicts = [
            make_verdict(output="Option A", model_name="m1"),
            make_verdict(output="Option A", model_name="m2"),
            make_verdict(output="Option B", model_name="m3"),
        ]
        result = combiner.combine(verdicts, CombineStrategy.MAJORITY_VOTE)
        assert result.final_output == "Option A"
        assert result.agreement_score >= 0.5

    def test_weighted_vote_prefers_higher_tier(self):
        combiner = VerdictCombiner()
        verdicts = [
            make_verdict(output="Simple", model_name="haiku", model_tier="haiku", confidence=0.9),
            make_verdict(output="Detailed", model_name="opus", model_tier="premium", confidence=0.9),
        ]
        result = combiner.combine(verdicts, CombineStrategy.WEIGHTED_VOTE)
        assert result.final_output == "Detailed"

    def test_best_of_n_selects_highest_confidence(self):
        combiner = VerdictCombiner()
        verdicts = [
            make_verdict(output="A", confidence=0.6, model_name="m1"),
            make_verdict(output="B", confidence=0.95, model_name="m2"),
            make_verdict(output="C", confidence=0.7, model_name="m3"),
        ]
        result = combiner.combine(verdicts, CombineStrategy.BEST_OF_N)
        assert result.final_output == "B"

    def test_unanimous_agreement(self):
        combiner = VerdictCombiner()
        verdicts = [
            make_verdict(output="Same answer", model_name="m1"),
            make_verdict(output="Same answer", model_name="m2"),
            make_verdict(output="Same answer", model_name="m3"),
        ]
        result = combiner.combine(verdicts, CombineStrategy.UNANIMOUS)
        assert result.agreement_score == 1.0
        assert result.confidence > 0.0

    def test_unanimous_disagreement(self):
        combiner = VerdictCombiner()
        verdicts = [
            make_verdict(output="Answer A", model_name="m1"),
            make_verdict(output="Answer B", model_name="m2"),
        ]
        result = combiner.combine(verdicts, CombineStrategy.UNANIMOUS)
        assert result.agreement_score == 0.0
        assert result.confidence == 0.0

    def test_all_failed_verdicts(self):
        combiner = VerdictCombiner()
        verdicts = [
            make_verdict(output="", success=False, model_name="m1"),
            make_verdict(output="", success=False, model_name="m2"),
        ]
        result = combiner.combine(verdicts)
        assert result.confidence == 0.0
        assert result.participating_models == 0

    def test_cascade_prefers_higher_tier(self):
        combiner = VerdictCombiner()
        verdicts = [
            make_verdict(output="Opus answer", model_name="opus", model_tier="premium", confidence=0.9),
            make_verdict(output="Haiku answer", model_name="haiku", model_tier="haiku", confidence=0.9),
        ]
        result = combiner.combine(verdicts, CombineStrategy.CASCADE)
        assert "Opus" in result.final_output

    def test_calculates_total_cost(self):
        combiner = VerdictCombiner()
        verdicts = [
            make_verdict(cost_usd=0.01, model_name="m1"),
            make_verdict(cost_usd=0.05, model_name="m2"),
        ]
        result = combiner.combine(verdicts)
        assert result.total_cost_usd == pytest.approx(0.06)

    def test_default_strategy_is_weighted(self):
        combiner = VerdictCombiner()
        assert combiner.default_strategy == CombineStrategy.WEIGHTED_VOTE


# ── DissentDetector Tests ──────────────────────────────────────────


class TestDissentDetector:
    def test_no_dissent_when_models_agree(self):
        detector = DissentDetector()
        outputs = [
            {"model_name": "m1", "output": "Same answer here", "confidence": 0.9, "model_tier": "standard"},
            {"model_name": "m2", "output": "Same answer here", "confidence": 0.85, "model_tier": "premium"},
        ]
        report = detector.detect(outputs)
        assert report.dissent_type == DissentType.NONE

    def test_detects_factual_dissent(self):
        detector = DissentDetector()
        outputs = [
            {"model_name": "m1", "output": "The answer is 42", "confidence": 0.9, "model_tier": "standard"},
            {"model_name": "m2", "output": "The answer is definitely 7", "confidence": 0.9, "model_tier": "standard"},
        ]
        report = detector.detect(outputs)
        assert report.severity != DissentSeverity.NONE

    def test_insufficient_models_returns_none(self):
        detector = DissentDetector()
        outputs = [
            {"model_name": "m1", "output": "Anything", "confidence": 0.9, "model_tier": "standard"},
        ]
        report = detector.detect(outputs)
        assert report.dissent_type == DissentType.NONE

    def test_confidence_gap_detected(self):
        detector = DissentDetector()
        outputs = [
            {"model_name": "m1", "output": "Same output text here", "confidence": 0.9, "model_tier": "standard"},
            {"model_name": "m2", "output": "Same output text here", "confidence": 0.3, "model_tier": "standard"},
        ]
        report = detector.detect(outputs)
        assert report.dissent_type == DissentType.CONFIDENCE_GAP

    def test_detect_from_verdicts(self):
        detector = DissentDetector()
        verdicts = [
            make_verdict(output="Same result", model_name="m1"),
            make_verdict(output="Same result", model_name="m2"),
        ]
        report = detector.detect_from_verdicts(verdicts)
        assert report.dissent_type == DissentType.NONE

    def test_security_keywords_critical(self):
        detector = DissentDetector()
        outputs = [
            {"model_name": "m1", "output": "Use AES encryption for password storage", "confidence": 0.9, "model_tier": "standard"},
            {"model_name": "m2", "output": "Store passwords in plaintext for speed", "confidence": 0.9, "model_tier": "standard"},
        ]
        report = detector.detect(outputs)
        assert report.severity == DissentSeverity.CRITICAL
        assert report.needs_human_review is True

    def test_history_accumulates(self):
        detector = DissentDetector()
        detector.detect([
            {"model_name": "a", "output": "x", "confidence": 0.5, "model_tier": "standard"},
            {"model_name": "b", "output": "x", "confidence": 0.5, "model_tier": "standard"},
        ])
        assert len(detector.get_history()) == 1

    def test_clear_removes_history(self):
        detector = DissentDetector()
        detector.detect([
            {"model_name": "a", "output": "x", "confidence": 0.5, "model_tier": "standard"},
            {"model_name": "b", "output": "x", "confidence": 0.5, "model_tier": "standard"},
        ])
        detector.clear()
        assert len(detector.get_history()) == 0

    def test_get_dissent_rate(self):
        detector = DissentDetector()
        detector.detect([
            {"model_name": "a", "output": "same", "confidence": 0.5, "model_tier": "standard"},
            {"model_name": "b", "output": "same", "confidence": 0.5, "model_tier": "standard"},
        ])
        rate = detector.get_dissent_rate()
        assert isinstance(rate, float)


# ── ConsensusRouter Tests ──────────────────────────────────────────


class TestConsensusRouter:
    def test_route_single_best(self):
        router = ConsensusRouter()
        result = router.route_sync(
            "Write a function",
            mode=ConsensusMode.SINGLE_BEST,
            eligible_models=["sonnet"],
        )
        assert result.outcome == ConsensusOutcome.CONSENSUS_REACHED
        assert result.models_queried == 1
        assert result.models_succeeded == 1

    def test_route_dual_verify_agreeing(self):
        router = ConsensusRouter()
        result = router.route_sync(
            "Write a function",
            mode=ConsensusMode.DUAL_VERIFY,
            eligible_models=["sonnet", "opus"],
        )
        assert result.models_queried >= 1
        assert result.combined_verdict.confidence > 0.0

    def test_route_majority_quorum(self):
        router = ConsensusRouter()
        result = router.route_sync(
            "Write a function",
            mode=ConsensusMode.MAJORITY_QUORUM,
            eligible_models=["haiku", "sonnet", "opus"],
        )
        assert result.models_queried == 3
        assert result.outcome in (
            ConsensusOutcome.CONSENSUS_REACHED,
            ConsensusOutcome.MAJORITY_ACCEPTED,
        )

    def test_route_full_consensus(self):
        router = ConsensusRouter()
        result = router.route_sync(
            "Critical security review",
            mode=ConsensusMode.FULL_CONSENSUS,
            eligible_models=["haiku", "sonnet", "opus"],
        )
        assert result.models_queried >= 2
        assert result.models_succeeded >= 1

    def test_route_with_fewer_models_than_mode(self):
        router = ConsensusRouter()
        result = router.route_sync(
            "Simple task",
            mode=ConsensusMode.MAJORITY_QUORUM,
            eligible_models=["haiku"],
        )
        assert result.models_queried == 1

    def test_session_tracking(self):
        router = ConsensusRouter()
        result = router.route_sync("Test", mode=ConsensusMode.SINGLE_BEST)
        session = router.get_session(result.session_id)
        assert session is not None
        assert session.task == "Test"

    def test_session_not_found(self):
        router = ConsensusRouter()
        assert router.get_session("nonexistent") is None

    def test_history_accumulates(self):
        router = ConsensusRouter()
        router.route_sync("Task 1", mode=ConsensusMode.SINGLE_BEST)
        router.route_sync("Task 2", mode=ConsensusMode.SINGLE_BEST)
        assert len(router.get_history()) == 2

    def test_get_stats(self):
        router = ConsensusRouter()
        router.route_sync("T1", mode=ConsensusMode.SINGLE_BEST)
        stats = router.get_stats()
        assert stats["total_routes"] == 1
        assert stats["consensus_rate"] >= 0.0

    def test_get_stats_empty(self):
        router = ConsensusRouter()
        stats = router.get_stats()
        assert stats["total_routes"] == 0

    def test_clear_removes_all(self):
        router = ConsensusRouter()
        router.route_sync("Task", mode=ConsensusMode.SINGLE_BEST)
        router.clear()
        assert len(router.get_history()) == 0
        assert router.get_session("any") is None

    def test_select_models_single_best(self):
        models = ConsensusRouter._select_models(
            ConsensusMode.SINGLE_BEST,
            ["haiku-model", "sonnet-model", "opus-model"],
        )
        assert len(models) == 1
        assert "opus" in models[0].lower()

    def test_select_models_dual_verify(self):
        models = ConsensusRouter._select_models(
            ConsensusMode.DUAL_VERIFY,
            ["haiku", "sonnet", "opus"],
        )
        assert len(models) == 2

    def test_select_models_majority_quorum(self):
        models = ConsensusRouter._select_models(
            ConsensusMode.MAJORITY_QUORUM,
            ["m1", "m2", "m3"],
        )
        assert len(models) == 3

    def test_infer_tier(self):
        assert ConsensusRouter._infer_tier("claude-opus-4") == "premium"
        assert ConsensusRouter._infer_tier("claude-sonnet-4") == "standard"
        assert ConsensusRouter._infer_tier("claude-haiku-4") == "haiku"
        assert ConsensusRouter._infer_tier("unknown-model") == "standard"


# ── ModelVerdict Tests ─────────────────────────────────────────────


class TestModelVerdict:
    def test_create_verdict(self):
        v = make_verdict()
        assert v.model_name == "sonnet"
        assert v.model_tier == "standard"
        assert v.confidence == 0.9
        assert v.success is True

    def test_failed_verdict(self):
        v = make_verdict(success=False, error_message="timeout")
        assert v.success is False
        assert v.error_message == "timeout"

    def test_frozen_dataclass(self):
        v = make_verdict()
        with pytest.raises(Exception):
            v.confidence = 0.5  # type: ignore[misc]
