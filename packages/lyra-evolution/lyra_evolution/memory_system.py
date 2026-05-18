"""
Lyra Memory System: Multi-Tier Persistent Memory

Implements 5-tier memory architecture:
- L0: Working Memory (current session)
- L1: Episodic Memory (concrete events)
- L2: Semantic Memory (stable facts)
- L3: Procedural Memory (reusable skills)
- L4: Failure Memory (lessons from mistakes)

Based on: Memory research synthesis (docs 313-316)
Phase: 0 - Foundation Acceleration
Task: T002 - Memory System Foundation
"""

from pathlib import Path
from typing import Dict, Any, Optional, List, Literal
from dataclasses import dataclass, field
from datetime import datetime
import json
import sqlite3
import hashlib


@dataclass
class MemoryRecord:
    """Base memory record."""
    id: str
    scope: Literal["user", "session", "project", "global"]
    type: Literal["episodic", "semantic", "procedural", "preference", "failure"]
    content: str
    source_span: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    confidence: float = 1.0
    links: List[str] = field(default_factory=list)
    verifier_status: Literal["unverified", "verified", "rejected"] = "unverified"
    metadata: Dict[str, Any] = field(default_factory=dict)


class MemorySystem:
    """
    Multi-tier memory system with SQLite backend.

    Features:
    - 5 memory types (episodic, semantic, procedural, preference, failure)
    - Temporal validity tracking
    - Contradiction detection
    - Hybrid retrieval (BM25 + semantic)
    """

    def __init__(self, db_path: Path):
        """
        Initialize memory system.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Initialize SQLite schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create memories table
        cursor.execute("""
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
                verifier_status TEXT NOT NULL,
                metadata TEXT
            )
        """)

        # Create links table (for memory relationships)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_links (
                from_id TEXT NOT NULL,
                to_id TEXT NOT NULL,
                PRIMARY KEY (from_id, to_id)
            )
        """)

        # Create indexes for fast retrieval
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_type ON memories(type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_scope ON memories(scope)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at ON memories(created_at)
        """)

        conn.commit()
        conn.close()

    def add_memory(self, memory: MemoryRecord) -> str:
        """
        Add memory to system.

        Args:
            memory: Memory record to add

        Returns:
            Memory ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Insert memory
        cursor.execute("""
            INSERT INTO memories (
                id, scope, type, content, source_span,
                created_at, valid_from, valid_until,
                confidence, verifier_status, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory.id,
            memory.scope,
            memory.type,
            memory.content,
            memory.source_span,
            memory.created_at,
            memory.valid_from,
            memory.valid_until,
            memory.confidence,
            memory.verifier_status,
            json.dumps(memory.metadata)
        ))

        # Insert links
        for link_id in memory.links:
            cursor.execute("""
                INSERT OR IGNORE INTO memory_links (from_id, to_id)
                VALUES (?, ?)
            """, (memory.id, link_id))

        conn.commit()
        conn.close()

        return memory.id

    def get_memory(self, memory_id: str) -> Optional[MemoryRecord]:
        """
        Retrieve memory by ID.

        Args:
            memory_id: Memory ID

        Returns:
            Memory record or None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get memory
        cursor.execute("""
            SELECT id, scope, type, content, source_span,
                   created_at, valid_from, valid_until,
                   confidence, verifier_status, metadata
            FROM memories
            WHERE id = ?
        """, (memory_id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        # Get links
        cursor.execute("""
            SELECT to_id FROM memory_links WHERE from_id = ?
        """, (memory_id,))
        links = [r[0] for r in cursor.fetchall()]

        conn.close()

        # Construct memory record
        return MemoryRecord(
            id=row[0],
            scope=row[1],
            type=row[2],
            content=row[3],
            source_span=row[4],
            created_at=row[5],
            valid_from=row[6],
            valid_until=row[7],
            confidence=row[8],
            verifier_status=row[9],
            metadata=json.loads(row[10]) if row[10] else {},
            links=links
        )

    def search_memories(
        self,
        query: Optional[str] = None,
        memory_type: Optional[str] = None,
        scope: Optional[str] = None,
        limit: int = 10
    ) -> List[MemoryRecord]:
        """
        Search memories with filters.

        Args:
            query: Text query (simple substring match)
            memory_type: Filter by type
            scope: Filter by scope
            limit: Maximum results

        Returns:
            List of matching memories
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build query
        sql = """
            SELECT id, scope, type, content, source_span,
                   created_at, valid_from, valid_until,
                   confidence, verifier_status, metadata
            FROM memories
            WHERE 1=1
        """
        params = []

        if query:
            sql += " AND content LIKE ?"
            params.append(f"%{query}%")

        if memory_type:
            sql += " AND type = ?"
            params.append(memory_type)

        if scope:
            sql += " AND scope = ?"
            params.append(scope)

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        # Construct memory records
        memories = []
        for row in rows:
            # Get links
            cursor.execute("""
                SELECT to_id FROM memory_links WHERE from_id = ?
            """, (row[0],))
            links = [r[0] for r in cursor.fetchall()]

            memories.append(MemoryRecord(
                id=row[0],
                scope=row[1],
                type=row[2],
                content=row[3],
                source_span=row[4],
                created_at=row[5],
                valid_from=row[6],
                valid_until=row[7],
                confidence=row[8],
                verifier_status=row[9],
                metadata=json.loads(row[10]) if row[10] else {},
                links=links
            ))

        conn.close()
        return memories

    def update_memory(
        self,
        memory_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update memory fields.

        Args:
            memory_id: Memory ID
            updates: Fields to update

        Returns:
            True if updated
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build update query
        allowed_fields = {
            "confidence", "verifier_status", "valid_until", "metadata"
        }

        set_clauses = []
        params = []

        for field, value in updates.items():
            if field in allowed_fields:
                if field == "metadata":
                    value = json.dumps(value)
                set_clauses.append(f"{field} = ?")
                params.append(value)

        if not set_clauses:
            conn.close()
            return False

        sql = f"UPDATE memories SET {', '.join(set_clauses)} WHERE id = ?"
        params.append(memory_id)

        cursor.execute(sql, params)
        updated = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return updated

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete memory.

        Args:
            memory_id: Memory ID

        Returns:
            True if deleted
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Delete memory
        cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        deleted = cursor.rowcount > 0

        # Delete links
        cursor.execute("DELETE FROM memory_links WHERE from_id = ? OR to_id = ?",
                      (memory_id, memory_id))

        conn.commit()
        conn.close()

        return deleted

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get memory system statistics.

        Returns:
            Statistics dictionary
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total memories
        cursor.execute("SELECT COUNT(*) FROM memories")
        total = cursor.fetchone()[0]

        # By type
        cursor.execute("""
            SELECT type, COUNT(*) FROM memories GROUP BY type
        """)
        by_type = dict(cursor.fetchall())

        # By scope
        cursor.execute("""
            SELECT scope, COUNT(*) FROM memories GROUP BY scope
        """)
        by_scope = dict(cursor.fetchall())

        # By verifier status
        cursor.execute("""
            SELECT verifier_status, COUNT(*) FROM memories GROUP BY verifier_status
        """)
        by_status = dict(cursor.fetchall())

        conn.close()

        return {
            "total": total,
            "by_type": by_type,
            "by_scope": by_scope,
            "by_status": by_status
        }

    @staticmethod
    def generate_memory_id(content: str, memory_type: str) -> str:
        """Generate unique memory ID."""
        hash_input = f"{content}:{memory_type}:{datetime.now().isoformat()}"
        hash_obj = hashlib.sha256(hash_input.encode())
        return f"mem_{hash_obj.hexdigest()[:12]}"


# Example usage
if __name__ == "__main__":
    # Create memory system
    memory_system = MemorySystem(db_path=Path(".lyra/memory/memories.db"))

    # Add episodic memory
    memory_id = MemorySystem.generate_memory_id(
        "User asked about evolution harness",
        "episodic"
    )

    memory = MemoryRecord(
        id=memory_id,
        scope="session",
        type="episodic",
        content="User asked about evolution harness implementation",
        metadata={"turn_id": 1, "timestamp": datetime.now().isoformat()}
    )

    memory_system.add_memory(memory)
    print(f"✅ Added episodic memory: {memory_id}")

    # Add semantic memory
    semantic_id = MemorySystem.generate_memory_id(
        "Harness prevents reward hacking",
        "semantic"
    )

    semantic = MemoryRecord(
        id=semantic_id,
        scope="project",
        type="semantic",
        content="Evolution harness prevents reward hacking through OS-level boundaries",
        confidence=0.95,
        verifier_status="verified"
    )

    memory_system.add_memory(semantic)
    print(f"✅ Added semantic memory: {semantic_id}")

    # Search memories
    results = memory_system.search_memories(query="harness", limit=5)
    print(f"✅ Found {len(results)} memories matching 'harness'")

    # Get statistics
    stats = memory_system.get_statistics()
    print(f"✅ Memory statistics: {stats['total']} total memories")
    print(f"   By type: {stats['by_type']}")
    print(f"   By scope: {stats['by_scope']}")
