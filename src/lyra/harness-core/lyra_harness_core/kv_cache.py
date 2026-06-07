"""KV-Cache-First Context Design — P2-B3 (CRITICAL, LOW effort).

Stable prompt prefix, append-only context, and explicit cache breakpoints.
10x cost differential between cached and uncached tokens drives every
design choice here.

See: plan-phase2-memory.md §4.3, Manus Context Engineering
"""
from __future__ import annotations

import hashlib
import json


# ---------------------------------------------------------------------------
# Cache Breakpoints
# ---------------------------------------------------------------------------


class CacheBreakpoint:
    """Marks a position in a prompt where KV-cache can split.

    A breakpoint after the system prompt (stable prefix) allows
    the system-prompt cache to be reused across every turn, while
    only the user/assistant suffix is recomputed.
    """

    __slots__ = ("name", "position", "reason")

    def __init__(self, name: str, position: int, reason: str = "") -> None:
        self.name = name
        self.position = position
        self.reason = reason

    def __repr__(self) -> str:
        return f"CacheBreakpoint({self.name!r}, pos={self.position})"


# ---------------------------------------------------------------------------
# Stable Prompt Prefix
# ---------------------------------------------------------------------------


def stable_system_prefix(system_prompt: str) -> str:
    """Build a stable system-prompt prefix suitable for KV-cache reuse.

    The system prompt is wrapped WITHOUT any timestamps, session IDs,
    or counters that would vary between requests. The result is a
    deterministic prefix whose KV-cache can be shared across all
    sessions using the same system prompt.

    Returns the stable prefix text.
    """
    return system_prompt


def cache_fingerprint(prompt: str) -> str:
    """Compute a deterministic fingerprint for KV-cache lookup.

    Two prompts with the same fingerprint can share a KV-cache.
    Returns the first 16 hex chars of SHA-256.
    """
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Append-Only Context
# ---------------------------------------------------------------------------


class AppendOnlyContext:
    """A context buffer that only allows appending, never modification.

    Once content is committed, it cannot be changed — preserving
    KV-cache coherence. Modifying previously-sent content would
    invalidate the cache for all downstream tokens.

    Usage::

        ctx = AppendOnlyContext()
        ctx.append_system("You are a helpful assistant.")
        ctx.append_user("What is 2+2?")
        ctx.append_assistant("4")
        ctx.append_user("Now multiply by 3.")
        # ctx.text  →  concatenated prompt
        # ctx.breakpoints  →  [CacheBreakpoint after system prompt]
    """

    def __init__(self) -> None:
        self._segments: list[tuple[str, str]] = []  # (role, content)
        self._breakpoints: list[CacheBreakpoint] = []
        self._char_count = 0

    def append(self, role: str, content: str) -> int:
        """Append a role-tagged segment. Returns the new total length."""
        self._segments.append((role, content))
        self._char_count += len(content)
        return self._char_count

    def append_system(self, content: str) -> int:
        """Append a system message.

        A system-message breakpoint is recorded immediately after it,
        so the system prompt can be cached across turns.
        """
        pos = self._char_count + len(content)
        self._breakpoints.append(
            CacheBreakpoint("system_prompt", pos, "stable prefix boundary")
        )
        return self.append("system", content)

    def append_user(self, content: str) -> int:
        return self.append("user", content)

    def append_assistant(self, content: str) -> int:
        return self.append("assistant", content)

    def append_tool_result(self, tool_name: str, content: str) -> int:
        return self.append("tool", content)

    def text(self, separator: str = "\n\n") -> str:
        """Return the full concatenated prompt text."""
        return separator.join(content for _, content in self._segments)

    @property
    def breakpoints(self) -> list[CacheBreakpoint]:
        """Cache breakpoints marking stable prefix boundaries."""
        return list(self._breakpoints)

    @property
    def char_count(self) -> int:
        return self._char_count

    @property
    def segment_count(self) -> int:
        return len(self._segments)

    @property
    def is_empty(self) -> bool:
        return len(self._segments) == 0

    def snapshot(self) -> list[tuple[str, str]]:
        """Return an immutable copy of all segments."""
        return list(self._segments)

    def cacheable_prefix(self) -> str:
        """Return the portion of the prompt that is cacheable.

        Everything up to and including the first non-system segment
        is stable and can be cached. For a typical setup, this is
        just the system prompt.
        """
        parts: list[str] = []
        for role, content in self._segments:
            if role == "system":
                parts.append(content)
            else:
                break
        return "\n\n".join(parts)

    def cacheable_prefix_length(self) -> int:
        """Character count of the cacheable prefix."""
        return len(self.cacheable_prefix())

    def __len__(self) -> int:
        return self._char_count


# ---------------------------------------------------------------------------
# Deterministic Serializer
# ---------------------------------------------------------------------------


class CacheFriendlySerializer:
    """Produces deterministic JSON output for KV-cache reuse.

    Stable key ordering, no whitespace variation, and consistent
    formatting ensure identical inputs produce identical byte sequences
    every time — maximizing cache hit rates for structured tool output.
    """

    def __init__(self, indent: int | None = None, sort_keys: bool = True) -> None:
        self._indent = indent
        self._sort_keys = sort_keys

    def dumps(self, obj: object) -> str:
        """Serialize with stable, deterministic output."""
        return json.dumps(
            obj,
            indent=self._indent,
            sort_keys=self._sort_keys,
            ensure_ascii=False,
            default=str,
        )

    def tool_output(self, tool_name: str, result: object) -> str:
        """Serialize tool output deterministically.

        Keys are sorted so repeated identical results produce
        byte-for-byte identical serializations.
        """
        return self.dumps({"result": result, "tool": tool_name})

    def message(self, role: str, content: str) -> str:
        """Serialize a chat message deterministically."""
        return self.dumps({"content": content, "role": role})


# ---------------------------------------------------------------------------
# Cache-Aware Prompt Assembly
# ---------------------------------------------------------------------------


def estimate_cache_savings(
    total_tokens: int,
    cacheable_tokens: int,
    *,
    cached_price_per_mtok: float = 0.30,
    uncached_price_per_mtok: float = 3.00,
) -> dict[str, float]:
    """Estimate cost savings from KV-cache reuse.

    Returns a dict with cached_cost, uncached_cost, and savings.
    """
    cached = (cacheable_tokens / 1_000_000) * cached_price_per_mtok
    uncached = ((total_tokens - cacheable_tokens) / 1_000_000) * uncached_price_per_mtok
    full_uncached = (total_tokens / 1_000_000) * uncached_price_per_mtok

    return {
        "cached_cost": round(cached + uncached, 6),
        "uncached_cost": round(full_uncached, 6),
        "savings": round(full_uncached - (cached + uncached), 6),
        "cache_hit_rate": round(cacheable_tokens / total_tokens, 4) if total_tokens else 0,
    }


__all__ = [
    "AppendOnlyContext",
    "CacheBreakpoint",
    "CacheFriendlySerializer",
    "cache_fingerprint",
    "estimate_cache_savings",
    "stable_system_prefix",
]
