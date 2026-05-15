"""Index-first session-resume surface (v3.13 — P0-1).

Steals the progressive-disclosure doctrine from ``thedotmack/claude-mem``:

    Show what exists and its retrieval cost first. Let the agent
    decide what to fetch.

At ``SessionStart`` the host injects a ~1 KB markdown index of past
lessons — IDs, ago-times, polarity emoji, titles, approximate token
costs. Bodies are *never* in the index. To read a lesson the agent
calls :func:`get_observation` with the stable ID. To filter before
reading, the agent calls :func:`search_index` (rows only) or
:func:`timeline_around` (chronological neighbours of an anchor ID).

This module is a thin compositional surface on top of the existing
:class:`~lyra_core.memory.reasoning_bank_store.SqliteReasoningBank`
and the in-memory
:class:`~lyra_core.memory.reasoning_bank.ReasoningBank`. No schema
change, no new dependency — the SQLite store already records
``inserted_at`` (Julian day) and exposes its connection for the
fast path.

Design rationale, captured from
``docs/context-engineering-deep-research-v2.md`` §1.2 (claude-mem
3-tier workflow) and §7 P0-1: an index row is ~80 rendered chars
(~20 tokens); a typical lesson body is 500-1000 tokens. So the
"10x token savings" claim from claude-mem's
``mem-search/SKILL.md`` holds for lyra too — provided the agent
actually filters before fetching. The tool-call docstrings below
mirror that exact instruction so the model is steered into the
right workflow.
"""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from typing import Optional, Protocol

from .reasoning_bank import Lesson, TrajectoryOutcome


# Polarity → emoji glyph. The single-cell glyph is two display
# columns wide in most monospace fonts; widening it would push past
# the 1 KB budget at 20 rows.
_POLARITY_EMOJI = {
    TrajectoryOutcome.SUCCESS: "🟢",
    TrajectoryOutcome.FAILURE: "🔴",
}

# Julian-day → epoch seconds offset. Used to convert the SQLite
# ``inserted_at`` column (stored as ``julianday('now')``) back to
# wall-clock so we can render an ago-string.
_JD_EPOCH_OFFSET = 2440587.5

# Single-row character estimate. Padded so the byte cap accounts
# for header + footer + per-line join overhead.
_HEADER = "| ID | Ago | T | Title | Tok |\n|---|---|---|---|---|"
_FOOTER = (
    "*Index only — fetch a full lesson with "
    "`mem_get_observation(id)`. Filter first via "
    "`mem_search_index(query)`; 10x token savings.*"
)


@dataclass(frozen=True)
class IndexRow:
    """One row in the session-resume index.

    Designed to fit in ~80 rendered characters so an index of 10-20
    rows fits in 1 KB. The agent uses :attr:`id` to fetch the full
    body via :func:`get_observation`; everything else is metadata
    for the routing decision.
    """

    id: str
    type_emoji: str       # 🟢 / 🔴 / •
    title: str            # ≤ 60 chars, whitespace-collapsed
    body_tokens: int      # ceil(chars / 4); never zero for non-empty bodies
    timestamp_ago: str    # "3s" / "5m" / "2h" / "1d" / "—" if unknown


class IndexBank(Protocol):
    """Minimum surface needed by the index helpers.

    Satisfied by both
    :class:`~lyra_core.memory.reasoning_bank_store.SqliteReasoningBank`
    and :class:`~lyra_core.memory.reasoning_bank.ReasoningBank`.
    """

    def all_lessons(
        self,
        *,
        polarity: TrajectoryOutcome | None = ...,
        limit: int | None = ...,
    ) -> tuple[Lesson, ...]: ...

    def recall(
        self,
        task_signature: str,
        *,
        k: int = ...,
        polarity: TrajectoryOutcome | None = ...,
        diversity_weighted: bool = ...,
    ) -> tuple[Lesson, ...]: ...


# ----------------------------------------------------------- helpers


def _truncate_title(title: str, *, cap: int = 60) -> str:
    """Collapse whitespace and cap at ``cap`` chars with an ellipsis."""
    title = " ".join(title.split())
    if len(title) <= cap:
        return title
    return title[: cap - 1] + "…"


def _format_ago(then_julianday: float, *, now: Optional[float] = None) -> str:
    """Short human-readable delta string for a Julian-day timestamp."""
    then_epoch = (then_julianday - _JD_EPOCH_OFFSET) * 86400.0
    now_epoch = now if now is not None else time.time()
    delta = max(0.0, now_epoch - then_epoch)
    if delta < 60:
        return f"{int(delta)}s"
    if delta < 3600:
        return f"{int(delta // 60)}m"
    if delta < 86400:
        return f"{int(delta // 3600)}h"
    return f"{int(delta // 86400)}d"


def _row_from_lesson(
    lesson: Lesson, *, timestamp_ago: str = "—"
) -> IndexRow:
    return IndexRow(
        id=lesson.id,
        type_emoji=_POLARITY_EMOJI.get(lesson.polarity, "•"),
        title=_truncate_title(lesson.title),
        body_tokens=max(1, len(lesson.body) // 4) if lesson.body else 0,
        timestamp_ago=timestamp_ago,
    )


def _has_sqlite_conn(bank: object) -> bool:
    """Duck-test: does ``bank`` expose a private SQLite connection?

    The SQLite store keeps it as ``_conn``; the in-memory store has
    no such attribute. Used to pick the fast path that pulls
    timestamps in the same query.
    """
    return hasattr(bank, "_conn") and isinstance(
        getattr(bank, "_conn", None), sqlite3.Connection
    )


def _index_rows_sqlite(
    bank: object, limit: int, now: Optional[float]
) -> tuple[IndexRow, ...]:
    """SQLite fast path — one query, pulls ``inserted_at`` inline.

    Tie-break on ``rowid`` so rapid back-to-back inserts (which can
    share a millisecond and therefore a ``julianday('now')``) still
    sort deterministically newest-first.
    """
    conn: sqlite3.Connection = bank._conn  # type: ignore[attr-defined]
    rows = conn.execute(
        "SELECT id, polarity, title, length(body) AS body_chars, "
        "inserted_at FROM lessons "
        "ORDER BY inserted_at DESC, rowid DESC LIMIT ?",
        (limit,),
    ).fetchall()
    out: list[IndexRow] = []
    for r in rows:
        polarity = TrajectoryOutcome(r["polarity"])
        body_chars = int(r["body_chars"] or 0)
        out.append(
            IndexRow(
                id=r["id"],
                type_emoji=_POLARITY_EMOJI.get(polarity, "•"),
                title=_truncate_title(r["title"]),
                body_tokens=max(1, body_chars // 4) if body_chars else 0,
                timestamp_ago=_format_ago(r["inserted_at"], now=now),
            )
        )
    return tuple(out)


# ------------------------------------------------------- public surface


def index_rows(
    bank: IndexBank,
    *,
    limit: int = 20,
    now: Optional[float] = None,
) -> tuple[IndexRow, ...]:
    """Most-recent-first index rows for the top ``limit`` lessons.

    Bodies are *not* included. The SQLite path also fills in
    :attr:`IndexRow.timestamp_ago`; the in-memory fallback marks
    timestamps as ``"—"`` since the in-memory store has no
    insertion-time column.
    """
    if _has_sqlite_conn(bank):
        return _index_rows_sqlite(bank, limit, now)
    lessons = bank.all_lessons(limit=limit)
    return tuple(_row_from_lesson(l) for l in lessons)


def render_session_index(
    bank: IndexBank,
    *,
    limit: int = 20,
    max_bytes: int = 1024,
    now: Optional[float] = None,
) -> str:
    """Render a ≤``max_bytes`` markdown index for SessionStart.

    Designed to be embedded verbatim in the system prompt. Each row
    points to a lesson by stable ID; rows past the byte budget are
    dropped (oldest first, since rows arrive newest-first).

    The header + footer always fit; if the bank is empty the
    function returns a single short stub instead of the table.
    """
    rows = index_rows(bank, limit=limit, now=now)
    if not rows:
        return "*(no past lessons recorded yet)*"

    lines: list[str] = [_HEADER]
    # +1 per join (newlines), include footer up front so we stop
    # rendering data rows when adding one more would push us over.
    body_size = len(_HEADER) + 1 + len(_FOOTER)
    for r in rows:
        line = _format_index_line(r)
        if body_size + len(line) + 1 > max_bytes:
            break
        lines.append(line)
        body_size += len(line) + 1
    lines.append(_FOOTER)
    return "\n".join(lines)


def _format_index_line(r: IndexRow) -> str:
    """Render one IndexRow as a markdown table row."""
    # ID is truncated to 12 chars for the rendered table; full ID is
    # available via the IndexRow object for callers that need it.
    return (
        f"| `{r.id[:12]}` | {r.timestamp_ago} | {r.type_emoji} | "
        f"{r.title} | {r.body_tokens} |"
    )


def search_index(
    bank: IndexBank,
    query: str,
    *,
    limit: int = 10,
    polarity: TrajectoryOutcome | None = None,
    now: Optional[float] = None,
) -> tuple[IndexRow, ...]:
    """Search by query; return index rows only (no bodies).

    Empty / whitespace-only query falls back to :func:`index_rows`
    (the recency view) so an agent that types ``/mem search`` with
    no arguments still gets useful output. Otherwise the underlying
    bank's ``recall`` decides ranking — same engine the in-loop
    memory injector uses.
    """
    if not query.strip():
        return index_rows(bank, limit=limit, now=now)
    lessons = bank.recall(query, k=limit, polarity=polarity)
    return tuple(_row_from_lesson(l) for l in lessons)


def timeline_around(
    bank: IndexBank,
    anchor_id: str,
    *,
    window: int = 5,
    now: Optional[float] = None,
) -> tuple[IndexRow, ...]:
    """Up to ``window`` lessons on each side of ``anchor_id``.

    SQLite path uses ``inserted_at`` for true chronological order;
    in-memory fallback uses insertion-list position. If the anchor
    is unknown, returns an empty tuple — the agent should call
    :func:`search_index` to find one first.
    """
    if _has_sqlite_conn(bank):
        return _timeline_sqlite(bank, anchor_id, window, now)

    lessons = bank.all_lessons()
    # all_lessons returns newest-first; reverse to oldest-first for
    # the positional-neighbourhood semantics.
    chrono = list(reversed(lessons))
    ids = [l.id for l in chrono]
    if anchor_id not in ids:
        return ()
    idx = ids.index(anchor_id)
    lo = max(0, idx - window)
    hi = min(len(chrono), idx + window + 1)
    return tuple(_row_from_lesson(l) for l in chrono[lo:hi])


def _timeline_sqlite(
    bank: object,
    anchor_id: str,
    window: int,
    now: Optional[float],
) -> tuple[IndexRow, ...]:
    """SQLite timeline window — chronologically ordered around an anchor.

    Tie-break on ``rowid`` (sqlite's insertion-order surrogate) so
    sub-second back-to-back inserts that share a ``julianday('now')``
    are still partitioned deterministically into before/after. The
    before/after partitions widen to ``inserted_at < anchor`` *or*
    ``inserted_at = anchor AND rowid < anchor_rowid`` so a lesson
    written in the same tick as the anchor still ends up on the
    correct side.
    """
    conn: sqlite3.Connection = bank._conn  # type: ignore[attr-defined]
    anchor_row = conn.execute(
        "SELECT rowid, inserted_at FROM lessons WHERE id = ?",
        (anchor_id,),
    ).fetchone()
    if anchor_row is None:
        return ()
    anchor_ts = anchor_row["inserted_at"]
    anchor_rowid = anchor_row["rowid"]

    before = conn.execute(
        "SELECT id, polarity, title, length(body) AS body_chars, "
        "inserted_at FROM lessons "
        "WHERE inserted_at < ? OR (inserted_at = ? AND rowid < ?) "
        "ORDER BY inserted_at DESC, rowid DESC LIMIT ?",
        (anchor_ts, anchor_ts, anchor_rowid, window),
    ).fetchall()
    anchor = conn.execute(
        "SELECT id, polarity, title, length(body) AS body_chars, "
        "inserted_at FROM lessons WHERE id = ?",
        (anchor_id,),
    ).fetchall()
    after = conn.execute(
        "SELECT id, polarity, title, length(body) AS body_chars, "
        "inserted_at FROM lessons "
        "WHERE inserted_at > ? OR (inserted_at = ? AND rowid > ?) "
        "ORDER BY inserted_at ASC, rowid ASC LIMIT ?",
        (anchor_ts, anchor_ts, anchor_rowid, window),
    ).fetchall()

    # Oldest → anchor → newest.
    ordered = list(reversed(before)) + list(anchor) + list(after)

    out: list[IndexRow] = []
    for r in ordered:
        polarity = TrajectoryOutcome(r["polarity"])
        body_chars = int(r["body_chars"] or 0)
        out.append(
            IndexRow(
                id=r["id"],
                type_emoji=_POLARITY_EMOJI.get(polarity, "•"),
                title=_truncate_title(r["title"]),
                body_tokens=max(1, body_chars // 4) if body_chars else 0,
                timestamp_ago=_format_ago(r["inserted_at"], now=now),
            )
        )
    return tuple(out)


def get_observation(bank: IndexBank, record_id: str) -> Lesson | None:
    """Fetch the full lesson body by stable ID — the expensive call.

    Costs ~10x an index row; filter with :func:`search_index` first.
    Returns ``None`` for unknown IDs (treat as cache miss; do not
    hallucinate the body).
    """
    if _has_sqlite_conn(bank):
        # Delegate to the store's own row-to-lesson if available
        # (it pulls task_signatures + source_trajectory_ids properly
        # from their side tables).
        if hasattr(bank, "_row_to_lesson"):
            conn: sqlite3.Connection = bank._conn  # type: ignore[attr-defined]
            row = conn.execute(
                "SELECT id, polarity, title, body FROM lessons "
                "WHERE id = ?",
                (record_id,),
            ).fetchone()
            if row is None:
                return None
            return bank._row_to_lesson(row)  # type: ignore[attr-defined]

    # In-memory fallback.
    for lesson in bank.all_lessons():
        if lesson.id == record_id:
            return lesson
    return None


__all__ = [
    "IndexBank",
    "IndexRow",
    "get_observation",
    "index_rows",
    "render_session_index",
    "search_index",
    "timeline_around",
]
