"""
SQLite database layer for Lyra memory system.

Implements multi-tier storage:
- Hot tier: In-memory (current session)
- Warm tier: SQLite (last 7 days)
- Cold tier: SQLite (older than 7 days)
- Graph tier: NetworkX (entity relationships)
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from lyra_memory.schema import MemoryRecord, MemoryScope, MemoryType, VerifierStatus


class MemoryDatabase:
    """SQLite database for persistent memory storage."""

    def __init__(self, db_path: Path):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                scope TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                source_span TEXT,
                created_at TEXT NOT NULL,
                valid_from TEXT,
                valid_until TEXT,
                confidence REAL NOT NULL,
                links TEXT,  -- JSON array
                verifier_status TEXT NOT NULL,
                metadata TEXT,  -- JSON object
                superseded_by TEXT,
                FOREIGN KEY (superseded_by) REFERENCES memories(id)
            );

            CREATE INDEX IF NOT EXISTS idx_scope ON memories(scope);
            CREATE INDEX IF NOT EXISTS idx_type ON memories(type);
            CREATE INDEX IF NOT EXISTS idx_created_at ON memories(created_at);
            CREATE INDEX IF NOT EXISTS idx_valid_from ON memories(valid_from);
            CREATE INDEX IF NOT EXISTS idx_valid_until ON memories(valid_until);
            CREATE INDEX IF NOT EXISTS idx_verifier_status ON memories(verifier_status);
            CREATE INDEX IF NOT EXISTS idx_superseded_by ON memories(superseded_by);

            -- Full-text search index
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                id UNINDEXED,
                content,
                content=memories,
                content_rowid=rowid
            );

            -- Triggers to keep FTS in sync
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, id, content)
                VALUES (new.rowid, new.id, new.content);
            END;

            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                DELETE FROM memories_fts WHERE rowid = old.rowid;
            END;

            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                UPDATE memories_fts SET content = new.content WHERE rowid = new.rowid;
            END;
        """)
        self.conn.commit()

    def insert(self, memory: MemoryRecord) -> None:
        """Insert a memory record."""
        self.conn.execute(
            """
            INSERT INTO memories (
                id, scope, type, content, source_span, created_at,
                valid_from, valid_until, confidence, links,
                verifier_status, metadata, superseded_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory.id,
                memory.scope.value,
                memory.type.value,
                memory.content,
                memory.source_span,
                memory.created_at.isoformat(),
                memory.valid_from.isoformat() if memory.valid_from else None,
                memory.valid_until.isoformat() if memory.valid_until else None,
                memory.confidence,
                json.dumps(memory.links),
                memory.verifier_status.value,
                json.dumps(memory.metadata),
                memory.superseded_by,
            ),
        )
        self.conn.commit()

    def get(self, memory_id: str) -> Optional[MemoryRecord]:
        """Get a memory by ID."""
        cursor = self.conn.execute(
            "SELECT * FROM memories WHERE id = ?",
            (memory_id,)
        )
        row = cursor.fetchone()
        if row:
            return self._row_to_memory(row)
        return None

    def update(self, memory: MemoryRecord) -> None:
        """Update a memory record."""
        self.conn.execute(
            """
            UPDATE memories SET
                scope = ?, type = ?, content = ?, source_span = ?,
                valid_from = ?, valid_until = ?, confidence = ?,
                links = ?, verifier_status = ?, metadata = ?,
                superseded_by = ?
            WHERE id = ?
            """,
            (
                memory.scope.value,
                memory.type.value,
                memory.content,
                memory.source_span,
                memory.valid_from.isoformat() if memory.valid_from else None,
                memory.valid_until.isoformat() if memory.valid_until else None,
                memory.confidence,
                json.dumps(memory.links),
                memory.verifier_status.value,
                json.dumps(memory.metadata),
                memory.superseded_by,
                memory.id,
            ),
        )
        self.conn.commit()

    def delete(self, memory_id: str) -> None:
        """Delete a memory by ID."""
        self.conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.conn.commit()

    def search_fts(self, query: str, limit: int = 10) -> List[MemoryRecord]:
        """Full-text search using SQLite FTS5."""
        cursor = self.conn.execute(
            """
            SELECT m.* FROM memories m
            JOIN memories_fts fts ON m.rowid = fts.rowid
            WHERE memories_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        )
        return [self._row_to_memory(row) for row in cursor.fetchall()]

    def filter(
        self,
        scope: Optional[MemoryScope] = None,
        type: Optional[MemoryType] = None,
        verifier_status: Optional[VerifierStatus] = None,
        valid_at: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[MemoryRecord]:
        """Filter memories by criteria."""
        conditions = []
        params = []

        if scope:
            conditions.append("scope = ?")
            params.append(scope.value)

        if type:
            conditions.append("type = ?")
            params.append(type.value)

        if verifier_status:
            conditions.append("verifier_status = ?")
            params.append(verifier_status.value)

        if valid_at:
            # Memory is valid if:
            # - valid_from is NULL OR valid_from <= valid_at
            # - valid_until is NULL OR valid_until >= valid_at
            conditions.append(
                "(valid_from IS NULL OR valid_from <= ?) AND "
                "(valid_until IS NULL OR valid_until >= ?)"
            )
            params.extend([valid_at.isoformat(), valid_at.isoformat()])

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM memories WHERE {where_clause} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor = self.conn.execute(query, params)
        return [self._row_to_memory(row) for row in cursor.fetchall()]

    def get_recent(self, days: int = 7, limit: int = 100) -> List[MemoryRecord]:
        """Get recent memories within the last N days."""
        cutoff = datetime.now() - timedelta(days=days)
        cursor = self.conn.execute(
            "SELECT * FROM memories WHERE created_at >= ? ORDER BY created_at DESC LIMIT ?",
            (cutoff.isoformat(), limit),
        )
        return [self._row_to_memory(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        cursor = self.conn.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN verifier_status = 'verified' THEN 1 END) as verified,
                COUNT(CASE WHEN verifier_status = 'unverified' THEN 1 END) as unverified,
                COUNT(CASE WHEN verifier_status = 'quarantined' THEN 1 END) as quarantined,
                COUNT(CASE WHEN superseded_by IS NOT NULL THEN 1 END) as superseded
            FROM memories
        """)
        row = cursor.fetchone()

        return {
            "total": row["total"],
            "verified": row["verified"],
            "unverified": row["unverified"],
            "quarantined": row["quarantined"],
            "superseded": row["superseded"],
            "active": row["total"] - row["superseded"],
        }

    def _row_to_memory(self, row: sqlite3.Row) -> MemoryRecord:
        """Convert database row to MemoryRecord."""
        return MemoryRecord(
            id=row["id"],
            scope=MemoryScope(row["scope"]),
            type=MemoryType(row["type"]),
            content=row["content"],
            source_span=row["source_span"],
            created_at=datetime.fromisoformat(row["created_at"]),
            valid_from=datetime.fromisoformat(row["valid_from"]) if row["valid_from"] else None,
            valid_until=datetime.fromisoformat(row["valid_until"]) if row["valid_until"] else None,
            confidence=row["confidence"],
            links=json.loads(row["links"]) if row["links"] else [],
            verifier_status=VerifierStatus(row["verifier_status"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            superseded_by=row["superseded_by"],
        )

    def close(self):
        """Close database connection."""
        self.conn.close()
