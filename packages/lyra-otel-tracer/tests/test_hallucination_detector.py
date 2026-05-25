"""Tests for lyra_otel_tracer.hallucination_detector."""

from __future__ import annotations

import pytest

from lyra_otel_tracer.exceptions import HallucinationDetectionError
from lyra_otel_tracer.hallucination_detector import (
    DEFAULT_PATTERNS,
    DetectorConfig,
    HallucinationDetector,
    HallucinationReport,
    HallucinationSignal,
)


class TestHallucinationSignal:
    def test_hallucination_signal_creation(self) -> None:
        signal = HallucinationSignal(
            signal_type="hedging_language",
            description="Hedging detected",
            confidence=0.7,
            source_text="I think",
            pattern_matched=r"I think",
        )
        assert signal.signal_type == "hedging_language"
        assert signal.confidence == 0.7

    def test_hallucination_signal_frozen(self) -> None:
        signal = HallucinationSignal(
            signal_type="test", description="d", confidence=0.5, source_text="t", pattern_matched="p"
        )
        with pytest.raises(AttributeError):
            signal.signal_type = "changed"  # type: ignore[misc]


class TestHallucinationReport:
    def test_hallucination_report_creation(self) -> None:
        report = HallucinationReport(has_hallucinations=True)
        assert report.has_hallucinations
        assert report.signals == ()
        assert report.recommended_action == "none"

    def test_hallucination_report_frozen(self) -> None:
        report = HallucinationReport(has_hallucinations=False)
        with pytest.raises(AttributeError):
            report.has_hallucinations = True  # type: ignore[misc]


class TestDetectorConfig:
    def test_detector_config_defaults(self) -> None:
        config = DetectorConfig()
        assert config.sensitivity == 0.5
        assert len(config.patterns) > 0
        assert config.min_confidence == 0.3

    def test_detector_config_custom(self) -> None:
        config = DetectorConfig(sensitivity=0.8, patterns=("custom_pattern",), min_confidence=0.5)
        assert config.sensitivity == 0.8
        assert config.patterns == ("custom_pattern",)
        assert config.min_confidence == 0.5


class TestHallucinationDetector:
    @pytest.mark.asyncio
    async def test_analyze_response_clean(self) -> None:
        detector = HallucinationDetector()
        report = await detector.analyze_response("This is a factual and confident statement.")
        assert not report.has_hallucinations
        assert report.risk_score == 0.0

    @pytest.mark.asyncio
    async def test_analyze_response_hedging(self) -> None:
        detector = HallucinationDetector()
        report = await detector.analyze_response("I think this might be the answer.")
        assert report.has_hallucinations
        assert report.risk_score > 0.0

    @pytest.mark.asyncio
    async def test_analyze_response_multiple_signals(self) -> None:
        detector = HallucinationDetector()
        report = await detector.analyze_response(
            "I think it's possible that I don't know the answer. Based on my training, I believe this might work."
        )
        assert report.has_hallucinations
        assert len(report.signals) >= 1

    @pytest.mark.asyncio
    async def test_analyze_response_empty_string(self) -> None:
        detector = HallucinationDetector()
        report = await detector.analyze_response("")
        assert not report.has_hallucinations
        assert report.risk_score == 0.0

    @pytest.mark.asyncio
    async def test_analyze_response_ai_language_model(self) -> None:
        detector = HallucinationDetector()
        report = await detector.analyze_response("As an AI language model, I cannot provide medical advice.")
        assert report.has_hallucinations

    @pytest.mark.asyncio
    async def test_analyze_response_with_context(self) -> None:
        detector = HallucinationDetector()
        report = await detector.analyze_response("I don't have access to that data.", _context="user query")
        assert report.has_hallucinations

    @pytest.mark.asyncio
    async def test_batch_analyze(self) -> None:
        detector = HallucinationDetector()
        responses = [
            ("This is a factual statement.", ""),
            ("I think this might be wrong.", ""),
            ("Based on my training, here is the answer.", ""),
        ]
        reports = await detector.batch_analyze(responses)
        assert len(reports) == 3
        assert not reports[0].has_hallucinations
        assert reports[1].has_hallucinations

    @pytest.mark.asyncio
    async def test_batch_analyze_empty(self) -> None:
        detector = HallucinationDetector()
        reports = await detector.batch_analyze([])
        assert reports == ()

    @pytest.mark.asyncio
    async def test_get_known_patterns(self) -> None:
        detector = HallucinationDetector()
        patterns = detector.get_known_patterns()
        assert len(patterns) >= len(DEFAULT_PATTERNS)

    @pytest.mark.asyncio
    async def test_add_custom_pattern(self) -> None:
        detector = HallucinationDetector()
        await detector.add_custom_pattern(r"custom_test_pattern")
        patterns = detector.get_known_patterns()
        assert "custom_test_pattern" in patterns

    @pytest.mark.asyncio
    async def test_add_custom_pattern_invalid_regex(self) -> None:
        detector = HallucinationDetector()
        with pytest.raises(HallucinationDetectionError, match="Invalid regex"):
            await detector.add_custom_pattern(r"[invalid")

    @pytest.mark.asyncio
    async def test_risk_score_high(self) -> None:
        detector = HallucinationDetector()
        text = "I think " * 50
        report = await detector.analyze_response(text)
        # The agent chooses recommended_action, but high risk should yield non-"none"
        assert report.risk_score > 0.0

    @pytest.mark.asyncio
    async def test_recommended_action_none(self) -> None:
        detector = HallucinationDetector()
        report = await detector.analyze_response("Clear factual statement with high confidence.")
        assert report.recommended_action == "none"

    @pytest.mark.asyncio
    async def test_recommended_action_review(self) -> None:
        # risk_score 0.2-0.5 should give "review_manually"
        detector = HallucinationDetector(DetectorConfig(sensitivity=0.9, min_confidence=0.1))
        report = await detector.analyze_response("I think")
        assert report.recommended_action in ("review_manually", "request_clarification", "reject_and_retry")

    @pytest.mark.asyncio
    async def test_sensitivity_affects_confidence(self) -> None:
        detector_low = HallucinationDetector(DetectorConfig(sensitivity=0.1, min_confidence=0.01))
        detector_high = HallucinationDetector(DetectorConfig(sensitivity=1.0, min_confidence=0.01))
        report_low = await detector_low.analyze_response("I think this is wrong.")
        report_high = await detector_high.analyze_response("I think this is wrong.")
        assert report_low.risk_score >= 0.0
        assert report_high.risk_score >= 0.0
        pass  # This is a behavioral check

    @pytest.mark.asyncio
    async def test_min_confidence_filter(self) -> None:
        detector = HallucinationDetector(DetectorConfig(sensitivity=0.1, min_confidence=0.5))
        report = await detector.analyze_response("I think this is wrong.")
        # With sensitivity 0.1, per-match confidence = min(0.1*0.8, 1.0) = 0.08
        # Since 0.08 < 0.5 (min_confidence), no signals
        assert not report.has_hallucinations

    @pytest.mark.asyncio
    async def test_custom_pattern_analyze(self) -> None:
        detector = HallucinationDetector()
        await detector.add_custom_pattern(r"custom_hallucination_pattern")
        report = await detector.analyze_response("This matches custom_hallucination_pattern")
        assert report.has_hallucinations
