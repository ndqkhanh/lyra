"""Data models for Lyra AGI cost tracking and optimization.

All models are frozen dataclasses to enforce immutability.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class ModelTier(Enum):
    """Four-tier model hierarchy for cost-aware routing."""

    TIER_0 = 0  # Local SLM ($0/M tokens)
    TIER_1 = 1  # Haiku / Flash / DeepSeek ($0.28-$5/M)
    TIER_2 = 2  # Sonnet 4 / GPT-4o ($3-$15/M)
    TIER_3 = 3  # Opus 4 / DeepSeek-V4-Pro ($5-$25/M)


# Per-1M-token pricing for each tier (input / output).
# These are default reference prices — consumers may override.
TIER_PRICING: dict[ModelTier, tuple[float, float]] = {
    ModelTier.TIER_0: (0.0, 0.0),
    ModelTier.TIER_1: (3.0, 15.0),
    ModelTier.TIER_2: (10.0, 30.0),
    ModelTier.TIER_3: (25.0, 75.0),
}

TIER_LABELS: dict[ModelTier, str] = {
    ModelTier.TIER_0: "Local SLM",
    ModelTier.TIER_1: "Haiku / Flash / DeepSeek",
    ModelTier.TIER_2: "Sonnet 4 / GPT-4o",
    ModelTier.TIER_3: "Opus 4 / DeepSeek-V4-Pro",
}


class CallOutcome(Enum):
    """Outcome of a single model API call."""

    SUCCESS = "success"
    FAILURE = "failure"
    CACHED_PROMPT = "cached_prompt"
    CACHED_SEMANTIC = "cached_semantic"
    DEGRADED = "degraded"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class CostRecord:
    """Record of a single model API call cost.

    Cached calls record zero or reduced input cost; output_cost is always zero
    since cached responses are not re-generated.
    """

    model_name: str
    model_tier: ModelTier
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    outcome: CallOutcome
    task_id: str | None = None
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class TaskCostSummary:
    """Aggregate cost summary for a single task."""

    task_id: str
    total_calls: int
    successful_calls: int
    total_cost: float
    successful_cost: float
    cached_cost_savings: float
    start_time: float
    end_time: float | None = None


@dataclass(frozen=True)
class SessionBudget:
    """Session-level budget tracking with circuit breaker state."""

    session_id: str
    total_spent: float
    total_calls: int
    successful_tasks: int
    failed_tasks: int
    circuit_breaker_triggered: bool
    circuit_breaker_limit: float = 5.0


@dataclass(frozen=True)
class CacheStats:
    """Cache hit/miss tracking for a single cache instance."""

    hits: int = 0
    misses: int = 0

    @property
    def total_requests(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests

    @property
    def estimated_savings(self) -> float:
        """Placeholder savings estimate — real value depends on cached token count."""
        return 0.0


@dataclass(frozen=True)
class LoopDetectionResult:
    """Result of a loop detection check on a quality score."""

    task_type: str
    quality_score: float
    consecutive_low: int
    blocked: bool


@dataclass(frozen=True)
class TierConfig:
    """Per-tier configuration: cost per 1M tokens and usage limits."""

    tier: ModelTier
    input_price_per_1m: float
    output_price_per_1m: float
    max_calls_per_task: int = 100

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        input_cost = (input_tokens / 1_000_000) * self.input_price_per_1m
        output_cost = (output_tokens / 1_000_000) * self.output_price_per_1m
        return input_cost + output_cost
