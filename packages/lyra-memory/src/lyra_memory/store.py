"""
Main memory store with hybrid retrieval (BM25 + vector).

Implements the complete memory system with:
- Multi-tier storage (hot/warm/cold)
- Hybrid BM25 + vector retrieval
- Temporal validity filtering
- Contradiction detection
- Verifier-gated writes
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from lyra_memory.database import MemoryDatabase
from lyra_memory.schema import MemoryRecord, MemoryScope, MemoryType, VerifierStatus


class MemoryStore:
    """
    Main memory store with hybrid retrieval.

    Architecture:
    - Hot tier: In-memory cache (current session)
    - Warm tier: SQLite (last 7 days)
    - Cold tier: SQLite (older than 7 days)
    - Hybrid retrieval: BM25 + vector embeddings
    """

    def __init__(
        self,
        db_path: Path,
        embedding_model: str = "all-MiniLM-L6-v2",
        enable_embeddings: bool = True,
    ):
        """
        Initialize memory store.

        Args:
            db_path: Path to SQLite database
            embedding_model: Sentence-transformers model name
            enable_embeddings: Whether to use vector embeddings
        """
        self.db = MemoryDatabase(db_path)
        self.enable_embeddings = enable_embeddings

        # Hot tier: in-memory cache
        self.hot_cache: Dict[str, MemoryRecord] = {}

        # Embedding model for vector search
        self.embedder = None
        if enable_embeddings:
            self.embedder = SentenceTransformer(embedding_model)

        # BM25 index (rebuilt on demand)
        self._bm25_index: Optional[BM25Okapi] = None
        self._bm25_docs: List[MemoryRecord] = []
        self._bm25_dirty = True

    def write(
        self,
        content: str,
        scope: MemoryScope = MemoryScope.SESSION,
        type: MemoryType = MemoryType.EPISODIC,
        source_span: Optional[str] = None,
        valid_from: Optional[datetime] = None,
        valid_until: Optional[datetime] = None,
        confidence: float = 1.0,
        links: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        verify: bool = True,
    ) -> MemoryRecord:
        """
        Write a memory to the store.

        Args:
            content: Memory content
            scope: Memory scope
            type: Memory type
            source_span: Source reference
            valid_from: When this fact became true
            valid_until: When this fact stopped being true
            confidence: Confidence score 0.0-1.0
            links: Related memory IDs
            metadata: Additional structured data
            verify: Whether to run verification

        Returns:
            The created MemoryRecord
        """
        memory = MemoryRecord(
            scope=scope,
            type=type,
            content=content,
            source_span=source_span,
            valid_from=valid_from,
            valid_until=valid_until,
            confidence=confidence,
            links=links or [],
            metadata=metadata or {},
            verifier_status=VerifierStatus.UNVERIFIED,
        )

        # Generate embedding if enabled
        if self.enable_embeddings and self.embedder:
            memory.embedding = self.embedder.encode(content).tolist()

        # Verify if requested
        if verify:
            memory.verifier_status = self._verify_memory(memory)

        # Write to appropriate tier
        if scope == MemoryScope.SESSION:
            # Hot tier: in-memory only
            self.hot_cache[memory.id] = memory
        else:
            # Warm/cold tier: persist to database
            self.db.insert(memory)

        # Mark BM25 index as dirty
        self._bm25_dirty = True

        return memory

    def retrieve(
        self,
        query: str,
        scope: Optional[MemoryScope] = None,
        type: Optional[MemoryType] = None,
        valid_at: Optional[datetime] = None,
        limit: int = 10,
        hybrid_alpha: float = 0.5,
    ) -> List[MemoryRecord]:
        """
        Retrieve memories using hybrid BM25 + vector search.

        Args:
            query: Search query
            scope: Filter by scope
            type: Filter by type
            valid_at: Filter by temporal validity (default: now)
            limit: Maximum results
            hybrid_alpha: Weight for BM25 vs vector (0.0 = pure BM25, 1.0 = pure vector)

        Returns:
            List of matching memories, ranked by relevance
        """
        valid_at = valid_at or datetime.now()

        # Get candidates from all tiers
        candidates = self._get_candidates(scope, type, valid_at)

        if not candidates:
            return []

        # Hybrid retrieval
        if self.enable_embeddings and self.embedder and hybrid_alpha > 0:
            scores = self._hybrid_score(query, candidates, hybrid_alpha)
        else:
            scores = self._bm25_score(query, candidates)

        # Sort by score and take top-k
        ranked = sorted(
            zip(candidates, scores),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        # Filter out superseded memories
        results = [mem for mem, score in ranked if not mem.is_superseded()]

        return results

    def get(self, memory_id: str) -> Optional[MemoryRecord]:
        """Get a memory by ID."""
        # Check hot cache first
        if memory_id in self.hot_cache:
            return self.hot_cache[memory_id]

        # Check database
        return self.db.get(memory_id)

    def update(self, memory: MemoryRecord) -> None:
        """Update a memory."""
        if memory.id in self.hot_cache:
            self.hot_cache[memory.id] = memory
        else:
            self.db.update(memory)

        self._bm25_dirty = True

    def delete(self, memory_id: str) -> None:
        """Delete a memory."""
        if memory_id in self.hot_cache:
            del self.hot_cache[memory_id]
        else:
            self.db.delete(memory_id)

        self._bm25_dirty = True

    def supersede(self, old_id: str, new_memory: MemoryRecord) -> None:
        """Mark an old memory as superseded by a new one."""
        old_memory = self.get(old_id)
        if old_memory:
            old_memory.superseded_by = new_memory.id
            old_memory.valid_until = datetime.now()
            self.update(old_memory)

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        db_stats = self.db.get_stats()
        return {
            **db_stats,
            "hot_cache_size": len(self.hot_cache),
        }

    def _get_candidates(
        self,
        scope: Optional[MemoryScope],
        type: Optional[MemoryType],
        valid_at: datetime,
    ) -> List[MemoryRecord]:
        """Get candidate memories from all tiers."""
        candidates = []

        # Hot tier
        for memory in self.hot_cache.values():
            if self._matches_filters(memory, scope, type, valid_at):
                candidates.append(memory)

        # Warm/cold tier
        db_candidates = self.db.filter(
            scope=scope,
            type=type,
            verifier_status=VerifierStatus.VERIFIED,
            valid_at=valid_at,
            limit=1000,
        )
        candidates.extend(db_candidates)

        return candidates

    def _matches_filters(
        self,
        memory: MemoryRecord,
        scope: Optional[MemoryScope],
        type: Optional[MemoryType],
        valid_at: datetime,
    ) -> bool:
        """Check if memory matches filters."""
        if scope and memory.scope != scope:
            return False
        if type and memory.type != type:
            return False
        if not memory.is_valid_at(valid_at):
            return False
        if memory.verifier_status != VerifierStatus.VERIFIED:
            return False
        return True

    def _bm25_score(self, query: str, candidates: List[MemoryRecord]) -> List[float]:
        """Score candidates using BM25."""
        if self._bm25_dirty:
            self._rebuild_bm25_index(candidates)

        if not self._bm25_index:
            return [0.0] * len(candidates)

        query_tokens = query.lower().split()
        scores = self._bm25_index.get_scores(query_tokens)
        return scores.tolist()

    def _vector_score(self, query: str, candidates: List[MemoryRecord]) -> List[float]:
        """Score candidates using vector similarity."""
        if not self.embedder:
            return [0.0] * len(candidates)

        query_embedding = self.embedder.encode(query)

        scores = []
        for memory in candidates:
            if memory.embedding:
                # Cosine similarity
                similarity = np.dot(query_embedding, memory.embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(memory.embedding)
                )
                scores.append(float(similarity))
            else:
                scores.append(0.0)

        return scores

    def _hybrid_score(
        self,
        query: str,
        candidates: List[MemoryRecord],
        alpha: float,
    ) -> List[float]:
        """Combine BM25 and vector scores."""
        bm25_scores = self._bm25_score(query, candidates)
        vector_scores = self._vector_score(query, candidates)

        # Normalize scores to [0, 1]
        bm25_scores = self._normalize(bm25_scores)
        vector_scores = self._normalize(vector_scores)

        # Weighted combination
        hybrid_scores = [
            (1 - alpha) * bm25 + alpha * vec
            for bm25, vec in zip(bm25_scores, vector_scores)
        ]

        return hybrid_scores

    def _normalize(self, scores: List[float]) -> List[float]:
        """Normalize scores to [0, 1]."""
        if not scores:
            return []

        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score:
            return [1.0] * len(scores)

        return [(s - min_score) / (max_score - min_score) for s in scores]

    def _rebuild_bm25_index(self, candidates: List[MemoryRecord]) -> None:
        """Rebuild BM25 index from candidates."""
        self._bm25_docs = candidates
        tokenized_docs = [doc.content.lower().split() for doc in candidates]
        self._bm25_index = BM25Okapi(tokenized_docs)
        self._bm25_dirty = False

    def _verify_memory(self, memory: MemoryRecord) -> VerifierStatus:
        """
        Verify a memory before storing.

        Currently implements basic checks. Will be extended with:
        - Contradiction detection
        - Fact-checking
        - Source verification
        """
        # Basic verification: check confidence threshold
        if memory.confidence < 0.5:
            return VerifierStatus.QUARANTINED

        # Check for suspicious patterns (basic prompt injection detection)
        suspicious_patterns = [
            "ignore previous",
            "disregard",
            "forget everything",
            "new instructions",
        ]
        content_lower = memory.content.lower()
        if any(pattern in content_lower for pattern in suspicious_patterns):
            return VerifierStatus.QUARANTINED

        return VerifierStatus.VERIFIED

    def close(self):
        """Close the memory store."""
        self.db.close()
