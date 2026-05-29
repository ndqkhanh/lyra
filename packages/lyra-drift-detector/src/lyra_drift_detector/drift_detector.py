"""Multi-signal drift detection engine.

Detects concept, distribution, performance, context, and reward drift across
agent execution signals using both statistical and threshold-based methods.

Supports:
- Statistical tests: Kolmogorov-Smirnov, KL divergence, Maximum Mean Discrepancy
- Threshold-based detection with configurable windows
- Real-time streaming and batch detection modes
- Multi-signal aggregation with ensemble scoring
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

import numpy as np

from .exceptions import InsufficientDataError, InvalidConfigurationError

logger = logging.getLogger(__name__)


# ── Enums and data classes ──────────────────────────────────────────────


class DriftType(Enum):
    """Categories of detectable drift."""

    PERFORMANCE = auto()  # Latency, error rate, throughput
    CONTEXT = auto()  # Topic shift, intent change
    DISTRIBUTION = auto()  # KS test, KL divergence, MMD
    REWARD = auto()  # RL reward signal changes
    CONCEPT = auto()  # Semantic shift over time


class DetectionMethod(Enum):
    """Statistical methods for drift detection."""

    KS_TEST = auto()
    KL_DIVERGENCE = auto()
    MAXIMUM_MEAN_DISCREPANCY = auto()
    THRESHOLD = auto()
    Z_SCORE = auto()
    CUSUM = auto()
    EWMA = auto()


class DriftSeverity(Enum):
    """Severity level for detected drift."""

    NONE = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass
class DriftSignal:
    """Result of a drift detection check on a single metric.

    Attributes:
        drift_type: Category of drift detected.
        metric: Name of the metric being monitored.
        score: Computed drift score (0.0 = no drift, higher = more drift).
        threshold: Configured threshold for this signal.
        is_drift: Whether drift was detected (score > threshold).
        severity: Computed severity level of the drift.
        method: Detection method used.
        timestamp: Unix timestamp of the check.
        details: Additional context (baseline values, current values, etc.).
    """

    drift_type: DriftType
    metric: str
    score: float
    threshold: float
    is_drift: bool
    severity: DriftSeverity = DriftSeverity.NONE
    method: DetectionMethod = DetectionMethod.THRESHOLD
    timestamp: float = field(default_factory=time.time)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DriftReport:
    """Aggregated report from multiple drift detectors.

    Attributes:
        timestamp: When the report was generated.
        signals: All individual drift signals.
        overall_score: Weighted aggregate drift score.
        drift_detected: Whether any signal exceeded its threshold.
        recommendation: Automated recommendation for handling drift.
    """

    timestamp: float
    signals: list[DriftSignal]
    overall_score: float
    drift_detected: bool
    recommendation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Statistical utilities ──────────────────────────────────────────────


def _ks_test(
    reference: np.ndarray, current: np.ndarray
) -> tuple[float, float]:
    """Two-sample Kolmogorov-Smirnov test.

    Args:
        reference: Baseline/reference data samples.
        current: Current data samples.

    Returns:
        Tuple of (KS statistic, approximate p-value).
    """
    if len(reference) == 0 or len(current) == 0:
        return 0.0, 1.0

    reference_sorted = np.sort(reference)
    current_sorted = np.sort(current)

    n1, n2 = len(reference_sorted), len(current_sorted)
    all_points = np.concatenate([reference_sorted, current_sorted])
    cdf1 = np.searchsorted(reference_sorted, all_points, side="right") / n1
    cdf2 = np.searchsorted(current_sorted, all_points, side="right") / n2

    ks_stat = np.max(np.abs(cdf1 - cdf2))

    # Approximate p-value using the Kolmogorov-Smirnov distribution
    en = np.sqrt(n1 * n2 / (n1 + n2))
    lambda_stat = en * ks_stat
    # Kolmogorov approximation
    p_value = 2.0 * np.sum(
        [(-1) ** (k - 1) * np.exp(-2.0 * k**2 * lambda_stat**2) for k in range(1, 101)]
    )
    p_value = min(max(p_value, 0.0), 1.0)

    return float(ks_stat), p_value


def _kl_divergence(p: np.ndarray, q: np.ndarray, epsilon: float = 1e-10) -> float:
    """Compute Kullback-Leibler divergence D_KL(P || Q).

    Args:
        p: Reference distribution (must sum to 1).
        q: Current distribution (must sum to 1).
        epsilon: Small constant to avoid log(0).

    Returns:
        KL divergence value (non-negative, 0 = identical).
    """
    p = np.asarray(p, dtype=np.float64) + epsilon
    q = np.asarray(q, dtype=np.float64) + epsilon
    p = p / np.sum(p)
    q = q / np.sum(q)
    return float(np.sum(p * np.log(p / q)))


def _mmd(
    x: np.ndarray,
    y: np.ndarray,
    kernel: str = "rbf",
    sigma: float | None = None,
) -> float:
    """Maximum Mean Discrepancy between two samples.

    Args:
        x: Reference samples.
        y: Current samples.
        kernel: Kernel type ('rbf' or 'linear').
        sigma: Bandwidth for RBF kernel. If None, uses median heuristic.

    Returns:
        MMD^2 value (0 = identical distributions).
    """
    x = np.asarray(x).reshape(-1, 1) if x.ndim == 1 else np.asarray(x)
    y = np.asarray(y).reshape(-1, 1) if y.ndim == 1 else np.asarray(y)

    if kernel == "linear":
        k_xx = np.mean(x @ x.T)
        k_yy = np.mean(y @ y.T)
        k_xy = np.mean(x @ y.T)
    else:
        if sigma is None:
            # Median heuristic for bandwidth
            n_samples = min(len(x), 100)
            pairwise_dists_list = []
            for i in range(n_samples):
                for j in range(i + 1, n_samples):
                    pairwise_dists_list.append(np.linalg.norm(x[i] - x[j]))
            if pairwise_dists_list:
                pairwise_dists = np.array(pairwise_dists_list)
                sigma = float(np.median(pairwise_dists))
            else:
                sigma = 1.0
            if sigma < 1e-10:
                sigma = 1.0

        gamma = 1.0 / (2.0 * sigma**2)

        def _rbf_kernel(a: np.ndarray, b: np.ndarray) -> float:
            aa = np.sum(a**2, axis=1).reshape(-1, 1)
            bb = np.sum(b**2, axis=1).reshape(1, -1)
            dists = aa + bb - 2.0 * (a @ b.T)
            return float(np.mean(np.exp(-gamma * np.maximum(dists, 0))))

        k_xx = _rbf_kernel(x, x)
        k_yy = _rbf_kernel(y, y)
        k_xy = _rbf_kernel(x, y)

    return max(0.0, k_xx + k_yy - 2.0 * k_xy)


def _compute_severity(score: float, threshold: float) -> DriftSeverity:
    """Map a drift score to a severity level.

    Args:
        score: The computed drift score.
        threshold: The configured threshold.

    Returns:
        Appropriate severity level.
    """
    if score <= threshold:
        return DriftSeverity.NONE
    ratio = score / max(threshold, 1e-10)
    if ratio < 1.5:
        return DriftSeverity.LOW
    elif ratio < 3.0:
        return DriftSeverity.MEDIUM
    elif ratio < 5.0:
        return DriftSeverity.HIGH
    else:
        return DriftSeverity.CRITICAL


# ── Drift Detectors ────────────────────────────────────────────────────


class BaseDriftDetector:
    """Abstract base for all drift detectors with common statistical utilities."""

    def __init__(
        self,
        window_size: int = 500,
        threshold: float = 0.15,
        min_samples: int = 30,
        detection_method: DetectionMethod = DetectionMethod.THRESHOLD,
    ) -> None:
        if window_size < 10:
            raise InvalidConfigurationError(
                self.__class__.__name__, "window_size must be >= 10"
            )
        if threshold <= 0:
            raise InvalidConfigurationError(
                self.__class__.__name__, "threshold must be positive"
            )

        self.window_size = window_size
        self.threshold = threshold
        self.min_samples = min_samples
        self.detection_method = detection_method
        self._baseline: np.ndarray | None = None
        self._drift_history: deque[DriftSignal] = deque(maxlen=1000)

    @property
    def has_baseline(self) -> bool:
        """Check if a baseline has been established."""
        return self._baseline is not None and len(self._baseline) >= self.min_samples

    @property
    def history(self) -> list[DriftSignal]:
        """Get the drift detection history."""
        return list(self._drift_history)

    def set_baseline(self, data: Sequence[float]) -> None:
        """Set or update the baseline reference distribution."""
        self._baseline = np.asarray(data, dtype=np.float64)

    def _ensure_baseline(self) -> None:
        """Raise if baseline is not ready."""
        if not self.has_baseline:
            raise InsufficientDataError(
                "baseline", self.min_samples, len(self._baseline) if self._baseline is not None else 0
            )

    def _record_signal(self, signal: DriftSignal) -> None:
        """Record a drift signal in the history."""
        self._drift_history.append(signal)
        if signal.is_drift:
            logger.info(
                "Drift detected: type=%s metric=%s score=%.4f threshold=%.4f severity=%s",
                signal.drift_type.name,
                signal.metric,
                signal.score,
                signal.threshold,
                signal.severity.name,
            )


class PerformanceDriftDetector(BaseDriftDetector):
    """Detects performance drift: latency, error rate, throughput, token usage.

    Monitors key performance metrics over rolling windows and compares against
    historical baselines using statistical tests and threshold-based methods.
    """

    def __init__(
        self,
        window_size: int = 500,
        threshold: float = 0.15,
        min_samples: int = 30,
        detection_method: DetectionMethod = DetectionMethod.EWMA,
        metrics: list[str] | None = None,
    ) -> None:
        super().__init__(window_size, threshold, min_samples, detection_method)
        self.metrics = metrics or ["latency_ms", "error_rate", "throughput", "tokens_per_second"]
        self._metric_buffers: dict[str, deque[float]] = {
            m: deque(maxlen=window_size) for m in self.metrics
        }
        self._ewma: dict[str, float] = dict.fromkeys(self.metrics, 0.0)
        self._ewma_alpha: float = 0.1  # Smoothing factor
        self._baselines: dict[str, np.ndarray] = {}

    def record(self, metric: str, value: float) -> None:
        """Record a performance metric observation.

        Args:
            metric: Name of the metric (e.g., 'latency_ms', 'error_rate').
            value: Observed value.
        """
        if metric not in self._metric_buffers:
            self._metric_buffers[metric] = deque(maxlen=self.window_size)
            self._ewma[metric] = 0.0
        self._metric_buffers[metric].append(value)
        # Update EWMA
        self._ewma[metric] = (
            self._ewma_alpha * value + (1 - self._ewma_alpha) * self._ewma[metric]
        )

    def record_batch(self, observations: dict[str, float]) -> None:
        """Record multiple metric observations at once."""
        for metric, value in observations.items():
            self.record(metric, value)

    def set_baseline_for_metric(self, metric: str, data: Sequence[float]) -> None:
        """Set baseline data for a specific metric."""
        self._baselines[metric] = np.asarray(data, dtype=np.float64)

    def check_drift(self, metric: str | None = None) -> DriftSignal | list[DriftSignal]:
        """Check for performance drift on one or all metrics.

        Args:
            metric: Specific metric to check, or None to check all.

        Returns:
            Single DriftSignal (if metric specified) or list of DriftSignals.
        """
        if metric is not None:
            return self._check_single_metric(metric)
        return [self._check_single_metric(m) for m in self.metrics]

    def _check_single_metric(self, metric: str) -> DriftSignal:
        """Check a single metric for drift."""
        buffer = self._metric_buffers.get(metric, deque())
        values = list(buffer)

        if len(values) < self.min_samples:
            return DriftSignal(
                drift_type=DriftType.PERFORMANCE,
                metric=metric,
                score=0.0,
                threshold=self.threshold,
                is_drift=False,
                method=self.detection_method,
                details={"reason": "insufficient_data", "samples": len(values)},
            )

        current = np.array(values[-self.min_samples:], dtype=np.float64)

        score: float
        if self.detection_method == DetectionMethod.EWMA:
            # Use EWMA deviation
            ewma_val = self._ewma.get(metric, float(np.mean(current)))
            score = abs(ewma_val - float(np.median(current))) / max(float(np.std(current)), 1e-10)

        elif self.detection_method == DetectionMethod.Z_SCORE:
            baseline = self._baselines.get(metric)
            if baseline is not None and len(baseline) >= self.min_samples:
                baseline_mean = float(np.mean(baseline))
                baseline_std = float(np.std(baseline))
                current_mean = float(np.mean(current))
                score = abs(current_mean - baseline_mean) / max(baseline_std, 1e-10)
            else:
                score = abs(float(np.mean(current)) - float(np.median(current))) / max(float(np.std(current)), 1e-10)

        elif self.detection_method == DetectionMethod.CUSUM:
            score = self._cusum_check(current)

        elif self.detection_method == DetectionMethod.KS_TEST:
            baseline = self._baselines.get(metric)
            if baseline is not None and len(baseline) >= self.min_samples:
                ks_stat, _ = _ks_test(baseline[:1000], current)
                score = ks_stat
            else:
                score = 0.0

        else:
            # Default: simple threshold
            score = abs(float(np.mean(current)) - float(np.median(current))) / max(float(np.std(current)), 1e-10)

        is_drift = score > self.threshold
        signal = DriftSignal(
            drift_type=DriftType.PERFORMANCE,
            metric=metric,
            score=float(score),
            threshold=self.threshold,
            is_drift=is_drift,
            severity=_compute_severity(float(score), self.threshold),
            method=self.detection_method,
            details={
                "mean": float(np.mean(current)),
                "median": float(np.median(current)),
                "std": float(np.std(current)),
                "samples": len(values),
                "ewma": self._ewma.get(metric, 0.0),
            },
        )
        self._record_signal(signal)
        return signal

    def _cusum_check(self, current: np.ndarray) -> float:
        """Cumulative Sum (CUSUM) change detection."""
        baseline = self._baselines.get("_cusum_ref")
        if baseline is None:
            self._baselines["_cusum_ref"] = current
            return 0.0

        ref_mean = float(np.mean(baseline))
        ref_std = float(np.std(baseline)) + 1e-10

        standardized = (current - ref_mean) / ref_std
        drift = 0.5  # Allowable shift magnitude
        cusum_pos = 0.0
        cusum_neg = 0.0
        max_cusum = 0.0

        for val in standardized:
            cusum_pos = max(0.0, cusum_pos + val - drift)
            cusum_neg = max(0.0, cusum_neg - val - drift)
            max_cusum = max(max_cusum, cusum_pos, cusum_neg)

        return max_cusum / len(standardized)


class ContextDriftDetector(BaseDriftDetector):
    """Detects context drift: topic shifts, intent changes, preference evolution.

    Tracks the distribution of context features over time and detects when the
    agent's operational context has substantially changed.
    """

    def __init__(
        self,
        threshold: float = 0.2,
        min_samples: int = 20,
        detection_method: DetectionMethod = DetectionMethod.KL_DIVERGENCE,
    ) -> None:
        super().__init__(window_size=1000, threshold=threshold, min_samples=min_samples,
                         detection_method=detection_method)
        self._baseline_profile: dict[str, float] = {}
        self._current_profile: dict[str, float] = {}
        self._profile_history: deque[dict[str, float]] = deque(maxlen=100)

    def set_baseline(self, profile: dict[str, float]) -> None:
        """Set the baseline context profile (e.g., codebase composition, tool usage)."""
        self._baseline_profile = dict(profile)
        self._baseline = np.array(list(profile.values()), dtype=np.float64)

    def update(self, profile: dict[str, float]) -> None:
        """Update the current context profile.

        Args:
            profile: Current context features with their values.
        """
        self._current_profile = dict(profile)
        self._profile_history.append(profile)

    def check_drift(self) -> DriftSignal:
        """Check for context drift between baseline and current profiles.

        Returns:
            DriftSignal with drift score and details.
        """
        if not self._baseline_profile or not self._current_profile:
            return DriftSignal(
                drift_type=DriftType.CONTEXT,
                metric="context_shift",
                score=0.0,
                threshold=self.threshold,
                is_drift=False,
                method=self.detection_method,
                details={"reason": "no_baseline_or_current"},
            )

        if self.detection_method == DetectionMethod.KL_DIVERGENCE:
            score = self._kl_context_check()
        elif self.detection_method == DetectionMethod.THRESHOLD:
            score = self._threshold_context_check()
        else:
            score = self._threshold_context_check()

        is_drift = score > self.threshold
        signal = DriftSignal(
            drift_type=DriftType.CONTEXT,
            metric="context_shift",
            score=score,
            threshold=self.threshold,
            is_drift=is_drift,
            severity=_compute_severity(score, self.threshold),
            method=self.detection_method,
            details={
                "baseline_keys": len(self._baseline_profile),
                "current_keys": len(self._current_profile),
                "new_keys": sorted(set(self._current_profile) - set(self._baseline_profile)),
                "removed_keys": sorted(set(self._baseline_profile) - set(self._current_profile)),
            },
        )
        self._record_signal(signal)
        return signal

    def _kl_context_check(self) -> float:
        """Compute symmetrized KL divergence between profiles."""
        all_keys = sorted(set(self._baseline_profile) | set(self._current_profile))
        if not all_keys:
            return 0.0

        p = np.array([self._baseline_profile.get(k, 0.0) + 1e-10 for k in all_keys])
        q = np.array([self._current_profile.get(k, 0.0) + 1e-10 for k in all_keys])

        p = p / np.sum(p)
        q = q / np.sum(q)

        return 0.5 * (_kl_divergence(p, q) + _kl_divergence(q, p))

    def _threshold_context_check(self) -> float:
        """Simple relative-change-based context drift check."""
        scores: list[float] = []
        for key in set(self._baseline_profile) | set(self._current_profile):
            b = self._baseline_profile.get(key, 0.0)
            c = self._current_profile.get(key, 0.0)
            if abs(b) > 1e-6:
                scores.append(abs(c - b) / abs(b))
            elif abs(c) > 1e-6:
                scores.append(1.0)  # New key appeared
        return float(np.mean(scores)) if scores else 0.0

    def get_recent_profiles(self, n: int = 10) -> list[dict[str, float]]:
        """Get the n most recent context profiles."""
        return list(self._profile_history)[-n:]


class DistributionDriftDetector(BaseDriftDetector):
    """Detects distribution drift using KS test, KL divergence, and MMD.

    Monitors the distribution of task types, complexities, and feature vectors
    over time, detecting when incoming data comes from a different distribution.
    """

    def __init__(
        self,
        threshold: float = 0.2,
        window_size: int = 1000,
        min_samples: int = 30,
        detection_method: DetectionMethod = DetectionMethod.MAXIMUM_MEAN_DISCREPANCY,
    ) -> None:
        super().__init__(window_size, threshold, min_samples, detection_method)
        self._reference_samples: deque[float] = deque(maxlen=window_size)
        self._current_samples: deque[float] = deque(maxlen=window_size)
        self._task_type_counts: dict[str, int] = {}
        self._feature_history: deque[dict[str, float]] = deque(maxlen=window_size)

    def set_reference(self, samples: Sequence[float]) -> None:
        """Set reference distribution samples."""
        self._reference_samples = deque(samples[-self.window_size:], maxlen=self.window_size)
        self._baseline = np.array(samples, dtype=np.float64)

    def record(self, value: float, task_type: str = "", features: dict[str, float] | None = None) -> None:
        """Record a new sample for distribution tracking.

        Args:
            value: The observation value.
            task_type: Optional task type label.
            features: Optional feature vector for the observation.
        """
        self._current_samples.append(value)
        self._task_type_counts[task_type] = self._task_type_counts.get(task_type, 0) + 1
        if features:
            self._feature_history.append(features)

    def check_drift(self) -> DriftSignal:
        """Check for distribution drift.

        Returns:
            DriftSignal with the drift assessment.
        """
        if len(self._current_samples) < self.min_samples:
            return DriftSignal(
                drift_type=DriftType.DISTRIBUTION,
                metric="distribution_shift",
                score=0.0,
                threshold=self.threshold,
                is_drift=False,
                method=self.detection_method,
                details={"reason": "insufficient_data", "samples": len(self._current_samples)},
            )

        if len(self._reference_samples) < self.min_samples:
            # Use the first half of current samples as reference
            half = len(self._current_samples) // 2
            ref = list(self._current_samples)[:half]
            cur = list(self._current_samples)[half:]
        else:
            ref = list(self._reference_samples)
            cur = list(self._current_samples)[-self.min_samples:]

        ref_arr = np.array(ref, dtype=np.float64)
        cur_arr = np.array(cur, dtype=np.float64)

        score: float
        details: dict[str, Any] = {}

        if self.detection_method == DetectionMethod.KS_TEST:
            ks_stat, p_value = _ks_test(ref_arr, cur_arr)
            score = ks_stat
            details["ks_statistic"] = ks_stat
            details["p_value"] = p_value

        elif self.detection_method == DetectionMethod.KL_DIVERGENCE:
            # Discretize into histograms
            combined = np.concatenate([ref_arr, cur_arr])
            bins = min(50, len(combined) // 10)
            hist_range = (float(np.min(combined)), float(np.max(combined)))
            p_hist, _ = np.histogram(ref_arr, bins=bins, range=hist_range)
            q_hist, _ = np.histogram(cur_arr, bins=bins, range=hist_range)
            score = _kl_divergence(p_hist, q_hist)
            details["method"] = "KL_divergence"

        elif self.detection_method == DetectionMethod.MAXIMUM_MEAN_DISCREPANCY:
            mmd_val = _mmd(ref_arr[:500], cur_arr[:500], kernel="rbf")
            # Normalize MMD to [0, 1] range approximately
            score = min(1.0, mmd_val / max(float(np.std(ref_arr)), 1e-10))
            details["mmd_squared"] = mmd_val

        else:
            # Simple mean/std comparison
            ref_mean, ref_std = float(np.mean(ref_arr)), float(np.std(ref_arr))
            cur_mean, cur_std = float(np.mean(cur_arr)), float(np.std(cur_arr))
            mean_shift = abs(cur_mean - ref_mean) / max(ref_std, 1e-10)
            std_ratio = abs(cur_std - ref_std) / max(ref_std, 1e-10)
            score = 0.5 * (mean_shift + std_ratio)
            details["reference_mean"] = ref_mean
            details["current_mean"] = cur_mean

        is_drift = score > self.threshold
        details["reference_samples"] = len(ref)
        details["current_samples"] = len(cur)

        signal = DriftSignal(
            drift_type=DriftType.DISTRIBUTION,
            metric="distribution_shift",
            score=float(score),
            threshold=self.threshold,
            is_drift=is_drift,
            severity=_compute_severity(float(score), self.threshold),
            method=self.detection_method,
            details=details,
        )
        self._record_signal(signal)
        return signal

    @property
    def task_distribution(self) -> dict[str, float]:
        """Get the current normalized task type distribution."""
        total = sum(self._task_type_counts.values())
        if total == 0:
            return {}
        return {k: v / total for k, v in self._task_type_counts.items()}


class RewardDriftDetector(BaseDriftDetector):
    """Detects reward drift: changes in reinforcement learning reward signals.

    Monitors reward statistics over time and detects when the reward distribution
    has shifted significantly, which may indicate concept drift in the learned policy.
    """

    def __init__(
        self,
        window_size: int = 500,
        threshold: float = 0.2,
        min_samples: int = 20,
        detection_method: DetectionMethod = DetectionMethod.Z_SCORE,
    ) -> None:
        super().__init__(window_size, threshold, min_samples, detection_method)
        self._rewards: deque[float] = deque(maxlen=window_size)
        self._context_tags: deque[str] = deque(maxlen=window_size)
        self._reward_by_context: dict[str, deque[float]] = {}

    def record(self, reward: float, context_tag: str = "") -> None:
        """Record a reward observation.

        Args:
            reward: The reward value received.
            context_tag: Optional tag identifying the context (e.g., task type).
        """
        self._rewards.append(reward)
        self._context_tags.append(context_tag)
        if context_tag:
            if context_tag not in self._reward_by_context:
                self._reward_by_context[context_tag] = deque(maxlen=self.window_size)
            self._reward_by_context[context_tag].append(reward)

    def check_drift(self) -> DriftSignal:
        """Check for reward signal drift.

        Returns:
            DriftSignal with the drift assessment.
        """
        if len(self._rewards) < self.min_samples:
            return DriftSignal(
                drift_type=DriftType.REWARD,
                metric="reward_signal",
                score=0.0,
                threshold=self.threshold,
                is_drift=False,
                method=self.detection_method,
                details={"reason": "insufficient_data", "samples": len(self._rewards)},
            )

        rewards_arr = np.array(self._rewards, dtype=np.float64)
        overall_mean = float(np.mean(rewards_arr))
        overall_std = float(np.std(rewards_arr))

        if overall_std < 1e-9:
            return DriftSignal(
                drift_type=DriftType.REWARD,
                metric="reward_signal",
                score=0.0,
                threshold=self.threshold,
                is_drift=False,
                method=self.detection_method,
                details={"reason": "zero_variance"},
            )

        # Compare recent window to overall history
        recent_n = min(self.min_samples, len(self._rewards))
        recent = np.array(list(self._rewards)[-recent_n:], dtype=np.float64)
        recent_mean = float(np.mean(recent))
        recent_std = float(np.std(recent))

        if self.detection_method == DetectionMethod.KS_TEST:
            baseline = rewards_arr[:-recent_n] if len(rewards_arr) > recent_n else rewards_arr[:len(rewards_arr)//2]
            ks_stat, _ = _ks_test(baseline, recent)
            score = ks_stat
        elif self.detection_method == DetectionMethod.Z_SCORE:
            score = abs(recent_mean - overall_mean) / max(overall_std, 1e-10)
        elif self.detection_method == DetectionMethod.EWMA:
            # Check if recent rewards follow the same trend
            expected_next = 2 * overall_mean - recent_mean  # Simple trend projection
            score = abs(recent_mean - expected_next) / max(overall_std, 1e-10)
        else:
            score = abs(recent_mean - overall_mean) / max(overall_std, 1e-10)

        details: dict[str, Any] = {
            "overall_mean": overall_mean,
            "recent_mean": recent_mean,
            "overall_std": overall_std,
            "recent_std": recent_std,
            "total_rewards": len(self._rewards),
        }

        # Per-context drift analysis
        if self._reward_by_context:
            context_drifts = {}
            for ctx, ctx_rewards in self._reward_by_context.items():
                if len(ctx_rewards) >= 10:
                    ctx_arr = np.array(ctx_rewards, dtype=np.float64)
                    ctx_mean = float(np.mean(ctx_arr))
                    context_drifts[ctx] = abs(ctx_mean - overall_mean) / max(overall_std, 1e-10)
            details["per_context_drift"] = context_drifts

        is_drift = float(score) > self.threshold
        signal = DriftSignal(
            drift_type=DriftType.REWARD,
            metric="reward_signal",
            score=float(score),
            threshold=self.threshold,
            is_drift=is_drift,
            severity=_compute_severity(float(score), self.threshold),
            method=self.detection_method,
            details=details,
        )
        self._record_signal(signal)
        return signal

    @property
    def reward_stats(self) -> dict[str, float]:
        """Get summary statistics of tracked rewards."""
        if not self._rewards:
            return {}
        arr = np.array(self._rewards, dtype=np.float64)
        return {
            "count": len(arr),
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "p50": float(np.percentile(arr, 50)),
            "p95": float(np.percentile(arr, 95)),
        }


class ConceptDriftDetector(BaseDriftDetector):
    """Detects concept drift: semantic shifts in what tasks or labels mean over time.

    Tracks the relationship between inputs and expected outputs, detecting when
    the underlying concept has changed even if the distribution looks stable.
    """

    def __init__(
        self,
        threshold: float = 0.2,
        window_size: int = 500,
        min_samples: int = 30,
        detection_method: DetectionMethod = DetectionMethod.EWMA,
    ) -> None:
        super().__init__(window_size, threshold, min_samples, detection_method)
        self._concept_history: deque[dict[str, Any]] = deque(maxlen=window_size)
        self._semantic_anchors: dict[str, np.ndarray] = {}
        self._prediction_errors: deque[float] = deque(maxlen=window_size)

    def record_instance(
        self,
        concept_id: str,
        features: dict[str, float],
        label: str,
        embedding: Sequence[float] | None = None,
    ) -> None:
        """Record a concept instance for tracking.

        Args:
            concept_id: Identifier for the concept being tracked.
            features: Feature vector for the instance.
            label: Ground truth label or expected output.
            embedding: Optional semantic embedding vector.
        """
        instance = {
            "concept_id": concept_id,
            "features": features,
            "label": label,
            "timestamp": time.time(),
        }
        if embedding is not None:
            instance["embedding"] = np.array(embedding, dtype=np.float64)
            if concept_id not in self._semantic_anchors:
                self._semantic_anchors[concept_id] = np.array(embedding, dtype=np.float64)
        self._concept_history.append(instance)

    def record_prediction_error(self, error: float) -> None:
        """Record a prediction error for concept drift tracking."""
        self._prediction_errors.append(error)

    def check_drift(self, concept_id: str | None = None) -> DriftSignal:
        """Check for concept drift.

        Args:
            concept_id: Optional specific concept to check, or None for overall.

        Returns:
            DriftSignal with the drift assessment.
        """
        recent_errors = list(self._prediction_errors)
        if len(recent_errors) < self.min_samples:
            return DriftSignal(
                drift_type=DriftType.CONCEPT,
                metric=f"concept_drift_{concept_id or 'overall'}",
                score=0.0,
                threshold=self.threshold,
                is_drift=False,
                method=self.detection_method,
                details={"reason": "insufficient_data", "samples": len(recent_errors)},
            )

        errors_arr = np.array(recent_errors, dtype=np.float64)
        half = len(errors_arr) // 2
        old_errors = errors_arr[:half]
        new_errors = errors_arr[half:]

        old_mean = float(np.mean(old_errors))
        new_mean = float(np.mean(new_errors))
        old_std = float(np.std(old_errors))
        new_std = float(np.std(new_errors))

        # Concept drift manifests as increasing prediction error
        error_increase = (new_mean - old_mean) / max(old_std, 1e-10)
        # Also check error variance increase
        variance_increase = (new_std - old_std) / max(old_std, 1e-10)

        if self.detection_method == DetectionMethod.EWMA:
            # Use an EWMA to track the trend
            if not hasattr(self, "_ewma_error"):
                self._ewma_error = float(np.mean(old_errors))
            alpha = 0.1
            self._ewma_error = alpha * new_mean + (1 - alpha) * self._ewma_error
            score = abs(new_mean - self._ewma_error) / max(old_std, 1e-10)
        else:
            score = 0.6 * max(0, error_increase) + 0.4 * max(0, variance_increase)

        # Semantic drift via embedding shift
        if concept_id and concept_id in self._semantic_anchors:
            recent_instances = [
                i for i in list(self._concept_history)[-self.min_samples:]
                if i["concept_id"] == concept_id and "embedding" in i
            ]
            if recent_instances:
                anchor = self._semantic_anchors[concept_id]
                recent_embeddings = np.array([i["embedding"] for i in recent_instances])
                semantic_shift = float(np.mean(np.linalg.norm(recent_embeddings - anchor, axis=1)))
                score = 0.5 * float(score) + 0.5 * min(1.0, semantic_shift)

        is_drift = float(score) > self.threshold
        signal = DriftSignal(
            drift_type=DriftType.CONCEPT,
            metric=f"concept_drift_{concept_id or 'overall'}",
            score=float(score),
            threshold=self.threshold,
            is_drift=is_drift,
            severity=_compute_severity(float(score), self.threshold),
            method=self.detection_method,
            details={
                "old_error_mean": old_mean,
                "new_error_mean": new_mean,
                "error_increase": error_increase,
                "variance_increase": variance_increase,
                "total_predictions": len(recent_errors),
            },
        )
        self._record_signal(signal)
        return signal


# ── Orchestrator ───────────────────────────────────────────────────────


class DriftOrchestrator:
    """Coordinates all drift detectors and produces aggregated drift reports.

    The orchestrator manages multiple specialized detectors, collects their
    signals, computes weighted ensemble scores, and provides a unified
    interface for drift monitoring and adaptation triggering.
    """

    def __init__(
        self,
        global_threshold: float = 0.15,
        aggregation: str = "weighted_max",
        detector_weights: dict[DriftType, float] | None = None,
    ) -> None:
        """Initialize the drift orchestrator.

        Args:
            global_threshold: Threshold for overall drift detection.
            aggregation: Aggregation method ('weighted_max', 'weighted_mean', 'any').
            detector_weights: Per-type weights for aggregation. Default weights if None.
        """
        self.global_threshold = global_threshold
        self.aggregation = aggregation
        self.detector_weights = detector_weights or {
            DriftType.PERFORMANCE: 1.0,
            DriftType.CONTEXT: 0.8,
            DriftType.DISTRIBUTION: 0.9,
            DriftType.REWARD: 1.0,
            DriftType.CONCEPT: 1.2,
        }

        # Initialize all detectors
        self.performance = PerformanceDriftDetector()
        self.context = ContextDriftDetector()
        self.distribution = DistributionDriftDetector()
        self.reward = RewardDriftDetector()
        self.concept = ConceptDriftDetector()

        self._reports: deque[DriftReport] = deque(maxlen=100)
        self._adaptation_enabled: bool = True

    async def check_all(self) -> list[DriftSignal]:
        """Run all detectors and collect signals.

        Returns:
            List of all drift signals from all detectors.
        """
        # Run checks concurrently
        async def _safe_check(
            detector: Any, method_name: str = "check_drift"
        ) -> list[DriftSignal]:
            try:
                result = getattr(detector, method_name)()
                loop = asyncio.get_running_loop()
                if asyncio.iscoroutine(result):
                    result = await result
                if isinstance(result, list):
                    return result
                return [result]
            except Exception as exc:
                logger.error("Drift check failed for %s: %s", detector.__class__.__name__, exc)
                return []

        tasks = [
            _safe_check(self.performance),
            _safe_check(self.context),
            _safe_check(self.distribution),
            _safe_check(self.reward),
            _safe_check(self.concept),
        ]
        results = await asyncio.gather(*tasks)

        all_signals: list[DriftSignal] = []
        for signal_list in results:
            all_signals.extend(signal_list)

        # Generate report
        self._generate_report(all_signals)

        return all_signals

    def check_all_sync(self) -> list[DriftSignal]:
        """Synchronous version of check_all."""
        all_signals: list[DriftSignal] = []
        detectors = [
            ("performance", self.performance),
            ("context", self.context),
            ("distribution", self.distribution),
            ("reward", self.reward),
            ("concept", self.concept),
        ]
        for name, detector in detectors:
            try:
                result = detector.check_drift()
                if isinstance(result, list):
                    all_signals.extend(result)
                else:
                    all_signals.append(result)
            except Exception as exc:
                logger.error("Drift check failed for %s: %s", name, exc)

        self._generate_report(all_signals)
        return all_signals

    def _generate_report(self, signals: list[DriftSignal]) -> None:
        """Generate a DriftReport from collected signals."""
        if not signals:
            return

        # Compute weighted aggregate score
        weighted_scores = []
        for s in signals:
            weight = self.detector_weights.get(s.drift_type, 1.0)
            weighted_scores.append(s.score * weight)

        if self.aggregation == "weighted_mean":
            overall = float(np.mean(weighted_scores)) if weighted_scores else 0.0
        elif self.aggregation == "any":
            overall = float(np.max(weighted_scores)) if weighted_scores else 0.0
        else:  # weighted_max
            overall = float(np.max(weighted_scores)) if weighted_scores else 0.0

        drift_detected = any(s.is_drift for s in signals)
        drifting_types = [s.drift_type.name for s in signals if s.is_drift]

        recommendation = "no_action"
        if drift_detected:
            if DriftType.CONCEPT.name in drifting_types:
                recommendation = "retrain_model"
            elif DriftType.PERFORMANCE.name in drifting_types:
                recommendation = "scale_resources"
            elif DriftType.REWARD.name in drifting_types:
                recommendation = "review_policy"
            elif DriftType.DISTRIBUTION.name in drifting_types:
                recommendation = "recalibrate_thresholds"
            else:
                recommendation = "investigate"

        report = DriftReport(
            timestamp=time.time(),
            signals=signals,
            overall_score=overall,
            drift_detected=drift_detected,
            recommendation=recommendation,
            metadata={
                "drifting_types": drifting_types,
                "signal_count": len(signals),
                "aggregation": self.aggregation,
            },
        )
        self._reports.append(report)

    @property
    def adaptation_needed(self) -> bool:
        """Check if adaptation is needed based on current signals."""
        signals = self.check_all_sync()
        return any(s.is_drift for s in signals) and self._adaptation_enabled

    @property
    def summary(self) -> dict[str, Any]:
        """Get a human-readable summary of the current drift state."""
        signals = self.check_all_sync()
        by_type: dict[str, list[dict[str, Any]]] = {}
        for s in signals:
            key = s.drift_type.name
            if key not in by_type:
                by_type[key] = []
            by_type[key].append({
                "metric": s.metric,
                "score": s.score,
                "threshold": s.threshold,
                "is_drift": s.is_drift,
                "severity": s.severity.name,
            })

        return {
            "adaptation_needed": any(s.is_drift for s in signals),
            "drift_count": sum(1 for s in signals if s.is_drift),
            "total_signals": len(signals),
            "by_type": by_type,
            "latest_report": {
                "overall_score": self._reports[-1].overall_score,
                "recommendation": self._reports[-1].recommendation,
            } if self._reports else None,
        }

    @property
    def latest_report(self) -> DriftReport | None:
        """Get the most recent drift report."""
        return self._reports[-1] if self._reports else None

    @property
    def reports(self) -> list[DriftReport]:
        """Get all historical drift reports."""
        return list(self._reports)

    def disable_adaptation(self) -> None:
        """Disable automatic adaptation triggering."""
        self._adaptation_enabled = False

    def enable_adaptation(self) -> None:
        """Enable automatic adaptation triggering."""
        self._adaptation_enabled = True

    def reset(self) -> None:
        """Reset all detectors to initial state."""
        self.performance = PerformanceDriftDetector()
        self.context = ContextDriftDetector()
        self.distribution = DistributionDriftDetector()
        self.reward = RewardDriftDetector()
        self.concept = ConceptDriftDetector()
        self._reports.clear()
