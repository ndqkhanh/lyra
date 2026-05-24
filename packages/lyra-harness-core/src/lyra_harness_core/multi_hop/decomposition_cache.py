"""Sub-question decomposition cache.

Per [docs/199-multi-hop-reasoning-techniques-arc.md](../../../../../../research/harness-engineering/docs/199-multi-hop-reasoning-techniques-arc.md)
and the Tier-0 day-by-day checklists in [docs/203], [docs/208], [docs/220].

Sub-question decompositions repeat across queries (especially fan-out questions
and recurring research patterns). Memoise by normalised question key + project
to cut latency on repeats.

The cache is **scoped** by ``namespace`` so cross-project / cross-tenant
poisoning is prevented — Aegis-Ops's per-runbook context isolation pattern
generalises here: the cache key includes the namespace.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Optional

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s\-]+")


def normalize_question(question: str) -> str:
    """Stable normalisation for cache keys.

    - Lowercase, strip, collapse whitespace.
    - Drop most punctuation (keep word chars + hyphen).
    - Result is a stable hash-equal key across cosmetic variations.

    >>> normalize_question("Who DIRECTED Casablanca?")
    'who directed casablanca'
    >>> normalize_question("  who directed casablanca? ")
    'who directed casablanca'
    """
    s = (question or "").lower().strip()
    s = _PUNCT_RE.sub("", s)
    s = _WS_RE.sub(" ", s).strip()
    return s


@dataclass
class DecompositionEntry:
    """One cached decomposition result."""

    question: str  # original (un-normalised) for audit
    sub_questions: tuple[str, ...]
    namespace: str = "default"
    created_at: float = field(default_factory=time.time)
    last_accessed_at: float = field(default_factory=time.time)
    hit_count: int = 0

    def touch(self) -> None:
        self.last_accessed_at = time.time()
        self.hit_count += 1


@dataclass
class DecompositionCache:
    """Namespaced sub-question cache with TTL + LRU eviction.

    The cache key is ``(namespace, normalize_question(q))``. Within a namespace,
    same-normalised questions return the same decomposition; different
    namespaces never share entries.

    >>> cache = DecompositionCache()
    >>> cache.put(question="Who directed Casablanca?",
    ...           sub_questions=("who is the director of Casablanca?",))
    >>> entry = cache.get("WHO DIRECTED CASABLANCA?")
    >>> entry.sub_questions
    ('who is the director of Casablanca?',)
    """

    ttl_seconds: Optional[float] = None  # None = no expiry
    max_entries: Optional[int] = None  # None = unbounded
    _entries: dict[tuple[str, str], DecompositionEntry] = field(default_factory=dict)

    def _key(self, question: str, namespace: str) -> tuple[str, str]:
        return (namespace, normalize_question(question))

    def put(
        self,
        *,
        question: str,
        sub_questions: tuple[str, ...] | list[str],
        namespace: str = "default",
    ) -> DecompositionEntry:
        """Insert or update an entry."""
        sub_q_tuple = tuple(sub_questions)
        if not sub_q_tuple:
            raise ValueError("sub_questions must be non-empty")
        entry = DecompositionEntry(
            question=question,
            sub_questions=sub_q_tuple,
            namespace=namespace,
        )
        self._entries[self._key(question, namespace)] = entry
        self._maybe_evict()
        return entry

    def get(
        self,
        question: str,
        *,
        namespace: str = "default",
    ) -> Optional[DecompositionEntry]:
        """Look up an entry; returns None on miss or TTL expiry."""
        entry = self._entries.get(self._key(question, namespace))
        if entry is None:
            return None
        if self.ttl_seconds is not None:
            age = time.time() - entry.created_at
            if age > self.ttl_seconds:
                # Expired — evict and miss.
                del self._entries[self._key(question, namespace)]
                return None
        entry.touch()
        return entry

    def invalidate(self, question: str, *, namespace: str = "default") -> bool:
        """Drop an entry. Returns True if it was present."""
        key = self._key(question, namespace)
        if key in self._entries:
            del self._entries[key]
            return True
        return False

    def clear_namespace(self, namespace: str) -> int:
        """Drop all entries in a namespace; returns count dropped."""
        keys = [k for k in self._entries if k[0] == namespace]
        for k in keys:
            del self._entries[k]
        return len(keys)

    def __len__(self) -> int:
        return len(self._entries)

    def stats(self) -> dict[str, int]:
        """Aggregate metrics: total entries, total hits, namespaces."""
        return {
            "entries": len(self._entries),
            "hits": sum(e.hit_count for e in self._entries.values()),
            "namespaces": len({k[0] for k in self._entries}),
        }

    def _maybe_evict(self) -> None:
        """LRU eviction if max_entries set and exceeded."""
        if self.max_entries is None or len(self._entries) <= self.max_entries:
            return
        # Sort by last_accessed_at; evict the least-recently-accessed.
        ordered = sorted(self._entries.items(), key=lambda kv: kv[1].last_accessed_at)
        n_to_evict = len(self._entries) - self.max_entries
        for key, _ in ordered[:n_to_evict]:
            del self._entries[key]


__all__ = ["DecompositionCache", "DecompositionEntry", "normalize_question"]
