"""Tests for src/self_knowledge/uncertainty.py and calibration.py."""
from __future__ import annotations

import pytest

from lyra.self_knowledge.uncertainty import (
    UncertaintyEstimator,
    ConfidenceScore,
    SelfConsistency,
    ExactMatchNormalizer,
    MATUDecomposer,
    CaTSAdaptiveSampler,
    StubDifficultyEstimator,
    AbstentionGate,
    AbstentionDecision,
)
from lyra.self_knowledge.calibration import (
    LoRACalibrator,
    CalibrationExample,
    CalibrationResult,
    StubLoRAOptimizer,
)


# ---------------------------------------------------------------------------
# UncertaintyEstimator
# ---------------------------------------------------------------------------


class TestUncertaintyEstimator:
    def test_estimate_returns_confidence_score(self):
        estimator = UncertaintyEstimator()
        result = estimator.estimate("some output text")
        assert isinstance(result, ConfidenceScore)
        assert 0.0 <= result.score <= 1.0

    def test_estimate_with_probability(self):
        estimator = UncertaintyEstimator()
        result = estimator.estimate("output", probability=0.85)
        assert result.components.get("probability") == 0.85

    def test_estimate_with_log_probs(self):
        estimator = UncertaintyEstimator()
        result = estimator.estimate("output", log_probs=[-0.5, -1.0, -0.3])
        assert "entropy" in result.components

    def test_estimate_batch(self):
        estimator = UncertaintyEstimator()
        results = estimator.estimate_batch(["output a", "output b"])
        assert len(results) == 2

    def test_heuristic_confidence_short_text(self):
        score = UncertaintyEstimator._heuristic_confidence("Hi")
        assert score < 0.5

    def test_heuristic_confidence_empty_text(self):
        score = UncertaintyEstimator._heuristic_confidence("")
        assert score == 0.1


# ---------------------------------------------------------------------------
# SelfConsistency
# ---------------------------------------------------------------------------


class TestSelfConsistency:
    def test_check_agreement(self):
        sc = SelfConsistency(num_samples=3)
        samples = ["yes", "yes", "yes"]
        idx = [0]
        def sampler():
            i = idx[0]
            idx[0] += 1
            return samples[i] if i < len(samples) else ""
        result = sc.check(sampler)
        assert result.agreement == 1.0
        assert result.majority_answer == "yes"

    def test_check_disagreement(self):
        sc = SelfConsistency(num_samples=3)
        samples = ["yes", "no", "maybe"]
        idx = [0]
        def sampler():
            i = idx[0]
            idx[0] += 1
            return samples[i] if i < len(samples) else ""
        result = sc.check(sampler)
        assert result.agreement < 1.0

    def test_exact_match_normalizer(self):
        nm = ExactMatchNormalizer()
        assert nm.normalize("  Hello World  ") == "hello world"

    def test_check_empty_samples(self):
        sc = SelfConsistency(num_samples=0)
        def sampler():
            return ""
        result = sc.check(sampler)
        assert result.agreement == 0.0


# ---------------------------------------------------------------------------
# MATUDecomposer
# ---------------------------------------------------------------------------


class TestMATUDecomposer:
    def test_decompose_empty_logits(self):
        decomp = MATUDecomposer()
        result = decomp.decompose([])
        assert result.aleatoric == 0.0
        assert result.epistemic == 0.0

    def test_decompose_single_prediction(self):
        decomp = MATUDecomposer()
        result = decomp.decompose([[1.0, 2.0, 0.5]])
        assert 0.0 <= result.total <= 1.0
        assert len(result.components) == decomp.n_components

    def test_decompose_with_samples(self):
        decomp = MATUDecomposer()
        logits = [[1.0, 2.0, 0.5]]
        samples = [
            [[1.1, 1.9, 0.6]],
            [[0.9, 2.1, 0.4]],
            [[1.0, 2.0, 0.5]],
        ]
        result = decomp.decompose(logits, samples)
        assert 0.0 <= result.aleatoric <= 1.0
        assert 0.0 <= result.epistemic <= 1.0


# ---------------------------------------------------------------------------
# CaTSAdaptiveSampler
# ---------------------------------------------------------------------------


class TestCaTSAdaptiveSampler:
    def test_sample(self):
        sampler = CaTSAdaptiveSampler(min_samples=1, max_samples=5)
        calls = [0]
        def sample_fn():
            calls[0] += 1
            return "answer"
        result = sampler.sample("easy question", sample_fn)
        assert result.output == "answer"
        assert result.samples_taken >= 1
        assert result.confidence > 0

    def test_sample_empty(self):
        sampler = CaTSAdaptiveSampler(min_samples=1, max_samples=3)
        def fail_fn():
            raise ValueError("fail")
        result = sampler.sample("test", fail_fn)
        assert result.output == ""
        assert result.confidence == 0.0


class TestStubDifficultyEstimator:
    def test_empty_input(self):
        est = StubDifficultyEstimator()
        assert est.estimate("") == 0.0

    def test_long_input_higher(self):
        est = StubDifficultyEstimator()
        easy = est.estimate("hello world")
        hard = est.estimate(" ".join(["complexification"] * 50))
        assert hard > easy


# ---------------------------------------------------------------------------
# AbstentionGate
# ---------------------------------------------------------------------------


class TestAbstentionGate:
    def test_abstain_below_threshold(self):
        gate = AbstentionGate(abstain_threshold=0.3, flag_threshold=0.6)
        decision = gate.decide(ConfidenceScore(score=0.1))
        assert decision.should_abstain is True

    def test_flag_between_thresholds(self):
        gate = AbstentionGate(abstain_threshold=0.3, flag_threshold=0.6)
        decision = gate.decide(ConfidenceScore(score=0.45))
        assert decision.should_abstain is False  # Flagged, but not abstained

    def test_pass_above_flag(self):
        gate = AbstentionGate(abstain_threshold=0.3, flag_threshold=0.6)
        decision = gate.decide(0.8)
        assert decision.should_abstain is False

    def test_invalid_thresholds(self):
        with pytest.raises(ValueError):
            AbstentionGate(abstain_threshold=0.7, flag_threshold=0.3)

    def test_evaluate_batch(self):
        gate = AbstentionGate(0.3, 0.6)
        decisions = gate.evaluate_batch([0.1, 0.45, 0.8])
        assert len(decisions) == 3
        assert decisions[0].should_abstain is True
        assert decisions[2].should_abstain is False

    def test_raw_float_input(self):
        gate = AbstentionGate(0.3, 0.6)
        decision = gate.decide(0.1)
        assert decision.should_abstain is True
        assert decision.confidence == 0.1


# ---------------------------------------------------------------------------
# LoRACalibrator
# ---------------------------------------------------------------------------


class TestLoRACalibrator:
    def test_add_example(self):
        cal = LoRACalibrator()
        cal.add_example("input", "output", confidence=0.9, actual_correct=True)
        assert cal.get_example_count() == 1

    def test_add_examples(self):
        cal = LoRACalibrator()
        examples = [
            CalibrationExample(input_text="a", predicted_output="b", confidence=0.8, actual_correct=True),
            CalibrationExample(input_text="c", predicted_output="d", confidence=0.3, actual_correct=False),
        ]
        cal.add_examples(examples)
        assert cal.get_example_count() == 2

    def test_evaluate_empty(self):
        cal = LoRACalibrator()
        result = cal.evaluate()
        assert result.ece == 0.0
        assert result.num_examples == 0

    def test_evaluate_with_examples(self):
        cal = LoRACalibrator(num_bins=5)
        cal.add_example("in1", "out1", confidence=0.9, actual_correct=True)
        cal.add_example("in2", "out2", confidence=0.8, actual_correct=True)
        cal.add_example("in3", "out3", confidence=0.2, actual_correct=False)
        result = cal.evaluate()
        assert result.num_examples == 3
        assert 0.0 <= result.ece <= 1.0

    def test_calibrate_insufficient_examples(self):
        cal = LoRACalibrator()
        metrics = cal.calibrate()
        assert "error" in metrics

    def test_calibrate_with_examples(self):
        cal = LoRACalibrator()
        cal.add_example("in1", "out1", confidence=0.9, actual_correct=True)
        cal.add_example("in2", "out2", confidence=0.8, actual_correct=True)
        metrics = cal.calibrate()
        assert cal.is_calibrated()

    def test_calibrate_confidence_uncalibrated(self):
        cal = LoRACalibrator()
        assert cal.calibrate_confidence(0.8) == 0.8

    def test_calibrate_confidence_after_calibration(self):
        cal = LoRACalibrator()
        cal.add_example("in1", "out1", confidence=0.9, actual_correct=True)
        cal.add_example("in2", "out2", confidence=0.8, actual_correct=True)
        cal.calibrate()
        adjusted = cal.calibrate_confidence(0.7)
        # Should be somewhat adjusted from 0.7 toward 1.0
        assert 0.5 <= adjusted <= 1.0

    def test_calibrate_confidence_with_score_object(self):
        cal = LoRACalibrator()
        result = cal.calibrate_confidence(ConfidenceScore(score=0.8))
        assert 0.0 <= result <= 1.0
