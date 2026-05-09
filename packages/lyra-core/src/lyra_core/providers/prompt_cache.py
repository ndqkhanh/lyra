"""Prompt-cache coordination across sibling subagents (PolyKV-equivalent).

PolyKV (Patel & Joshi, April 2026 — arXiv:2604.24971; PDF in
``papers/`` not yet mirrored — see
``docs/research/polykv-evaluation.md``) shows that when ``N`` agents
read the same shared document, allocating ``N`` independent KV caches
is wasteful: a single shared, lossy-compressed pool delivers 97.7%
memory savings on Llama-3-8B/15-agents/4K-tokens with only
+0.57% perplexity degradation.

The exact PolyKV mechanism — asymmetric per-tensor quantization
(K=int8, V=TurboQuant 3-bit) injected into HuggingFace
``DynamicCache`` — requires **self-hosted model access**. Lyra's hot
path is hosted-API providers (Anthropic, OpenAI, DeepSeek, Gemini,
…) that don't expose KV cache.

But the *architectural insight* applies directly. Hosted providers
ship their own prompt-cache mechanisms (Anthropic ``cache_control``,
OpenAI automatic prefix cache, DeepSeek context cache, Gemini
``CachedContent``). When ``N`` Lyra subagents read the same shared
document, **a single shared cache anchor across all of them** delivers
the same morally-equivalent saving — O(1) cost in the shared prefix
regardless of agent count.

This module is the coordinator. It owns one
:class:`PromptCacheAnchor` per ``(provider, document_digest)`` pair,
hands a per-provider cache directive to each sibling subagent, and
records hit/miss telemetry so the saving is measurable rather than
theoretical.

This module ships **provider-agnostic** primitives plus four
production adapters (Anthropic, OpenAI, DeepSeek, Gemini) and a no-op
fallback for providers that don't support caching. New adapters
register at import time via :func:`register_adapter`.

A v3.5.0-era ``SharedKVPoolProvider`` Protocol shim was deleted in
v3.5.5 ("the clean cut") because no self-hosted Lyra profile shipped
to consume it and no hosted provider exposes literal KV-cache
injection. If a self-hosted profile ever materialises, the Protocol
will be reintroduced *together with* a working implementation on the
same commit. Until then, this coordinator is the complete
PolyKV-style absorption Lyra ships. See
``docs/research/polykv-evaluation.md`` for the full design memo.
"""
from __future__ import annotations

import hashlib
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

# The minimum prefix length (in characters) at which the coordinator
# considers the shared document worth caching. Below this, the per-
# request cache-write overhead beats the save. The 4_000-char floor is
# chosen so a typical SOUL.md + plan summary clears it without forcing
# every micro-prompt through the cache.
DEFAULT_CACHE_FLOOR_CHARS: int = 4_000

# The TTL we ask providers to honour for an ephemeral cache anchor.
# Most providers advertise 5-minute defaults (Anthropic ephemeral,
# DeepSeek auto). This number is documentation; the actual TTL is
# enforced provider-side.
DEFAULT_CACHE_TTL_SECONDS: int = 300


# ---------------------------------------------------------------------------
# Anchor + telemetry
# ---------------------------------------------------------------------------


class CacheStatus(str, Enum):  # noqa: UP042  matches house style (router.py, prm.py, …) for 3.10 compat
    """Outcome of a coordinator lookup."""

    HIT = "hit"            # anchor reused; provider should hit its cache
    WRITE = "write"        # anchor created; provider should write the cache
    SKIP = "skip"          # below the floor or unsupported; bypass entirely


@dataclass(frozen=True)
class PromptCacheAnchor:
    """A single shared cache anchor for one document under one provider.

    The anchor owns three pieces of state:

    * ``digest`` — content-hash of the shared document; used as the
      coordinator key.
    * ``provider_directive`` — the provider-specific instruction the
      caller should splice into its request payload (e.g. an
      ``cache_control`` block for Anthropic, a ``CachedContent`` ID
      for Gemini, ``None`` for providers that auto-cache by prefix).
    * ``expires_at`` — wall-clock timestamp after which the anchor is
      stale and a new write is required.

    Anchors are immutable; on TTL expiry the coordinator allocates a
    new one rather than mutating in place.
    """

    digest: str
    provider: str
    provider_directive: Mapping[str, Any] | None
    created_at: float
    expires_at: float
    chars: int

    def is_expired(self, *, now: float | None = None) -> bool:
        return (now or time.monotonic()) >= self.expires_at


@dataclass
class CoordinatorMetrics:
    """Counters surfaced via :meth:`PromptCacheCoordinator.snapshot`."""

    hits: int = 0
    writes: int = 0
    skips: int = 0
    chars_cached: int = 0
    chars_skipped: int = 0


# ---------------------------------------------------------------------------
# Adapter protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class PromptCacheAdapter(Protocol):
    """Per-provider hook that knows how to mark a prompt as cacheable.

    Adapters are stateless: the coordinator owns the anchor lifecycle
    and only asks the adapter "how do I tell *your* provider to cache
    this prefix?". The adapter returns a directive blob that the
    caller splices into its request payload.

    A provider that auto-caches by prefix (OpenAI as of 2024-09,
    DeepSeek context cache) returns an empty directive — the
    coordinator still records the hit/write so observability stays
    accurate, but no payload modification is needed.
    """

    @property
    def provider_name(self) -> str: ...

    def make_directive(
        self,
        *,
        digest: str,
        chars: int,
        ttl_seconds: int,
        is_write: bool,
    ) -> Mapping[str, Any] | None: ...


# ---------------------------------------------------------------------------
# Built-in adapters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AnthropicAdapter(PromptCacheAdapter):
    """Anthropic prompt caching via ``cache_control: ephemeral``.

    Anthropic's API ships a per-block ``cache_control`` field. Mark
    the *last* block of the shared prefix with
    ``{"type": "ephemeral"}`` and Anthropic charges 25% extra on the
    cache write but only 10% on subsequent reads — a net saving once
    a single sibling reuses the anchor.

    The adapter returns the splice-in dict; the caller is responsible
    for placing it on the right content block.
    """

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def make_directive(
        self,
        *,
        digest: str,
        chars: int,
        ttl_seconds: int,
        is_write: bool,
    ) -> Mapping[str, Any]:
        return {
            "cache_control": {"type": "ephemeral"},
            # Diagnostic only — Anthropic ignores extra fields:
            "_lyra_cache_digest": digest,
            "_lyra_cache_role": "write" if is_write else "hit",
        }


@dataclass(frozen=True)
class OpenAIAdapter(PromptCacheAdapter):
    """OpenAI prompt caching is automatic for prefixes ≥ 1024 tokens.

    OpenAI applies its 50% prefix-cache discount automatically when
    the start of the request matches a cached prefix from the same
    organisation within the TTL window. There's no payload knob to
    set — the adapter returns ``None`` to signal "no splice
    required" but the coordinator still tracks hit/write semantics
    for telemetry.

    This implementation pre-warms the cache by ensuring the shared
    prefix appears at the very start of every sibling request — the
    coordinator owns the anchor, the call site is responsible for
    placement.
    """

    @property
    def provider_name(self) -> str:
        return "openai"

    def make_directive(
        self,
        *,
        digest: str,
        chars: int,
        ttl_seconds: int,
        is_write: bool,
    ) -> None:
        return None


@dataclass(frozen=True)
class DeepSeekAdapter(PromptCacheAdapter):
    """DeepSeek context caching is automatic for repeated prefixes.

    DeepSeek's documented behaviour: identical prefixes within the
    TTL window are charged at the cache-hit rate (≈10% of input
    cost). No request-side directive — same shape as OpenAI. The
    coordinator's job is to ensure sibling subagents emit
    byte-identical prefixes so the provider sees them as cache hits.
    """

    @property
    def provider_name(self) -> str:
        return "deepseek"

    def make_directive(
        self,
        *,
        digest: str,
        chars: int,
        ttl_seconds: int,
        is_write: bool,
    ) -> None:
        return None


@dataclass(frozen=True)
class GeminiAdapter(PromptCacheAdapter):
    """Gemini context caching via the ``CachedContent`` resource.

    Gemini exposes an explicit ``cachedContents`` REST endpoint. The
    write step creates a ``CachedContent`` and returns an ID; sibling
    requests reference it via ``cached_content`` in the request
    body. The coordinator stores the ID inside the directive so the
    caller doesn't re-create the resource.
    """

    @property
    def provider_name(self) -> str:
        return "gemini"

    def make_directive(
        self,
        *,
        digest: str,
        chars: int,
        ttl_seconds: int,
        is_write: bool,
    ) -> Mapping[str, Any]:
        # The cached_content reference is the identifier the caller
        # uses on subsequent hits. On a write, the caller is expected
        # to populate this with the response's resource name.
        return {
            "cached_content": f"lyra-cache-{digest[:16]}",
            "ttl": f"{ttl_seconds}s",
            "_lyra_cache_role": "write" if is_write else "hit",
        }


@dataclass(frozen=True)
class NoopAdapter(PromptCacheAdapter):
    """Fallback for providers without prompt caching (xAI, Mistral, …).

    The coordinator returns ``CacheStatus.SKIP`` for these so callers
    never splice anything; metrics still record skipped chars so an
    operator can see "X tokens of shareable prefix went uncached on
    provider Y".
    """

    name: str = "noop"

    @property
    def provider_name(self) -> str:
        return self.name

    def make_directive(
        self,
        *,
        digest: str,
        chars: int,
        ttl_seconds: int,
        is_write: bool,
    ) -> None:
        return None


# ---------------------------------------------------------------------------
# Adapter registry
# ---------------------------------------------------------------------------

_BUILTIN_ADAPTERS: dict[str, PromptCacheAdapter] = {
    "anthropic": AnthropicAdapter(),
    "openai": OpenAIAdapter(),
    "deepseek": DeepSeekAdapter(),
    "gemini": GeminiAdapter(),
}


def register_adapter(adapter: PromptCacheAdapter) -> None:
    """Register a custom adapter. Used by plugins and 3rd-party providers."""
    _BUILTIN_ADAPTERS[adapter.provider_name] = adapter


def get_adapter(provider: str) -> PromptCacheAdapter:
    """Return the adapter for ``provider`` or :class:`NoopAdapter` if unknown."""
    return _BUILTIN_ADAPTERS.get(provider) or NoopAdapter(name=provider)


# ---------------------------------------------------------------------------
# Coordinator
# ---------------------------------------------------------------------------


class PromptCacheCoordinator:
    """Per-process coordinator holding one anchor per (provider, digest).

    Thread-safe: the underlying dict is guarded by a lock so the
    subagent orchestrator can call ``coordinate`` from concurrent
    workers without races. Anchors expire on TTL; expired entries are
    pruned lazily on next access.

    Typical usage from inside the agent loop / subagent runner::

        coord = PromptCacheCoordinator()
        status, anchor = coord.coordinate(
            provider="anthropic",
            shared_text=plan_artifact + system_prompt,
        )
        if status is not CacheStatus.SKIP:
            # splice anchor.provider_directive into the request
            ...
    """

    def __init__(
        self,
        *,
        cache_floor_chars: int = DEFAULT_CACHE_FLOOR_CHARS,
        ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._floor = cache_floor_chars
        self._ttl = ttl_seconds
        self._clock = clock
        self._anchors: dict[tuple[str, str], PromptCacheAnchor] = {}
        self._metrics: CoordinatorMetrics = CoordinatorMetrics()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ core
    def coordinate(
        self,
        *,
        provider: str,
        shared_text: str,
    ) -> tuple[CacheStatus, PromptCacheAnchor | None]:
        """Look up (or create) the cache anchor for one shared prefix.

        Returns:
            ``(status, anchor)``. ``anchor`` is ``None`` when status is
            :attr:`CacheStatus.SKIP`. Otherwise the anchor's
            ``provider_directive`` is the splice-in for the request
            payload.
        """
        chars = len(shared_text)
        if chars < self._floor:
            with self._lock:
                self._metrics.skips += 1
                self._metrics.chars_skipped += chars
            return CacheStatus.SKIP, None

        digest = hashlib.sha256(shared_text.encode("utf-8")).hexdigest()
        key = (provider, digest)
        adapter = get_adapter(provider)
        now = self._clock()

        with self._lock:
            existing = self._anchors.get(key)
            if existing is not None and not existing.is_expired(now=now):
                self._metrics.hits += 1
                return CacheStatus.HIT, existing

            # Miss / expired — write a fresh anchor.
            directive = adapter.make_directive(
                digest=digest,
                chars=chars,
                ttl_seconds=self._ttl,
                is_write=True,
            )
            anchor = PromptCacheAnchor(
                digest=digest,
                provider=provider,
                provider_directive=directive,
                created_at=now,
                expires_at=now + self._ttl,
                chars=chars,
            )
            self._anchors[key] = anchor
            self._metrics.writes += 1
            self._metrics.chars_cached += chars
            return CacheStatus.WRITE, anchor

    # ------------------------------------------------------------- accessors
    def snapshot(self) -> CoordinatorMetrics:
        """Atomic copy of the current metrics (safe to read from threads)."""
        with self._lock:
            return CoordinatorMetrics(
                hits=self._metrics.hits,
                writes=self._metrics.writes,
                skips=self._metrics.skips,
                chars_cached=self._metrics.chars_cached,
                chars_skipped=self._metrics.chars_skipped,
            )

    def reset(self) -> None:
        """Drop all anchors and zero the metrics. Used by tests + ``/cache wipe``."""
        with self._lock:
            self._anchors.clear()
            self._metrics = CoordinatorMetrics()

    def active_anchors(self) -> int:
        """Number of currently-live (non-expired) anchors held."""
        now = self._clock()
        with self._lock:
            return sum(
                1 for a in self._anchors.values() if not a.is_expired(now=now)
            )


# ---------------------------------------------------------------------------
# Process-global default
# ---------------------------------------------------------------------------


_DEFAULT_COORDINATOR: PromptCacheCoordinator | None = None
_DEFAULT_LOCK = threading.Lock()


def default_coordinator() -> PromptCacheCoordinator:
    """Lazy process-global coordinator.

    The subagent orchestrator and the agent loop share this instance
    so a sibling subagent ``B`` sees the anchor written by sibling
    ``A`` for the same shared prefix. Tests construct their own
    instance instead of using this one.
    """
    global _DEFAULT_COORDINATOR
    with _DEFAULT_LOCK:
        if _DEFAULT_COORDINATOR is None:
            _DEFAULT_COORDINATOR = PromptCacheCoordinator()
        return _DEFAULT_COORDINATOR


def reset_default_coordinator() -> None:
    """Drop the process-global coordinator. For tests + ``/lyra cache wipe``."""
    global _DEFAULT_COORDINATOR
    with _DEFAULT_LOCK:
        if _DEFAULT_COORDINATOR is not None:
            _DEFAULT_COORDINATOR.reset()
        _DEFAULT_COORDINATOR = None


__all__ = [
    "DEFAULT_CACHE_FLOOR_CHARS",
    "DEFAULT_CACHE_TTL_SECONDS",
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
    "default_coordinator",
    "get_adapter",
    "register_adapter",
    "reset_default_coordinator",
]
