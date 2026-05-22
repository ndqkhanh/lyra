"""Drift Detector — Multi-signal drift detection for continuous adaptation."""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

try:
    import numpy as np
    def _mean(values):
        return np.mean(values) if values else 0.0
    def _std(values):
        return np.std(values) if values else 0.0
except ImportError:
    np = None
    import statistics as _stats
    def _mean(values):
        return _stats.mean(values) if values else 0.0
    def _std(values):
        return _stats.stdev(values) if values else 0.0

logger = logging.getLogger(__name__)

__all__ = [
    "DriftType",
    "DriftSignal",
    "PerformanceDriftDetector",
    "ContextDriftDetector",
    "DistributionDriftDetector",
    "RewardDriftDetector",
    "DriftOrchestrator",
]




class DriftType(Enum):
    PERFORMANCE = auto()
    CONTEXT = auto()
    DISTRIBUTION = auto()
    REWARD = auto()


@dataclass
class DriftSignal:
    drift_type: DriftType
    metric: str
    score: float
    threshold: float
    is_drift: bool
    details: dict[str, Any] = field(default_factory=dict)


class PerformanceDriftDetector:
    """Monitors skill success rate over time for performance regression."""

    def __init__(self, window_size: int = 100, threshold: float = 0.15):
        self.window_size = window_size
        self.threshold = threshold
        self.successes: deque[bool] = deque(maxlen=window_size)

    def record_attempt(self, success: bool) -> None:
        self.successes.append(success)

    def check_drift(self) -> DriftSignal:
        if len(self.successes) < 10:
            return DriftSignal(
                DriftType.PERFORMANCE, "success_rate", 0.0, self.threshold, False
            )
        current_rate = sum(self.successes) / len(self.successes)
        baseline_rate = self._compute_baseline()
        drift = abs(current_rate - baseline_rate)
        return DriftSignal(
            DriftType.PERFORMANCE, "success_rate", drift, self.threshold,
            is_drift=drift > self.threshold,
            details={"current_rate": current_rate, "baseline_rate": baseline_rate},
        )

    def _compute_baseline(self) -> float:
        if len(self.successes) < 20:
            return 0.5
        half = len(self.successes) // 2
        return sum(list(self.successes)[:half]) / half


class ContextDriftDetector:
    """Detects changes in user codebase, tools, or preferences."""

    def __init__(self, threshold: float = 0.2):
        self.threshold = threshold
        self.baseline: dict[str, float] = {}
        self.current: dict[str, float] = {}

    def set_baseline(self, profile: dict[str, float]) -> None:
        self.baseline = profile

    def update_current(self, profile: dict[str, float]) -> None:
        self.current = profile

    def check_drift(self) -> DriftSignal:
        if not self.baseline or not self.current:
            return DriftSignal(DriftType.CONTEXT, "context_shift", 0.0, self.threshold, False)
        scores = []
        for key in set(self.baseline) | set(self.current):
            b = self.baseline.get(key, 0.0)
            c = self.current.get(key, 0.0)
            if abs(b) > 0.001:
                scores.append(abs(c - b) / abs(b))
        avg_drift = _mean(scores) if scores else 0.0
        return DriftSignal(
            DriftType.CONTEXT, "context_shift", avg_drift, self.threshold,
            is_drift=avg_drift > self.threshold,
            details={"baseline_keys": len(self.baseline), "current_keys": len(self.current)},
        )


class DistributionDriftDetector:
    """Detects shifts in the type distribution of incoming tasks."""

    def __init__(self, threshold: float = 0.2):
        self.threshold = threshold
        self.task_types: deque[dict[str, float]] = deque(maxlen=200)

    def record_task(self, task_type: str, features: dict[str, float]) -> None:
        self.task_types.append({task_type: 1.0, **features})

    def check_drift(self) -> DriftSignal:
        if len(self.task_types) < 20:
            return DriftSignal(DriftType.DISTRIBUTION, "task_distribution", 0.0, self.threshold, False)
        types = {}
        for t in self.task_types:
            for key in t:
                types[key] = types.get(key, 0) + 1
        total = len(self.task_types)
        ratios = {k: v / total for k, v in types.items()}

        recent = list(self.task_types)[-min(20, len(self.task_types)):]
        recent_types = {}
        for t in recent:
            for key in t:
                recent_types[key] = recent_types.get(key, 0) + 1
        recent_total = len(recent)
        recent_ratios = {k: v / recent_total for k, v in recent_types.items()}

        drift_scores = []
        for key in set(ratios) | set(recent_ratios):
            old_r = ratios.get(key, 0.0)
            new_r = recent_ratios.get(key, 0.0)
            drift_scores.append(abs(new_r - old_r))
        avg_drift = _mean(drift_scores) if drift_scores else 0.0
        return DriftSignal(
            DriftType.DISTRIBUTION, "task_distribution", avg_drift, self.threshold,
            is_drift=avg_drift > self.threshold,
        )


class RewardDriftDetector:
    """Monitors if the user's reward signal has changed meaning over time."""

    def __init__(self, window_size: int = 50, threshold: float = 0.2):
        self.window_size = window_size
        self.threshold = threshold
        self.rewards: deque[float] = deque(maxlen=window_size)
        self.context_tags: deque[str] = deque(maxlen=window_size)

    def record_reward(self, reward: float, context: str = "") -> None:
        self.rewards.append(reward)
        self.context_tags.append(context)

    def check_drift(self) -> DriftSignal:
        if len(self.rewards) < 10:
            return DriftSignal(DriftType.REWARD, "reward_signal", 0.0, self.threshold, False)
        mean = _mean(self.rewards)
        std = _std(self.rewards)
        if std < 1e-6:
            return DriftSignal(DriftType.REWARD, "reward_signal", 0.0, self.threshold, False)
        recent = list(self.rewards)[-min(10, len(self.rewards)):]
        recent_mean = _mean(recent)
        drift = abs(recent_mean - mean) / std
        return DriftSignal(
            DriftType.REWARD, "reward_signal", drift, self.threshold,
            is_drift=drift > self.threshold,
            details={"overall_mean": mean, "recent_mean": recent_mean, "std": std},
        )


class DriftOrchestrator:
    """Coordinates all drift detectors and triggers adaptation when threshold exceeded."""

    def __init__(self, global_threshold: float = 0.15):
        self.global_threshold = global_threshold
        self.performance = PerformanceDriftDetector()
        self.context = ContextDriftDetector()
        self.distribution = DistributionDriftDetector()
        self.reward = RewardDriftDetector()

    def check_all(self) -> list[DriftSignal]:
        signals = [
            self.performance.check_drift(),
            self.context.check_drift(),
            self.distribution.check_drift(),
            self.reward.check_drift(),
        ]
        return signals

    @property
    def adaptation_needed(self) -> bool:
        return any(s.is_drift for s in self.check_all())

    @property
    def summary(self) -> dict[str, Any]:
        signals = self.check_all()
        return {
            "adaptation_needed": any(s.is_drift for s in signals),
            "drift_count": sum(1 for s in signals if s.is_drift),
            "signals": {
                s.drift_type.name: {
                    "score": s.score,
                    "threshold": s.threshold,
                    "is_drift": s.is_drift,
                }
                for s in signals
            },
        }
