"""SQLite + FTS5 persistence for :class:`~.reasoning_bank.ReasoningBank`.

Phase 1 of the bank kept lessons in a Python list — every restart
emptied the memory, which made any wiring into a long-running session
feel toy-like. Phase 2 (this module) reuses the *exact* persistence
shape Lyra already uses for procedural memory (see
:mod:`lyra_core.memory.procedural`): a primary table for the
authoritative lesson rows + an FTS5 virtual table for keyword search,
both inside one SQLite file. No external services, no embeddings, no
new dependencies.

Why this layout instead of bolting onto ``ProceduralMemory``:

1. Lessons carry **polarity** (success vs anti-skill); skills don't.
   Filtering lessons by polarity at the SQL layer is much cheaper
   than post-filtering Python objects.
2. Lessons reference *multiple* task signatures and source
   trajectories — modelled as a side table for normalised lookup
   without forcing a JSON column.
3. The bank advertises diversity-weighted recall via MMR; that lives
   in the in-memory ``ReasoningBank.recall`` and is composable with
   the SQLite ranker by passing the ranked candidates through
   :func:`lyra_core.diversity.mmr_select`.

The SQLite store is a drop-in for the in-memory bank: same
``record`` / ``recall`` / ``matts_prefix`` surface, same return
shapes. The agent loop and the chat memory injector both treat it
duck-typed, so swapping is a one-line change.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path

from .reasoning_bank import (
    Distiller,
    Lesson,
    Trajectory,
    TrajectoryOutcome,
)

# Default location — mirrors lyra_core.memory.procedural.ProceduralMemory
# so a user who opens the .lyra/memory/ directory finds both kinds of
# memory side-by-side.
DEFAULT_DB_FILENAME = "reasoning_bank.sqlite"


def default_db_path(repo_root: Path) -> Path:
    """``<repo>/.lyra/memory/reasoning_bank.sqlite``."""
    return Path(repo_root) / ".lyra" / "memory" / DEFAULT_DB_FILENAME


class SqliteReasoningBank:
    """Persistent reasoning bank backed by SQLite + FTS5.

    Public surface matches :class:`~.reasoning_bank.ReasoningBank`
    exactly: ``record(trajectory) -> tuple[Lesson, ...]``,
    ``recall(task_signature, *, k, polarity, diversity_weighted)
    -> tuple[Lesson, ...]``, and ``matts_prefix(task_signature,
    attempt_index, *, k) -> str``.
    """

    def __init__(self, distiller: Distiller, db_path: Path) -> None:
        self._distiller = distiller
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._has_fts = False
        self._init_schema()

    # ------------------------------------------------------------------ schema
    def _init_schema(self) -> None:
        with closing(self._conn.cursor()) as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS lessons ("
                "  id TEXT PRIMARY KEY,"
                "  polarity TEXT NOT NULL,"
                "  title TEXT NOT NULL,"
                "  body TEXT NOT NULL,"
                "  inserted_at REAL NOT NULL DEFAULT (julianday('now'))"
                ")"
            )
            c.execute(
                "CREATE TABLE IF NOT EXISTS lesson_signatures ("
                "  lesson_id TEXT NOT NULL,"
                "  signature TEXT NOT NULL,"
                "  PRIMARY KEY (lesson_id, signature),"
                "  FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE"
                ")"
            )
            c.execute(
                "CREATE TABLE IF NOT EXISTS lesson_trajectories ("
                "  lesson_id TEXT NOT NULL,"
                "  trajectory_id TEXT NOT NULL,"
                "  PRIMARY KEY (lesson_id, trajectory_id),"
                "  FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE"
                ")"
            )
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_lesson_signature "
                "  ON lesson_signatures(signature)"
            )
            try:
                c.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS lessons_fts USING fts5("
                    "  id UNINDEXED, title, body, signatures,"
                    "  tokenize = 'porter unicode61'"
                    ")"
                )
                self._has_fts = True
            except sqlite3.OperationalError:
                self._has_fts = False
        self._conn.commit()

    # --------------------------------------------------------------- mutation
    def record_lesson(self, lesson: Lesson) -> Lesson:
        """Persist a pre-distilled lesson directly (skips the distiller).

        Idempotent: replaces any existing row with the same ``id``.
        Used by ``MemoryToolset.commit_consolidation`` to commit a
        :class:`~lyra_core.memory.consolidator.ConsolidationProposal`
        without funnelling it through trajectory distillation.
        """
        self._write_lessons((lesson,))
        return lesson

    def record(self, trajectory: Trajectory) -> tuple[Lesson, ...]:
        """Distill and persist; returns the lessons just stored."""
        lessons = tuple(self._distiller.distill(trajectory))
        if not lessons:
            return ()
        self._write_lessons(lessons)
        return lessons

    def _write_lessons(self, lessons: Sequence[Lesson]) -> None:
        """Single-transaction upsert. Used by both ``record`` and
        ``record_lesson`` so the persistence path is identical."""
        if not lessons:
            return
        with closing(self._conn.cursor()) as c:
            for lesson in lessons:
                c.execute(
                    "INSERT OR REPLACE INTO lessons(id, polarity, title, body) "
                    "VALUES (?, ?, ?, ?)",
                    (lesson.id, lesson.polarity.value, lesson.title, lesson.body),
                )
                c.execute(
                    "DELETE FROM lesson_signatures WHERE lesson_id = ?", (lesson.id,)
                )
                for sig in lesson.task_signatures:
                    c.execute(
                        "INSERT OR IGNORE INTO lesson_signatures(lesson_id, signature)"
                        " VALUES (?, ?)",
                        (lesson.id, sig.strip().lower()),
                    )
                c.execute(
                    "DELETE FROM lesson_trajectories WHERE lesson_id = ?",
                    (lesson.id,),
                )
                for traj_id in lesson.source_trajectory_ids:
                    c.execute(
                        "INSERT OR IGNORE INTO lesson_trajectories(lesson_id, trajectory_id)"
                        " VALUES (?, ?)",
                        (lesson.id, traj_id),
                    )
                if self._has_fts:
                    c.execute("DELETE FROM lessons_fts WHERE id = ?", (lesson.id,))
                    c.execute(
                        "INSERT INTO lessons_fts(id, title, body, signatures) "
                        "VALUES (?, ?, ?, ?)",
                        (
                            lesson.id,
                            lesson.title,
                            lesson.body,
                            " ".join(lesson.task_signatures),
                        ),
                    )
        self._conn.commit()

    # ------------------------------------------------------------------- read
    def recall(
        self,
        task_signature: str,
        *,
        k: int = 3,
        polarity: TrajectoryOutcome | None = None,
        diversity_weighted: bool = False,
    ) -> tuple[Lesson, ...]:
        if k <= 0:
            return ()
        sig_norm = task_signature.strip().lower()

        # Stage 1 — exact-signature matches (cheap, indexed).
        rows = self._conn.execute(
            "SELECT l.id, l.polarity, l.title, l.body, ls.signature "
            "FROM lessons l "
            "JOIN lesson_signatures ls ON ls.lesson_id = l.id "
            "WHERE ls.signature = ? "
            "ORDER BY l.inserted_at DESC",
            (sig_norm,),
        ).fetchall()

        # Stage 2 — FTS5 ranker if available, otherwise LIKE substring.
        fts_rows: list[sqlite3.Row] = []
        if rows:
            seen_ids = {r["id"] for r in rows}
        else:
            seen_ids = set()

        if self._has_fts and sig_norm:
            try:
                fts_rows = list(
                    self._conn.execute(
                        "SELECT l.id, l.polarity, l.title, l.body, '' AS signature "
                        "FROM lessons l "
                        "JOIN lessons_fts f ON f.id = l.id "
                        "WHERE lessons_fts MATCH ? "
                        "ORDER BY bm25(lessons_fts) "
                        "LIMIT ?",
                        (self._fts_query(sig_norm), max(k * 4, 16)),
                    )
                )
            except sqlite3.OperationalError:
                fts_rows = []
        elif sig_norm:
            like = f"%{sig_norm}%"
            fts_rows = list(
                self._conn.execute(
                    "SELECT l.id, l.polarity, l.title, l.body, '' AS signature "
                    "FROM lessons l "
                    "WHERE l.title LIKE ? OR l.body LIKE ? "
                    "ORDER BY l.inserted_at DESC "
                    "LIMIT ?",
                    (like, like, max(k * 4, 16)),
                )
            )

        merged: list[sqlite3.Row] = list(rows)
        for r in fts_rows:
            if r["id"] in seen_ids:
                continue
            seen_ids.add(r["id"])
            merged.append(r)

        candidates = [
            self._row_to_lesson(r)
            for r in merged
            if polarity is None or r["polarity"] == polarity.value
        ]

        if diversity_weighted and len(candidates) > k:
            from lyra_core.diversity import mmr_select

            relevance: dict[str, float] = {}
            id_to_lesson: dict[str, Lesson] = {}
            for idx, lesson in enumerate(candidates):
                key = lesson.body or lesson.title or lesson.id
                relevance[key] = max(relevance.get(key, 0.0), 1.0 / (1 + idx))
                id_to_lesson[key] = lesson
            picked_keys = mmr_select(
                tuple(relevance.keys()), k=k, relevance=relevance
            )
            return tuple(id_to_lesson[picked] for picked in picked_keys)

        return tuple(candidates[:k])

    def matts_prefix(
        self,
        task_signature: str,
        attempt_index: int,
        *,
        k: int = 3,
    ) -> str:
        pool = self.recall(task_signature, k=max(k * 2, k + attempt_index + 1))
        if not pool:
            return f"# matts attempt={attempt_index} signature={task_signature} (no lessons)"
        rotated = (
            pool[attempt_index % len(pool):]
            + pool[: attempt_index % len(pool)]
        )
        chosen = rotated[:k]
        body = "\n".join(f"- {lesson.title}: {lesson.body}" for lesson in chosen)
        return (
            f"# matts attempt={attempt_index} signature={task_signature}\n"
            f"{body}"
        )

    # ----------------------------------------------------------- introspection
    def all_lessons(
        self,
        *,
        polarity: TrajectoryOutcome | None = None,
        limit: int | None = None,
    ) -> tuple[Lesson, ...]:
        query = (
            "SELECT id, polarity, title, body, '' AS signature "
            "FROM lessons "
        )
        params: list[object] = []
        if polarity is not None:
            query += "WHERE polarity = ? "
            params.append(polarity.value)
        query += "ORDER BY inserted_at DESC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        rows = self._conn.execute(query, params).fetchall()
        return tuple(self._row_to_lesson(r) for r in rows)

    def stats(self) -> dict[str, int]:
        cur = self._conn.cursor()
        n_total = cur.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
        n_success = cur.execute(
            "SELECT COUNT(*) FROM lessons WHERE polarity = 'success'"
        ).fetchone()[0]
        n_failure = cur.execute(
            "SELECT COUNT(*) FROM lessons WHERE polarity = 'failure'"
        ).fetchone()[0]
        n_signatures = cur.execute(
            "SELECT COUNT(DISTINCT signature) FROM lesson_signatures"
        ).fetchone()[0]
        n_trajectories = cur.execute(
            "SELECT COUNT(DISTINCT trajectory_id) FROM lesson_trajectories"
        ).fetchone()[0]
        return {
            "lessons_total": n_total,
            "lessons_success": n_success,
            "lessons_failure": n_failure,
            "task_signatures": n_signatures,
            "source_trajectories": n_trajectories,
        }

    def wipe(self) -> int:
        cur = self._conn.cursor()
        n = cur.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
        cur.execute("DELETE FROM lessons")
        cur.execute("DELETE FROM lesson_signatures")
        cur.execute("DELETE FROM lesson_trajectories")
        if self._has_fts:
            cur.execute("DELETE FROM lessons_fts")
        self._conn.commit()
        return int(n)

    def close(self) -> None:
        self._conn.close()

    # --------------------------------------------------------------- internal
    def _row_to_lesson(self, row: sqlite3.Row) -> Lesson:
        sigs = tuple(
            r["signature"]
            for r in self._conn.execute(
                "SELECT signature FROM lesson_signatures WHERE lesson_id = ? "
                "ORDER BY signature",
                (row["id"],),
            )
        )
        traj_ids = tuple(
            r["trajectory_id"]
            for r in self._conn.execute(
                "SELECT trajectory_id FROM lesson_trajectories WHERE lesson_id = ? "
                "ORDER BY trajectory_id",
                (row["id"],),
            )
        )
        polarity = TrajectoryOutcome(row["polarity"])
        return Lesson(
            id=row["id"],
            polarity=polarity,
            title=row["title"],
            body=row["body"],
            task_signatures=sigs,
            source_trajectory_ids=traj_ids,
        )

    @staticmethod
    def _fts_query(text: str) -> str:
        """Render a safe FTS5 MATCH query from a free-form signature.

        We OR the alphanumeric tokens. Anything weird (quotes,
        operators) is stripped so we don't bomb the query parser. If
        nothing usable remains, callers will skip FTS entirely.
        """
        tokens = [t for t in (w.strip() for w in text.replace('"', " ").split()) if t.isalnum()]
        if not tokens:
            return text
        return " OR ".join(tokens[:8])


__all__ = ["DEFAULT_DB_FILENAME", "SqliteReasoningBank", "default_db_path"]


# Phase-2 helper: factory that picks the right backend based on
# whether a db_path is supplied. The agent loop and the chat memory
# injector use this so they don't have to repeat the import.
def open_default_bank(
    distiller: Distiller,
    *,
    db_path: Path | None,
) -> object:
    """Return a persistent bank if a path is given, else an in-memory one.

    Returns the abstract :class:`Bank` shape (any object exposing
    ``record/recall/matts_prefix``); callers duck-type.
    """
    if db_path is None:
        from .reasoning_bank import ReasoningBank

        return ReasoningBank(distiller=distiller)
    return SqliteReasoningBank(distiller=distiller, db_path=db_path)


def __getattr__(name: str) -> object:
    """Module-level helper exports kept stable across phases."""
    if name == "open_default_bank":
        return open_default_bank
    raise AttributeError(name)
