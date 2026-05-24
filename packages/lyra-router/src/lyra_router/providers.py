"""
Provider registry for the Lyra Model Router (V4).

Pre-configured with current May 2026 pricing data across Anthropic, DeepSeek,
Google, OpenAI, and OpenRouter. All API keys read from environment variables.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from .models import ModelAssignment, ModelTier, Provider

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Registry of available AI model providers with pricing data.

    Pre-configured with current May 2026 pricing. API keys are never
    stored — they are read from environment variables at call time.
    """

    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}
        self._models: dict[str, ModelAssignment] = {}
        self._register_builtins()

    # ── Registration ──────────────────────────────────────────────

    def register_provider(self, provider: Provider) -> None:
        """Register a provider and its models."""
        self._providers[provider.name] = provider

    def register_model(self, model: ModelAssignment) -> None:
        """Register a single model assignment."""
        self._models[model.model_name] = model
        provider = self._providers.get(model.provider)
        if provider and model.model_name not in provider.models:
            provider.models.append(model.model_name)

    # ── Query ─────────────────────────────────────────────────────

    def get_provider(self, name: str) -> Optional[Provider]:
        """Return a provider by name, or None."""
        return self._providers.get(name)

    def get_model(self, model_name: str) -> Optional[ModelAssignment]:
        """Return a model assignment by name, or None."""
        return self._models.get(model_name)

    def list_providers(self) -> list[str]:
        """Return all registered provider names."""
        return list(self._providers.keys())

    def list_models(self, provider: Optional[str] = None) -> list[str]:
        """List model names, optionally filtered by provider."""
        if provider:
            return [
                m for m, a in self._models.items() if a.provider == provider
            ]
        return list(self._models.keys())

    def get_api_key(self, provider_name: str) -> Optional[str]:
        """Read an API key from the environment for the given provider."""
        provider = self._providers.get(provider_name)
        if not provider or not provider.api_key_env:
            logger.warning("No api_key_env configured for provider '%s'", provider_name)
            return None
        key = os.environ.get(provider.api_key_env)
        if not key:
            logger.debug("API key env var %s is not set", provider.api_key_env)
        return key

    def has_api_key(self, provider_name: str) -> bool:
        """Check whether the required API key is available."""
        return self.get_api_key(provider_name) is not None

    # ── Model selection helpers ───────────────────────────────────

    def get_best_model_for_tier(
        self, tier: ModelTier, require_key: bool = True
    ) -> Optional[ModelAssignment]:
        """
        Return the cheapest available model at a given tier.

        Args:
            tier: Desired model capability tier.
            require_key: If True, skip models whose provider lacks an API key.
        """
        candidates = [
            m for m in self._models.values()
            if m.tier == tier
            and (not require_key or self.has_api_key(m.provider))
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda m: m.cost_per_1m_tokens)
        return candidates[0]

    def get_fallback_model(
        self, tier: ModelTier, _budget_regime: str = "high"
    ) -> Optional[ModelAssignment]:
        """
        Return a model one tier below (cheaper) for budget-constrained routing.

        Args:
            tier: Original desired tier.
            budget_regime: Current budget regime (high/medium/low/critical).
        """
        tier_order = list(ModelTier)
        try:
            idx = tier_order.index(tier)
        except ValueError:
            return None

        if idx == 0:
            return self.get_best_model_for_tier(tier)

        # Try each lower tier until we find an available model
        for fallback_idx in range(idx - 1, -1, -1):
            candidate = self.get_best_model_for_tier(tier_order[fallback_idx])
            if candidate:
                return candidate
        return self.get_best_model_for_tier(tier)

    # ── Built-in providers (May 2026 pricing) ─────────────────────

    def _register_builtins(self) -> None:
        """Register all built-in providers with current pricing."""

        # --- Anthropic ---
        self.register_provider(Provider(
            name="anthropic",
            base_url="https://api.anthropic.com/v1",
            api_key_env="ANTHROPIC_API_KEY",
            max_requests_per_minute=50,
        ))
        self.register_model(ModelAssignment(
            model_name="claude-haiku-4-20250514",
            provider="anthropic",
            cost_per_1m_tokens=1.0,     # $1/1M input
            tier=ModelTier.HAIKU,
            context_window=200_000,
        ))
        self.register_model(ModelAssignment(
            model_name="claude-sonnet-4-20250514",
            provider="anthropic",
            cost_per_1m_tokens=3.0,     # $3/1M input
            tier=ModelTier.STANDARD,
            context_window=200_000,
        ))
        self.register_model(ModelAssignment(
            model_name="claude-opus-4-20250514",
            provider="anthropic",
            cost_per_1m_tokens=15.0,    # $15/1M input
            tier=ModelTier.PREMIUM,
            context_window=200_000,
        ))

        # --- DeepSeek ---
        self.register_provider(Provider(
            name="deepseek",
            base_url="https://api.deepseek.com/v1",
            api_key_env="DEEPSEEK_API_KEY",
            max_requests_per_minute=60,
        ))
        self.register_model(ModelAssignment(
            model_name="deepseek-chat-v4",
            provider="deepseek",
            cost_per_1m_tokens=0.27,    # $0.27/1M input
            tier=ModelTier.FAST,
            context_window=128_000,
        ))
        self.register_model(ModelAssignment(
            model_name="deepseek-reasoner-v4",
            provider="deepseek",
            cost_per_1m_tokens=0.55,     # $0.55/1M input
            tier=ModelTier.STANDARD,
            context_window=128_000,
        ))

        # --- Google ---
        self.register_provider(Provider(
            name="google",
            base_url="https://generativelanguage.googleapis.com/v1beta",
            api_key_env="GOOGLE_API_KEY",
            max_requests_per_minute=30,
        ))
        self.register_model(ModelAssignment(
            model_name="gemini-2.5-flash",
            provider="google",
            cost_per_1m_tokens=0.15,    # $0.15/1M input
            tier=ModelTier.HAIKU,
            context_window=1_000_000,
        ))
        self.register_model(ModelAssignment(
            model_name="gemini-2.5-pro",
            provider="google",
            cost_per_1m_tokens=1.25,     # $1.25/1M input
            tier=ModelTier.STANDARD,
            context_window=1_000_000,
        ))

        # --- OpenAI ---
        self.register_provider(Provider(
            name="openai",
            base_url="https://api.openai.com/v1",
            api_key_env="OPENAI_API_KEY",
            max_requests_per_minute=60,
        ))
        self.register_model(ModelAssignment(
            model_name="gpt-4o-mini-2025",
            provider="openai",
            cost_per_1m_tokens=0.15,    # $0.15/1M input
            tier=ModelTier.HAIKU,
            context_window=128_000,
        ))
        self.register_model(ModelAssignment(
            model_name="gpt-4o-2025",
            provider="openai",
            cost_per_1m_tokens=2.50,    # $2.50/1M input
            tier=ModelTier.STANDARD,
            context_window=128_000,
        ))
        self.register_model(ModelAssignment(
            model_name="gpt-5",
            provider="openai",
            cost_per_1m_tokens=12.50,   # $12.50/1M input
            tier=ModelTier.PREMIUM,
            context_window=256_000,
        ))

        # --- OpenRouter (aggregator) ---
        self.register_provider(Provider(
            name="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key_env="OPENROUTER_API_KEY",
            max_requests_per_minute=200,
        ))
        # OpenRouter provides access to many models — register key tier mappings
        self.register_model(ModelAssignment(
            model_name="openrouter/deepseek/deepseek-chat-v4",
            provider="openrouter",
            cost_per_1m_tokens=0.27,
            tier=ModelTier.FAST,
        ))
        self.register_model(ModelAssignment(
            model_name="openrouter/anthropic/claude-sonnet-4-20250514",
            provider="openrouter",
            cost_per_1m_tokens=3.0,
            tier=ModelTier.STANDARD,
        ))

    def get_stats(self) -> dict:
        """Return summary statistics about the provider registry."""
        total_models = len(self._models)
        providers_with_keys = sum(
            1 for p in self._providers if self.has_api_key(p)
        )
        return {
            "total_providers": len(self._providers),
            "total_models": total_models,
            "providers_with_keys": providers_with_keys,
            "models_by_tier": {
                tier.value: sum(
                    1 for m in self._models.values() if m.tier == tier
                )
                for tier in ModelTier
            },
        }
