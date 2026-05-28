"""Multi-objective reward calculator for RL-based routing.

Computes a scalar reward from:
  - Quality: did the model produce a correct/useful response? (0-1)
  - Cost: normalized token cost relative to budget
  - Latency: response time relative to threshold
  - Safety: penalty for safety-flagged outputs

Final reward = w_q * quality - w_c * cost_penalty - w_l * latency_penalty - w_s * safety_penalty
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RewardConfig:
    """Weights for the multi-objective reward function."""

    quality_weight: float = 0.5
    cost_weight: float = 0.25
    latency_weight: float = 0.15
    safety_weight: float = 0.10

    quality_threshold: float = 0.7       # below this, quality penalty applies
    latency_threshold_ms: float = 2000.0  # above this, latency penalty applies
    cost_budget_usd: float = 5.0          # total budget for cost normalization

    def __post_init__(self) -> None:
        total = self.quality_weight + self.cost_weight + self.latency_weight + self.safety_weight
        if not 0.99 <= total <= 1.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


@dataclass(frozen=True)
class RewardComponents:
    """Decomposed reward for interpretability."""

    quality_score: float
    cost_penalty: float
    latency_penalty: float
    safety_penalty: float
    total: float


class RewardCalculator:
    """Computes scalar rewards for RL routing policy training."""

    def __init__(self, config: RewardConfig | None = None) -> None:
        self._config = config or RewardConfig()

    def compute(
        self,
        *,
        quality: float = 1.0,
        cost_usd: float = 0.0,
        latency_ms: float = 0.0,
        safety_flagged: bool = False,
        tier: str = "fast",
    ) -> RewardComponents:
        cfg = self._config

        quality_score = self._clamp(quality) * cfg.quality_weight
        cost_penalty = self._cost_penalty(cost_usd, tier)
        latency_penalty = self._latency_penalty(latency_ms)
        safety_penalty = (1.0 if safety_flagged else 0.0) * cfg.safety_weight

        if quality < cfg.quality_threshold:
            quality_score -= cfg.quality_weight * (1.0 - quality / cfg.quality_threshold)

        total = quality_score - cost_penalty - latency_penalty - safety_penalty

        return RewardComponents(
            quality_score=round(quality_score, 6),
            cost_penalty=round(cost_penalty, 6),
            latency_penalty=round(latency_penalty, 6),
            safety_penalty=round(safety_penalty, 6),
            total=round(total, 6),
        )

    def _cost_penalty(self, cost_usd: float, tier: str) -> float:
        cfg = self._config
        tier_multipliers = {"fast": 0.3, "reasoning": 1.0, "advisor": 1.5}
        multiplier = tier_multipliers.get(tier, 1.0)

        if cfg.cost_budget_usd <= 0:
            return 0.0

        normalized = min(cost_usd / cfg.cost_budget_usd, 1.0)
        return normalized * multiplier * cfg.cost_weight

    def _latency_penalty(self, latency_ms: float) -> float:
        cfg = self._config
        if latency_ms <= cfg.latency_threshold_ms:
            return 0.0
        excess = (latency_ms - cfg.latency_threshold_ms) / cfg.latency_threshold_ms
        return min(excess * cfg.latency_weight, cfg.latency_weight)

    @staticmethod
    def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, v))

    @property
    def config(self) -> RewardConfig:
        return self._config


__all__ = ["RewardCalculator", "RewardComponents", "RewardConfig"]
