"""Provider registry with capability metadata (plan Phase 7).

Describes each LLM provider as a small, stable :class:`ProviderSpec`
dataclass so the CLI, the REPL, and any tool picking a model can make
decisions without hardcoding provider names. Capabilities mirror
NousResearch/hermes-agent's ``CANONICAL_PROVIDERS`` shape:

- ``supports_reasoning`` — reasoning-mode models (o3, claude-opus, etc.).
- ``supports_tools`` — function/tool calling available.
- ``context_window`` — max tokens for input context (best-known).
- ``default_model`` — sensible first-choice model name.
"""

from .registry import (
    PROVIDER_REGISTRY,
    ProviderSpec,
    get_provider,
    providers_by_capability,
)

__all__ = [
    "PROVIDER_REGISTRY",
    "ProviderSpec",
    "get_provider",
    "providers_by_capability",
]
