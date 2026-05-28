"""Tests for Spectral Guardrails — hallucination detection via token-level anomaly scoring."""

import pytest

from lyra_core.safety.spectral_guardrails import (
    SpectralAlert,
    SpectralConfig,
    SpectralGuardrail,
    SpectralResult,
    TokenAnomaly,
)


class TestSpectralAlert:
    def test_alert_levels(self):
        assert SpectralAlert.NONE.value == "none"
        assert SpectralAlert.LOW.value == "low"
        assert SpectralAlert.MEDIUM.value == "medium"
        assert SpectralAlert.HIGH.value == "high"
        assert SpectralAlert.CRITICAL.value == "critical"

    def test_five_levels(self):
        assert len(SpectralAlert) == 5


class TestTokenAnomaly:
    def test_anomaly_creation(self):
        anomaly = TokenAnomaly(
            position=5,
            token="confabulated",
            spectral_score=0.85,
            baseline_mean=0.5,
            z_score=3.2,
        )
        assert anomaly.position == 5
        assert anomaly.token == "confabulated"
        assert anomaly.z_score == 3.2

    def test_anomaly_immutable(self):
        a = TokenAnomaly(position=1, token="x", spectral_score=0.5, baseline_mean=0.3, z_score=2.0)
        with pytest.raises(Exception):
            a.z_score = 5.0


class TestSpectralResult:
    def test_clean_result(self):
        result = SpectralResult(
            text="The sky is blue.",
            tokens_analyzed=4,
            anomaly_count=0,
            max_z_score=0.5,
            alert_level=SpectralAlert.NONE,
            anomalies=(),
            hallucination_probability=0.0,
        )
        assert result.alert_level == SpectralAlert.NONE
        assert result.is_clean is True
        assert result.hallucination_probability == 0.0

    def test_with_anomalies(self):
        a1 = TokenAnomaly(position=3, token="fake", spectral_score=0.9, baseline_mean=0.2, z_score=3.5)
        a2 = TokenAnomaly(position=7, token="wrong", spectral_score=0.95, baseline_mean=0.2, z_score=4.2)
        result = SpectralResult(
            text="some fake and wrong info",
            tokens_analyzed=6,
            anomaly_count=2,
            max_z_score=4.2,
            alert_level=SpectralAlert.HIGH,
            anomalies=(a1, a2),
            hallucination_probability=0.35,
        )
        assert result.alert_level == SpectralAlert.HIGH
        assert result.anomaly_count == 2
        assert result.max_z_score == 4.2
        assert result.is_clean is False

    def test_result_immutable(self):
        r = SpectralResult("ok", 1, 0, 0.0, SpectralAlert.NONE, (), 0.0)
        with pytest.raises(Exception):
            r.alert_level = SpectralAlert.CRITICAL


class TestSpectralConfig:
    def test_default_config(self):
        config = SpectralConfig()
        assert config.z_threshold_low == 2.0
        assert config.z_threshold_high == 4.0
        assert config.window_size == 50

    def test_custom_config(self):
        config = SpectralConfig(z_threshold_low=3.0, window_size=100)
        assert config.z_threshold_low == 3.0
        assert config.window_size == 100


class TestSpectralGuardrail:
    def test_empty_analysis(self):
        guard = SpectralGuardrail()
        result = guard.analyze("", [])
        assert result.alert_level == SpectralAlert.NONE

    def test_too_few_tokens(self):
        guard = SpectralGuardrail()
        result = guard.analyze("hi", [("hi", 0.5)])
        assert result.alert_level == SpectralAlert.NONE
        assert result.tokens_analyzed == 1

    def test_normal_text_no_anomalies(self):
        guard = SpectralGuardrail()
        tokens = guard.simulate_token_scores("this is a normal sentence")
        result = guard.analyze("this is a normal sentence", tokens)
        assert isinstance(result, SpectralResult)
        assert result.tokens_analyzed == len(tokens)

    def test_anomaly_detection(self):
        guard = SpectralGuardrail()
        guard.analyze("normal text", [("norm", 0.0), ("al", 0.0), ("text", 0.0)])
        result = guard.analyze(
            "test BIZARRE text",
            [("test", 0.0), ("BIZARRE", 5.0), ("text", 0.0)],
        )
        assert result.anomaly_count >= 1

    def test_baseline_stats(self):
        guard = SpectralGuardrail()
        guard.analyze("hello world", [("hel", 0.3), ("lo", 0.4)])
        stats = guard.baseline_stats
        assert "mean" in stats
        assert "std" in stats
        assert "samples" in stats

    def test_simulate_token_scores(self):
        guard = SpectralGuardrail()
        scores = guard.simulate_token_scores("test sentence here")
        assert isinstance(scores, list)
        assert len(scores) == 3
        assert all(isinstance(s, tuple) and len(s) == 2 for s in scores)

    def test_total_analyzed(self):
        guard = SpectralGuardrail()
        assert guard.total_analyzed == 0
        guard.analyze("a b c", [("a", 0.1), ("b", 0.2), ("c", 0.3)])
        assert guard.total_analyzed == 1
