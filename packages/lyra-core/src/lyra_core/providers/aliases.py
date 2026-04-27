"""Model alias registry.

Short names (``opus``, ``sonnet``, ``haiku``, ``grok``, ``kimi``) that
claw-code / hermes / opencode users already type should resolve to
Lyra's canonical slugs. Resolution is case-insensitive and falls back
to the input if the alias is unknown — so passing the canonical slug
directly always works.

Design notes:

* The default registry is a module-level :class:`AliasRegistry` that
  the CLI imports; callers that want isolated resolution (tests,
  multi-tenant scenarios) can construct their own instance.
* Alias → slug is a many-to-one map: ``grok`` and ``grok-4`` both map
  to ``grok-4`` as of this file.
* The registry also carries a *provider key* per alias so the factory
  can route short names (e.g. ``--model opus``) to the right backend
  without waiting for the provider cascade.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(frozen=True)
class AliasEntry:
    slug: str
    provider: str   # "anthropic" / "xai" / "dashscope" / ...


@dataclass
class AliasRegistry:
    """Case-insensitive model alias → (canonical slug, provider) map."""

    _aliases: Dict[str, AliasEntry] = field(default_factory=dict)

    def register(self, alias: str, slug: str, *, provider: str = "") -> None:
        self._aliases[alias.lower().strip()] = AliasEntry(slug=slug, provider=provider)

    def resolve(self, model: str) -> str:
        norm = (model or "").lower().strip()
        entry = self._aliases.get(norm)
        return entry.slug if entry else (model or "").strip()

    def provider_for(self, model: str) -> Optional[str]:
        norm = (model or "").lower().strip()
        entry = self._aliases.get(norm)
        return entry.provider if entry and entry.provider else None

    def canonical_slugs(self) -> list[str]:
        """Return every canonical slug known to the registry, sorted.

        The registry maps many aliases onto fewer slugs (e.g. ``opus`` and
        ``claude-opus-4.5`` both resolve to ``claude-opus-4.5``). For
        embedded callers (``LyraClient.list_models``) we want the
        deduplicated, sorted *target* set rather than every alias the
        user might type, so this collapses duplicates and returns
        a stable ordering for tests / UIs.
        """
        return sorted({entry.slug for entry in self._aliases.values()})

    def aliases_for(self, slug: str) -> list[str]:
        """Return every alias that resolves to *slug* (sorted).

        Useful for surfaces that want to *show* "you can also type
        ``opus``, ``claude-opus-4.5``" beside the canonical slug
        without leaking the raw ``_aliases`` dict.
        """
        target = (slug or "").strip()
        return sorted(
            a for a, e in self._aliases.items() if e.slug == target
        )


DEFAULT_ALIASES = AliasRegistry()


def _seed(reg: AliasRegistry) -> None:
    for a, s in (
        ("opus", "claude-opus-4.5"),
        ("claude-opus-4.5", "claude-opus-4.5"),
        ("sonnet", "claude-sonnet-4.5"),
        ("claude-sonnet-4.5", "claude-sonnet-4.5"),
        ("haiku", "claude-haiku-4"),
        ("claude-haiku-4", "claude-haiku-4"),
    ):
        reg.register(a, s, provider="anthropic")
    for a, s in (("grok", "grok-4"), ("grok-4", "grok-4"),
                 ("grok-mini", "grok-4-mini"), ("grok-4-mini", "grok-4-mini"),
                 ("grok-3", "grok-3"), ("grok-2", "grok-2")):
        reg.register(a, s, provider="xai")
    for a, s in (("kimi", "kimi-k2.5"), ("kimi-k2.5", "kimi-k2.5"),
                 ("kimi-k1.5", "kimi-k1.5")):
        reg.register(a, s, provider="dashscope")
    for a in ("qwen-max", "qwen-plus", "qwen-turbo", "qwen3-coder"):
        reg.register(a, a, provider="dashscope")
    for a, s in (("llama-3.3", "llama-3.3-70b-versatile"),
                 ("llama-3.3-70b", "llama-3.3-70b-versatile")):
        reg.register(a, s, provider="groq")
    # DeepSeek small/smart split (v2.7.1).
    #
    # Lyra mimics Claude Code's "Haiku for cheap turns, Sonnet for
    # reasoning" pattern but on DeepSeek's catalog: a fast/cheap general
    # model for tool calls, summaries, and simple chat, and a slower
    # reasoning model for planning, multi-file refactors, and verifier
    # rounds. ``deepseek-v4-flash`` and ``deepseek-v4-pro`` are the
    # *user-facing* aliases callers type; they resolve to the real
    # DeepSeek API slugs (``deepseek-chat`` for the general/V3.x model
    # and ``deepseek-reasoner`` for the R1 chain-of-thought model).
    #
    # We expose both shapes (``deepseek-flash`` / ``deepseek-pro`` plus
    # the explicit ``v4`` versioned aliases) so users who copy the slug
    # from settings.json or our docs always land on something that
    # works. ``deepseek-chat`` and ``deepseek-reasoner`` themselves are
    # registered as identity aliases so callers can also paste the raw
    # API slug and skip translation.
    for a, s in (
        ("deepseek-v4-flash", "deepseek-chat"),
        ("deepseek-flash", "deepseek-chat"),
        ("deepseek-chat", "deepseek-chat"),
        ("deepseek-v4-pro", "deepseek-reasoner"),
        ("deepseek-pro", "deepseek-reasoner"),
        ("deepseek-reasoner", "deepseek-reasoner"),
        ("deepseek-coder", "deepseek-chat"),
    ):
        reg.register(a, s, provider="deepseek")


_seed(DEFAULT_ALIASES)


def resolve_alias(model: str) -> str:
    """Resolve a model alias against the default registry."""
    return DEFAULT_ALIASES.resolve(model)


def provider_key_for(model: str) -> Optional[str]:
    """Return the provider key for a model alias, or ``None`` if unknown."""
    return DEFAULT_ALIASES.provider_for(model)


def register_alias(alias: str, slug: str, *, provider: str = "") -> None:
    """Register a new alias in the default registry at runtime."""
    DEFAULT_ALIASES.register(alias, slug, provider=provider)


__all__ = [
    "AliasEntry",
    "AliasRegistry",
    "DEFAULT_ALIASES",
    "resolve_alias",
    "register_alias",
    "provider_key_for",
]
