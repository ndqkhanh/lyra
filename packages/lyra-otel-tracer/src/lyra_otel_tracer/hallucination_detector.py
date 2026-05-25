"""Detect hallucinated outputs in agent responses."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple

from .exceptions import HallucinationDetectionError


DEFAULT_PATTERNS: Tuple[str, ...] = (
    r"I (don't|do not) (have|know|understand)",
    r"as an AI (language model|assistant)",
    r"I cannot (provide|confirm|verify|access)",
    r"I'm (sorry|afraid)",
    r"I don't have (access|information|data|the ability)",
    r"it's possible that",
    r"it is possible that",
    r"in my (training|knowledge|experience)",
    r"based on my (training|knowledge|understanding|analysis)",
    r"I think",
    r"I believe",
    r"I'm not sure",
    r"I am not sure",
    r"hypothetically",
    r"in theory",
    r"theoretically",
)


@dataclass(frozen=True)
class HallucinationSignal:
    """A detected signal indicating potential hallucination."""

    signal_type: str
    description: str
    confidence: float
    source_text: str
    pattern_matched: str


@dataclass(frozen=True)
class HallucinationReport:
    """Report of hallucination analysis for a response."""

    has_hallucinations: bool
    signals: Tuple[HallucinationSignal, ...] = ()
    risk_score: float = 0.0
    recommended_action: str = "none"


@dataclass(frozen=True)
class DetectorConfig:
    """Configuration for the hallucination detector."""

    sensitivity: float = 0.5
    patterns: Tuple[str, ...] = DEFAULT_PATTERNS
    min_confidence: float = 0.3


class HallucinationDetector:
    """Detects hallucinated or low-confidence outputs in agent responses."""

    def __init__(
        self,
        config: DetectorConfig | None = None,
    ) -> None:
        self._config = config or DetectorConfig()
        self._custom_patterns: List[str] = []

    async def analyze_response(
        self,
        text: str,
        _context: str = "",
    ) -> HallucinationReport:
        """Analyze a single response for hallucination signals."""
        signals: List[HallucinationSignal] = []
        all_patterns = list(self._config.patterns) + self._custom_patterns

        for pattern in all_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                matched_text = match if isinstance(match, str) else match[0]
                confidence = min(
                    self._config.sensitivity * 0.8,  # per-match confidence
                    1.0,
                )
                if confidence >= self._config.min_confidence:
                    signals.append(
                        HallucinationSignal(
                            signal_type="hedging_language",
                            description=f"Pattern matched: {pattern}",
                            confidence=confidence,
                            source_text=matched_text,
                            pattern_matched=pattern,
                        )
                    )

        risk_score = 0.0
        if signals:
            # Weighted risk score based on signal count and confidence
            avg_confidence = sum(s.confidence for s in signals) / len(signals)
            density = len(signals) / max(len(text.split()), 1)
            risk_score = min(avg_confidence * density * 10, 1.0)
            risk_score = round(risk_score, 4)

        recommended_action = self._get_recommended_action(risk_score)

        return HallucinationReport(
            has_hallucinations=len(signals) > 0,
            signals=tuple(signals),
            risk_score=risk_score,
            recommended_action=recommended_action,
        )

    async def batch_analyze(
        self,
        responses: List[Tuple[str, str]],
    ) -> Tuple[HallucinationReport, ...]:
        """Analyze multiple (text, context) pairs for hallucination signals."""
        reports: List[HallucinationReport] = []
        for text, context in responses:
            report = await self.analyze_response(text, context)
            reports.append(report)
        return tuple(reports)

    def get_known_patterns(self) -> Tuple[str, ...]:
        """Return all known detection patterns."""
        return tuple(self._config.patterns) + tuple(self._custom_patterns)

    async def add_custom_pattern(self, pattern: str) -> None:
        """Add a custom regex pattern for hallucination detection."""
        try:
            re.compile(pattern)
        except re.error as e:
            raise HallucinationDetectionError(
                f"Invalid regex pattern: {e}"
            ) from e
        self._custom_patterns.append(pattern)

    @staticmethod
    def _get_recommended_action(risk_score: float) -> str:
        """Get the recommended action based on risk score."""
        if risk_score >= 0.8:
            return "reject_and_retry"
        elif risk_score >= 0.5:
            return "request_clarification"
        elif risk_score >= 0.2:
            return "review_manually"
        return "none"
