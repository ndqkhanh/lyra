"""Individual signal monitors with configurable windows and thresholds.

Each monitor tracks a specific kind of agent behavior signal, maintains
historical baselines, and supports real-time streaming detection.
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np

from .drift_detector import (
    DetectionMethod,
    DriftSignal,
    DriftType,
    _compute_severity,
)
from .exceptions import InsufficientDataError, MonitorNotInitializedError

logger = logging.getLogger(__name__)


# ── Protocols and Types ─────────────────────────────────────────────────


class SignalCallback(Protocol):
    """Protocol for async signal callbacks."""

    async def __call__(self, signal: DriftSignal) -> None: ...


@dataclass
class MonitorConfig:
    """Configuration for a signal monitor.

    Attributes:
        name: Human-readable monitor name.
        window_size: Number of observations to retain.
        threshold: Drift score threshold.
        min_samples: Minimum observations before checking.
        check_interval_seconds: How often to run automated checks (0 = manual).
        enabled: Whether this monitor is active.
        detection_method: Statistical method for drift detection.
    """

    name: str
    window_size: int = 500
    threshold: float = 0.15
    min_samples: int = 30
    check_interval_seconds: float = 0.0
    enabled: bool = True
    detection_method: DetectionMethod = DetectionMethod.THRESHOLD


@dataclass
class MonitorState:
    """Runtime state of a monitor.

    Attributes:
        initialized: Whether baseline has been set.
        observation_count: Total observations recorded.
        last_check_time: Unix timestamp of last drift check.
        drift_count: Number of drift events detected.
        last_signal: Most recent drift signal.
    """

    initialized: bool = False
    observation_count: int = 0
    last_check_time: float = field(default_factory=time.time)
    drift_count: int = 0
    last_signal: DriftSignal | None = None


# ── Base Monitor ───────────────────────────────────────────────────────


class BaseMonitor(ABC):
    """Abstract base for all signal monitors.

    Provides common functionality: sliding windows, baseline management,
    streaming check triggers, and callback registration.
    """

    def __init__(self, config: MonitorConfig) -> None:
        self.config = config
        self.state = MonitorState()
        self._callbacks: list[SignalCallback] = []
        self._data: deque[float] = deque(maxlen=config.window_size)
        self._timestamps: deque[float] = deque(maxlen=config.window_size)
        self._baseline_data: np.ndarray | None = None
        self._running: bool = False
        self._check_task: asyncio.Task[None] | None = None

    @property
    def name(self) -> str:
        """Monitor name."""
        return self.config.name

    @property
    @abstractmethod
    def drift_type(self) -> DriftType:
        """Override in subclasses."""

    def register_callback(self, callback: SignalCallback) -> None:
        """Register an async callback for drift signals."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: SignalCallback) -> None:
        """Remove a registered callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def _notify_callbacks(self, signal: DriftSignal) -> None:
        """Notify all registered callbacks of a drift signal."""
        for cb in self._callbacks:
            try:
                await cb(signal)
            except Exception as exc:
                logger.error("Callback %s failed: %s", cb, exc)

    def observe(self, value: float, timestamp: float | None = None) -> None:
        """Record an observation.

        Args:
            value: The observed value.
            timestamp: Optional timestamp (defaults to now).
        """
        if not self.config.enabled:
            return
        self._data.append(value)
        self._timestamps.append(timestamp or time.time())
        self.state.observation_count += 1

    def set_baseline(self, data: Sequence[float]) -> None:
        """Set the baseline/reference data for comparison.

        Args:
            data: Historical data used as the baseline distribution.
        """
        self._baseline_data = np.array(data, dtype=np.float64)
        self.state.initialized = True
        logger.info("Monitor '%s' baseline set with %d samples", self.name, len(data))

    def _ensure_ready(self) -> None:
        """Check that the monitor is initialized and has enough data."""
        if not self.state.initialized:
            raise MonitorNotInitializedError(self.name)
        if len(self._data) < self.config.min_samples:
            raise InsufficientDataError(self.name, self.config.min_samples, len(self._data))

    @abstractmethod
    def compute_drift_score(self) -> float:
        """Compute the raw drift score.

        Returns:
            Drift score in [0, inf).
        """

    async def check(self) -> DriftSignal:
        """Perform a drift check and produce a signal.

        Returns:
            DriftSignal with the check result.
        """
        if not self.state.initialized:
            return DriftSignal(
                drift_type=self.drift_type,
                metric=self.name,
                score=0.0,
                threshold=self.config.threshold,
                is_drift=False,
                method=self.config.detection_method,
                details={"reason": "not_initialized"},
            )

        if len(self._data) < self.config.min_samples:
            return DriftSignal(
                drift_type=self.drift_type,
                metric=self.name,
                score=0.0,
                threshold=self.config.threshold,
                is_drift=False,
                method=self.config.detection_method,
                details={"reason": "insufficient_data", "samples": len(self._data)},
            )

        score = self.compute_drift_score()
        is_drift = score > self.config.threshold
        severity = _compute_severity(score, self.config.threshold)

        signal = DriftSignal(
            drift_type=self.drift_type,
            metric=self.name,
            score=score,
            threshold=self.config.threshold,
            is_drift=is_drift,
            severity=severity,
            method=self.config.detection_method,
            timestamp=time.time(),
            details=self._build_check_details(score),
        )

        self.state.last_signal = signal
        self.state.last_check_time = time.time()
        if is_drift:
            self.state.drift_count += 1

        await self._notify_callbacks(signal)
        logger.debug(
            "Monitor '%s' check: score=%.4f threshold=%.4f drift=%s",
            self.name,
            score,
            self.config.threshold,
            is_drift,
        )

        return signal

    def _build_check_details(self, score: float) -> dict[str, Any]:
        """Build the details dict for the drift signal."""
        data_arr = np.array(list(self._data), dtype=np.float64)
        return {
            "score": score,
            "samples": len(data_arr),
            "mean": float(np.mean(data_arr)),
            "std": float(np.std(data_arr)),
            "median": float(np.median(data_arr)),
            "p95": float(np.percentile(data_arr, 95)),
        }

    async def start_streaming(self) -> None:
        """Start periodic automatic checks."""
        if self.config.check_interval_seconds <= 0:
            logger.warning(
                "Monitor '%s' has check_interval_seconds=0, streaming not started", self.name
            )
            return
        self._running = True
        self._check_task = asyncio.create_task(self._stream_loop())
        logger.info(
            "Monitor '%s' started streaming with interval %.1fs",
            self.name,
            self.config.check_interval_seconds,
        )

    async def stop_streaming(self) -> None:
        """Stop periodic automatic checks."""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        logger.info("Monitor '%s' streaming stopped", self.name)

    async def _stream_loop(self) -> None:
        """Main loop for periodic drift checking."""
        while self._running:
            try:
                await asyncio.sleep(self.config.check_interval_seconds)
                if len(self._data) >= self.config.min_samples:
                    await self.check()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Stream loop error in '%s': %s", self.name, exc)

    def reset(self) -> None:
        """Reset the monitor to initial state."""
        self._data.clear()
        self._timestamps.clear()
        self.state = MonitorState()
        self._baseline_data = None

    @property
    def recent_data(self) -> list[float]:
        """Get the most recent observations."""
        return list(self._data)

    @property
    def stats(self) -> dict[str, Any]:
        """Get monitor statistics."""
        data_arr = np.array(list(self._data), dtype=np.float64) if self._data else np.array([])
        return {
            "name": self.name,
            "initialized": self.state.initialized,
            "observations": self.state.observation_count,
            "window_count": len(self._data),
            "drift_count": self.state.drift_count,
            "mean": float(np.mean(data_arr)) if len(data_arr) > 0 else 0.0,
            "std": float(np.std(data_arr)) if len(data_arr) > 0 else 0.0,
            "streaming": self._running,
        }


# ── Specialized Monitors ───────────────────────────────────────────────


class PerformanceMonitor(BaseMonitor):
    """Monitors agent performance signals: latency, success rate, throughput."""

    def __init__(
        self,
        config: MonitorConfig | None = None,
        metric: str = "latency_ms",
    ) -> None:
        super().__init__(
            config
            or MonitorConfig(
                name=f"performance_{metric}",
                threshold=0.15,
                min_samples=20,
                detection_method=DetectionMethod.EWMA,
            )
        )
        self.metric = metric
        self._ewma: float = 0.0
        self._ewma_alpha: float = 0.1

    @property
    def drift_type(self) -> DriftType:
        return DriftType.PERFORMANCE

    def observe(self, value: float, timestamp: float | None = None) -> None:
        """Record a performance metric observation with EWMA update."""
        super().observe(value, timestamp)
        self._ewma = self._ewma_alpha * value + (1 - self._ewma_alpha) * self._ewma

    def compute_drift_score(self) -> float:
        """Compute drift using EWMA deviation from median."""
        data = list(self._data)
        if len(data) < 10:
            return 0.0

        arr = np.array(data[-self.config.min_samples :], dtype=np.float64)
        median = float(np.median(arr))
        std = float(np.std(arr))

        if std < 1e-10:
            return abs(self._ewma - median)

        # How many std deviations is EWMA from the median?
        return abs(self._ewma - median) / std

    def _build_check_details(self, score: float) -> dict[str, Any]:
        details = super()._build_check_details(score)
        details["metric"] = self.metric
        details["ewma"] = self._ewma
        return details


class ContextMonitor(BaseMonitor):
    """Monitors context signals: topic distribution, tool usage patterns, codebase changes."""

    def __init__(
        self,
        config: MonitorConfig | None = None,
        feature_keys: list[str] | None = None,
    ) -> None:
        super().__init__(
            config
            or MonitorConfig(
                name="context_monitor",
                threshold=0.2,
                min_samples=10,
                detection_method=DetectionMethod.KL_DIVERGENCE,
            )
        )
        self.feature_keys = feature_keys or []
        self._feature_history: deque[dict[str, float]] = deque(maxlen=self.config.window_size)
        self._profile_history: deque[dict[str, float]] = deque(maxlen=100)

    @property
    def drift_type(self) -> DriftType:
        return DriftType.CONTEXT

    def observe_profile(self, profile: dict[str, float]) -> None:
        """Record a full context profile observation.

        Args:
            profile: Dictionary mapping feature names to their values.
        """
        if not self.config.enabled:
            return
        self._profile_history.append(profile)
        self.state.observation_count += 1

    def compute_drift_score(self) -> float:
        """Compute drift using Jensen-Shannon divergence on profiles."""
        profiles = list(self._profile_history)
        if len(profiles) < 10:
            return 0.0

        # Split into old and recent halves
        half = len(profiles) // 2
        old_profiles = profiles[:half]
        recent_profiles = profiles[half:]

        # Build aggregate distributions
        old_agg: dict[str, float] = {}
        recent_agg: dict[str, float] = {}

        for p in old_profiles:
            for k, v in p.items():
                old_agg[k] = old_agg.get(k, 0.0) + v
        for p in recent_profiles:
            for k, v in p.items():
                recent_agg[k] = recent_agg.get(k, 0.0) + v

        # Normalize
        old_total = sum(old_agg.values()) or 1.0
        recent_total = sum(recent_agg.values()) or 1.0

        # Jensen-Shannon divergence via smoothed KL
        all_keys = sorted(set(old_agg) | set(recent_agg))
        if not all_keys:
            return 0.0

        epsilon = 1e-10
        p = np.array([old_agg.get(k, 0.0) / old_total + epsilon for k in all_keys])
        q = np.array([recent_agg.get(k, 0.0) / recent_total + epsilon for k in all_keys])
        p /= p.sum()
        q /= q.sum()
        m = 0.5 * (p + q)

        from .drift_detector import _kl_divergence

        jsd = 0.5 * _kl_divergence(p, m) + 0.5 * _kl_divergence(q, m)
        return float(jsd)

    def _build_check_details(self, score: float) -> dict[str, Any]:
        details = {
            "score": score,
            "profiles_observed": len(self._profile_history),
        }
        # Track which features changed most
        profiles = list(self._profile_history)
        if len(profiles) >= 10:
            half = len(profiles) // 2
            old_keys = set().union(*(p.keys() for p in profiles[:half]))
            recent_keys = set().union(*(p.keys() for p in profiles[half:]))
            details["new_features"] = sorted(recent_keys - old_keys)
            details["removed_features"] = sorted(old_keys - recent_keys)
        return details


class DistributionMonitor(BaseMonitor):
    """Monitors distribution signals: task type ratios, complexity distributions."""

    def __init__(
        self,
        config: MonitorConfig | None = None,
        num_bins: int = 50,
    ) -> None:
        super().__init__(
            config
            or MonitorConfig(
                name="distribution_monitor",
                threshold=0.2,
                min_samples=30,
                detection_method=DetectionMethod.MAXIMUM_MEAN_DISCREPANCY,
            )
        )
        self.num_bins = num_bins
        self._task_type_counter: dict[str, int] = {}
        self._multivariate_data: deque[np.ndarray] = deque(maxlen=self.config.window_size)

    @property
    def drift_type(self) -> DriftType:
        return DriftType.DISTRIBUTION

    def observe_task(self, task_type: str) -> None:
        """Record a task type observation."""
        if not self.config.enabled:
            return
        self._task_type_counter[task_type] = self._task_type_counter.get(task_type, 0) + 1
        self.state.observation_count += 1

    def compute_drift_score(self) -> float:
        """Compute drift using MMD or task type distribution change."""
        # Check task type distribution changes
        if self._task_type_counter:
            total = sum(self._task_type_counter.values())
            if total > 10:
                # Compare recent task types to overall
                # Use the most recent task counts as a virtual "recent" slice
                # For simplicity: use ratio deviation on top task types
                sorted_types = sorted(self._task_type_counter.items(), key=lambda x: -x[1])
                top_types = sorted_types[:10]
                top_ratios = np.array([c / total for _, c in top_types])
                uniform = np.ones(len(top_types)) / len(top_types)
                from .drift_detector import _kl_divergence

                return min(1.0, float(_kl_divergence(top_ratios, uniform)))

        # Fall through to data-based computation
        data = list(self._data)
        if len(data) < self.config.min_samples:
            return 0.0

        arr = np.array(data, dtype=np.float64)
        half = len(arr) // 2
        old = arr[:half]
        recent = arr[half:]

        from .drift_detector import _mmd

        mmd_val = _mmd(old, recent, kernel="rbf")
        return min(1.0, mmd_val / max(float(np.std(old)), 1e-10))

    @property
    def task_distribution(self) -> dict[str, float]:
        """Get normalized task type distribution."""
        total = sum(self._task_type_counter.values())
        if total == 0:
            return {}
        return {k: v / total for k, v in self._task_type_counter.items()}


class RewardMonitor(BaseMonitor):
    """Monitors reward signals: RL reward values, user feedback scores, quality ratings."""

    def __init__(
        self,
        config: MonitorConfig | None = None,
        track_per_context: bool = True,
    ) -> None:
        super().__init__(
            config
            or MonitorConfig(
                name="reward_monitor",
                threshold=0.2,
                min_samples=15,
                detection_method=DetectionMethod.Z_SCORE,
            )
        )
        self.track_per_context = track_per_context
        self._context_rewards: dict[str, deque[float]] = {}

    @property
    def drift_type(self) -> DriftType:
        return DriftType.REWARD

    def observe_with_context(self, reward: float, context_tag: str) -> None:
        """Record a reward with context.

        Args:
            reward: Reward value.
            context_tag: Label for the context (e.g., task type, user segment).
        """
        if not self.config.enabled:
            return
        self.observe(reward)
        if self.track_per_context and context_tag:
            if context_tag not in self._context_rewards:
                self._context_rewards[context_tag] = deque(maxlen=self.config.window_size)
            self._context_rewards[context_tag].append(reward)

    def compute_drift_score(self) -> float:
        """Compute reward drift using z-score of recent rewards vs overall."""
        data = list(self._data)
        if len(data) < self.config.min_samples:
            return 0.0

        arr = np.array(data, dtype=np.float64)
        overall_mean = float(np.mean(arr))
        overall_std = float(np.std(arr))
        if overall_std < 1e-10:
            return 0.0

        recent_n = min(self.config.min_samples, len(arr))
        recent = arr[-recent_n:]
        recent_mean = float(np.mean(recent))

        score = abs(recent_mean - overall_mean) / overall_std

        # Blend in per-context drift
        if self.track_per_context and self._context_rewards:
            context_scores = []
            for _ctx, rewards in self._context_rewards.items():
                if len(rewards) >= 10:
                    ctx_arr = np.array(rewards, dtype=np.float64)
                    ctx_mean = float(np.mean(ctx_arr))
                    context_scores.append(abs(ctx_mean - overall_mean) / max(overall_std, 1e-10))
            if context_scores:
                score = 0.7 * score + 0.3 * float(np.max(context_scores))

        return float(score)

    @property
    def reward_stats(self) -> dict[str, Any]:
        """Get comprehensive reward statistics."""
        if not self._data:
            return {}
        arr = np.array(self._data, dtype=np.float64)
        stats: dict[str, Any] = {
            "count": len(arr),
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "p50": float(np.percentile(arr, 50)),
            "p95": float(np.percentile(arr, 95)),
        }
        if self._context_rewards:
            stats["per_context"] = {}
            for ctx, rewards in self._context_rewards.items():
                ctx_arr = np.array(rewards, dtype=np.float64)
                stats["per_context"][ctx] = {
                    "count": len(ctx_arr),
                    "mean": float(np.mean(ctx_arr)),
                    "std": float(np.std(ctx_arr)),
                }
        return stats


# ── Monitor Registry ───────────────────────────────────────────────────


class MonitorRegistry:
    """Registry for managing multiple monitors across different signal types.

    Provides centralized access, batch operations, and aggregated insights
    across all registered monitors.
    """

    def __init__(self) -> None:
        self._monitors: dict[str, BaseMonitor] = {}
        self._by_type: dict[DriftType, list[str]] = {}

    def register(self, monitor: BaseMonitor) -> None:
        """Register a monitor.

        Args:
            monitor: The monitor instance to register.

        Raises:
            ValueError: If a monitor with the same name is already registered.
        """
        if monitor.name in self._monitors:
            raise ValueError(f"Monitor '{monitor.name}' already registered")
        self._monitors[monitor.name] = monitor
        dt = monitor.drift_type
        if dt not in self._by_type:
            self._by_type[dt] = []
        self._by_type[dt].append(monitor.name)
        logger.info("Registered monitor '%s' (type=%s)", monitor.name, dt.name)

    def unregister(self, name: str) -> BaseMonitor | None:
        """Remove a monitor by name."""
        monitor = self._monitors.pop(name, None)
        if monitor:
            dt = monitor.drift_type
            if dt in self._by_type:
                self._by_type[dt] = [n for n in self._by_type[dt] if n != name]
        return monitor

    def get(self, name: str) -> BaseMonitor | None:
        """Get a monitor by name."""
        return self._monitors.get(name)

    def get_by_type(self, drift_type: DriftType) -> list[BaseMonitor]:
        """Get all monitors of a given drift type."""
        names = self._by_type.get(drift_type, [])
        return [self._monitors[n] for n in names if n in self._monitors]

    async def check_all(self) -> list[DriftSignal]:
        """Run drift checks on all monitors concurrently.

        Returns:
            List of all drift signals.
        """

        async def _check_one(monitor: BaseMonitor) -> DriftSignal:
            return await monitor.check()

        tasks = [_check_one(m) for m in self._monitors.values()]
        return list(await asyncio.gather(*tasks))

    def check_all_sync(self) -> list[DriftSignal]:
        """Synchronous version of check_all."""

        async def _run():
            return await self.check_all()

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create a new one
            return asyncio.run(self.check_all())

        # If loop is running, we cannot use run(), so call sync version
        signals = []
        for monitor in self._monitors.values():
            try:
                signal = monitor.compute_drift_score()  # type: ignore[assignment]
                # Create signal manually for sync context
                signals.append(
                    DriftSignal(
                        drift_type=monitor.drift_type,
                        metric=monitor.name,
                        score=float(signal),
                        threshold=monitor.config.threshold,
                        is_drift=float(signal) > monitor.config.threshold,
                        severity=_compute_severity(float(signal), monitor.config.threshold),
                        method=monitor.config.detection_method,
                        timestamp=time.time(),
                    )
                )
            except Exception as exc:
                logger.error("Sync check failed for '%s': %s", monitor.name, exc)
        return signals

    @property
    def summary(self) -> dict[str, Any]:
        """Get summary of all monitors."""
        signals = self.check_all_sync()
        return {
            "total_monitors": len(self._monitors),
            "by_type": {dt.name: len(names) for dt, names in self._by_type.items()},
            "drift_count": sum(1 for s in signals if s.is_drift),
            "monitor_stats": {name: monitor.stats for name, monitor in self._monitors.items()},
        }

    @property
    def monitor_names(self) -> list[str]:
        """Get all registered monitor names."""
        return list(self._monitors.keys())

    def stop_all_streaming(self) -> None:
        """Stop streaming on all monitors."""
        for monitor in self._monitors.values():
            # Create a synchronous stop
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(monitor.stop_streaming())
            except RuntimeError:
                monitor._running = False
