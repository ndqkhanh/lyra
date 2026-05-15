"""Memory Management System for Lyra.

Implements reasoning bank, skills memory, and playbook memory.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Lesson:
    """A lesson learned from experience."""
    id: Optional[int]
    tags: list[str]
    verdict: str  # success | failure | insight
    lesson: str
    timestamp: str
    context: Optional[str] = None


class ReasoningBank:
    """SQLite-backed reasoning bank for storing lessons."""

    def __init__(self, db_path: str = "~/.lyra/memory/reasoning_bank.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tags TEXT NOT NULL,
                verdict TEXT NOT NULL,
                lesson TEXT NOT NULL,
                context TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def add_lesson(self, tags: list[str], verdict: str, lesson: str, context: str = None):
        """Add a lesson to the reasoning bank."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO lessons (tags, verdict, lesson, context, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            json.dumps(tags),
            verdict,
            lesson,
            context,
            datetime.now().isoformat()
        ))
        conn.commit()
        lesson_id = cursor.lastrowid
        conn.close()
        return lesson_id

    def search_lessons(self, query: str = None, tags: list[str] = None) -> list[Lesson]:
        """Search lessons by query or tags."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if tags:
            # Search by tags
            results = []
            for tag in tags:
                cursor.execute("""
                    SELECT id, tags, verdict, lesson, context, timestamp
                    FROM lessons
                    WHERE tags LIKE ?
                    ORDER BY timestamp DESC
                """, (f'%{tag}%',))
                results.extend(cursor.fetchall())
        elif query:
            # Full-text search
            cursor.execute("""
                SELECT id, tags, verdict, lesson, context, timestamp
                FROM lessons
                WHERE lesson LIKE ? OR context LIKE ?
                ORDER BY timestamp DESC
            """, (f'%{query}%', f'%{query}%'))
            results = cursor.fetchall()
        else:
            # Get all lessons
            cursor.execute("""
                SELECT id, tags, verdict, lesson, context, timestamp
                FROM lessons
                ORDER BY timestamp DESC
            """)
            results = cursor.fetchall()

        conn.close()

        lessons = []
        for row in results:
            lessons.append(Lesson(
                id=row[0],
                tags=json.loads(row[1]),
                verdict=row[2],
                lesson=row[3],
                context=row[4],
                timestamp=row[5]
            ))
        return lessons


class MemoryManager:
    """Manages all memory systems."""

    def __init__(self):
        self.reasoning_bank = ReasoningBank()
        self.skills_memory = {}
        self.playbook_memory = {}
        self._load_memories()

    def _load_memories(self):
        """Load memories from disk."""
        memory_dir = Path("~/.lyra/memory").expanduser()
        memory_dir.mkdir(parents=True, exist_ok=True)

        # Load skills memory
        skills_file = memory_dir / "skills_memory.json"
        if skills_file.exists():
            with open(skills_file) as f:
                self.skills_memory = json.load(f)

        # Load playbook memory
        playbook_file = memory_dir / "playbook_memory.json"
        if playbook_file.exists():
            with open(playbook_file) as f:
                self.playbook_memory = json.load(f)

    def _save_memories(self):
        """Save memories to disk."""
        memory_dir = Path("~/.lyra/memory").expanduser()

        # Save skills memory
        with open(memory_dir / "skills_memory.json", "w") as f:
            json.dump(self.skills_memory, f, indent=2)

        # Save playbook memory
        with open(memory_dir / "playbook_memory.json", "w") as f:
            json.dump(self.playbook_memory, f, indent=2)

    def reflect(self, tags: list[str], verdict: str, lesson: str, context: str = None) -> int:
        """Add a reflection/lesson to memory."""
        lesson_id = self.reasoning_bank.add_lesson(tags, verdict, lesson, context)
        return lesson_id

    def recall(self, query: str = None, tags: list[str] = None) -> list[Lesson]:
        """Recall lessons from memory."""
        return self.reasoning_bank.search_lessons(query, tags)

    def add_skill_memory(self, skill_name: str, usage_count: int = 1):
        """Track skill usage."""
        if skill_name not in self.skills_memory:
            self.skills_memory[skill_name] = {
                "usage_count": 0,
                "last_used": None,
                "success_rate": 0.0,
            }

        self.skills_memory[skill_name]["usage_count"] += usage_count
        self.skills_memory[skill_name]["last_used"] = datetime.now().isoformat()
        self._save_memories()

    def add_playbook_entry(self, pattern: str, solution: str, tags: list[str]):
        """Add a pattern-solution pair to playbook."""
        entry_id = f"playbook_{len(self.playbook_memory)}"
        self.playbook_memory[entry_id] = {
            "pattern": pattern,
            "solution": solution,
            "tags": tags,
            "created": datetime.now().isoformat(),
        }
        self._save_memories()

    def get_stats(self) -> dict:
        """Get memory statistics."""
        lessons = self.reasoning_bank.search_lessons()
        return {
            "total_lessons": len(lessons),
            "skills_tracked": len(self.skills_memory),
            "playbook_entries": len(self.playbook_memory),
        }
