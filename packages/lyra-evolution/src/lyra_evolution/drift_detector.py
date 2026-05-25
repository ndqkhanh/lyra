"""PRISM Prompt Drift Detection.

Daily automated detection of LLM prompt degradation with auto-repair.
Tracks success rate, latency, token usage, and output quality across
all active prompts, comparing recent signals against a rolling baseline
to detect and alert on performance drift.

Phase 13.4 — PRISM: Prompt Reliability & Integrity Surveillance Module.
"""

from __future__ import annotations

import logging
import statistics
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DriftSignal:
    """A single performance signal recorded for a prompt.

    Attributes:
        prompt_name: Name/identifier of the prompt being tracked.
        timestamp: Unix timestamp when the signal was recorded.
        success_rate: Fraction of successful calls (0.0 – 1.0).
        avg_latency_ms: Average response latency in milliseconds.
        token_usage: Total tokens consumed in this measurement window.
        output_quality_score: Quality score for generated output (0.0 – 1.0).
        anomaly_flags: Any flags raised (e.g., "high_latency", "low_quality").
    """

    prompt_name: str
    timestamp: float = field(default_factory=time.time)
    success_rate: float = 1.0
    avg_latency_ms: float = 0.0
    token_usage: int = 0
    output_quality_score: float = 1.0
    anomaly_flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.success_rate <= 1.0:
            raise ValueError(
                f"success_rate must be in [0, 1], got {self.success_rate}"
            )
        if not 0.0 <= self.output_quality_score <= 1.0:
            raise ValueError(
                f"output_quality_score must be in [0, 1], got {self.output_quality_score}"
            )
        if self.avg_latency_ms < 0:
            raise ValueError(
                f"avg_latency_ms must be non-negative, got {self.avg_latency_ms}"
            )
        if self.token_usage < 0:
            raise ValueError(
                f"token_usage must be non-negative, got {self.token_usage}"
            )


class DriftAlert(Enum):
    """Severity level of a drift alert.

    Values:
        NONE: Performance is within acceptable bounds.
        WARNING: Minor degradation detected; schedule optimization.
        DEGRADATION: Significant degradation; trigger re-optimisation.
        CRITICAL: Severe degradation; rollback and alert on-call.
    """

    NONE = auto()
    WARNING = auto()
    DEGRADATION = auto()
    CRITICAL = auto()


@dataclass(frozen=True)
class DriftReport:
    """Result of a drift check for a single prompt.

    Attributes:
        prompt_name: Name of the prompt that was checked.
        alert_level: Severity of the detected drift.
        current_success_rate: Most recent success rate measurement.
        baseline_success_rate: Baseline average success rate.
        degradation_pct: Percentage drop from baseline (negative = degradation).
        recommended_action: Human-readable action recommendation.
        signals_analyzed: Number of signals used in the analysis.
    """

    prompt_name: str
    alert_level: DriftAlert = DriftAlert.NONE
    current_success_rate: float = 1.0
    baseline_success_rate: float = 1.0
    degradation_pct: float = 0.0
    recommended_action: str = "no action"
    signals_analyzed: int = 0

    def __post_init__(self) -> None:
        if not 0.0 <= self.current_success_rate <= 1.0:
            raise ValueError(
                f"current_success_rate must be in [0, 1], got {self.current_success_rate}"
            )
        if not 0.0 <= self.baseline_success_rate <= 1.0:
            raise ValueError(
                f"baseline_success_rate must be in [0, 1], got {self.baseline_success_rate}"
            )
        if self.signals_analyzed < 0:
            raise ValueError(
                f"signals_analyzed must be non-negative, got {self.signals_analyzed}"
            )

    @property
    def is_degraded(self) -> bool:
        """True when the alert level is DEGRADATION or higher."""
        return self.alert_level in (DriftAlert.DEGRADATION, DriftAlert.CRITICAL)


# ---------------------------------------------------------------------------
# PRISM Drift Detector
# ---------------------------------------------------------------------------


class PRISMDriftDetector:
    """Detects prompt performance drift by comparing recent signals to a baseline.

    The detector maintains a sliding window of performance signals per prompt.
    When queried, it compares the most recent window against the baseline (older
    window) and produces a ``DriftReport`` with an appropriate alert level.

    Usage::

        detector = PRISMDriftDetector(baseline_window_days=7, alert_threshold=0.05)

        signal = DriftSignal(prompt_name="code_gen", success_rate=0.92)
        detector.record_signal(signal)

        report = detector.check_drift("code_gen")
        if report.is_degraded:
            action = detector.recommend_action(report)
            logger.warning("Drift detected: %s", action)
    """

    def __init__(
        self,
        *,
        baseline_window_days: int = 7,
        alert_threshold: float = 0.05,
        critical_threshold: float = 0.15,
    ) -> None:
        """Initialise the drift detector.

        Args:
            baseline_window_days: Number of days of historical data to use as
                the baseline. Signals older than this are still retained but
                not used as the "current" comparison window.
            alert_threshold: Minimum degradation fraction that triggers a
                WARNING alert (e.g., 0.05 = 5% drop from baseline).
            critical_threshold: Degradation fraction that triggers a CRITICAL
                alert (e.g., 0.15 = 15% drop from baseline).
        """
        if baseline_window_days < 1:
            raise ValueError(
                f"baseline_window_days must be >= 1, got {baseline_window_days}"
            )
        if not 0.0 < alert_threshold < 1.0:
            raise ValueError(
                f"alert_threshold must be in (0, 1), got {alert_threshold}"
            )
        if not 0.0 < critical_threshold < 1.0:
            raise ValueError(
                f"critical_threshold must be in (0, 1), got {critical_threshold}"
            )

        self._baseline_window_days = baseline_window_days
        self._alert_threshold = alert_threshold
        self._critical_threshold = critical_threshold

        # prompt_name -> list of DriftSignal (already sorted by timestamp)
        self._signals: dict[str, list[DriftSignal]] = {}
        self._max_signals_per_prompt: int = 10_000

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_signal(self, signal: DriftSignal) -> None:
        """Record a performance signal for drift analysis.

        Args:
            signal: The ``DriftSignal`` to store.
        """
        if signal.prompt_name not in self._signals:
            self._signals[signal.prompt_name] = []

        signals = self._signals[signal.prompt_name]
        signals.append(signal)

        # Keep within limits
        if len(signals) > self._max_signals_per_prompt:
            self._signals[signal.prompt_name] = signals[
                -self._max_signals_per_prompt :
            ]

        logger.debug(
            "Recorded signal for '%s': success_rate=%.3f, quality=%.3f",
            signal.prompt_name,
            signal.success_rate,
            signal.output_quality_score,
        )

    # ------------------------------------------------------------------
    # Drift checking
    # ------------------------------------------------------------------

    def check_drift(self, prompt_name: str) -> DriftReport:
        """Compare the recent signal window against the baseline.

        Args:
            prompt_name: The prompt to check for drift.

        Returns:
            A ``DriftReport`` with the alert level, rates, and
            recommended action.

        Raises:
            ValueError: If no signals have been recorded for the prompt.
        """
        signals = self._signals.get(prompt_name)
        if not signals:
            raise ValueError(f"No signals recorded for prompt '{prompt_name}'")

        # Split into baseline (older) and recent windows
        baseline_cutoff = time.time() - (self._baseline_window_days * 86_400)
        recent_cutoff = time.time() - (self._baseline_window_days * 86_400 // 2)

        baseline_signals = [s for s in signals if s.timestamp <= baseline_cutoff]
        recent_signals = [
            s for s in signals if baseline_cutoff < s.timestamp <= recent_cutoff
        ]

        # Fallback: use oldest half as baseline and newest half as recent
        if not baseline_signals or not recent_signals:
            mid = len(signals) // 2
            baseline_signals = signals[:mid]
            recent_signals = signals[mid:]

        baseline_rate = (
            sum(s.success_rate for s in baseline_signals) / len(baseline_signals)
            if baseline_signals
            else 1.0
        )
        current_rate = (
            sum(s.success_rate for s in recent_signals) / len(recent_signals)
            if recent_signals
            else 1.0
        )

        # Degradation: negative pct means drop from baseline
        if baseline_rate > 0:
            degradation_pct = (current_rate - baseline_rate) / baseline_rate * 100
        else:
            degradation_pct = 0.0

        alert_level = self._classify_drift(degradation_pct)
        action = self._action_for_level(alert_level)

        return DriftReport(
            prompt_name=prompt_name,
            alert_level=alert_level,
            current_success_rate=round(current_rate, 4),
            baseline_success_rate=round(baseline_rate, 4),
            degradation_pct=round(degradation_pct, 4),
            recommended_action=action,
            signals_analyzed=len(recent_signals),
        )

    def detect_all(self) -> list[DriftReport]:
        """Check drift for every tracked prompt.

        Returns:
            A list of ``DriftReport`` objects, one per tracked prompt.
        """
        return [
            self.check_drift(prompt_name) for prompt_name in list(self._signals)
        ]

    # ------------------------------------------------------------------
    # Baseline queries
    # ------------------------------------------------------------------

    def get_baseline(
        self, prompt_name: str
    ) -> tuple[float, float]:
        """Return baseline statistics for a prompt.

        Args:
            prompt_name: The prompt to query.

        Returns:
            A ``(avg_success_rate, std_dev)`` tuple over the baseline window.

        Raises:
            ValueError: If no signals have been recorded for the prompt.
        """
        signals = self._signals.get(prompt_name)
        if not signals:
            raise ValueError(f"No signals recorded for prompt '{prompt_name}'")

        cutoff = time.time() - (self._baseline_window_days * 86_400)
        baseline = [s for s in signals if s.timestamp <= cutoff]

        if not baseline:
            baseline = signals

        rates = [s.success_rate for s in baseline]
        avg = sum(rates) / len(rates)
        std = statistics.stdev(rates) if len(rates) > 1 else 0.0

        return (round(avg, 4), round(std, 4))

    # ------------------------------------------------------------------
    # Recommendations
    # ------------------------------------------------------------------

    def recommend_action(self, report: DriftReport) -> str:
        """Return a human-readable action based on the drift alert level.

        Args:
            report: The drift report to evaluate.

        Returns:
            Action recommendation string.
        """
        return self._action_for_level(report.alert_level)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate statistics across all tracked prompts.

        Returns:
            Dict with keys: ``prompts_tracked``, ``alerts_active``,
            ``critical_count``, ``avg_health``.
        """
        reports = self.detect_all()
        prompts_tracked = len(self._signals)
        alerts_active = sum(
            1 for r in reports if r.alert_level != DriftAlert.NONE
        )
        critical_count = sum(
            1 for r in reports if r.alert_level == DriftAlert.CRITICAL
        )

        healths = [r.current_success_rate for r in reports] if reports else [1.0]
        avg_health = sum(healths) / len(healths)

        return {
            "prompts_tracked": prompts_tracked,
            "alerts_active": alerts_active,
            "critical_count": critical_count,
            "avg_health": round(avg_health, 4),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _classify_drift(self, degradation_pct: float) -> DriftAlert:
        """Map a degradation percentage to an alert level.

        Positive degradation_pct means improvement (no alert).
        Negative means degradation.
        """
        if degradation_pct >= -self._alert_threshold * 100:
            return DriftAlert.NONE
        if degradation_pct >= -self._critical_threshold * 100:
            return DriftAlert.WARNING
        # Every non-critical degradation is checked against critical threshold
        # degradation_pct < -critical_threshold * 100 means severe enough
        if degradation_pct < -self._critical_threshold * 100:
            return DriftAlert.CRITICAL
        return DriftAlert.DEGRADATION

    @staticmethod
    def _action_for_level(level: DriftAlert) -> str:
        """Map an alert level to an action string."""
        actions = {
            DriftAlert.NONE: "no action",
            DriftAlert.WARNING: "schedule GEPA optimization",
            DriftAlert.DEGRADATION: "trigger GEPA re-optimization now",
            DriftAlert.CRITICAL: "rollback to last known good + alert oncall",
        }
        return actions[level]


__all__ = [
    "DriftAlert",
    "DriftReport",
    "DriftSignal",
    "PRISMDriftDetector",
]
