"""Model Router V2 models.

Based on Pyramid MoA (probabilistic anytime inference), SCOPE (RL-based
pre-hoc routing, 25.7% accuracy boost / 95.1% cost cut), RouteNLP
(conformal cascading, 58% cost reduction), MTRouter (multi-turn routing).
"""

from dataclasses import dataclass
from enum import Enum


class ModelProvider(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    BEDROCK = "bedrock"
    LITELLM = "litellm"
    OPENROUTER = "openrouter"


class ModelTier(Enum):
    REASONING = "reasoning"  # Opus 4.7, DeepSeek-v4-pro
    STANDARD = "standard"  # Sonnet 4.6, GPT-5.4
    FAST = "fast"  # Haiku 4.5, GPT-5.4-nano
    CHEAP = "cheap"  # Small local/open models


class RoutingStrategy(Enum):
    COST_OPTIMAL = "cost_optimal"
    PERFORMANCE_MAX = "performance_max"
    BALANCED = "balanced"
    MULTI_TURN = "multi_turn"
    CONFORMAL = "conformal"


@dataclass(frozen=True)
class ModelSpec:
    """Specification for a model in the routing pool."""

    name: str
    provider: ModelProvider
    tier: ModelTier
    cost_per_1k_tokens: float
    latency_ms: float
    accuracy_estimate: float
    context_window: int = 200000
    supports_reasoning: bool = False


@dataclass(frozen=True)
class RoutingDecision:
    """A routing decision for a specific query/task."""

    model: ModelSpec
    confidence: float
    estimated_cost: float
    fallback_models: tuple[ModelSpec, ...] = ()
    strategy: RoutingStrategy = RoutingStrategy.BALANCED
    reasoning: str = ""


@dataclass(frozen=True)
class TurnContext:
    """Context for a multi-turn routing decision."""

    turn_index: int
    query: str
    history_tokens: int = 0
    estimated_complexity: float = 0.5
    is_reasoning_task: bool = False


@dataclass(frozen=True)
class Budget:
    """Token/cost budget for routing decisions."""

    max_cost: float
    max_tokens: int
    spent_cost: float = 0.0
    spent_tokens: int = 0

    @property
    def remaining_cost(self) -> float:
        return max(0.0, self.max_cost - self.spent_cost)

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.max_tokens - self.spent_tokens)

    @property
    def cost_exhausted(self) -> bool:
        return self.spent_cost >= self.max_cost

    @property
    def tokens_exhausted(self) -> bool:
        return self.spent_tokens >= self.max_tokens


@dataclass(frozen=True)
class RouterSnapshot:
    """Point-in-time router statistics."""

    total_decisions: int
    decisions_by_tier: dict[str, int]
    total_cost: float
    total_tokens: int
    avg_confidence: float
    fallback_rate: float
