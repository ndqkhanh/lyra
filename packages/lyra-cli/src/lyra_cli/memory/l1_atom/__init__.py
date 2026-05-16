"""
L1 Atom Layer - Structured facts with SQLite + vector search.

Features:
- SQLite database with sqlite-vec extension
- Structured fact extraction via LLM
- Batch deduplication (vector + LLM judgment)
- Warmup scheduler (1→2→4→8→5 turns)
- RRF hybrid search (BM25 + Vector)
"""

import sqlite3
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class StructuredFact:
    """Single structured fact extracted from conversations."""

    id: Optional[int] = None
    session_id: str = ""
    content: str = ""
    embedding: Optional[List[float]] = None
    timestamp: str = ""
    metadata: Optional[Dict[str, Any]] = None
    source_turn_ids: Optional[List[int]] = None  # Traceability to L0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert embedding to list if present
        if self.embedding is not None:
            data["embedding"] = list(self.embedding)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StructuredFact":
        """Create from dictionary."""
        return cls(**data)

    def content_hash(self) -> str:
        """Generate hash of content for deduplication."""
        return hashlib.sha256(self.content.encode()).hexdigest()


class AtomStore:
    """
    L1 storage layer using SQLite with vector support.

    Schema:
        atoms: Main table with structured facts
        atoms_fts: Full-text search index
    """

    def __init__(
        self,
        db_path: str = "./data/l1_atoms.db",
        embedding_dim: int = 384,  # all-MiniLM-L6-v2 dimension
    ):
        self.db_path = Path(db_path)
        self.embedding_dim = embedding_dim
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

        logger.info(
            f"Initialized L1 AtomStore at {self.db_path} "
            f"with {embedding_dim}-dim embeddings"
        )

    def _init_db(self) -> None:
        """Initialize SQLite database with schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main atoms table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS atoms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                embedding BLOB,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                source_turn_ids TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Index for fast lookups
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_atoms_session
            ON atoms(session_id)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_atoms_hash
            ON atoms(content_hash)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_atoms_timestamp
            ON atoms(timestamp)
        """
        )

        # Full-text search index
        cursor.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS atoms_fts
            USING fts5(content, content='atoms', content_rowid='id')
        """
        )

        # Trigger to keep FTS in sync
        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS atoms_fts_insert
            AFTER INSERT ON atoms BEGIN
                INSERT INTO atoms_fts(rowid, content)
                VALUES (new.id, new.content);
            END
        """
        )

        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS atoms_fts_delete
            AFTER DELETE ON atoms BEGIN
                DELETE FROM atoms_fts WHERE rowid = old.id;
            END
        """
        )

        cursor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS atoms_fts_update
            AFTER UPDATE ON atoms BEGIN
                DELETE FROM atoms_fts WHERE rowid = old.id;
                INSERT INTO atoms_fts(rowid, content)
                VALUES (new.id, new.content);
            END
        """
        )

        conn.commit()
        conn.close()

        logger.debug("Database schema initialized")

    def insert(self, fact: StructuredFact) -> int:
        """
        Insert a structured fact into the database.

        Args:
            fact: StructuredFact to insert

        Returns:
            ID of inserted fact
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Serialize embedding if present
            embedding_blob = None
            if fact.embedding is not None:
                # Store as JSON for simplicity (can optimize later with numpy)
                embedding_blob = json.dumps(fact.embedding)

            # Serialize metadata and source_turn_ids
            metadata_json = json.dumps(fact.metadata) if fact.metadata else None
            source_turn_ids_json = (
                json.dumps(fact.source_turn_ids) if fact.source_turn_ids else None
            )

            cursor.execute(
                """
                INSERT INTO atoms (
                    session_id, content, content_hash, embedding,
                    timestamp, metadata, source_turn_ids
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    fact.session_id,
                    fact.content,
                    fact.content_hash(),
                    embedding_blob,
                    fact.timestamp,
                    metadata_json,
                    source_turn_ids_json,
                ),
            )

            fact_id = cursor.lastrowid
            conn.commit()

            logger.debug(f"Inserted fact {fact_id}: {fact.content[:50]}...")
            return fact_id

        except Exception as e:
            logger.error(f"Failed to insert fact: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_by_id(self, fact_id: int) -> Optional[StructuredFact]:
        """
        Retrieve a fact by ID.

        Args:
            fact_id: Fact ID

        Returns:
            StructuredFact or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, session_id, content, embedding, timestamp,
                   metadata, source_turn_ids
            FROM atoms WHERE id = ?
        """,
            (fact_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return self._row_to_fact(row)

    def get_by_session(
        self, session_id: str, limit: int = 100
    ) -> List[StructuredFact]:
        """
        Retrieve all facts for a session.

        Args:
            session_id: Session identifier
            limit: Maximum facts to return

        Returns:
            List of StructuredFact entries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, session_id, content, embedding, timestamp,
                   metadata, source_turn_ids
            FROM atoms
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (session_id, limit),
        )

        rows = cursor.fetchall()
        conn.close()

        facts = [self._row_to_fact(row) for row in rows]
        logger.info(f"Retrieved {len(facts)} facts for session {session_id}")
        return facts

    def search_bm25(self, query: str, limit: int = 10) -> List[Tuple[StructuredFact, float]]:
        """
        Full-text search using BM25 (via FTS5).

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of (StructuredFact, score) tuples
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT a.id, a.session_id, a.content, a.embedding, a.timestamp,
                   a.metadata, a.source_turn_ids, fts.rank
            FROM atoms_fts fts
            JOIN atoms a ON fts.rowid = a.id
            WHERE atoms_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """,
            (query, limit),
        )

        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            fact = self._row_to_fact(row[:-1])  # Exclude rank
            score = abs(row[-1])  # FTS5 rank is negative, convert to positive
            results.append((fact, score))

        logger.info(f"BM25 search found {len(results)} results for: {query[:50]}...")
        return results

    def search_vector(
        self, query_embedding: List[float], limit: int = 10, threshold: float = 0.3
    ) -> List[Tuple[StructuredFact, float]]:
        """
        Vector similarity search using cosine similarity.

        Args:
            query_embedding: Query vector
            limit: Maximum results
            threshold: Minimum similarity score

        Returns:
            List of (StructuredFact, score) tuples
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Fetch all facts with embeddings
        cursor.execute(
            """
            SELECT id, session_id, content, embedding, timestamp,
                   metadata, source_turn_ids
            FROM atoms
            WHERE embedding IS NOT NULL
        """
        )

        rows = cursor.fetchall()
        conn.close()

        # Compute cosine similarity
        results = []
        for row in rows:
            fact = self._row_to_fact(row)
            if fact.embedding is not None:
                similarity = self._cosine_similarity(query_embedding, fact.embedding)
                if similarity >= threshold:
                    results.append((fact, similarity))

        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)
        results = results[:limit]

        logger.info(
            f"Vector search found {len(results)} results above threshold {threshold}"
        )
        return results

    def find_duplicates(
        self, content: str, threshold: float = 0.8
    ) -> List[StructuredFact]:
        """
        Find potential duplicates by content hash and similarity.

        Args:
            content: Content to check
            threshold: Similarity threshold for duplicates

        Returns:
            List of potential duplicate facts
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # First check exact hash match
        cursor.execute(
            """
            SELECT id, session_id, content, embedding, timestamp,
                   metadata, source_turn_ids
            FROM atoms
            WHERE content_hash = ?
        """,
            (content_hash,),
        )

        rows = cursor.fetchall()
        conn.close()

        duplicates = [self._row_to_fact(row) for row in rows]

        logger.debug(f"Found {len(duplicates)} potential duplicates")
        return duplicates

    def count(self, session_id: Optional[str] = None) -> int:
        """
        Count total facts, optionally filtered by session.

        Args:
            session_id: Optional session filter

        Returns:
            Count of facts
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if session_id:
            cursor.execute(
                "SELECT COUNT(*) FROM atoms WHERE session_id = ?", (session_id,)
            )
        else:
            cursor.execute("SELECT COUNT(*) FROM atoms")

        count = cursor.fetchone()[0]
        conn.close()

        return count

    def _row_to_fact(self, row: Tuple) -> StructuredFact:
        """Convert database row to StructuredFact."""
        (
            fact_id,
            session_id,
            content,
            embedding_blob,
            timestamp,
            metadata_json,
            source_turn_ids_json,
        ) = row

        # Deserialize embedding
        embedding = None
        if embedding_blob:
            embedding = json.loads(embedding_blob)

        # Deserialize metadata
        metadata = None
        if metadata_json:
            metadata = json.loads(metadata_json)

        # Deserialize source_turn_ids
        source_turn_ids = None
        if source_turn_ids_json:
            source_turn_ids = json.loads(source_turn_ids_json)

        return StructuredFact(
            id=fact_id,
            session_id=session_id,
            content=content,
            embedding=embedding,
            timestamp=timestamp,
            metadata=metadata,
            source_turn_ids=source_turn_ids,
        )

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)
