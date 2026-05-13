"""
Tests for memory extraction from conversations.
"""

import tempfile
from pathlib import Path

import pytest

from lyra_memory.extractor import MemoryExtractor, extract_memories_from_conversation
from lyra_memory.schema import MemoryScope, MemoryType
from lyra_memory.store import MemoryStore


@pytest.fixture
def temp_store():
    """Create a temporary memory store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = MemoryStore(db_path, enable_embeddings=False)
        yield store
        store.close()


@pytest.fixture
def extractor(temp_store):
    """Create a memory extractor."""
    return MemoryExtractor(temp_store)


def test_extract_user_preference(extractor):
    """Test extracting user preferences."""
    memories = extractor.extract_from_turn(
        user_input="I prefer pytest over unittest",
        assistant_response="Understood, I'll use pytest.",
        turn_number=1,
    )

    assert len(memories) >= 1
    pref_memory = next((m for m in memories if m.type == MemoryType.PREFERENCE), None)
    assert pref_memory is not None
    assert pref_memory.scope == MemoryScope.USER
    assert "pytest" in pref_memory.content.lower()


def test_extract_project_fact(extractor):
    """Test extracting project facts."""
    memories = extractor.extract_from_turn(
        user_input="This project uses Python 3.10",
        assistant_response="Got it.",
        turn_number=1,
    )

    assert len(memories) >= 1
    fact_memory = next((m for m in memories if m.type == MemoryType.SEMANTIC), None)
    assert fact_memory is not None
    assert fact_memory.scope == MemoryScope.PROJECT
    assert "Python 3.10" in fact_memory.content


def test_extract_correction(extractor):
    """Test extracting corrections."""
    memories = extractor.extract_from_turn(
        user_input="Actually, we use Python 3.11, not 3.10",
        assistant_response="Thanks for the correction.",
        turn_number=2,
    )

    assert len(memories) >= 1
    correction = next((m for m in memories if m.metadata.get("is_correction")), None)
    assert correction is not None
    assert correction.confidence >= 0.9  # High confidence for corrections


def test_extract_tool_failure(extractor):
    """Test extracting tool failures."""
    tool_results = [
        {
            "tool": "read_file",
            "success": False,
            "error": "File not found: test.py",
        }
    ]

    memories = extractor.extract_from_turn(
        user_input="Read test.py",
        assistant_response="I'll read that file.",
        tool_results=tool_results,
        turn_number=1,
    )

    failure_memory = next((m for m in memories if m.type == MemoryType.FAILURE), None)
    assert failure_memory is not None
    assert "read_file" in failure_memory.content
    assert "File not found" in failure_memory.content


def test_extract_file_operation(extractor):
    """Test extracting file operations."""
    tool_results = [
        {
            "tool": "write_file",
            "success": True,
            "file_path": "/path/to/file.py",
        }
    ]

    memories = extractor.extract_from_turn(
        user_input="Write to file.py",
        assistant_response="Writing file.",
        tool_results=tool_results,
        turn_number=1,
    )

    file_memory = next((m for m in memories if m.type == MemoryType.EPISODIC), None)
    assert file_memory is not None
    assert "file.py" in file_memory.content


def test_deduplication(extractor):
    """Test that duplicate memories are removed."""
    # Extract twice with same input
    memories1 = extractor.extract_from_turn(
        user_input="I prefer pytest",
        assistant_response="OK",
        turn_number=1,
    )

    memories2 = extractor.extract_from_turn(
        user_input="I prefer pytest",
        assistant_response="OK",
        turn_number=2,
    )

    # Should have same number of memories (deduplicated)
    assert len(memories1) == len(memories2)


def test_contradiction_detection_version_change(temp_store):
    """Test detecting version contradictions."""
    extractor = MemoryExtractor(temp_store)

    # First memory: Python 3.9
    memories1 = extractor.extract_from_turn(
        user_input="This project uses Python 3.9",
        assistant_response="Noted.",
        turn_number=1,
    )
    assert len(memories1) >= 1

    # Second memory: Python 3.10 (contradiction)
    memories2 = extractor.extract_from_turn(
        user_input="Actually, this project uses Python 3.10",
        assistant_response="Updated.",
        turn_number=2,
    )
    assert len(memories2) >= 1

    # Old memory should be superseded
    old_memory = temp_store.get(memories1[0].id)
    assert old_memory.is_superseded()


def test_contradiction_detection_preference_change(temp_store):
    """Test detecting preference contradictions."""
    extractor = MemoryExtractor(temp_store)

    # First preference
    memories1 = extractor.extract_from_turn(
        user_input="I prefer unittest",
        assistant_response="OK",
        turn_number=1,
    )

    # Changed preference
    memories2 = extractor.extract_from_turn(
        user_input="Actually, I prefer pytest",
        assistant_response="Updated.",
        turn_number=2,
    )

    # Old memory should be superseded
    old_memory = temp_store.get(memories1[0].id)
    assert old_memory.is_superseded()


def test_extract_from_conversation_history(temp_store):
    """Test extracting from full conversation history."""
    conversation = [
        ("I prefer pytest", "Understood."),
        ("This project uses Python 3.10", "Noted."),
        ("Read config.py", "Reading file."),
    ]

    memories = extract_memories_from_conversation(temp_store, conversation)

    assert len(memories) >= 2  # At least preference + project fact
    assert any(m.type == MemoryType.PREFERENCE for m in memories)
    assert any(m.type == MemoryType.SEMANTIC for m in memories)


def test_source_span_tracking(extractor):
    """Test that source spans are tracked correctly."""
    memories = extractor.extract_from_turn(
        user_input="I prefer pytest",
        assistant_response="OK",
        turn_number=42,
    )

    assert len(memories) >= 1
    assert memories[0].source_span == "turn 42"


def test_confidence_scores(extractor):
    """Test that confidence scores are appropriate."""
    # Correction should have high confidence
    correction_memories = extractor.extract_from_turn(
        user_input="Actually, that's wrong",
        assistant_response="Thanks.",
        turn_number=1,
    )
    correction = next((m for m in correction_memories if m.metadata.get("is_correction")), None)
    if correction:
        assert correction.confidence >= 0.9

    # Inferred fact should have lower confidence
    inferred_memories = extractor.extract_from_turn(
        user_input="What version?",
        assistant_response="I found that it uses Python 3.10",
        turn_number=1,
    )
    inferred = next((m for m in inferred_memories if "found" in m.content.lower()), None)
    if inferred:
        assert inferred.confidence <= 0.7


def test_no_extraction_from_generic_input(extractor):
    """Test that generic input doesn't create memories."""
    memories = extractor.extract_from_turn(
        user_input="Hello",
        assistant_response="Hi there!",
        turn_number=1,
    )

    # Should not extract memories from generic greetings
    assert len(memories) == 0


def test_metadata_preservation(extractor):
    """Test that metadata is preserved in extracted memories."""
    tool_results = [
        {
            "tool": "read_file",
            "success": False,
            "error": "Permission denied",
        }
    ]

    memories = extractor.extract_from_turn(
        user_input="Read file",
        assistant_response="Trying.",
        tool_results=tool_results,
        turn_number=1,
    )

    failure = next((m for m in memories if m.type == MemoryType.FAILURE), None)
    assert failure is not None
    assert failure.metadata["tool"] == "read_file"
    assert failure.metadata["error"] == "Permission denied"
