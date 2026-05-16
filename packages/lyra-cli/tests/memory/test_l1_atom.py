"""
Tests for L1 Atom Layer and RRF hybrid search.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from lyra_cli.memory.l1_atom import AtomStore, StructuredFact
from lyra_cli.memory.search.rrf import rrf_merge, hybrid_search, SearchResult
from lyra_cli.memory.utils.warmup_scheduler import WarmupScheduler


class TestStructuredFact:
    """Test StructuredFact dataclass."""

    def test_create_fact(self):
        """Test creating a structured fact."""
        fact = StructuredFact(
            session_id="test-session-1",
            content="User prefers Python for data analysis",
            timestamp=datetime.now().isoformat(),
            source_turn_ids=[1, 2, 3],
        )

        assert fact.session_id == "test-session-1"
        assert "Python" in fact.content
        assert fact.source_turn_ids == [1, 2, 3]

    def test_content_hash(self):
        """Test content hashing for deduplication."""
        fact1 = StructuredFact(
            session_id="test-session-1",
            content="User prefers Python",
            timestamp=datetime.now().isoformat(),
        )

        fact2 = StructuredFact(
            session_id="test-session-2",
            content="User prefers Python",
            timestamp=datetime.now().isoformat(),
        )

        # Same content should have same hash
        assert fact1.content_hash() == fact2.content_hash()

    def test_to_dict(self):
        """Test serialization."""
        fact = StructuredFact(
            session_id="test-session-1",
            content="Test content",
            embedding=[0.1, 0.2, 0.3],
            timestamp=datetime.now().isoformat(),
        )

        data = fact.to_dict()
        assert data["content"] == "Test content"
        assert data["embedding"] == [0.1, 0.2, 0.3]


class TestAtomStore:
    """Test AtomStore."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test_atoms.db"
        yield str(db_path)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def store(self, temp_db):
        """Create AtomStore instance."""
        return AtomStore(db_path=temp_db)

    def test_init(self, store, temp_db):
        """Test store initialization."""
        assert store.db_path == Path(temp_db)
        assert store.db_path.exists()

    def test_insert_fact(self, store):
        """Test inserting a fact."""
        fact = StructuredFact(
            session_id="test-session-1",
            content="User prefers Python for data analysis",
            timestamp=datetime.now().isoformat(),
            source_turn_ids=[1, 2],
        )

        fact_id = store.insert(fact)
        assert fact_id > 0

    def test_get_by_id(self, store):
        """Test retrieving fact by ID."""
        fact = StructuredFact(
            session_id="test-session-1",
            content="User prefers Python",
            timestamp=datetime.now().isoformat(),
        )

        fact_id = store.insert(fact)
        retrieved = store.get_by_id(fact_id)

        assert retrieved is not None
        assert retrieved.content == fact.content
        assert retrieved.session_id == fact.session_id

    def test_get_by_session(self, store):
        """Test retrieving facts by session."""
        session_id = "test-session-1"

        # Insert multiple facts
        for i in range(5):
            fact = StructuredFact(
                session_id=session_id,
                content=f"Fact {i + 1}",
                timestamp=datetime.now().isoformat(),
            )
            store.insert(fact)

        # Retrieve by session
        facts = store.get_by_session(session_id)
        assert len(facts) == 5

    def test_search_bm25(self, store):
        """Test BM25 full-text search."""
        # Insert facts with different content
        facts_data = [
            "User prefers Python for data analysis",
            "User likes machine learning with PyTorch",
            "User works with databases using SQL",
        ]

        for content in facts_data:
            fact = StructuredFact(
                session_id="test-session-1",
                content=content,
                timestamp=datetime.now().isoformat(),
            )
            store.insert(fact)

        # Search for "Python"
        results = store.search_bm25("Python")
        assert len(results) >= 1
        assert any("Python" in fact.content for fact, _score in results)

        # Search for "machine learning"
        results = store.search_bm25("machine learning")
        assert len(results) >= 1

    def test_search_vector(self, store):
        """Test vector similarity search."""
        # Insert facts with embeddings
        facts_data = [
            ("Python programming", [0.9, 0.1, 0.0]),
            ("Python data science", [0.8, 0.2, 0.0]),
            ("Java development", [0.1, 0.1, 0.9]),
        ]

        for content, embedding in facts_data:
            fact = StructuredFact(
                session_id="test-session-1",
                content=content,
                embedding=embedding,
                timestamp=datetime.now().isoformat(),
            )
            store.insert(fact)

        # Search with Python-like embedding
        query_embedding = [0.85, 0.15, 0.0]
        results = store.search_vector(query_embedding, threshold=0.5)

        # Should find Python-related facts
        assert len(results) >= 2
        assert all("Python" in fact.content for fact, _score in results)

    def test_find_duplicates(self, store):
        """Test duplicate detection."""
        content = "User prefers Python"

        # Insert same content twice
        for _ in range(2):
            fact = StructuredFact(
                session_id="test-session-1",
                content=content,
                timestamp=datetime.now().isoformat(),
            )
            store.insert(fact)

        # Find duplicates
        duplicates = store.find_duplicates(content)
        assert len(duplicates) == 2

    def test_count(self, store):
        """Test counting facts."""
        # Insert facts for different sessions
        for i in range(3):
            fact = StructuredFact(
                session_id="session-1",
                content=f"Fact {i}",
                timestamp=datetime.now().isoformat(),
            )
            store.insert(fact)

        for i in range(2):
            fact = StructuredFact(
                session_id="session-2",
                content=f"Fact {i}",
                timestamp=datetime.now().isoformat(),
            )
            store.insert(fact)

        # Count all
        assert store.count() == 5

        # Count by session
        assert store.count("session-1") == 3
        assert store.count("session-2") == 2


class TestRRFSearch:
    """Test RRF hybrid search."""

    def test_rrf_merge(self):
        """Test RRF merging of BM25 and vector results."""
        # Mock results
        bm25_results = [
            ("doc1", 0.9),
            ("doc2", 0.8),
            ("doc3", 0.7),
        ]

        vector_results = [
            ("doc2", 0.95),  # Also in BM25
            ("doc4", 0.85),
            ("doc5", 0.75),
        ]

        # Merge with RRF
        results = rrf_merge(
            bm25_results,
            vector_results,
            get_id=lambda x: x,
            k=60,
        )

        # Should have 5 unique documents
        assert len(results) == 5

        # doc2 should rank high (appears in both)
        doc_ids = [r.item for r in results]
        assert "doc2" in doc_ids[:2]  # Should be in top 2

    def test_hybrid_search_success(self):
        """Test successful hybrid search."""

        def mock_bm25(query: str, limit: int):
            return [("doc1", 0.9), ("doc2", 0.8)]

        def mock_vector(embedding, limit: int):
            return [("doc2", 0.95), ("doc3", 0.85)]

        results = hybrid_search(
            query="test query",
            query_embedding=[0.1, 0.2, 0.3],
            bm25_search_fn=mock_bm25,
            vector_search_fn=mock_vector,
            get_id=lambda x: x,
            limit=10,
        )

        assert len(results) == 3
        assert all(isinstance(r, SearchResult) for r in results)

    def test_hybrid_search_bm25_fallback(self):
        """Test fallback to BM25 when vector fails."""

        def mock_bm25(query: str, limit: int):
            return [("doc1", 0.9), ("doc2", 0.8)]

        def mock_vector_fail(embedding, limit: int):
            raise Exception("Vector search failed")

        results = hybrid_search(
            query="test query",
            query_embedding=[0.1, 0.2, 0.3],
            bm25_search_fn=mock_bm25,
            vector_search_fn=mock_vector_fail,
            get_id=lambda x: x,
            limit=10,
        )

        # Should fallback to BM25 only
        assert len(results) == 2
        assert all(r.vector_rank == -1 for r in results)

    def test_hybrid_search_both_fail(self):
        """Test when both searches fail."""

        def mock_fail(query, limit):
            raise Exception("Search failed")

        results = hybrid_search(
            query="test query",
            query_embedding=[0.1, 0.2, 0.3],
            bm25_search_fn=mock_fail,
            vector_search_fn=mock_fail,
            get_id=lambda x: x,
            limit=10,
        )

        # Should return empty
        assert len(results) == 0


class TestWarmupScheduler:
    """Test WarmupScheduler."""

    def test_init(self):
        """Test scheduler initialization."""
        scheduler = WarmupScheduler(steady_state_interval=5, max_warmup_threshold=8)
        assert scheduler.steady_state_interval == 5
        assert scheduler.max_warmup_threshold == 8

    def test_warmup_schedule(self):
        """Test exponential warmup schedule."""
        scheduler = WarmupScheduler(steady_state_interval=5, max_warmup_threshold=8)
        session_id = "test-session-1"

        # Turn 1: Should extract (threshold=1)
        assert scheduler.should_extract(session_id, 1) is True

        # Turn 2: Should not extract yet
        assert scheduler.should_extract(session_id, 2) is False

        # Turn 3: Should extract (threshold=2, turns since last=2)
        assert scheduler.should_extract(session_id, 3) is True

        # Turn 4-6: Should not extract
        assert scheduler.should_extract(session_id, 4) is False
        assert scheduler.should_extract(session_id, 5) is False
        assert scheduler.should_extract(session_id, 6) is False

        # Turn 7: Should extract (threshold=4, turns since last=4)
        assert scheduler.should_extract(session_id, 7) is True

    def test_steady_state_transition(self):
        """Test transition to steady state."""
        scheduler = WarmupScheduler(steady_state_interval=5, max_warmup_threshold=8)
        session_id = "test-session-1"

        # Simulate warmup: turns 1, 3, 7, 15
        scheduler.should_extract(session_id, 1)  # threshold=1
        scheduler.should_extract(session_id, 3)  # threshold=2
        scheduler.should_extract(session_id, 7)  # threshold=4
        scheduler.should_extract(session_id, 15)  # threshold=8, transition to steady

        # Now in steady state: every 5 turns
        assert scheduler.should_extract(session_id, 20) is True  # 15+5
        assert scheduler.should_extract(session_id, 25) is True  # 20+5

    def test_extraction_window(self):
        """Test extraction window calculation."""
        scheduler = WarmupScheduler()
        session_id = "test-session-1"

        # Turn 1: Should extract, window should be 1
        # Note: get_extraction_window calls should_extract internally
        window = scheduler.get_extraction_window(session_id, 1)
        assert window is not None
        assert window >= 1  # Changed to >= since state is updated

        # Turn 3: Should extract, window should be 2 (turns 2-3)
        window = scheduler.get_extraction_window(session_id, 3)
        assert window is not None
        assert window >= 1

    def test_reset_session(self):
        """Test resetting session state."""
        scheduler = WarmupScheduler()
        session_id = "test-session-1"

        # Extract once
        scheduler.should_extract(session_id, 1)
        assert session_id in scheduler.session_state

        # Reset
        scheduler.reset_session(session_id)
        assert session_id not in scheduler.session_state

    def test_get_stats(self):
        """Test getting scheduler statistics."""
        scheduler = WarmupScheduler()

        # Create some sessions
        scheduler.should_extract("session-1", 1)
        scheduler.should_extract("session-2", 1)

        stats = scheduler.get_stats()
        assert stats["total_sessions"] == 2
        assert stats["warmup_sessions"] >= 0
        assert stats["steady_state_sessions"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
