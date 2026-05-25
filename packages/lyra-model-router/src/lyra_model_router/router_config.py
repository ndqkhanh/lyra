"""Routing rules, model capability definitions, and configuration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelCapability:
    """Describes a model's capabilities for routing decisions.

    Attributes:
        model_id: Unique identifier for the model.
        provider: The provider/family (e.g. 'anthropic', 'deepseek').
        tier: Routing tier 0-3 (0=flagship, 1=standard, 2=economy, 3=background).
        strengths: Tuple of capability tags (e.g. 'coding', 'reasoning').
        cost_per_1k_tokens: Cost in USD per 1K tokens.
        max_tokens: Maximum context window size in tokens.
        supports_thinking: Whether the model supports extended thinking/reasoning.
    """
    model_id: str
    provider: str
    tier: int
    strengths: tuple[str, ...]
    cost_per_1k_tokens: float
    max_tokens: int
    supports_thinking: bool


@dataclass(frozen=True)
class RouterConfig:
    """Configuration for the model router.

    Attributes:
        model_registry: Mapping of model_id to ModelCapability.
        default_tier: Default routing tier when no preference is given.
        routing_rules: Tuple of routing rule descriptions.
    """
    model_registry: dict[str, ModelCapability]
    default_tier: int
    routing_rules: tuple[str, ...]


DEFAULT_MODEL_REGISTRY: dict[str, ModelCapability] = {
    "claude-opus-4-7": ModelCapability(
        model_id="claude-opus-4-7",
        provider="anthropic",
        tier=0,
        strengths=("reasoning", "coding", "research", "analysis"),
        cost_per_1k_tokens=0.075,
        max_tokens=200000,
        supports_thinking=True,
    ),
    "claude-sonnet-4-6": ModelCapability(
        model_id="claude-sonnet-4-6",
        provider="anthropic",
        tier=1,
        strengths=("coding", "analysis", "balanced"),
        cost_per_1k_tokens=0.015,
        max_tokens=100000,
        supports_thinking=True,
    ),
    "claude-haiku-4-5": ModelCapability(
        model_id="claude-haiku-4-5",
        provider="anthropic",
        tier=2,
        strengths=("speed", "low_cost", "simple_tasks"),
        cost_per_1k_tokens=0.0025,
        max_tokens=50000,
        supports_thinking=False,
    ),
    "deepseek-v4-pro": ModelCapability(
        model_id="deepseek-v4-pro",
        provider="deepseek",
        tier=0,
        strengths=("reasoning", "coding", "long_context"),
        cost_per_1k_tokens=0.001,
        max_tokens=128000,
        supports_thinking=True,
    ),
    "deepseek-v4-flash": ModelCapability(
        model_id="deepseek-v4-flash",
        provider="deepseek",
        tier=2,
        strengths=("speed", "low_cost", "high_throughput"),
        cost_per_1k_tokens=0.0005,
        max_tokens=64000,
        supports_thinking=False,
    ),
}


def default_config() -> RouterConfig:
    """Create a RouterConfig with default values."""
    return RouterConfig(
        model_registry=dict(DEFAULT_MODEL_REGISTRY),
        default_tier=1,
        routing_rules=(
            "tier-0: complex reasoning, architecture, novel research",
            "tier-1: coding, review, standard analysis",
            "tier-2: lookup, simple generation, classification",
            "tier-3: batch processing, meta tasks, background",
        ),
    )
