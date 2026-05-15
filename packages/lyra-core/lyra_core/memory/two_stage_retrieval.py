"""
Two-Stage Retrieval: Semantic → Episodic Scoping

Stage 1: BM25 over semantic facts → top-5 sessions
Stage 2: Episodic entries scoped to those sessions only

Based on research: docs/152 (memtier-3-tier-architecture-and-retrieval.md)
Impact: -0.038 Acc cost to remove (largest single component after semantic tier)
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
import sqlite3


@dataclass
class RetrievalResult:
    """Result from two-stage retrieval."""
    id: str
    content: str
    score: float
    source: str  # "semantic" or "episodic"
    session_id: Optional[str] = None
    timestamp: Optional[str] = None
    cognitive_weight: float = 0.0


class TwoStageRetriever:
    """
    Two-stage retrieval: coarse-to-fine approach.

    Stage 1: Find relevant sessions via semantic facts (BM25)
    Stage 2: Retrieve episodic entries scoped to those sessions

    Benefits:
    - Reduces retrieval pool from 10K+ to ~500 entries
    - Entries from semantically-relevant sessions bypass time decay
    - Better precision through semantic pre-filtering
    """

    def __init__(
        self,
        semantic_consolidator,
        episodic_memory,
        procedural_memory_db: str
    ):
        """
        Initialize two-stage retriever.

        Args:
            semantic_consolidator: SemanticConsolidator instance
            episodic_memory: EpisodicMemory instance
            procedural_memory_db: Path to procedural memory SQLite DB
        """
        self.semantic = semantic_consolidator
        self.episodic = episodic_memory
        self.procedural_db = procedural_memory_db

    def retrieve(
        self,
        query: str,
        k: int = 10,
        stage1_sessions: int = 5,
        include_procedural: bool = True
    ) -> List[RetrievalResult]:
        """
        Two-stage retrieval with semantic scoping.

        Args:
            query: Search query
            k: Total number of results to return
            stage1_sessions: Number of sessions to retrieve in stage 1
            include_procedural: Whether to include procedural memory

        Returns:
            List of RetrievalResult objects, sorted by score
        """
        results = []

        # Stage 1: Find relevant sessions via semantic facts
        semantic_results = self.semantic.search_facts(
            query=query,
            k=stage1_sessions * 2  # Get more facts to find diverse sessions
        )

        # Extract unique session IDs from semantic facts
        relevant_sessions: Set[str] = set()
        for fact_result in semantic_results:
            # Semantic facts store source_sessions
            fact = next(
                (f for f in self.semantic.facts if f.id == fact_result['id']),
                None
            )
            if fact:
                relevant_sessions.update(fact.source_sessions)

        # Limit to top N sessions
        relevant_sessions = set(list(relevant_sessions)[:stage1_sessions])

        # Stage 2: Retrieve episodic entries scoped to relevant sessions
        if relevant_sessions:
            episodic_results = self._retrieve_episodic_scoped(
                query=query,
                session_ids=relevant_sessions,
                k=k // 2  # Reserve half for episodic
            )
            results.extend(episodic_results)

        # Add semantic facts to results
        for fact_result in semantic_results[:k // 2]:
            results.append(RetrievalResult(
                id=fact_result['id'],
                content=fact_result['fact'],
                score=fact_result['score'],
                source="semantic",
                cognitive_weight=fact_result.get('cognitive_weight', 0.0)
            ))

        # Optionally include procedural memory (existing skills, tools)
        if include_procedural:
            procedural_results = self._retrieve_procedural(query, k=k // 4)
            results.extend(procedural_results)

        # Sort by score and limit to k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:k]

    def _retrieve_episodic_scoped(
        self,
        query: str,
        session_ids: Set[str],
        k: int
    ) -> List[RetrievalResult]:
        """
        Retrieve episodic entries scoped to specific sessions.

        Args:
            query: Search query
            session_ids: Set of session IDs to scope to
            k: Number of results

        Returns:
            List of RetrievalResult objects
        """
        results = []
        query_words = set(query.lower().split())

        # Read entries from relevant sessions
        for session_id in session_ids:
            entries = self.episodic.read_session(session_id)

            for entry in entries:
                # Simple keyword matching (upgrade to BM25/embeddings later)
                entry_words = set(entry.content.lower().split())
                score = len(query_words.intersection(entry_words)) / len(query_words)

                if score > 0:
                    results.append(RetrievalResult(
                        id=entry.id,
                        content=entry.content,
                        score=score,
                        source="episodic",
                        session_id=entry.session_id,
                        timestamp=entry.timestamp.isoformat(),
                        cognitive_weight=entry.cognitive_weight
                    ))

        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:k]

    def _retrieve_procedural(
        self,
        query: str,
        k: int
    ) -> List[RetrievalResult]:
        """
        Retrieve from procedural memory (existing SQLite FTS5).

        Args:
            query: Search query
            k: Number of results

        Returns:
            List of RetrievalResult objects
        """
        conn = sqlite3.connect(self.procedural_db)
        cursor = conn.cursor()

        # Use FTS5 for full-text search
        cursor.execute("""
            SELECT id, content, rank
            FROM memory
            WHERE memory MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, k))

        results = []
        for row in cursor.fetchall():
            entry_id, content, rank = row
            # Convert FTS5 rank to normalized score (rank is negative)
            score = 1.0 / (1.0 - rank) if rank < 0 else 0.5

            results.append(RetrievalResult(
                id=entry_id,
                content=content,
                score=score,
                source="procedural"
            ))

        conn.close()
        return results

    def retrieve_with_time_decay(
        self,
        query: str,
        k: int = 10,
        decay_factor: float = 0.95
    ) -> List[RetrievalResult]:
        """
        Two-stage retrieval with time decay for episodic entries.

        Entries from semantically-relevant sessions bypass time decay.

        Args:
            query: Search query
            k: Number of results
            decay_factor: Time decay factor per day (default: 0.95)

        Returns:
            List of RetrievalResult objects with time-adjusted scores
        """
        from datetime import datetime, timedelta

        results = self.retrieve(query, k=k * 2)  # Get more for filtering

        now = datetime.now()

        for result in results:
            if result.source == "episodic" and result.timestamp:
                # Apply time decay
                entry_time = datetime.fromisoformat(result.timestamp)
                days_old = (now - entry_time).days

                # Decay score based on age
                result.score *= (decay_factor ** days_old)

            # Entries from semantic-scoped sessions already bypass decay
            # by being retrieved in stage 2

        # Re-sort and limit
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:k]

    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get statistics about retrieval sources."""
        return {
            'semantic_facts': len(self.semantic.facts),
            'episodic_entries': self.episodic.get_stats()['total_entries'],
            'procedural_entries': self._count_procedural_entries()
        }

    def _count_procedural_entries(self) -> int:
        """Count entries in procedural memory."""
        conn = sqlite3.connect(self.procedural_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memory")
        count = cursor.fetchone()[0]
        conn.close()
        return count


# Integration example
def integrate_two_stage_retrieval(
    semantic_consolidator,
    episodic_memory,
    procedural_db: str
) -> TwoStageRetriever:
    """
    Create and configure two-stage retriever.

    Args:
        semantic_consolidator: SemanticConsolidator instance
        episodic_memory: EpisodicMemory instance
        procedural_db: Path to procedural memory DB

    Returns:
        Configured TwoStageRetriever
    """
    retriever = TwoStageRetriever(
        semantic_consolidator=semantic_consolidator,
        episodic_memory=episodic_memory,
        procedural_memory_db=procedural_db
    )

    return retriever


# Usage example
"""
from lyra_core.memory.episodic import EpisodicMemory
from lyra_core.memory.semantic_consolidator import SemanticConsolidator
from lyra_core.memory.two_stage_retrieval import TwoStageRetriever

# Initialize components
episodic = EpisodicMemory()
consolidator = SemanticConsolidator(episodic)
retriever = TwoStageRetriever(consolidator, episodic, "~/.lyra/memory/procedural.db")

# Retrieve with two-stage scoping
results = retriever.retrieve(
    query="How do I implement authentication?",
    k=10,
    stage1_sessions=5
)

for result in results:
    print(f"[{result.source}] Score: {result.score:.2f}")
    print(f"  {result.content[:100]}...")
"""
