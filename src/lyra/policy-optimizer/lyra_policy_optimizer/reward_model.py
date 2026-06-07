"""Reward modeling and shaping for policy optimization."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

import numpy as np

from .exceptions import RewardModelError


@dataclass(frozen=True)
class RewardConfig:
    """Configuration for reward computation."""

    metrics: tuple[str, ...] = ("accuracy", "latency", "cost")
    weights: tuple[float, ...] = (0.5, 0.25, 0.25)
    discount_factor: float = 0.99
    shaping_enabled: bool = True


@dataclass(frozen=True)
class RewardSignal:
    """A single reward signal from one metric."""

    metric: str
    value: float
    normalized: float
    weight: float
    timestamp: float


@dataclass(frozen=True)
class RewardSummary:
    """Aggregated reward summary across all signals."""

    signals: tuple[RewardSignal, ...]
    total_reward: float
    discounted_reward: float
    cumulative: float


class RewardModel:
    """Reward model supporting reward computation, shaping, and normalization."""

    _cumulative: float = 0.0

    async def compute_reward(
        self, metrics: dict[str, float], config: RewardConfig
    ) -> RewardSummary:
        """Compute reward from raw metrics using the given configuration."""
        if not metrics:
            raise RewardModelError("metrics dict must not be empty")
        if len(config.metrics) != len(config.weights):
            raise RewardModelError(
                "metrics and weights must have the same length"
            )
        if any(w < 0 for w in config.weights):
            raise RewardModelError("weights must be non-negative")
        total_weight = sum(config.weights)
        if total_weight <= 0:
            raise RewardModelError("total weight must be positive")

        now = time.time()
        signals: list[RewardSignal] = []
        total = 0.0

        for metric, weight in zip(config.metrics, config.weights, strict=False):
            raw_value = metrics.get(metric)
            if raw_value is None:
                raise RewardModelError(f"metric '{metric}' not found in input")

            normalized = self._normalize_single(metric, raw_value)
            signal = RewardSignal(
                metric=metric,
                value=raw_value,
                normalized=normalized,
                weight=weight,
                timestamp=now,
            )
            signals.append(signal)
            total += normalized * weight

        discounted = total * (config.discount_factor ** len(signals))
        self._cumulative += total

        return RewardSummary(
            signals=tuple(signals),
            total_reward=total,
            discounted_reward=discounted,
            cumulative=self._cumulative,
        )

    async def shape_reward(
        self, signals: tuple[RewardSignal, ...]
    ) -> tuple[RewardSignal, ...]:
        """Apply reward shaping to encourage consistent improvement."""
        if not signals:
            return signals

        shaped: list[RewardSignal] = []
        for i, signal in enumerate(signals):
            shaping_bonus = 0.0
            if i > 0:
                prev = signals[i - 1]
                shaping_bonus = max(0.0, signal.normalized - prev.normalized) * 0.1

            shaped_signal = RewardSignal(
                metric=signal.metric,
                value=signal.value,
                normalized=min(1.0, signal.normalized + shaping_bonus),
                weight=signal.weight,
                timestamp=signal.timestamp,
            )
            shaped.append(shaped_signal)

        return tuple(shaped)

    async def normalize_rewards(
        self, rewards: tuple[float, ...]
    ) -> tuple[float, ...]:
        """Normalize a tuple of reward values to [0, 1] range."""
        if not rewards:
            return ()

        arr = np.array(rewards, dtype=np.float64)
        min_r = np.min(arr)
        max_r = np.max(arr)

        if max_r - min_r < 1e-10:
            return tuple(np.full_like(arr, 0.5))

        normalized = (arr - min_r) / (max_r - min_r)
        return tuple(normalized.tolist())

    def compute_discounted(
        self, rewards: tuple[float, ...], gamma: float
    ) -> float:
        """Compute discounted sum of rewards."""
        if not rewards:
            return 0.0
        if gamma < 0.0 or gamma > 1.0:
            raise RewardModelError("discount factor gamma must be in [0.0, 1.0]")

        total = 0.0
        for i, r in enumerate(rewards):
            total += r * (gamma**i)
        return total

    def _normalize_single(self, metric: str, value: float) -> float:
        """Normalize a single metric value to [0, 1]."""
        if metric in ("latency", "cost"):
            normalized = 1.0 / (1.0 + math.exp(value))
        else:
            normalized = max(0.0, min(1.0, value))
        return normalized
