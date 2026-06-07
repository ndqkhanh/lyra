"""
Data models for the Lyra 3-Tier Intelligent Model Router (V4).

Frozen dataclasses, enums, and type definitions for routing decisions,
budget regimes, task complexity classification, and provider configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ModelTier(str, Enum):
    """Capability/quality tier of an AI model."""

    LOCAL_SLM = "local_slm"         # Local small language model (~$0)
    HAIKU = "haiku"                  # Claude Haiku / Gemini Flash (~$0.0001)
    FAST = "fast"                    # GPT-4o-mini / DeepSeek-Lite (~$0.0005)
    STANDARD = "standard"            # Sonnet 4 / GPT-4o (~$0.01)
    PREMIUM = "premium"              # Opus 4 / DeepSeek-V4-Pro (~$0.05)
    AGENTIC = "agentic"              # Opus + tool orchestration (~$0.10+)


class TaskComplexity(str, Enum):
    """Estimated complexity of a user task for model routing."""

    TRIVIAL = "trivial"              # Greetings, yes/no
    SIMPLE = "simple"                # Factual lookup
    MODERATE = "moderate"            # Multi-step, standard coding
    COMPLEX = "complex"              # Architecture, deep analysis
    AGENTIC = "agentic"              # Autonomous, self-correcting


class BudgetRegime(str, Enum):
    """Budget regimes for BATS-style budget-aware routing."""

    HIGH = "high"                    # >70% budget remaining
    MEDIUM = "medium"                # 30-70% budget remaining
    LOW = "low"                      # 10-30% budget remaining
    CRITICAL = "critical"            # <10% budget remaining


@dataclass(frozen=True)
class ModelAssignment:
    """
    A concrete model assignment with pricing data.

    Attributes:
        model_name: Canonical model name (e.g. ``claude-sonnet-4-20250514``).
        provider: Provider identifier (e.g. ``anthropic``).
        cost_per_1m_tokens: Cost in USD per 1M input tokens.
        tier: Capability tier of this model.
        context_window: Maximum context window in tokens.
        supports_tool_use: Whether the model supports tool calling.
    """

    model_name: str
    provider: str
    cost_per_1m_tokens: float
    tier: ModelTier
    context_window: int = 200_000
    supports_tool_use: bool = True


@dataclass(frozen=True)
class RoutingDecision:
    """
    Result of a model routing decision through the 3-tier cascade.

    Attributes:
        model: The assigned model name.
        tier: The model tier that was selected.
        complexity: Estimated task complexity.
        confidence: Routing confidence in [0, 1].
        reasoning: Human-readable explanation of the routing decision.
        cost_estimate_usd: Estimated USD cost for this task.
        tier_used: Which router tier made the decision (1=rule, 2=semantic, 3=neural).
        budget_regime: The budget regime when this decision was made.
        latency_ms: Time spent in the routing cascade (ms).
        effort_level: The effort level used for this decision (low→ultracode).
        effort_budget_tokens: Token budget from the effort mapping.
        effort_instruction: Prompt-level thinking instruction (for providers without budget_tokens).
        effort_reasoning: OpenAI reasoning_effort value.
    """

    model: str
    tier: ModelTier
    complexity: TaskComplexity
    confidence: float
    reasoning: str
    cost_estimate_usd: float
    tier_used: int = 1
    budget_regime: BudgetRegime = BudgetRegime.HIGH
    latency_ms: float = 0.0
    effort_level: str = ""
    effort_budget_tokens: int = 0
    effort_instruction: str = ""
    effort_reasoning: str = ""
    orchestration_enabled: bool = False


@dataclass(frozen=True)
class Provider:
    """
    Provider configuration for a model API service.

    Attributes:
        name: Provider name (e.g. ``anthropic``, ``deepseek``).
        models: List of model names available from this provider.
        base_url: API base URL.
        api_key_env: Environment variable name for the API key.
        supports_streaming: Whether streaming responses are supported.
        max_requests_per_minute: Rate limit for this provider.
    """

    name: str
    models: list[str] = field(default_factory=list)
    base_url: str = ""
    api_key_env: str = ""
    supports_streaming: bool = True
    max_requests_per_minute: int = 100


# Task complexity to model tier default mapping
_COMPLEXITY_TO_TIER: dict[TaskComplexity, ModelTier] = {
    TaskComplexity.TRIVIAL: ModelTier.LOCAL_SLM,
    TaskComplexity.SIMPLE: ModelTier.HAIKU,
    TaskComplexity.MODERATE: ModelTier.STANDARD,
    TaskComplexity.COMPLEX: ModelTier.PREMIUM,
    TaskComplexity.AGENTIC: ModelTier.AGENTIC,
}


def get_tier_for_complexity(complexity: TaskComplexity) -> ModelTier:
    """Return the default model tier for a given task complexity."""
    return _COMPLEXITY_TO_TIER[complexity]


# Approximate cost ranges per task complexity (USD)
_COST_ESTIMATES: dict[TaskComplexity, float] = {
    TaskComplexity.TRIVIAL: 0.0001,
    TaskComplexity.SIMPLE: 0.001,
    TaskComplexity.MODERATE: 0.01,
    TaskComplexity.COMPLEX: 0.05,
    TaskComplexity.AGENTIC: 0.10,
}


def get_cost_estimate(complexity: TaskComplexity) -> float:
    """Return the approximate USD cost for a given task complexity."""
    return _COST_ESTIMATES[complexity]
