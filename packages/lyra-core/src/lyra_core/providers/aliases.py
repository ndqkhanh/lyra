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

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class AliasEntry:
    slug: str
    provider: str   # "anthropic" / "xai" / "dashscope" / ...


@dataclass
class AliasRegistry:
    """Case-insensitive model alias → (canonical slug, provider) map.

    Two layers of resolution:

    1. **Exact aliases** (``register``) — short names like ``opus`` and
       version-pinned slugs like ``deepseek-v4-pro``.
    2. **Pattern aliases** (``register_pattern``) — regexes for whole
       families (e.g. ``^deepseek-v\\d+-pro$``) so newly-released versions
       resolve correctly without a code change. Patterns are tried only
       after exact lookup misses, so explicit registrations always win.
    """

    _aliases: Dict[str, AliasEntry] = field(default_factory=dict)
    _patterns: List[Tuple[re.Pattern[str], AliasEntry]] = field(default_factory=list)

    def register(self, alias: str, slug: str, *, provider: str = "") -> None:
        self._aliases[alias.lower().strip()] = AliasEntry(slug=slug, provider=provider)

    def register_pattern(self, pattern: str, slug: str, *, provider: str = "") -> None:
        """Register a regex pattern that resolves to ``slug``.

        Patterns are matched case-insensitively against the trimmed
        model name. Use this for model families with predictable
        versioning (``deepseek-vN-pro``, ``llama-3.X-instruct``).
        """
        compiled = re.compile(pattern, re.IGNORECASE)
        self._patterns.append((compiled, AliasEntry(slug=slug, provider=provider)))

    def _lookup(self, model: str) -> Optional[AliasEntry]:
        norm = (model or "").lower().strip()
        if not norm:
            return None
        entry = self._aliases.get(norm)
        if entry is not None:
            return entry
        for pattern, pat_entry in self._patterns:
            if pattern.fullmatch(norm):
                return pat_entry
        return None

    def resolve(self, model: str) -> str:
        entry = self._lookup(model)
        return entry.slug if entry else (model or "").strip()

    def provider_for(self, model: str) -> Optional[str]:
        entry = self._lookup(model)
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
    # ---------------------------------------------------------------- Anthropic
    # Claude family. ``opus`` / ``sonnet`` / ``haiku`` resolve to the
    # *current* generation; older versions are reachable by version-pinned
    # alias (``opus-4``, ``sonnet-3.5``) for users on legacy contracts.
    for a, s in (
        ("opus", "claude-opus-4.5"),
        ("opus-latest", "claude-opus-4.7"),
        ("opus-4.7", "claude-opus-4.7"),
        ("opus-4.6", "claude-opus-4.6"),
        ("opus-4.5", "claude-opus-4.5"),
        ("opus-4.1", "claude-opus-4.1"),
        ("opus-4", "claude-opus-4"),
        ("opus-3", "claude-3-opus"),
        ("claude-opus-4.7", "claude-opus-4.7"),
        ("claude-opus-4.6", "claude-opus-4.6"),
        ("claude-opus-4.5", "claude-opus-4.5"),
        ("claude-opus-4.1", "claude-opus-4.1"),
        ("claude-opus-4", "claude-opus-4"),
        ("claude-3-opus", "claude-3-opus"),
        ("sonnet", "claude-sonnet-4.5"),
        ("sonnet-latest", "claude-sonnet-4.5"),
        ("sonnet-4.6", "claude-sonnet-4.6"),
        ("sonnet-4.5", "claude-sonnet-4.5"),
        ("sonnet-4", "claude-sonnet-4"),
        ("sonnet-3.7", "claude-3.7-sonnet"),
        ("sonnet-3.5", "claude-3.5-sonnet"),
        ("claude-sonnet-4.6", "claude-sonnet-4.6"),
        ("claude-sonnet-4.5", "claude-sonnet-4.5"),
        ("claude-sonnet-4", "claude-sonnet-4"),
        ("claude-3.7-sonnet", "claude-3.7-sonnet"),
        ("claude-3.5-sonnet", "claude-3.5-sonnet"),
        # NB: ``haiku`` keeps pointing at claude-haiku-4 to preserve the
        # alias contract pinned by ``test_resolves_haiku_to_current_slug``.
        # Users on Haiku 4.5 should type ``haiku-4.5`` explicitly.
        ("haiku", "claude-haiku-4"),
        ("haiku-4.5", "claude-haiku-4.5"),
        ("haiku-4", "claude-haiku-4"),
        ("haiku-3.5", "claude-3.5-haiku"),
        ("haiku-3", "claude-3-haiku"),
        ("claude-haiku-4.5", "claude-haiku-4.5"),
        ("claude-haiku-4", "claude-haiku-4"),
        ("claude-3.5-haiku", "claude-3.5-haiku"),
        ("claude-3-haiku", "claude-3-haiku"),
    ):
        reg.register(a, s, provider="anthropic")

    # ---------------------------------------------------------------- OpenAI
    # GPT-5 / GPT-4.x. The o-series (reasoning) lives in its own provider
    # bucket so dispatch can flip on extended thinking automatically.
    for a, s in (
        ("gpt", "gpt-5.5"),
        ("gpt-5.5", "gpt-5.5"),
        ("gpt5.5", "gpt-5.5"),
        ("gpt-5.5-pro", "gpt-5.5-pro"),
        ("gpt-5.5-thinking", "gpt-5.5-thinking"),
        ("gpt-5.5-instant", "gpt-5.5-instant"),
        ("gpt-5", "gpt-5"),
        ("gpt5", "gpt-5"),
        ("gpt-5-pro", "gpt-5-pro"),
        ("gpt-5-mini", "gpt-5-mini"),
        ("gpt-5-nano", "gpt-5-nano"),
        ("gpt-5-chat", "gpt-5-chat-latest"),
        ("gpt-5-chat-latest", "gpt-5-chat-latest"),
        ("gpt-4o", "gpt-4o"),
        ("4o", "gpt-4o"),
        ("gpt-4o-mini", "gpt-4o-mini"),
        ("4o-mini", "gpt-4o-mini"),
        ("chatgpt-4o-latest", "chatgpt-4o-latest"),
        ("gpt-4o-latest", "chatgpt-4o-latest"),
        ("gpt-4.1", "gpt-4.1"),
        ("gpt-4.1-mini", "gpt-4.1-mini"),
        ("gpt-4.1-nano", "gpt-4.1-nano"),
        ("gpt-4-turbo", "gpt-4-turbo"),
        ("gpt-4", "gpt-4"),
        ("gpt-3.5-turbo", "gpt-3.5-turbo"),
    ):
        reg.register(a, s, provider="openai")

    for a, s in (
        ("o3", "o3"),
        ("o3-pro", "o3-pro"),
        ("o3-mini", "o3-mini"),
        ("o3-deep-research", "o3-deep-research"),
        ("o4-mini", "o4-mini"),
        ("o4-mini-deep-research", "o4-mini-deep-research"),
        ("o1", "o1"),
        ("o1-pro", "o1-pro"),
        ("o1-mini", "o1-mini"),
        ("o1-preview", "o1-preview"),
    ):
        reg.register(a, s, provider="openai-reasoning")

    # ---------------------------------------------------------------- Google
    # Gemini. ``gemini`` / ``gemini-pro`` / ``gemini-flash`` are the
    # short forms; explicit version pins live alongside.
    for a, s in (
        ("gemini", "gemini-3.1-pro"),
        ("gemini-pro", "gemini-3.1-pro"),
        ("gemini-flash", "gemini-3.1-flash"),
        ("gemini-3.1-pro", "gemini-3.1-pro"),
        ("gemini-3.1-flash", "gemini-3.1-flash"),
        ("gemini-3.1-flash-lite", "gemini-3.1-flash-lite"),
        ("gemini-3", "gemini-3.1-pro"),
        ("gemini-2.5", "gemini-2.5-pro"),
        ("gemini-2.5-pro", "gemini-2.5-pro"),
        ("gemini-2.5-flash", "gemini-2.5-flash"),
        ("gemini-2.5-flash-lite", "gemini-2.5-flash-lite"),
        ("gemini-2.5-flash-thinking", "gemini-2.5-flash-thinking"),
        ("gemini-2.5-deep-think", "gemini-2.5-deep-think"),
        ("gemini-2.0-flash", "gemini-2.0-flash"),
        ("gemini-2.0-flash-thinking", "gemini-2.0-flash-thinking"),
        ("gemini-2.0-pro", "gemini-2.0-pro"),
        ("gemini-1.5-pro", "gemini-1.5-pro"),
        ("gemini-1.5-flash", "gemini-1.5-flash"),
        ("gemini-1.5-flash-8b", "gemini-1.5-flash-8b"),
        ("gemini-exp", "gemini-exp-1206"),
    ):
        reg.register(a, s, provider="gemini")

    # ---------------------------------------------------------------- xAI Grok
    for a, s in (
        ("grok", "grok-4"),
        ("grok-4", "grok-4"),
        ("grok-4-mini", "grok-4-mini"),
        ("grok-mini", "grok-4-mini"),
        ("grok-4-fast", "grok-4-fast"),
        ("grok-4-fast-reasoning", "grok-4-fast-reasoning"),
        ("grok-code-fast", "grok-code-fast-1"),
        ("grok-code-fast-1", "grok-code-fast-1"),
        ("grok-3", "grok-3"),
        ("grok-3-mini", "grok-3-mini"),
        ("grok-3-fast", "grok-3-fast"),
        ("grok-2", "grok-2"),
        ("grok-2-vision", "grok-2-vision-1212"),
        ("grok-beta", "grok-beta"),
    ):
        reg.register(a, s, provider="xai")

    # ---------------------------------------------------------------- Kimi / Moonshot
    # Routed via ``dashscope`` to preserve the contract pinned by
    # ``test_provider_key_for_resolves_to_expected_bucket``. Users with a
    # native MOONSHOT_API_KEY can override at the env-var level — alias
    # resolution is independent of provider-pick.
    for a, s in (
        ("kimi", "kimi-k2.5"),
        ("kimi-latest", "kimi-k2.5"),
        ("kimi-k2.5", "kimi-k2.5"),
        ("kimi-k2", "kimi-k2-instruct"),
        ("kimi-k2-instruct", "kimi-k2-instruct"),
        ("kimi-k2-0711", "kimi-k2-0711-preview"),
        ("kimi-k2-0711-preview", "kimi-k2-0711-preview"),
        ("kimi-k1.5", "kimi-k1.5"),
        ("moonshot", "moonshot-v1-128k"),
        ("moonshot-v1", "moonshot-v1-128k"),
        ("moonshot-v1-8k", "moonshot-v1-8k"),
        ("moonshot-v1-32k", "moonshot-v1-32k"),
        ("moonshot-v1-128k", "moonshot-v1-128k"),
    ):
        reg.register(a, s, provider="dashscope")

    # ---------------------------------------------------------------- Qwen / Alibaba
    for a, s in (
        ("qwen", "qwen-max"),
        ("qwen-max", "qwen-max"),
        ("qwen-max-latest", "qwen-max-latest"),
        ("qwen-plus", "qwen-plus"),
        ("qwen-turbo", "qwen-turbo"),
        ("qwen-long", "qwen-long"),
        ("qwen3", "qwen3-max"),
        ("qwen3-max", "qwen3-max"),
        ("qwen3-235b", "qwen3-235b-a22b-instruct"),
        ("qwen3-72b", "qwen3-72b"),
        ("qwen3-32b", "qwen3-32b"),
        ("qwen3-coder", "qwen3-coder-480b-a35b-instruct"),
        ("qwen3-coder-plus", "qwen3-coder-plus"),
        ("qwen2.5-72b", "qwen2.5-72b-instruct"),
        ("qwen2.5-coder", "qwen2.5-coder-32b-instruct"),
        ("qwen2.5-coder-32b", "qwen2.5-coder-32b-instruct"),
        ("qwq", "qwq-32b-preview"),
        ("qwq-32b", "qwq-32b-preview"),
        ("qvq", "qvq-72b-preview"),
        ("qvq-72b", "qvq-72b-preview"),
    ):
        reg.register(a, s, provider="dashscope")

    # ---------------------------------------------------------------- Meta Llama (Groq)
    for a, s in (
        ("llama", "llama-3.3-70b-versatile"),
        ("llama-3.3", "llama-3.3-70b-versatile"),
        ("llama-3.3-70b", "llama-3.3-70b-versatile"),
        ("llama-3.3-70b-versatile", "llama-3.3-70b-versatile"),
        ("llama-3.1-70b", "llama-3.1-70b-versatile"),
        ("llama-3.1-8b", "llama-3.1-8b-instant"),
        ("llama-4-scout", "llama-4-scout-17b-16e-instruct"),
        ("llama-4-maverick", "llama-4-maverick-17b-128e-instruct"),
        ("llama4-scout", "llama-4-scout-17b-16e-instruct"),
        ("llama4-maverick", "llama-4-maverick-17b-128e-instruct"),
    ):
        reg.register(a, s, provider="groq")

    # ---------------------------------------------------------------- Mistral
    for a, s in (
        ("mistral", "mistral-large-latest"),
        ("mistral-large", "mistral-large-latest"),
        ("mistral-large-latest", "mistral-large-latest"),
        ("mistral-medium", "mistral-medium"),
        ("mistral-small", "mistral-small-latest"),
        ("mistral-small-latest", "mistral-small-latest"),
        ("mistral-nemo", "open-mistral-nemo"),
        ("open-mistral-nemo", "open-mistral-nemo"),
        ("codestral", "codestral-latest"),
        ("codestral-latest", "codestral-latest"),
        ("ministral-8b", "ministral-8b-latest"),
        ("ministral-3b", "ministral-3b-latest"),
        ("pixtral", "pixtral-large-latest"),
        ("pixtral-large", "pixtral-large-latest"),
        ("magistral", "magistral-medium-latest"),
        ("magistral-medium", "magistral-medium-latest"),
    ):
        reg.register(a, s, provider="mistral")

    # ---------------------------------------------------------------- Cerebras
    for a in (
        "llama3.3-70b",
        "llama-4-scout-17b-16e-instruct",
        "qwen-3-32b",
        "qwen-3-coder",
        "qwen-3-235b",
    ):
        reg.register(a, a, provider="cerebras")

    # ---------------------------------------------------------------- OpenRouter
    # Meta-provider — most popular slugs surface here so muscle-memory
    # type-ahead works. The full 300+ catalog stays reachable via the
    # raw ``openrouter/provider/model`` slug (identity-resolved).
    for a, s in (
        ("openrouter", "openrouter/auto"),
        ("openrouter/auto", "openrouter/auto"),
        ("openrouter/anthropic/claude-opus-4.5", "openrouter/anthropic/claude-opus-4.5"),
        ("openrouter/anthropic/claude-sonnet-4.5", "openrouter/anthropic/claude-sonnet-4.5"),
        ("openrouter/openai/gpt-5", "openrouter/openai/gpt-5"),
        ("openrouter/openai/o3", "openrouter/openai/o3"),
        ("openrouter/google/gemini-2.5-pro", "openrouter/google/gemini-2.5-pro"),
        ("openrouter/deepseek/deepseek-r1", "openrouter/deepseek/deepseek-r1"),
        ("openrouter/deepseek/deepseek-chat", "openrouter/deepseek/deepseek-chat"),
        ("openrouter/x-ai/grok-4", "openrouter/x-ai/grok-4"),
        ("openrouter/moonshotai/kimi-k2", "openrouter/moonshotai/kimi-k2"),
        ("openrouter/qwen/qwen3-coder", "openrouter/qwen/qwen3-coder"),
        ("openrouter/meta-llama/llama-4-maverick", "openrouter/meta-llama/llama-4-maverick"),
        ("openrouter/mistralai/mistral-large", "openrouter/mistralai/mistral-large"),
    ):
        reg.register(a, s, provider="openrouter")

    # ---------------------------------------------------------------- DeepSeek
    # Small/smart split (v2.7.1).
    #
    # Lyra mimics Claude Code's "Haiku for cheap turns, Sonnet for
    # reasoning" pattern but on DeepSeek's catalog: a fast/cheap general
    # model for tool calls, summaries, and simple chat, and a slower
    # reasoning model for planning, multi-file refactors, and verifier
    # rounds. ``deepseek-v4-flash`` and ``deepseek-v4-pro`` are the
    # *user-facing* aliases callers type; they resolve to the real
    # DeepSeek API slugs (``deepseek-chat`` for the general/V3.x model
    # and ``deepseek-reasoner`` for the R1 chain-of-thought model).
    for a, s in (
        ("deepseek", "deepseek-chat"),
        ("deepseek-v4-flash", "deepseek-chat"),
        ("deepseek-flash", "deepseek-chat"),
        ("deepseek-chat", "deepseek-chat"),
        ("deepseek-v3", "deepseek-chat"),
        ("deepseek-v3.1", "deepseek-chat"),
        ("deepseek-v3.2", "deepseek-chat"),
        ("deepseek-v4-pro", "deepseek-reasoner"),
        ("deepseek-pro", "deepseek-reasoner"),
        ("deepseek-reasoner", "deepseek-reasoner"),
        ("deepseek-r1", "deepseek-reasoner"),
        ("deepseek-r1-distill", "deepseek-reasoner"),
        ("deepseek-r2", "deepseek-reasoner"),
        ("deepseek-coder", "deepseek-chat"),
        ("deepseek-coder-v2", "deepseek-coder-v2"),
        ("deepseek-vl2", "deepseek-vl2"),
    ):
        reg.register(a, s, provider="deepseek")

    # Future-proof DeepSeek versions: any ``deepseek-vN(.M)?-suffix``
    # routes to the canonical API slug for its family.
    reg.register_pattern(
        r"^deepseek-v\d+(?:\.\d+)?-(?:pro|reasoner|smart|smart-reasoning)$",
        "deepseek-reasoner",
        provider="deepseek",
    )
    reg.register_pattern(
        r"^deepseek-v\d+(?:\.\d+)?-(?:flash|chat|fast|small|coder|cheap)$",
        "deepseek-chat",
        provider="deepseek",
    )

    # ---------------------------------------------------------------- Ollama (local)
    for a in (
        "llama3.2",
        "llama3.1",
        "qwen2.5-coder",
        "deepseek-r1:7b",
        "phi4",
        "phi-4",
        "gemma3",
        "mistral-nemo",
        "mixtral",
    ):
        reg.register(a, a, provider="ollama")


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


def register_pattern(pattern: str, slug: str, *, provider: str = "") -> None:
    """Register a regex pattern in the default registry at runtime."""
    DEFAULT_ALIASES.register_pattern(pattern, slug, provider=provider)


__all__ = [
    "AliasEntry",
    "AliasRegistry",
    "DEFAULT_ALIASES",
    "resolve_alias",
    "register_alias",
    "register_pattern",
    "provider_key_for",
]
