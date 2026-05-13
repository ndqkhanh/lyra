"""Temporal fact store — Zep/Graphiti-style fact invalidation.

When a codebase fact changes (file moves, function renamed, convention
deprecated), vector-only memory surfaces the stale version because it is
semantically similar to the query. Temporal invalidation avoids this by
marking facts invalid at a specific time rather than deleting them.

Research grounding: §4 (Zep/Graphiti LongMemEval 63.8 % vs Mem0 49.0 %
due to temporal correctness), §9 (temporal invalidation forgetting policy),
§13 #5 ("Zep for temporal correctness — when a file moves, a function is
renamed, or a convention is deprecated, vector-only memory will surface
the stale version").
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


@dataclass
class TemporalFact:
    """A codebase fact with a validity window.

    A fact is *current* when ``invalid_at`` is None.
    ``superseded_by`` optionally links to the replacement fact's id.
    """

    id: str
    fact: str
    category: str  # e.g. "file_location", "function_name", "convention"
    valid_from: str
    invalid_at: str | None = None
    superseded_by: str | None = None  # id of the replacement fact

    @property
    def is_valid(self) -> bool:
        return self.invalid_at is None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TemporalFact":
        return cls(**d)


@dataclass(frozen=True)
class FactRecallResult:
    """Result of a recall query."""

    facts: tuple[TemporalFact, ...]
    total_stored: int
    total_valid: int
    total_invalid: int


class TemporalFactStore:
    """Store, invalidate, and recall codebase facts with temporal tracking.

    When a fact changes, call :meth:`invalidate` on the old fact and
    :meth:`add` a new one. Old facts are retained for audit; only valid
    facts are returned by :meth:`recall`.

    Usage::
        store = TemporalFactStore()
        fid = store.add("auth module is at src/auth/", category="file_location")
        # Later, the file moves:
        new_fid = store.add("auth module is at src/core/auth/", category="file_location")
        store.invalidate(fid, superseded_by=new_fid)
        # recall() returns only the new fact
        current = store.recall()
    """

    def __init__(self, store_path: Path | None = None) -> None:
        self._facts: dict[str, TemporalFact] = {}
        self._store_path = store_path
        if store_path and store_path.exists():
            self._load(store_path)

    # ------------------------------------------------------------------
    # Mutating operations
    # ------------------------------------------------------------------

    def add(
        self,
        fact: str,
        *,
        category: str = "general",
        fact_id: str | None = None,
    ) -> str:
        """Store a new fact. Returns its id."""
        fid = fact_id or str(uuid.uuid4())
        self._facts[fid] = TemporalFact(
            id=fid,
            fact=fact,
            category=category,
            valid_from=_now_iso(),
        )
        if self._store_path:
            self._save(self._store_path)
        return fid

    def invalidate(
        self,
        fact_id: str,
        *,
        superseded_by: str | None = None,
    ) -> bool:
        """Mark *fact_id* as invalid. Returns True if the fact existed."""
        fact = self._facts.get(fact_id)
        if fact is None:
            return False
        self._facts[fact_id] = TemporalFact(
            id=fact.id,
            fact=fact.fact,
            category=fact.category,
            valid_from=fact.valid_from,
            invalid_at=_now_iso(),
            superseded_by=superseded_by,
        )
        if self._store_path:
            self._save(self._store_path)
        return True

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def recall(
        self,
        *,
        category: str | None = None,
        include_invalid: bool = False,
    ) -> FactRecallResult:
        """Return facts, optionally filtered by *category*.

        By default only valid (non-invalidated) facts are returned.
        Pass ``include_invalid=True`` for auditing.
        """
        all_facts = list(self._facts.values())
        valid = [f for f in all_facts if f.is_valid]
        invalid = [f for f in all_facts if not f.is_valid]

        pool = all_facts if include_invalid else valid
        if category:
            pool = [f for f in pool if f.category == category]

        pool_sorted = sorted(pool, key=lambda f: f.valid_from, reverse=True)
        return FactRecallResult(
            facts=tuple(pool_sorted),
            total_stored=len(all_facts),
            total_valid=len(valid),
            total_invalid=len(invalid),
        )

    def get(self, fact_id: str) -> TemporalFact | None:
        return self._facts.get(fact_id)

    def as_context_block(self, *, category: str | None = None) -> str:
        """Format current facts as a compact system-message block."""
        result = self.recall(category=category)
        if not result.facts:
            return ""
        lines = ["## Current Codebase Facts\n"]
        for f in result.facts:
            cat = f" [{f.category}]" if f.category != "general" else ""
            lines.append(f"- {f.fact}{cat}")
        return "\n".join(lines)

    def invalidation_log(self) -> list[TemporalFact]:
        """Return all invalidated facts, newest first, for audit."""
        return sorted(
            (f for f in self._facts.values() if not f.is_valid),
            key=lambda f: f.invalid_at or "",
            reverse=True,
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps([f.to_dict() for f in self._facts.values()], indent=2)
        )

    def _load(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text())
            self._facts = {d["id"]: TemporalFact.from_dict(d) for d in data}
        except (json.JSONDecodeError, TypeError, KeyError):
            self._facts = {}


__all__ = [
    "TemporalFact",
    "TemporalFactStore",
    "FactRecallResult",
]
