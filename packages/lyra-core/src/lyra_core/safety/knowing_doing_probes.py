"""Knowing-Doing Probes — bridging the action-gap between knowledge and execution.

Based on arXiv:2605.14038 — hidden-state confidence probing reveals tool-use
gaps (26.5-54.0%) where agents KNOW the correct action but fail to DO it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class GapSeverity(StrEnum):
    NONE = "none"
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ProbeResult:
    """Result of a single confidence probe on a tool-use decision."""

    tool_name: str
    expected_action: str
    actual_action: str
    knowledge_confidence: float
    execution_confidence: float
    gap_score: float
    severity: GapSeverity


@dataclass(frozen=True)
class GapReport:
    """Aggregate knowing-doing gap analysis across multiple probes."""

    probes: tuple[ProbeResult, ...]
    mean_gap: float
    max_gap: float
    severe_count: int
    overall_severity: GapSeverity


@dataclass
class ProbeConfig:
    gap_threshold_minor: float = 0.1
    gap_threshold_moderate: float = 0.25
    gap_threshold_severe: float = 0.4
    gap_threshold_critical: float = 0.6


def _classify_gap(gap: float, config: ProbeConfig) -> GapSeverity:
    if gap >= config.gap_threshold_critical:
        return GapSeverity.CRITICAL
    if gap >= config.gap_threshold_severe:
        return GapSeverity.SEVERE
    if gap >= config.gap_threshold_moderate:
        return GapSeverity.MODERATE
    if gap >= config.gap_threshold_minor:
        return GapSeverity.MINOR
    return GapSeverity.NONE


class KnowingDoingProbe:
    """Measures and tracks the gap between knowledge confidence and execution.

    Agents often KNOW the right tool to use (high knowledge confidence) but
    DO something else (low execution alignment). This probe quantifies that
    gap to surface improvement opportunities.
    """

    def __init__(self, config: ProbeConfig | None = None) -> None:
        self.config = config or ProbeConfig()
        self._history: list[ProbeResult] = []

    def probe(
        self,
        tool_name: str,
        expected_action: str,
        actual_action: str,
        knowledge_confidence: float,
        execution_confidence: float,
    ) -> ProbeResult:
        """Record a single knowing-doing probe.

        Args:
            tool_name: The tool being invoked.
            expected_action: What the agent knew it should do.
            actual_action: What the agent actually did.
            knowledge_confidence: Hidden-state confidence in the correct action.
            execution_confidence: Confidence in the actual executed action.

        Returns:
            ProbeResult with gap analysis.
        """
        gap = max(0.0, knowledge_confidence - execution_confidence)
        severity = _classify_gap(gap, self.config)

        result = ProbeResult(
            tool_name=tool_name,
            expected_action=expected_action,
            actual_action=actual_action,
            knowledge_confidence=round(knowledge_confidence, 4),
            execution_confidence=round(execution_confidence, 4),
            gap_score=round(gap, 4),
            severity=severity,
        )
        self._history.append(result)
        return result

    def generate_report(self) -> GapReport:
        """Generate aggregate gap analysis from all recorded probes."""
        if not self._history:
            return GapReport(
                probes=(),
                mean_gap=0.0,
                max_gap=0.0,
                severe_count=0,
                overall_severity=GapSeverity.NONE,
            )

        gaps = [p.gap_score for p in self._history]
        mean_gap = sum(gaps) / len(gaps)
        max_gap = max(gaps)

        severe_count = sum(
            1 for p in self._history
            if p.severity in (GapSeverity.SEVERE, GapSeverity.CRITICAL)
        )

        overall = _classify_gap(mean_gap, self.config)

        return GapReport(
            probes=tuple(self._history),
            mean_gap=round(mean_gap, 4),
            max_gap=round(max_gap, 4),
            severe_count=severe_count,
            overall_severity=overall,
        )

    @property
    def history(self) -> list[ProbeResult]:
        return list(self._history)

    @property
    def total_probes(self) -> int:
        return len(self._history)

    @property
    def mean_gap(self) -> float:
        if not self._history:
            return 0.0
        return round(sum(p.gap_score for p in self._history) / len(self._history), 4)
