"""Provider registry with capability metadata (plan Phase 7).

Describes each LLM provider as a small, stable :class:`ProviderSpec`
dataclass so the CLI, the REPL, and any tool picking a model can make
decisions without hardcoding provider names. Capabilities mirror
NousResearch/hermes-agent's ``CANONICAL_PROVIDERS`` shape:

- ``supports_reasoning`` — reasoning-mode models (o3, claude-opus, etc.).
- ``supports_tools`` — function/tool calling available.
- ``context_window`` — max tokens for input context (best-known).
- ``default_model`` — sensible first-choice model name.

Phase 5g (Apr 2026) added the prompt-cache coordinator — the PolyKV
(arXiv:2604.24971) absorption for hosted-API providers. See
:mod:`lyra_core.providers.prompt_cache` for the production mechanism
that ships against Anthropic, OpenAI, DeepSeek, and Gemini cache
discounts.
"""

from .prompt_cache import (
    DEFAULT_CACHE_FLOOR_CHARS,
    DEFAULT_CACHE_TTL_SECONDS,
    AnthropicAdapter,
    CacheStatus,
    CoordinatorMetrics,
    DeepSeekAdapter,
    GeminiAdapter,
    NoopAdapter,
    OpenAIAdapter,
    PromptCacheAdapter,
    PromptCacheAnchor,
    PromptCacheCoordinator,
    default_coordinator,
    get_adapter,
    register_adapter,
    reset_default_coordinator,
)
from .registry import (
    PROVIDER_REGISTRY,
    ProviderSpec,
    get_provider,
    providers_by_capability,
)

__all__ = [
    "DEFAULT_CACHE_FLOOR_CHARS",
    "DEFAULT_CACHE_TTL_SECONDS",
    "PROVIDER_REGISTRY",
    "AnthropicAdapter",
    "CacheStatus",
    "CoordinatorMetrics",
    "DeepSeekAdapter",
    "GeminiAdapter",
    "NoopAdapter",
    "OpenAIAdapter",
    "PromptCacheAdapter",
    "PromptCacheAnchor",
    "PromptCacheCoordinator",
    "ProviderSpec",
    "default_coordinator",
    "get_adapter",
    "get_provider",
    "providers_by_capability",
    "register_adapter",
    "reset_default_coordinator",
]
