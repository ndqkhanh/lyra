"""
Test Suite for MEMTIER Memory System

Tests all components of the 3-tier memory architecture:
- Episodic memory (JSONL storage)
- Semantic consolidation (LLM fact extraction)
- Cognitive weight attribution
- Two-stage retrieval
- Memory integration
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import json

from lyra_core.memory.episodic import EpisodicMemory, EpisodicEntry
from lyra_core.memory.semantic_consolidator import SemanticConsolidator, SemanticFact
from lyra_core.memory.cognitive_weight import CognitiveWeightAttributor
from lyra_core.memory.two_stage_retrieval import TwoStageRetriever


class TestEpisodicMemory:
    """Test episodic memory tier."""

    @pytest.fixture
    def temp_memory_dir(self):
        """Create temporary memory directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def episodic(self, temp_memory_dir):
        """Create episodic memory instance."""
        return EpisodicMemory(temp_memory_dir)

    def test_append_event(self, episodic):
        """Test appending events to episodic memory."""
        entry = episodic.append_event(
            session_id="test_session",
            project="test_project",
            event_type="user_input",
            content="How do I implement authentication?",
            tokens=10
        )

        assert entry.id.startswith("ep_")
        assert entry.session_id == "test_session"
        assert entry.event_type == "user_input"

    def test_read_session(self, episodic):
        """Test reading entries by session."""
        # Add multiple entries
        episodic.append_event("sess1", "proj1", "user_input", "Query 1", 10)
        episodic.append_event("sess1", "proj1", "tool_call", "Result 1", 20)
        episodic.append_event("sess2", "proj1", "user_input", "Query 2", 10)

        # Read session 1
        entries = episodic.read_session("sess1")
        assert len(entries) == 2
        assert all(e.session_id == "sess1" for e in entries)

    def test_read_day(self, episodic):
        """Test reading entries by day."""
        today = datetime.now()

        episodic.append_event("sess1", "proj1", "user_input", "Query 1", 10)
        episodic.append_event("sess1", "proj1", "user_input", "Query 2", 10)

        entries = episodic.read_day(today)
        assert len(entries) == 2

    def test_mark_promoted(self, episodic):
        """Test marking entries as promoted."""
        entry = episodic.append_event("sess1", "proj1", "user_input", "Query", 10)

        success = episodic.mark_promoted(entry.id)
        assert success

        # Verify promotion
        entries = episodic.read_session("sess1")
        assert entries[0].promoted

    def test_get_stats(self, episodic):
        """Test getting episodic memory statistics."""
        episodic.append_event("sess1", "proj1", "user_input", "Query 1", 10)
        episodic.append_event("sess1", "proj1", "tool_call", "Result 1", 20)

        stats = episodic.get_stats()
        assert stats['total_entries'] == 2
        assert stats['total_tokens'] == 30
        assert stats['event_types']['user_input'] == 1
        assert stats['event_types']['tool_call'] == 1


class TestSemanticConsolidator:
    """Test semantic consolidation."""

    @pytest.fixture
    def temp_memory_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def episodic(self, temp_memory_dir):
        return EpisodicMemory(temp_memory_dir / "episodic")

    @pytest.fixture
    def consolidator(self, episodic, temp_memory_dir):
        return SemanticConsolidator(
            episodic,
            semantic_store_path=temp_memory_dir / "semantic.json"
        )

    def test_cluster_entries(self, consolidator, episodic):
        """Test clustering episodic entries."""
        # Add entries to same session
        now = datetime.now()
        entries = []
        for i in range(5):
            entry = EpisodicEntry(
                id=f"ep_{i}",
                timestamp=now + timedelta(minutes=i * 10),
                session_id="sess1",
                project="proj1",
                event_type="user_input",
                content=f"Query {i}",
                tokens=10,
                metadata={}
            )
            entries.append(entry)

        clusters = consolidator._cluster_entries(entries)
        assert len(clusters) == 1  # All in same 1-hour window
        assert len(clusters[0]) == 5

    def test_jaccard_similarity(self, consolidator):
        """Test Jaccard similarity calculation."""
        fact1 = "User prefers TypeScript over JavaScript"
        fact2 = "User prefers TypeScript for development"

        similarity = consolidator._jaccard_similarity(fact1, fact2)
        assert 0.0 < similarity < 1.0

    def test_is_duplicate(self, consolidator):
        """Test duplicate detection."""
        # Add a fact
        consolidator.facts.append(SemanticFact(
            id="sem_1",
            fact="User prefers TypeScript",
            source_sessions=["sess1"],
            source_entry_ids=["ep_1"],
            extracted_at=datetime.now(),
            cognitive_weight=0.0,
            tags=["preference"],
            confidence=0.9
        ))

        # Check duplicate
        assert consolidator._is_duplicate("User prefers TypeScript", threshold=0.7)
        assert not consolidator._is_duplicate("User prefers Python", threshold=0.7)

    def test_search_facts(self, consolidator):
        """Test searching semantic facts."""
        # Add facts
        consolidator.facts.extend([
            SemanticFact(
                id="sem_1",
                fact="User prefers TypeScript for web development",
                source_sessions=["sess1"],
                source_entry_ids=["ep_1"],
                extracted_at=datetime.now(),
                cognitive_weight=0.0,
                tags=["preference", "language"],
                confidence=0.9
            ),
            SemanticFact(
                id="sem_2",
                fact="Project uses React for frontend",
                source_sessions=["sess1"],
                source_entry_ids=["ep_2"],
                extracted_at=datetime.now(),
                cognitive_weight=0.0,
                tags=["tech_stack"],
                confidence=0.8
            )
        ])

        results = consolidator.search_facts("TypeScript development", k=5)
        assert len(results) > 0
        assert results[0]['id'] == "sem_1"


class TestCognitiveWeight:
    """Test cognitive weight attribution."""

    @pytest.fixture
    def temp_db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        # Create test database
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE memory (
                id TEXT PRIMARY KEY,
                content TEXT,
                cognitive_weight REAL DEFAULT 0.0,
                retrieval_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE tool_calls (
                turn_id INTEGER,
                session_id TEXT,
                tool_name TEXT,
                success BOOLEAN,
                retrieved_entry_ids TEXT
            )
        """)
        conn.commit()
        conn.close()

        yield db_path

        # Cleanup
        Path(db_path).unlink()

    def test_get_weighted_score(self, temp_db):
        """Test applying cognitive weight to scores."""
        import sqlite3

        # Add test entry
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO memory (id, content, cognitive_weight)
            VALUES ('mem_1', 'Test content', 0.5)
        """)
        conn.commit()
        conn.close()

        attributor = CognitiveWeightAttributor(temp_db)
        weighted_score = attributor.get_weighted_score('mem_1', 0.8)

        # Score should be boosted by positive weight
        assert weighted_score > 0.8

    def test_get_entry_stats(self, temp_db):
        """Test getting entry statistics."""
        import sqlite3

        # Add test entry with stats
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO memory (id, content, cognitive_weight, retrieval_count, success_count, failure_count)
            VALUES ('mem_1', 'Test', 0.3, 10, 7, 3)
        """)
        conn.commit()
        conn.close()

        attributor = CognitiveWeightAttributor(temp_db)
        stats = attributor.get_entry_stats('mem_1')

        assert stats['cognitive_weight'] == 0.3
        assert stats['retrieval_count'] == 10
        assert stats['success_rate'] == 0.7


class TestTwoStageRetrieval:
    """Test two-stage retrieval."""

    @pytest.fixture
    def temp_memory_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def memory_components(self, temp_memory_dir):
        episodic = EpisodicMemory(temp_memory_dir / "episodic")
        consolidator = SemanticConsolidator(
            episodic,
            semantic_store_path=temp_memory_dir / "semantic.json"
        )

        # Create temp procedural DB
        import sqlite3
        db_path = str(temp_memory_dir / "procedural.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE VIRTUAL TABLE memory USING fts5(id, content)
        """)
        conn.commit()
        conn.close()

        return episodic, consolidator, db_path

    def test_retrieve(self, memory_components):
        """Test two-stage retrieval."""
        episodic, consolidator, db_path = memory_components

        # Add semantic facts
        consolidator.facts.append(SemanticFact(
            id="sem_1",
            fact="User prefers TypeScript",
            source_sessions=["sess1"],
            source_entry_ids=["ep_1"],
            extracted_at=datetime.now(),
            cognitive_weight=0.0,
            tags=["preference"],
            confidence=0.9
        ))

        # Add episodic entries
        episodic.append_event("sess1", "proj1", "user_input", "TypeScript is great", 10)

        retriever = TwoStageRetriever(consolidator, episodic, db_path)
        results = retriever.retrieve("TypeScript", k=10)

        assert len(results) > 0
        assert any(r.source == "semantic" for r in results)


# Integration tests
class TestMemoryIntegration:
    """Test full memory system integration."""

    def test_end_to_end_flow(self):
        """Test complete flow: log → consolidate → retrieve."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from lyra_core.memory import MemTierMemorySystem

            memory = MemTierMemorySystem(
                memory_dir=Path(tmpdir),
                auto_consolidate=False
            )

            # Log events
            memory.log_event("sess1", "proj1", "user_input", "How do I use TypeScript?", 10)
            memory.log_event("sess1", "proj1", "agent_response", "TypeScript is a typed superset of JavaScript", 20)

            # Search
            results = memory.search("TypeScript", k=5)
            assert len(results) > 0

            # Get stats
            stats = memory.get_stats()
            assert stats['episodic']['total_entries'] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
