"""
Cognitive Weight Attribution System for Lyra Memory

Implements closed-loop feedback where memory entries are scored based on
their correlation with successful tool calls. Entries that co-occur with
successful outcomes get higher weights; those with failures get lower weights.

Based on MEMTIER research (docs/152-memtier-3-tier-architecture-and-retrieval.md)
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import sqlite3


@dataclass
class MemoryEntry:
    """Memory entry with cognitive weight."""
    id: str
    content: str
    session_id: str
    timestamp: datetime
    cognitive_weight: float = 0.0  # Range: [-1.0, 1.0]
    retrieval_count: int = 0
    success_count: int = 0
    failure_count: int = 0


class CognitiveWeightAttributor:
    """
    Manages cognitive weight attribution for memory entries.

    Updates weights based on tool call outcomes using Jaccard similarity
    as a fallback when embeddings are not available.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_schema()

    def _init_schema(self):
        """Add cognitive weight fields to memory schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Add cognitive weight fields if they don't exist
        try:
            cursor.execute("""
                ALTER TABLE memory
                ADD COLUMN cognitive_weight REAL DEFAULT 0.0
            """)
            cursor.execute("""
                ALTER TABLE memory
                ADD COLUMN retrieval_count INTEGER DEFAULT 0
            """)
            cursor.execute("""
                ALTER TABLE memory
                ADD COLUMN success_count INTEGER DEFAULT 0
            """)
            cursor.execute("""
                ALTER TABLE memory
                ADD COLUMN failure_count INTEGER DEFAULT 0
            """)
            conn.commit()
        except sqlite3.OperationalError:
            # Columns already exist
            pass
        finally:
            conn.close()

    def update_weights_for_session(self, session_id: str):
        """
        Update cognitive weights for all memory entries based on
        tool call outcomes in the given session.

        Args:
            session_id: Session to analyze for weight updates
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all tool calls for this session
        cursor.execute("""
            SELECT turn_id, tool_name, success, retrieved_entry_ids
            FROM tool_calls
            WHERE session_id = ?
            ORDER BY turn_id
        """, (session_id,))

        tool_calls = cursor.fetchall()

        for turn_id, tool_name, success, retrieved_ids_str in tool_calls:
            if not retrieved_ids_str:
                continue

            retrieved_ids = retrieved_ids_str.split(',')
            delta = 0.1 if success else -0.1

            for entry_id in retrieved_ids:
                # Update cognitive weight
                cursor.execute("""
                    UPDATE memory
                    SET cognitive_weight = CASE
                        WHEN cognitive_weight + ? > 1.0 THEN 1.0
                        WHEN cognitive_weight + ? < -1.0 THEN -1.0
                        ELSE cognitive_weight + ?
                    END,
                    retrieval_count = retrieval_count + 1,
                    success_count = success_count + CASE WHEN ? THEN 1 ELSE 0 END,
                    failure_count = failure_count + CASE WHEN ? THEN 0 ELSE 1 END
                    WHERE id = ?
                """, (delta, delta, delta, success, success, entry_id))

        conn.commit()
        conn.close()

    def get_weighted_score(self, entry_id: str, base_score: float) -> float:
        """
        Apply cognitive weight to a base retrieval score.

        Args:
            entry_id: Memory entry ID
            base_score: Base similarity/relevance score

        Returns:
            Weighted score incorporating cognitive weight
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT cognitive_weight
            FROM memory
            WHERE id = ?
        """, (entry_id,))

        result = cursor.fetchone()
        conn.close()

        if not result:
            return base_score

        cognitive_weight = result[0]

        # Apply weight: positive weight boosts score, negative weight reduces it
        weighted_score = base_score * (1.0 + cognitive_weight)

        # Clamp to [0, 1] if base_score was normalized
        if 0 <= base_score <= 1:
            weighted_score = max(0.0, min(1.0, weighted_score))

        return weighted_score

    def get_entry_stats(self, entry_id: str) -> Optional[Dict]:
        """Get statistics for a memory entry."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT cognitive_weight, retrieval_count,
                   success_count, failure_count
            FROM memory
            WHERE id = ?
        """, (entry_id,))

        result = cursor.fetchone()
        conn.close()

        if not result:
            return None

        weight, retrieval_count, success_count, failure_count = result

        return {
            'cognitive_weight': weight,
            'retrieval_count': retrieval_count,
            'success_count': success_count,
            'failure_count': failure_count,
            'success_rate': success_count / retrieval_count if retrieval_count > 0 else 0.0
        }

    def prune_low_weight_entries(self, threshold: float = -0.5):
        """
        Remove memory entries with cognitive weight below threshold.

        Args:
            threshold: Minimum cognitive weight to keep (default: -0.5)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM memory
            WHERE cognitive_weight < ?
            AND retrieval_count >= 5  -- Only prune if retrieved at least 5 times
        """, (threshold,))

        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted_count


# Integration with existing retrieval
def apply_cognitive_weights(results: List[Dict], attributor: CognitiveWeightAttributor) -> List[Dict]:
    """
    Apply cognitive weights to retrieval results.

    Args:
        results: List of retrieval results with 'id' and 'score' fields
        attributor: CognitiveWeightAttributor instance

    Returns:
        Results with weighted scores, sorted by weighted score
    """
    for result in results:
        entry_id = result['id']
        base_score = result['score']
        result['weighted_score'] = attributor.get_weighted_score(entry_id, base_score)
        result['base_score'] = base_score  # Keep original for debugging

    # Re-sort by weighted score
    results.sort(key=lambda x: x['weighted_score'], reverse=True)

    return results
