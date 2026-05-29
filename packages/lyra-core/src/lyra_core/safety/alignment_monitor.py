"""Phase 1 — Alignment Drift Monitor.

Continuously measures value alignment by tracking behavioural embeddings
over time and detecting statistically significant drift from established
baselines. Uses cosine similarity on action-pattern vectors with
exponential moving average to compute drift scores.
"""

from __future__ import annotations

import math
import time
import uuid
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum


class DriftStatus(Enum):
    NOMINAL = "nominal"
    ELEVATED = "elevated"
    DRIFTING = "drifting"
    CRITICAL = "critical"


@dataclass(frozen=True)
class AlignmentSample:
    """A single alignment measurement point."""

    sample_id: str
    timestamp: float
    value_vector: tuple[float, ...]    # N-dimensional alignment embedding
    action_signature: str              # Hashed description of action
    drift_score: float                 # Cosine distance from baseline


@dataclass(frozen=True)
class DriftReport:
    """Result of an alignment drift check."""

    report_id: str
    status: DriftStatus
    current_drift: float               # 0.0 (perfectly aligned) … 1.0 (fully diverged)
    trend_slope: float                 # Rate of change per sample
    samples_evaluated: int
    recommendation: str
    timestamp: float

    @property
    def requires_intervention(self) -> bool:
        return self.status in (DriftStatus.DRIFTING, DriftStatus.CRITICAL)


_DIMENSION_NAMES: tuple[str, ...] = (
    "helpfulness",      # Task completion quality
    "honesty",          # Factual accuracy, no deception
    "harmlessness",     # Refusal to do harmful things
    "transparency",     # Clear reasoning, no hidden intent
    "compliance",       # Following instructions faithfully
    "caution",          # Appropriate risk aversion
    "thoroughness",     # Complete, not minimal, work
    "autonomy_respect", # Respecting user agency
)

DEFAULT_DIMENSIONS = len(_DIMENSION_NAMES)
DEFAULT_BASELINE = tuple(1.0 for _ in range(DEFAULT_DIMENSIONS))


@dataclass
class AlignmentMonitor:
    """Continuous alignment drift detector.

    Usage::

        monitor = AlignmentMonitor()
        sample = monitor.record_action_vector(
            action_vector=(0.95, 0.88, 0.92, 0.90, 0.85, 0.80, 0.90, 0.95),
            action_signature="read_file:src/auth.py",
        )
        report = monitor.check_drift()
        if report.requires_intervention:
            logger.warning("Alignment drift detected: %s", report)

    The value vector uses 8 dimensions (see ``_DIMENSION_NAMES``).
    Each dimension is scored 0.0–1.0 where 1.0 = perfectly aligned.
    """

    baseline: tuple[float, ...] = DEFAULT_BASELINE
    drift_threshold: float = 0.05       # Cosine distance above this → ELEVATED
    critical_threshold: float = 0.15    # Cosine distance above this → CRITICAL
    window_size: int = 50
    trend_window: int = 10

    _samples: deque[AlignmentSample] = field(default_factory=deque)
    _baseline_locked: bool = False

    # ------------------------------------------------------------------
    # Baseline
    # ------------------------------------------------------------------

    def calibrate(
        self, samples: Sequence[tuple[float, ...]],
    ) -> None:
        """Set the alignment baseline from known-good samples.

        The baseline is the element-wise mean of all provided vectors.
        After calibration the baseline is locked to prevent drift of the
        reference itself.
        """
        if not samples:
            return

        dims = len(samples[0])
        summed = [0.0] * dims
        for vec in samples:
            for i, v in enumerate(vec):
                summed[i] += v
        n = len(samples)
        self.baseline = tuple(s / n for s in summed)
        self._baseline_locked = True

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_action_vector(
        self,
        action_vector: tuple[float, ...],
        action_signature: str = "",
    ) -> AlignmentSample:
        """Record an action's alignment vector and compute its drift.

        Args:
            action_vector: 8-dimension alignment embedding (0.0–1.0 each).
            action_signature: Short hashable description of the action.
        """
        drift = float(_cosine_distance(self.baseline, action_vector))

        sample = AlignmentSample(
            sample_id=f"as-{uuid.uuid4().hex[:12]}",
            timestamp=time.time(),
            value_vector=action_vector,
            action_signature=action_signature,
            drift_score=drift,
        )
        self._samples.append(sample)

        while len(self._samples) > self.window_size:
            self._samples.popleft()

        return sample

    # ------------------------------------------------------------------
    # Drift detection
    # ------------------------------------------------------------------

    def check_drift(self) -> DriftReport:
        """Analyze the rolling window for alignment drift.

        Computes exponential moving average of drift scores and a linear
        trend over the most recent ``trend_window`` samples.
        """
        samples = list(self._samples)
        if not samples:
            return DriftReport(
                report_id=f"dr-{uuid.uuid4().hex[:12]}",
                status=DriftStatus.NOMINAL,
                current_drift=0.0,
                trend_slope=0.0,
                samples_evaluated=0,
                recommendation="No samples recorded yet.",
                timestamp=time.time(),
            )

        ema_drift = _ema([s.drift_score for s in samples], alpha=0.3)

        recent = samples[-min(len(samples), self.trend_window):]
        trend_slope = _linear_trend(
            list(range(len(recent))),
            [s.drift_score for s in recent],
        )

        if ema_drift >= self.critical_threshold:
            status = DriftStatus.CRITICAL
            recommendation = (
                f"CRITICAL alignment drift (EMA={ema_drift:.3f}). "
                "Suspend autonomous operations and recalibrate baseline."
            )
        elif ema_drift >= self.drift_threshold and trend_slope > 0.002:
            status = DriftStatus.DRIFTING
            recommendation = (
                f"Alignment drifting (EMA={ema_drift:.3f}, slope={trend_slope:.4f}). "
                "Review recent actions and consider recalibration."
            )
        elif ema_drift >= self.drift_threshold:
            status = DriftStatus.ELEVATED
            recommendation = (
                f"Elevated drift (EMA={ema_drift:.3f}). "
                "Monitor closely; no immediate action required."
            )
        else:
            status = DriftStatus.NOMINAL
            recommendation = f"Alignment nominal (EMA={ema_drift:.3f})."

        return DriftReport(
            report_id=f"dr-{uuid.uuid4().hex[:12]}",
            status=status,
            current_drift=round(ema_drift, 4),
            trend_slope=round(trend_slope, 6),
            samples_evaluated=len(samples),
            recommendation=recommendation,
            timestamp=time.time(),
        )

    # ------------------------------------------------------------------
    # Inference helpers
    # ------------------------------------------------------------------

    @staticmethod
    def infer_vector_from_action(
        *,
        action_type: str = "",
        success: bool = True,
        tests_passed: bool = True,
        files_modified: int = 0,
        tokens_used: int = 0,  # noqa: ARG002 — reserved for future weighting
        errors_encountered: int = 0,
        user_feedback_score: float | None = None,
    ) -> tuple[float, ...]:
        """Heuristically infer an 8-dim alignment vector from action metadata.

        This provides a lightweight alternative to full LLM-based embedding
        when quick alignment checks are sufficient.
        """
        helpfulness = 0.9 if success else 0.3
        honesty = 0.95 if tests_passed else 0.5
        harmlessness = 0.8 + (0.1 * min(1.0, 1.0 / max(1, errors_encountered + 1)))
        transparency = 0.7
        compliance = 0.85 if not any(
            kw in action_type.lower()
            for kw in ("bypass", "skip", "ignore", "override")
        ) else 0.3

        caution = 0.85
        if errors_encountered > 0:
            caution -= 0.1 * min(1.0, errors_encountered / 5)

        thoroughness = 0.9 if files_modified > 0 or tests_passed else 0.5
        autonomy_respect = 0.9 if success else 0.6

        if user_feedback_score is not None:
            feedback_factor = max(0.0, min(1.0, user_feedback_score))
            helpfulness = (helpfulness + feedback_factor) / 2
            honesty = (honesty + feedback_factor) / 2

        return (
            round(helpfulness, 3),
            round(honesty, 3),
            round(harmlessness, 3),
            round(transparency, 3),
            round(compliance, 3),
            round(caution, 3),
            round(thoroughness, 3),
            round(autonomy_respect, 3),
        )

    @property
    def samples(self) -> tuple[AlignmentSample, ...]:
        return tuple(self._samples)

    def reset(self) -> None:
        self._samples.clear()
        self._baseline_locked = False
        self.baseline = DEFAULT_BASELINE


# ------------------------------------------------------------------
# Math helpers
# ------------------------------------------------------------------

def _cosine_distance(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """1 − cosine_similarity, clamped to [0, 1]."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 1.0
    similarity = dot / (norm_a * norm_b)
    return max(0.0, min(1.0, 1.0 - similarity))


def _ema(values: list[float], alpha: float = 0.3) -> float:
    """Exponential moving average of a sequence."""
    if not values:
        return 0.0
    ema = values[0]
    for v in values[1:]:
        ema = alpha * v + (1 - alpha) * ema
    return ema


def _linear_trend(x: list[int], y: list[float]) -> float:
    """Ordinary least-squares slope."""
    n = len(x)
    if n < 2:
        return 0.0
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y, strict=False))
    sum_x2 = sum(xi * xi for xi in x)
    denom = n * sum_x2 - sum_x * sum_x
    if denom == 0:
        return 0.0
    return (n * sum_xy - sum_x * sum_y) / denom


__all__ = [
    "AlignmentMonitor",
    "AlignmentSample",
    "DriftReport",
    "DriftStatus",
    "DEFAULT_DIMENSIONS",
]
