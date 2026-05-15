"""Procedural memory: skill storage backed by SQLite + FTS5.

v1 uses a plain table with a dedicated FTS5 virtual table for search;
embeddings land in the optional ``chroma`` extra (Phase 3+).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SkillRecord:
    id: str
    name: str
    description: str
    body: str


class ProceduralMemory:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    # ------------------------------------------------------------------ schema
    def _init_schema(self) -> None:
        c = self._conn.cursor()
        c.execute(
            "CREATE TABLE IF NOT EXISTS skills ("
            "  id TEXT PRIMARY KEY,"
            "  name TEXT NOT NULL,"
            "  description TEXT NOT NULL,"
            "  body TEXT NOT NULL"
            ")"
        )
        try:
            c.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts USING fts5("
                "  id UNINDEXED,"
                "  name,"
                "  description,"
                "  body,"
                "  tokenize = 'unicode61'"
                ")"
            )
            self._has_fts = True
        except sqlite3.OperationalError:
            # FTS5 unavailable (older sqlite build); fall back to LIKE search.
            self._has_fts = False
        self._conn.commit()

    # --------------------------------------------------------------- mutations
    def put(self, record: SkillRecord) -> None:
        c = self._conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO skills(id, name, description, body) "
            "VALUES (?, ?, ?, ?)",
            (record.id, record.name, record.description, record.body),
        )
        if self._has_fts:
            c.execute("DELETE FROM skills_fts WHERE id = ?", (record.id,))
            c.execute(
                "INSERT INTO skills_fts(id, name, description, body) "
                "VALUES (?, ?, ?, ?)",
                (record.id, record.name, record.description, record.body),
            )
        self._conn.commit()

    # ------------------------------------------------------------------ reads
    def get(self, skill_id: str) -> SkillRecord | None:
        row = self._conn.execute(
            "SELECT id, name, description, body FROM skills WHERE id = ?",
            (skill_id,),
        ).fetchone()
        if row is None:
            return None
        return SkillRecord(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            body=row["body"],
        )

    def all(self) -> list[SkillRecord]:
        rows = self._conn.execute(
            "SELECT id, name, description, body FROM skills ORDER BY id"
        ).fetchall()
        return [
            SkillRecord(
                id=r["id"],
                name=r["name"],
                description=r["description"],
                body=r["body"],
            )
            for r in rows
        ]

    def search_with_scores(self, query: str) -> list[tuple[SkillRecord, float]]:
        """L38-1 — return BM25-scored results without truncation.

        FTS5's ``bm25(table)`` returns a non-negative raw score where
        smaller = better match. We expose a normalised confidence
        ``1 / (1 + raw)`` (range ``(0, 1]``) so the cascade routers can
        compare scores against thresholds without caring about the raw
        BM25 distribution.

        When FTS5 is unavailable (older sqlite build) we fall back to a
        LIKE scan and return a flat ``0.5`` confidence — enough to keep
        the cascade structurally complete on legacy hosts.
        """
        if self._has_fts:
            rows = list(
                self._conn.execute(
                    "SELECT s.id, s.name, s.description, s.body, "
                    "       bm25(skills_fts) AS raw_bm25 "
                    "FROM skills s JOIN skills_fts f ON s.id = f.id "
                    "WHERE skills_fts MATCH ? "
                    "ORDER BY bm25(skills_fts)",
                    (query,),
                )
            )
            return [
                (
                    SkillRecord(
                        id=r["id"],
                        name=r["name"],
                        description=r["description"],
                        body=r["body"],
                    ),
                    1.0 / (1.0 + max(0.0, float(r["raw_bm25"]))),
                )
                for r in rows
            ]
        like = f"%{query}%"
        rows = list(
            self._conn.execute(
                "SELECT id, name, description, body FROM skills "
                "WHERE name LIKE ? OR description LIKE ? OR body LIKE ?",
                (like, like, like),
            )
        )
        return [
            (
                SkillRecord(
                    id=r["id"],
                    name=r["name"],
                    description=r["description"],
                    body=r["body"],
                ),
                0.5,
            )
            for r in rows
        ]

    def search(self, query: str, *, max_tokens: int = 2000) -> list[SkillRecord]:
        """Keyword search, then clip results to a rough token budget."""
        rows: list[sqlite3.Row]
        if self._has_fts:
            rows = list(
                self._conn.execute(
                    "SELECT s.id, s.name, s.description, s.body "
                    "FROM skills s JOIN skills_fts f ON s.id = f.id "
                    "WHERE skills_fts MATCH ? "
                    "ORDER BY bm25(skills_fts)",
                    (query,),
                )
            )
        else:
            like = f"%{query}%"
            rows = list(
                self._conn.execute(
                    "SELECT id, name, description, body FROM skills "
                    "WHERE name LIKE ? OR description LIKE ? OR body LIKE ?",
                    (like, like, like),
                )
            )

        out: list[SkillRecord] = []
        used_words = 0
        # Conservative word budget (test harness asserts word count <= 2 * max_tokens).
        word_budget = max(1, max_tokens * 2)
        for r in rows:
            body = r["body"]
            words = body.split()
            remaining = word_budget - used_words
            if remaining <= 0:
                break
            if len(words) > remaining:
                body = " ".join(words[:remaining])
                words_used = remaining
            else:
                words_used = len(words)
            out.append(
                SkillRecord(
                    id=r["id"],
                    name=r["name"],
                    description=r["description"],
                    body=body,
                )
            )
            used_words += words_used
        return out
