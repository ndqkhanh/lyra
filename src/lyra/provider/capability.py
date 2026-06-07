"""
Provider Capability Matrix — documents what each provider supports.

This is the single source of truth for provider feature support. The router,
skills system, and workflow engine consult this matrix to make provider-aware
decisions (e.g. "don't route vision tasks to DeepSeek", "use prompt-based
tool calling for open-weights models").

Updated: May 2026 — current as of the latest provider API versions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderCapability:
    """
    Feature support record for a single provider.

    Attributes:
        provider: Provider identifier (``anthropic``, ``deepseek``, etc.).
        tool_calling: Supports native tool/function calling API.
        json_mode: Supports structured JSON output mode.
        vision: Supports image inputs.
        streaming: Supports streaming (SSE) responses.
        prompt_caching: Supports prompt caching (reduces cost for repeated prefixes).
        reasoning_budget: Has a native API parameter for reasoning effort/budget.
        max_context_tokens: Maximum context window in tokens.
        concurrent_limit: Max concurrent requests (provider-enforced).
        notes: Free-text notes about quirks or limitations.
    """

    provider: str
    tool_calling: bool = True
    json_mode: bool = False
    vision: bool = False
    streaming: bool = True
    prompt_caching: bool = False
    reasoning_budget: bool = False
    max_context_tokens: int = 128_000
    concurrent_limit: int = 50
    notes: str = ""


class CapabilityMatrix:
    """
    Registry of provider capabilities — consulted by router, skills, and workflows.

    Usage::

        matrix = get_capability_matrix()
        if matrix.supports("deepseek", "vision"):
            ...  # won't execute — DeepSeek has no vision support
    """

    def __init__(self) -> None:
        self._capabilities: dict[str, ProviderCapability] = {}
        self._register_builtins()

    def get(self, provider: str) -> ProviderCapability | None:
        """Return capabilities for a provider, or None if unknown."""
        return self._capabilities.get(provider)

    def supports(self, provider: str, feature: str) -> bool:
        """
        Check whether a provider supports a specific feature.

        Args:
            provider: Provider identifier.
            feature: Feature name (``tool_calling``, ``json_mode``, ``vision``,
                     ``streaming``, ``prompt_caching``, ``reasoning_budget``).

        Returns:
            True if supported, False if unknown provider or not supported.
        """
        cap = self._capabilities.get(provider)
        if cap is None:
            return False
        return getattr(cap, feature, False)

    def get_context_window(self, provider: str) -> int:
        """Return the max context window for a provider, or a safe default."""
        cap = self._capabilities.get(provider)
        return cap.max_context_tokens if cap else 128_000

    def list_providers(self) -> list[str]:
        """Return all registered provider identifiers."""
        return list(self._capabilities.keys())

    def list_providers_supporting(self, feature: str) -> list[str]:
        """
        Return all providers that support a given feature.

        Useful for the router: "I need vision — which providers can do that?"
        """
        return [
            p for p, c in self._capabilities.items()
            if getattr(c, feature, False)
        ]

    # ── Built-in capability declarations (May 2026) ──────────────

    def _register_builtins(self) -> None:
        """Register capability records for all known providers."""

        self._capabilities["anthropic"] = ProviderCapability(
            provider="anthropic",
            tool_calling=True,
            json_mode=True,
            vision=True,
            streaming=True,
            prompt_caching=True,
            reasoning_budget=True,  # budget_tokens API
            max_context_tokens=200_000,
            concurrent_limit=50,
            notes="Opus 4.8, Sonnet 4.6, Haiku 4.5. Prompt caching reduces cost ~90% for cached tokens.",
        )

        self._capabilities["deepseek"] = ProviderCapability(
            provider="deepseek",
            tool_calling=True,
            json_mode=False,
            vision=False,
            streaming=True,
            prompt_caching=False,
            reasoning_budget=False,  # No budget_tokens — uses prompt instructions
            max_context_tokens=128_000,
            concurrent_limit=60,
            notes="DeepSeek-V4 series. No native reasoning budget — Lyra injects thinking instructions into system prompt.",
        )

        self._capabilities["openai"] = ProviderCapability(
            provider="openai",
            tool_calling=True,
            json_mode=True,
            vision=True,
            streaming=True,
            prompt_caching=False,
            reasoning_budget=True,  # reasoning_effort API
            max_context_tokens=256_000,
            concurrent_limit=60,
            notes="GPT-5, GPT-4o, GPT-4o-mini. reasoning_effort supported on o-series models.",
        )

        self._capabilities["google"] = ProviderCapability(
            provider="google",
            tool_calling=True,
            json_mode=True,
            vision=True,
            streaming=True,
            prompt_caching=False,
            reasoning_budget=False,
            max_context_tokens=1_000_000,
            concurrent_limit=30,
            notes="Gemini 2.5 Flash/Pro. 1M context window is the largest. Rate limits are lower than Anthropic/DeepSeek.",
        )

        self._capabilities["openrouter"] = ProviderCapability(
            provider="openrouter",
            tool_calling=True,
            json_mode=True,
            vision=True,
            streaming=True,
            prompt_caching=False,
            reasoning_budget=True,  # Passthrough to underlying provider
            max_context_tokens=200_000,
            concurrent_limit=200,
            notes="Aggregator — capabilities depend on the routed model. Higher rate limits.",
        )

        self._capabilities["openweights"] = ProviderCapability(
            provider="openweights",
            tool_calling=False,  # Prompt-based only
            json_mode=False,
            vision=False,
            streaming=True,
            prompt_caching=False,
            reasoning_budget=False,
            max_context_tokens=32_000,
            concurrent_limit=10,
            notes="Local/self-hosted models. Tool calls via prompt formatting. Limited context. Variable quality.",
        )


# Singleton instance
_capability_matrix: CapabilityMatrix | None = None


def get_capability_matrix() -> CapabilityMatrix:
    """Return the global capability matrix (singleton)."""
    global _capability_matrix
    if _capability_matrix is None:
        _capability_matrix = CapabilityMatrix()
    return _capability_matrix
