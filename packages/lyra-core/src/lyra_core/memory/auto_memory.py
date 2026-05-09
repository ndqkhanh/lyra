"""Auto-memory — append-only ``memory.md`` per project (v3.7 L37-6).

Anthropic's Claude Code "Auto memory" lets the agent accumulate
project knowledge (build commands, common errors, preferences) across
sessions in a flat ``memory.md`` file plus a per-entry index. Lyra's
existing procedural memory (SQLite FTS5 in ``memory/``) is a
*query-time* substrate; auto-memory is the *human-readable* surface
the user inspects directly.

Storage layout::

    ~/.lyra/memory/<project_slug>/
      memory.md             # human-readable digest, append-only
      entries.jsonl         # one row per entry (typed)

Entries are typed: ``user`` / ``feedback`` / ``project`` / ``reference``
(matches the Polaris session's auto-memory taxonomy). Append-only;
deletion is explicit and tombstoned (``deleted: true`` row) so the
log retains the audit chain.

Bright-line: ``LBL-AUTO-MEMORY-APPEND-ONLY`` — past entries never
mutate; rewrites create new dated entries. ``forget`` is a tombstone,
not a delete.
"""
from __future__ import annotations

import enum
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Iterable

from .decay import AccessStats, half_life_for, weighted_score


_LBL_APPEND_ONLY: str = "LBL-AUTO-MEMORY-APPEND-ONLY"

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z\-']{3,}")
_SLUG_RE = re.compile(r"[^A-Za-z0-9_-]+")


class MemoryKind(str, enum.Enum):
    USER = "user"               # role / preferences
    FEEDBACK = "feedback"       # corrections / confirmations
    PROJECT = "project"         # ongoing work, decisions
    REFERENCE = "reference"     # external pointers (docs, dashboards)


@dataclass(frozen=True)
class MemoryEntry:
    """One auto-memory entry."""

    entry_id: str
    kind: MemoryKind
    title: str
    body: str
    created_ts: float
    deleted: bool = False
    extra: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    def to_json(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "kind": self.kind.value,
            "title": self.title,
            "body": self.body,
            "created_ts": self.created_ts,
            "deleted": self.deleted,
            "extra": dict(self.extra),
        }

    @classmethod
    def from_json(cls, row: dict[str, Any]) -> "MemoryEntry":
        return cls(
            entry_id=str(row["entry_id"]),
            kind=MemoryKind(str(row.get("kind", "project"))),
            title=str(row.get("title", "")),
            body=str(row.get("body", "")),
            created_ts=float(row.get("created_ts", 0.0)),
            deleted=bool(row.get("deleted", False)),
            extra=dict(row.get("extra", {}) or {}),
        )


def project_slug(project: str) -> str:
    s = _SLUG_RE.sub("-", project.strip()).strip("-")
    return s.lower() or "default"


@dataclass
class AutoMemory:
    """File-backed auto-memory store for one project."""

    root: Path                       # ~/.lyra/memory
    project: str                     # raw project name; slug derived

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self._slug = project_slug(self.project)
        self._dir = self.root / self._slug
        self._dir.mkdir(parents=True, exist_ok=True)
        self._md_path = self._dir / "memory.md"
        self._jsonl_path = self._dir / "entries.jsonl"
        self._access_path = self._dir / "access_stats.json"
        self._lock = Lock()
        self._entries: dict[str, MemoryEntry] = {}
        # Sidecar in-memory mirror of last-accessed-ts + access-count;
        # persisted to ``access_stats.json`` on every successful retrieve.
        # Decoupled from the audit-grade ``entries.jsonl`` log so a hot
        # record doesn't balloon the audit chain with one row per read.
        self._access: dict[str, AccessStats] = {}
        self._load()
        self._load_access()

    @property
    def md_path(self) -> Path:
        return self._md_path

    @property
    def jsonl_path(self) -> Path:
        return self._jsonl_path

    @property
    def access_path(self) -> Path:
        return self._access_path

    def access_stats(self, entry_id: str) -> AccessStats:
        """Return the access-stats sidecar row for ``entry_id``.

        Returns a zeroed :class:`AccessStats` for unknown ids so callers
        can score uniformly without branching.
        """
        return self._access.get(entry_id, AccessStats())

    def __len__(self) -> int:
        return sum(1 for e in self._entries.values() if not e.deleted)

    def save(
        self,
        *,
        kind: MemoryKind,
        title: str,
        body: str,
        extra: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Append a new entry. Past entries are never mutated."""
        entry_id = f"{kind.value}-{int(time.time() * 1000)}-{len(self._entries)}"
        entry = MemoryEntry(
            entry_id=entry_id, kind=kind, title=title, body=body,
            created_ts=time.time(), extra=dict(extra or {}),
        )
        return self._append(entry)

    def forget(self, entry_id: str) -> MemoryEntry:
        """Tombstone an entry. Original row stays in the log; a new
        ``deleted=True`` row is appended."""
        if entry_id not in self._entries:
            raise KeyError(f"unknown entry_id {entry_id!r}")
        prev = self._entries[entry_id]
        if prev.deleted:
            return prev
        tombstone = MemoryEntry(
            entry_id=entry_id, kind=prev.kind,
            title=prev.title, body=prev.body,
            created_ts=time.time(), deleted=True,
            extra=dict(prev.extra),
        )
        return self._append(tombstone, replace_md=True)

    def all(self, *, include_deleted: bool = False) -> tuple[MemoryEntry, ...]:
        items = self._entries.values()
        if include_deleted:
            return tuple(items)
        return tuple(e for e in items if not e.deleted)

    def by_kind(self, kind: MemoryKind) -> tuple[MemoryEntry, ...]:
        return tuple(
            e for e in self._entries.values()
            if e.kind is kind and not e.deleted
        )

    def retrieve(
        self,
        query: str,
        *,
        top_n: int = 5,
        decay: bool = True,
        half_life_overrides: dict[str, float] | None = None,
        now_ts: float | None = None,
        record_access: bool = True,
    ) -> tuple[MemoryEntry, ...]:
        """Return the top-N entries by Jaccard token overlap with ``query``.

        v3.8 (steal from agentmemory): when ``decay`` is on, the base
        Jaccard score is multiplied by an Ebbinghaus decay × access-
        strengthening factor (see :mod:`lyra_core.memory.decay`).
        Per-kind half-life defaults live in ``DEFAULT_HALF_LIFE_S``;
        callers override per-deployment via ``half_life_overrides``.

        ``record_access=True`` (default) bumps each returned entry's
        access count and persists the sidecar ``access_stats.json``,
        which is what makes the strengthening loop close. Set to
        ``False`` for read-only inspection (e.g. CLI ``lyra memory ls``).
        """
        query_toks = _content_tokens(query)
        if not query_toks:
            return ()
        now = now_ts if now_ts is not None else time.time()
        scored: list[tuple[float, MemoryEntry]] = []
        for entry in self._entries.values():
            if entry.deleted:
                continue
            haystack = _content_tokens(f"{entry.title} {entry.body}")
            if not haystack:
                continue
            overlap = len(query_toks & haystack) / len(query_toks | haystack)
            if overlap <= 0:
                continue
            if not decay:
                final_score = overlap
            else:
                stats = self._access.get(entry.entry_id, AccessStats())
                hl = half_life_for(entry.kind.value, overrides=half_life_overrides)
                final_score = weighted_score(
                    base_score=overlap,
                    last_accessed_ts=stats.last_accessed_ts,
                    access_count=stats.access_count,
                    half_life_s=hl,
                    now_ts=now,
                    fallback_ts=entry.created_ts,
                )
            scored.append((final_score, entry))
        scored.sort(key=lambda r: (-r[0], -r[1].created_ts))
        results = tuple(e for _, e in scored[:top_n])

        if record_access and results:
            self._touch(tuple(e.entry_id for e in results), now=now)

        return results

    def session_start_digest(self, *, top_n: int = 10) -> str:
        """Return a short markdown digest the session loader injects."""
        active = [e for e in self._entries.values() if not e.deleted]
        active.sort(key=lambda e: -e.created_ts)
        if not active:
            return ""
        lines = [f"# Auto-memory for {self.project}", ""]
        for entry in active[:top_n]:
            lines.append(f"- ({entry.kind.value}) **{entry.title}** — {entry.body}")
        return "\n".join(lines).rstrip() + "\n"

    # --- internal -------------------------------------------------------

    def _append(self, entry: MemoryEntry, *, replace_md: bool = False) -> MemoryEntry:
        with self._lock:
            self._entries[entry.entry_id] = entry
            with self._jsonl_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry.to_json(), sort_keys=True))
                fh.write("\n")
            if replace_md:
                self._rewrite_md()
            else:
                self._append_md(entry)
        return entry

    def _append_md(self, entry: MemoryEntry) -> None:
        if entry.deleted:
            return
        with self._md_path.open("a", encoding="utf-8") as fh:
            fh.write(
                f"\n## {entry.title}\n"
                f"_({entry.kind.value} · {time.strftime('%Y-%m-%d', time.gmtime(entry.created_ts))})_\n\n"
                f"{entry.body}\n"
            )

    def _rewrite_md(self) -> None:
        active = [e for e in self._entries.values() if not e.deleted]
        active.sort(key=lambda e: e.created_ts)
        with self._md_path.open("w", encoding="utf-8") as fh:
            fh.write(f"# Memory — {self.project}\n")
            for e in active:
                fh.write(
                    f"\n## {e.title}\n"
                    f"_({e.kind.value} · {time.strftime('%Y-%m-%d', time.gmtime(e.created_ts))})_\n\n"
                    f"{e.body}\n"
                )

    def _load(self) -> None:
        if not self._jsonl_path.exists():
            return
        with self._jsonl_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                entry = MemoryEntry.from_json(json.loads(line))
                self._entries[entry.entry_id] = entry

    def _load_access(self) -> None:
        """Hydrate the access-stats sidecar; missing file is fine."""
        if not self._access_path.exists():
            return
        try:
            with self._access_path.open("r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (json.JSONDecodeError, OSError):
            # Sidecar is best-effort — corruption shouldn't block memory
            # reads. Reset to empty and the next retrieve rebuilds.
            self._access = {}
            return
        for entry_id, payload in (raw or {}).items():
            try:
                self._access[str(entry_id)] = AccessStats(
                    last_accessed_ts=float(payload.get("last_accessed_ts", 0.0)),
                    access_count=int(payload.get("access_count", 0)),
                )
            except (TypeError, ValueError):
                continue

    def _persist_access(self) -> None:
        payload = {
            entry_id: {
                "last_accessed_ts": stats.last_accessed_ts,
                "access_count": stats.access_count,
            }
            for entry_id, stats in self._access.items()
        }
        # Atomic write: temp file → rename. Single-process; the global
        # ``self._lock`` already serialises retrievers within one
        # process. Multi-process safety is out of scope (matches the
        # entries.jsonl shape).
        tmp = self._access_path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, sort_keys=True)
        tmp.replace(self._access_path)

    def _touch(self, entry_ids: Iterable[str], *, now: float) -> None:
        with self._lock:
            for eid in entry_ids:
                prev = self._access.get(eid, AccessStats())
                self._access[eid] = AccessStats(
                    last_accessed_ts=now,
                    access_count=prev.access_count + 1,
                )
            self._persist_access()


def _content_tokens(text: str) -> set[str]:
    return {tok.lower() for tok in _TOKEN_RE.findall(text or "")}


__all__ = [
    "AutoMemory",
    "MemoryEntry",
    "MemoryKind",
    "project_slug",
]
