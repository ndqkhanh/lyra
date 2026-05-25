"""Monitor distributional drift across traces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

from .exceptions import DriftIntegrationError


@dataclass(frozen=True)
class DriftConfig:
    """Configuration for drift detection."""

    window_size: int = 100
    drift_threshold: float = 0.1
    metrics: Tuple[str, ...] = ("latency", "token_count", "cost")


@dataclass(frozen=True)
class DriftMeasurement:
    """A single drift measurement for one metric."""

    metric: str
    reference_mean: float
    current_mean: float
    drift_magnitude: float
    is_drifting: bool
    ks_statistic: float


@dataclass(frozen=True)
class DriftReport:
    """Complete drift analysis report."""

    measurements: Tuple[DriftMeasurement, ...] = ()
    overall_drift_score: float = 0.0
    requires_attention: bool = False
    recommendations: Tuple[str, ...] = ()


class DriftIntegrator:
    """Monitors distributional drift for trace metrics using statistical tests."""

    def __init__(
        self,
        config: DriftConfig | None = None,
    ) -> None:
        self._config = config or DriftConfig()
        self._samples: Dict[str, List[float]] = {}
        self._baseline: Dict[str, float] = {}

    async def feed_sample(self, metric: str, value: float) -> None:
        """Feed a new sample for a given metric."""
        if metric not in self._config.metrics:
            raise DriftIntegrationError(
                f"Unknown metric '{metric}'. Configured metrics: {self._config.metrics}"
            )

        if metric not in self._samples:
            self._samples[metric] = []

        self._samples[metric].append(value)

        # Enforce window size
        if len(self._samples[metric]) > self._config.window_size * 2:
            self._samples[metric] = self._samples[metric][-self._config.window_size * 2 :]

        # Initialize baseline from first window
        if metric not in self._baseline and len(self._samples[metric]) >= self._config.window_size:
            window = self._samples[metric][: self._config.window_size]
            self._baseline[metric] = float(np.mean(window))

    async def check_drift(self) -> DriftReport:
        """Check for drift across all metrics and return a report."""
        measurements: List[DriftMeasurement] = []
        total_drift = 0.0

        for metric in self._config.metrics:
            samples = self._samples.get(metric, [])
            ref_mean = self._baseline.get(metric, 0.0)

            if len(samples) < self._config.window_size or ref_mean == 0.0:
                # Not enough data for meaningful comparison
                measurements.append(
                    DriftMeasurement(
                        metric=metric,
                        reference_mean=ref_mean,
                        current_mean=0.0,
                        drift_magnitude=0.0,
                        is_drifting=False,
                        ks_statistic=0.0,
                    )
                )
                continue

            # Current window (most recent samples)
            current_window = samples[-self._config.window_size :]
            current_mean = float(np.mean(current_window))

            # Compute drift magnitude using percentage change
            drift_magnitude = abs(current_mean - ref_mean) / max(abs(ref_mean), 1e-10)

            # Compute KS-like statistic using ECDF max difference
            ks_statistic = self._compute_ks_statistic(
                samples[: self._config.window_size],
                current_window,
            )

            is_drifting = drift_magnitude > self._config.drift_threshold or ks_statistic > 0.3

            measurements.append(
                DriftMeasurement(
                    metric=metric,
                    reference_mean=round(ref_mean, 4),
                    current_mean=round(current_mean, 4),
                    drift_magnitude=round(drift_magnitude, 4),
                    is_drifting=is_drifting,
                    ks_statistic=round(ks_statistic, 4),
                )
            )

            total_drift += drift_magnitude

        overall_drift_score = round(total_drift / max(len(self._config.metrics), 1), 4)
        requires_attention = any(m.is_drifting for m in measurements)
        recommendations = self._generate_recommendations(measurements)

        return DriftReport(
            measurements=tuple(measurements),
            overall_drift_score=overall_drift_score,
            requires_attention=requires_attention,
            recommendations=tuple(recommendations),
        )

    async def reset_baseline(self) -> None:
        """Reset all baselines to be recomputed from current data."""
        self._baseline = {}

    async def get_drift_history(self) -> Tuple[DriftMeasurement, ...]:
        """Get the most recent drift measurements."""
        report = await self.check_drift()
        return report.measurements

    @staticmethod
    def _compute_ks_statistic(
        reference: List[float],
        current: List[float],
    ) -> float:
        """Compute an approximate KS statistic using ECDF max difference."""
        if not reference or not current:
            return 0.0

        all_values = sorted(set(reference + current))
        max_diff = 0.0

        for x in all_values:
            ref_ecdf = sum(1 for v in reference if v <= x) / len(reference)
            cur_ecdf = sum(1 for v in current if v <= x) / len(current)
            diff = abs(ref_ecdf - cur_ecdf)
            if diff > max_diff:
                max_diff = diff

        return max_diff

    def _generate_recommendations(
        self,
        measurements: List[DriftMeasurement],
    ) -> List[str]:
        """Generate actionable recommendations based on drift measurements."""
        recommendations: List[str] = []

        drifting_metrics = [m for m in measurements if m.is_drifting]

        if not drifting_metrics:
            recommendations.append("No drift detected; continue normal monitoring.")
        else:
            for m in drifting_metrics:
                direction = "increased" if m.current_mean > m.reference_mean else "decreased"
                recommendations.append(
                    f"Metric '{m.metric}' has {direction} (drift: {m.drift_magnitude:.3f}). "
                    f"Consider investigating root cause."
                )

            if len(drifting_metrics) >= 2:
                recommendations.append(
                    "Multiple metrics drifting simultaneously. "
                    "Possible systemic change — consider resetting baseline."
                )

        return recommendations
