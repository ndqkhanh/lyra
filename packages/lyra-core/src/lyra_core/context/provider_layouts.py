"""Per-provider context-layout metadata (Phase CE.3, P2-1).

Different inference providers reward different prompt-cache layouts.
Anthropic wants explicit ``cache_control`` blocks; OpenAI relies on
implicit common-prefix detection; Gemini exposes a separate
``cachedContent`` resource; local llama.cpp / vLLM only see the
prompt at all.

This module is *metadata only* — it doesn't reorganise the actual
prompt assembly. It exposes a small lookup so callers (`pipeline.py`,
`compactor.py`, etc.) can ask "for provider X, how many cache
breakpoints does it honour, and which message role should the SOUL
block carry?" and behave accordingly.

The deeper per-provider rewrite (Open Question 3 on the context-engine
block spec) lands later. This file is the foothold: name the
distinctions, make them queryable, keep them in one place so we don't
hardcode provider names across the engine.
"""
from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Style tokens — keep these centralised so call sites can switch on them.
# ---------------------------------------------------------------------------


CACHE_STYLE_EXPLICIT = "explicit"  # Anthropic-style cache_control blocks
CACHE_STYLE_IMPLICIT = "implicit"  # OpenAI common-prefix detection
CACHE_STYLE_RESOURCE = "resource"  # Gemini cachedContent resource id
CACHE_STYLE_KV_LOCAL = "kv_local"  # local backend's own KV cache, opaque


SOUL_ROLE_SYSTEM = "system"
SOUL_ROLE_DEVELOPER = "developer"  # OpenAI o-series + reasoning models


@dataclass(frozen=True)
class ProviderLayout:
    """How a provider prefers its prompt laid out.

    Fields:
        provider: Canonical lower-case provider name.
        cache_style: One of the ``CACHE_STYLE_*`` constants. Tells the
            assembler whether to emit explicit cache breakpoints, rely
            on prefix stability, or hand off a cached-content handle.
        cache_breakpoints: How many explicit breakpoints the provider
            honours per request. ``0`` means none (implicit/local
            styles). Anthropic accepts 4 today.
        soul_role: Which role the SOUL block lands in. Most providers
            take ``"system"``; some accept a ``"developer"`` role
            distinct from the user-facing ``"system"`` slot.
        prefers_single_system: When True, all system content must be
            concatenated into one message (Gemini's preference). When
            False, multiple consecutive system messages are fine.
        max_tools: Soft cap on number of tool schemas before the
            description block itself starts to crowd context. ``None``
            means no known cap.
    """

    provider: str
    cache_style: str
    cache_breakpoints: int
    soul_role: str
    prefers_single_system: bool
    max_tools: int | None = None


ANTHROPIC = ProviderLayout(
    provider="anthropic",
    cache_style=CACHE_STYLE_EXPLICIT,
    cache_breakpoints=4,
    soul_role=SOUL_ROLE_SYSTEM,
    prefers_single_system=False,
    max_tools=64,
)

OPENAI = ProviderLayout(
    provider="openai",
    cache_style=CACHE_STYLE_IMPLICIT,
    cache_breakpoints=0,
    soul_role=SOUL_ROLE_DEVELOPER,
    prefers_single_system=False,
    max_tools=128,
)

GEMINI = ProviderLayout(
    provider="gemini",
    cache_style=CACHE_STYLE_RESOURCE,
    cache_breakpoints=0,
    soul_role=SOUL_ROLE_SYSTEM,
    prefers_single_system=True,
    max_tools=None,
)

OLLAMA = ProviderLayout(
    provider="ollama",
    cache_style=CACHE_STYLE_KV_LOCAL,
    cache_breakpoints=0,
    soul_role=SOUL_ROLE_SYSTEM,
    prefers_single_system=False,
    max_tools=None,
)

VLLM = ProviderLayout(
    provider="vllm",
    cache_style=CACHE_STYLE_KV_LOCAL,
    cache_breakpoints=0,
    soul_role=SOUL_ROLE_SYSTEM,
    prefers_single_system=False,
    max_tools=None,
)


_REGISTRY: dict[str, ProviderLayout] = {
    p.provider: p for p in (ANTHROPIC, OPENAI, GEMINI, OLLAMA, VLLM)
}


# Sensible default when we don't recognise the provider — implicit
# cache and a single system role. Picked deliberately to be the safest
# common subset across hosted providers.
DEFAULT = ProviderLayout(
    provider="default",
    cache_style=CACHE_STYLE_IMPLICIT,
    cache_breakpoints=0,
    soul_role=SOUL_ROLE_SYSTEM,
    prefers_single_system=False,
    max_tools=None,
)


def get_layout(provider: str | None) -> ProviderLayout:
    """Look up a layout by name. Unknown names return :data:`DEFAULT`."""
    if not provider:
        return DEFAULT
    key = provider.strip().lower()
    return _REGISTRY.get(key, DEFAULT)


def list_layouts() -> list[ProviderLayout]:
    """All registered layouts in canonical insertion order."""
    return list(_REGISTRY.values())


def supports_explicit_cache(provider: str | None) -> bool:
    """Sugar for the common branch: 'should I emit cache_control?'"""
    return get_layout(provider).cache_style == CACHE_STYLE_EXPLICIT


__all__ = [
    "ANTHROPIC",
    "CACHE_STYLE_EXPLICIT",
    "CACHE_STYLE_IMPLICIT",
    "CACHE_STYLE_KV_LOCAL",
    "CACHE_STYLE_RESOURCE",
    "DEFAULT",
    "GEMINI",
    "OLLAMA",
    "OPENAI",
    "ProviderLayout",
    "SOUL_ROLE_DEVELOPER",
    "SOUL_ROLE_SYSTEM",
    "VLLM",
    "get_layout",
    "list_layouts",
    "supports_explicit_cache",
]
