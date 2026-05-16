"""Memory Management System for Lyra — Phase E (MemGPT/Mem0 inspired).

Three-tier memory architecture:
  CoreMemoryStore  — always-in-context user facts (≤500 tokens, JSON-persisted)
  ArchivalStore    — SQLite FTS5 store for past session summaries (BM25 search)
  ReasoningBank    — lessons/reflections from experience (existing)
  MemoryManager    — facade over all tiers

Evidence:
- Mem0 (41k★, arXiv:2504.19413): 93% per-turn token reduction, 26% accuracy gain
- MemGPT (arXiv:2310.08560): OS-style virtual context, persistent memory
- context-mode (14.8k★): SQLite session continuity, ≤2KB compaction snapshots
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Lesson:
    """A lesson learned from experience."""
    id: Optional[int]
    tags: list[str]
    verdict: str
    lesson: str
    timestamp: str
    context: Optional[str] = None


# ── Tier 1: Core Memory ────────────────────────────────────────────────────

class CoreMemoryStore:
    """Always-in-context user facts. ≤500 tokens. JSON-persisted.

    Holds things the model must always know: user preferences, active tasks,
    established facts. Injected into every system prompt.
    """

    MAX_TOKENS_EST: int = 500

    def __init__(self, db_path: str = "~/.lyra/memory/core.json") -> None:
        self._path = Path(db_path).expanduser()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._facts: list[str] = self._load()

    def _load(self) -> list[str]:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
                return data if isinstance(data, list) else []
            except Exception:
                return []
        return []

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._facts, indent=2))

    def add(self, fact: str) -> None:
        if fact and fact not in self._facts:
            self._facts.append(fact)
            self._trim()
            self._save()

    def remove(self, index: int) -> None:
        if 0 <= index < len(self._facts):
            self._facts.pop(index)
            self._save()

    def clear(self) -> None:
        self._facts.clear()
        self._save()

    def get_all(self) -> list[str]:
        return list(self._facts)

    def to_prompt_block(self) -> str:
        if not self._facts:
            return ""
        lines = "\n".join(f"- {f}" for f in self._facts)
        return f"## Context\n{lines}"

    def token_estimate(self) -> int:
        return len(self.to_prompt_block()) // 4

    def _trim(self) -> None:
        while self.token_estimate() > self.MAX_TOKENS_EST and len(self._facts) > 1:
            self._facts.pop(0)


# ── Tier 2: Archival Memory ────────────────────────────────────────────────

class ArchivalStore:
    """SQLite FTS5 store for past session summaries. Retrieved by BM25 search.

    Past sessions are never loaded wholesale — only the top-k relevant
    chunks are retrieved for each query and injected into context.
    """

    def __init__(self, db_path: str = "~/.lyra/memory/archival.db") -> None:
        self._db_path = Path(db_path).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS archival
                USING fts5(session_id, summary, tags, created_at UNINDEXED)
            """)

    def store(self, session_id: str, summary: str, tags: list[str] | None = None) -> None:
        tags_str = ",".join(tags or [])
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO archival(session_id, summary, tags, created_at) VALUES (?, ?, ?, ?)",
                (session_id, summary, tags_str, datetime.now().isoformat()),
            )

    def search(self, query: str, limit: int = 3) -> list[str]:
        if not query.strip():
            return []
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute(
                    "SELECT summary FROM archival WHERE archival MATCH ? ORDER BY rank LIMIT ?",
                    (query, limit),
                )
                return [row[0] for row in cursor.fetchall()]
        except Exception:
            return []

    def count(self) -> int:
        try:
            with sqlite3.connect(self._db_path) as conn:
                return conn.execute("SELECT COUNT(*) FROM archival").fetchone()[0]
        except Exception:
            return 0

    def list_sessions(self, limit: int = 10) -> list[dict]:
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute(
                    "SELECT session_id, created_at, summary FROM archival "
                    "ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                )
                return [
                    {"session_id": r[0], "created_at": r[1], "summary": r[2][:100] + "…"}
                    for r in cursor.fetchall()
                ]
        except Exception:
            return []


# ── Tier 3: Reasoning Bank (existing) ─────────────────────────────────────

class ReasoningBank:
    """SQLite-backed store for lessons learned from experience."""

    def __init__(self, db_path: str = "~/.lyra/memory/reasoning_bank.db") -> None:
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tags TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    lesson TEXT NOT NULL,
                    context TEXT,
                    timestamp TEXT NOT NULL
                )
            """)

    def add_lesson(
        self,
        tags: list[str],
        verdict: str,
        lesson: str,
        context: str | None = None,
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO lessons (tags, verdict, lesson, context, timestamp) VALUES (?, ?, ?, ?, ?)",
                (json.dumps(tags), verdict, lesson, context, datetime.now().isoformat()),
            )
            return cursor.lastrowid  # type: ignore[return-value]

    def search_lessons(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
    ) -> list[Lesson]:
        with sqlite3.connect(self.db_path) as conn:
            if tags:
                results = []
                for tag in tags:
                    cursor = conn.execute(
                        "SELECT id, tags, verdict, lesson, context, timestamp "
                        "FROM lessons WHERE tags LIKE ? ORDER BY timestamp DESC",
                        (f'%{tag}%',),
                    )
                    results.extend(cursor.fetchall())
            elif query:
                cursor = conn.execute(
                    "SELECT id, tags, verdict, lesson, context, timestamp "
                    "FROM lessons WHERE lesson LIKE ? OR context LIKE ? ORDER BY timestamp DESC",
                    (f'%{query}%', f'%{query}%'),
                )
                results = cursor.fetchall()
            else:
                cursor = conn.execute(
                    "SELECT id, tags, verdict, lesson, context, timestamp "
                    "FROM lessons ORDER BY timestamp DESC"
                )
                results = cursor.fetchall()

        return [
            Lesson(
                id=r[0],
                tags=json.loads(r[1]),
                verdict=r[2],
                lesson=r[3],
                context=r[4],
                timestamp=r[5],
            )
            for r in results
        ]


# ── Facade ─────────────────────────────────────────────────────────────────

class MemoryManager:
    """Facade over all memory tiers. Used by TUI commands and agent_integration."""

    def __init__(self) -> None:
        self.reasoning_bank = ReasoningBank()
        self.core_memory = CoreMemoryStore()
        self.archival = ArchivalStore()
        self.skills_memory: dict = {}
        self.playbook_memory: dict = {}
        self._load_memories()

    # ── Tier 1: Core memory ──────────────────────────────────────────────

    def get_core_prompt_block(self) -> str:
        """Phase E: Return core facts formatted for system prompt injection."""
        return self.core_memory.to_prompt_block()

    def add_core_fact(self, fact: str) -> None:
        self.core_memory.add(fact)

    def remove_core_fact(self, index: int) -> None:
        self.core_memory.remove(index)

    def get_core_facts(self) -> list[str]:
        return self.core_memory.get_all()

    # ── Tier 2: Archival memory ──────────────────────────────────────────

    def archive_session(
        self, session_id: str, summary: str, tags: list[str] | None = None
    ) -> None:
        self.archival.store(session_id, summary, tags)

    def search_archival(self, query: str, limit: int = 3) -> list[str]:
        return self.archival.search(query, limit)

    def list_archived_sessions(self, limit: int = 10) -> list[dict]:
        return self.archival.list_sessions(limit)

    # ── Tier 3: Reasoning bank ───────────────────────────────────────────

    def reflect(
        self,
        tags: list[str],
        verdict: str,
        lesson: str,
        context: str | None = None,
    ) -> int:
        return self.reasoning_bank.add_lesson(tags, verdict, lesson, context)

    def recall(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
    ) -> list[Lesson]:
        return self.reasoning_bank.search_lessons(query, tags)

    # ── Skills & Playbook (unchanged) ───────────────────────────────────

    def add_skill_memory(self, skill_name: str, usage_count: int = 1) -> None:
        if skill_name not in self.skills_memory:
            self.skills_memory[skill_name] = {
                "usage_count": 0,
                "last_used": None,
                "success_rate": 0.0,
            }
        self.skills_memory[skill_name]["usage_count"] += usage_count
        self.skills_memory[skill_name]["last_used"] = datetime.now().isoformat()
        self._save_memories()

    def add_playbook_entry(self, pattern: str, solution: str, tags: list[str]) -> None:
        entry_id = f"playbook_{len(self.playbook_memory)}"
        self.playbook_memory[entry_id] = {
            "pattern": pattern,
            "solution": solution,
            "tags": tags,
            "created": datetime.now().isoformat(),
        }
        self._save_memories()

    def get_stats(self) -> dict:
        lessons = self.reasoning_bank.search_lessons()
        return {
            "total_lessons": len(lessons),
            "skills_tracked": len(self.skills_memory),
            "playbook_entries": len(self.playbook_memory),
            "core_facts": len(self.core_memory.get_all()),
            "core_tokens_est": self.core_memory.token_estimate(),
            "archived_sessions": self.archival.count(),
        }

    # ── Persistence (skills + playbook) ─────────────────────────────────

    def _load_memories(self) -> None:
        memory_dir = Path("~/.lyra/memory").expanduser()
        memory_dir.mkdir(parents=True, exist_ok=True)

        skills_file = memory_dir / "skills_memory.json"
        if skills_file.exists():
            try:
                self.skills_memory = json.loads(skills_file.read_text())
            except Exception:
                self.skills_memory = {}

        playbook_file = memory_dir / "playbook_memory.json"
        if playbook_file.exists():
            try:
                self.playbook_memory = json.loads(playbook_file.read_text())
            except Exception:
                self.playbook_memory = {}

    def _save_memories(self) -> None:
        memory_dir = Path("~/.lyra/memory").expanduser()
        (memory_dir / "skills_memory.json").write_text(
            json.dumps(self.skills_memory, indent=2)
        )
        (memory_dir / "playbook_memory.json").write_text(
            json.dumps(self.playbook_memory, indent=2)
        )
