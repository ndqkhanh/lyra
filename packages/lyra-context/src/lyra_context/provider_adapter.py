"""
Provider-Adaptive Context Strategy — adapts compaction to context window size.

Different providers have vastly different context windows (200K vs 64K vs 8K),
requiring different compaction strategies. This module maps providers to
optimal strategies based on their context window size and the current usage ratio.

Per the SYNTHESIS research: provider-adaptive context optimization is an
unaddressed frontier. This is Lyra's specific contribution.
"""

from __future__ import annotations

from dataclasses import dataclass

from lyra_context.compactor import CompactionStrategy


# Provider context windows (default — can be overridden per model)
_PROVIDER_CONTEXT_WINDOWS: dict[str, int] = {
    "anthropic": 200_000,
    "openai": 128_000,
    "google": 2_000_000,
    "deepseek": 64_000,
    "openrouter": 128_000,
    "local": 8_000,  # Conservative default for open-weight models
    "default": 128_000,
}


@dataclass(frozen=True)
class ProviderContextConfig:
    """Context configuration for a specific provider."""

    provider_name: str
    context_window: int
    safety_margin: float = 0.85  # Trigger compaction at 85% usage

    @property
    def compaction_threshold(self) -> int:
        """Token count at which compaction triggers."""
        return int(self.context_window * self.safety_margin)


class ProviderAdaptiveCompactor:
    """
    Compactor that adapts strategy based on provider context window size.

    Small-window providers (DeepSeek 64K, local 8K) get more aggressive
    compaction. Large-window providers (Google 2M) get lighter touch.

    Usage::

        compactor = ProviderAdaptiveCompactor()
        result = compactor.compact(
            items=context_items,
            provider="deepseek",
            model="deepseek-chat",
        )
    """

    def __init__(self) -> None:
        self._providers = dict(_PROVIDER_CONTEXT_WINDOWS)

    def register_provider(
        self, name: str, context_window: int
    ) -> None:
        """Register or override a provider's context window."""
        self._providers[name] = context_window

    def get_context_window(self, provider: str, model: str = "") -> int:
        """Get the context window for a provider + model combination."""
        if model and f"{provider}/{model}" in self._providers:
            return self._providers[f"{provider}/{model}"]
        return self._providers.get(provider, _PROVIDER_CONTEXT_WINDOWS["default"])

    def select_strategy(
        self,
        *,
        provider: str,
        model: str = "",
        current_tokens: int = 0,
    ) -> CompactionStrategy:
        """
        Select the optimal compaction strategy for a provider.

        Small-window providers (DeepSeek 64K, local 8K) get more aggressive
        compaction. Large-window providers (Google 2M) get lighter touch.
        """
        context_window = self.get_context_window(provider, model)
        usage_ratio = current_tokens / max(context_window, 1)

        # Select strategy based on provider window + usage
        if usage_ratio < 0.5:
            return CompactionStrategy.NONE
        elif usage_ratio < 0.7:
            return CompactionStrategy.SUMMARIZE
        elif usage_ratio < 0.85:
            if context_window <= 64_000:
                return CompactionStrategy.TRUNCATE
            return CompactionStrategy.SUMMARIZE
        elif usage_ratio < 0.95:
            if context_window <= 64_000:
                return CompactionStrategy.AGGRESSIVE
            return CompactionStrategy.KV_EVICT
        return CompactionStrategy.AGGRESSIVE

    def estimate_tokens_before_compaction(
        self, provider: str, model: str = ""
    ) -> int:
        """Estimate how many tokens can be used before compaction triggers."""
        context_window = self.get_context_window(provider, model)
        return int(context_window * 0.85)
