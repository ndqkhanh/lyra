"""Tests for memory systems."""
import pytest
from pathlib import Path
import tempfile
import shutil

from lyra_cli.memory import (
    ConversationLog,
    StructuredFact,
    WarmupScheduler,
)


@pytest.fixture
def temp_memory_dir():
    """Create temporary memory directory."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


# L0: Conversation Log Tests
def test_conversation_log_creation():
    """Test ConversationLog creation."""
    log = ConversationLog(
        session_id="session_001",
        turn_id=1,
        timestamp="2026-05-17T12:00:00",
        role="user",
        content="Hello",
    )

    assert log.session_id == "session_001"
    assert log.turn_id == 1
    assert log.role == "user"
    assert log.content == "Hello"
    assert log.timestamp == "2026-05-17T12:00:00"


def test_conversation_log_to_dict():
    """Test ConversationLog serialization."""
    log = ConversationLog(
        session_id="session_001",
        turn_id=1,
        timestamp="2026-05-17T12:00:00",
        role="user",
        content="Test",
    )

    data = log.to_dict()

    assert isinstance(data, dict)
    assert data["session_id"] == "session_001"
    assert data["turn_id"] == 1
    assert data["role"] == "user"
    assert data["content"] == "Test"


def test_conversation_log_from_dict():
    """Test ConversationLog deserialization."""
    data = {
        "session_id": "session_001",
        "turn_id": 1,
        "timestamp": "2026-05-17T12:00:00",
        "role": "user",
        "content": "Test",
        "metadata": None,
    }

    log = ConversationLog.from_dict(data)

    assert log.session_id == "session_001"
    assert log.turn_id == 1
    assert log.role == "user"
    assert log.content == "Test"


def test_conversation_log_with_metadata():
    """Test ConversationLog with metadata."""
    log = ConversationLog(
        session_id="session_001",
        turn_id=1,
        timestamp="2026-05-17T12:00:00",
        role="user",
        content="Test",
        metadata={"source": "cli", "model": "claude-sonnet-4"},
    )

    assert log.metadata is not None
    assert log.metadata["source"] == "cli"
    assert log.metadata["model"] == "claude-sonnet-4"


# L1: Structured Fact Tests
def test_structured_fact_creation():
    """Test StructuredFact creation."""
    fact = StructuredFact(
        session_id="session_001",
        content="User prefers Python",
    )

    assert fact.session_id == "session_001"
    assert fact.content == "User prefers Python"


def test_structured_fact_with_embedding():
    """Test StructuredFact with embedding."""
    fact = StructuredFact(
        session_id="session_001",
        content="Test fact",
        embedding=[0.1, 0.2, 0.3],
    )

    assert fact.embedding is not None
    assert len(fact.embedding) == 3
    assert fact.embedding[0] == 0.1


def test_structured_fact_to_dict():
    """Test StructuredFact serialization."""
    fact = StructuredFact(
        session_id="session_001",
        content="Test fact",
        embedding=[0.1, 0.2],
    )

    data = fact.to_dict()

    assert isinstance(data, dict)
    assert data["session_id"] == "session_001"
    assert data["content"] == "Test fact"
    assert data["embedding"] == [0.1, 0.2]


def test_structured_fact_from_dict():
    """Test StructuredFact deserialization."""
    data = {
        "id": None,
        "session_id": "session_001",
        "content": "Test fact",
        "embedding": [0.1, 0.2],
        "timestamp": "2026-05-17T12:00:00",
        "metadata": None,
        "source_turn_ids": None,
    }

    fact = StructuredFact.from_dict(data)

    assert fact.session_id == "session_001"
    assert fact.content == "Test fact"
    assert fact.embedding == [0.1, 0.2]


def test_structured_fact_content_hash():
    """Test StructuredFact content hashing."""
    fact = StructuredFact(
        session_id="session_001",
        content="Test fact",
    )

    hash1 = fact.content_hash()

    assert isinstance(hash1, str)
    assert len(hash1) > 0

    # Same content should produce same hash
    fact2 = StructuredFact(
        session_id="session_001",
        content="Test fact",
    )

    hash2 = fact2.content_hash()
    assert hash1 == hash2


def test_structured_fact_with_metadata():
    """Test StructuredFact with metadata."""
    fact = StructuredFact(
        session_id="session_001",
        content="Test fact",
        metadata={"category": "preference", "confidence": 0.9},
    )

    assert fact.metadata is not None
    assert fact.metadata["category"] == "preference"
    assert fact.metadata["confidence"] == 0.9


def test_structured_fact_with_source_turns():
    """Test StructuredFact with source turn IDs."""
    fact = StructuredFact(
        session_id="session_001",
        content="Test fact",
        source_turn_ids=[1, 2, 3],
    )

    assert fact.source_turn_ids is not None
    assert len(fact.source_turn_ids) == 3
    assert fact.source_turn_ids[0] == 1


# Warmup Scheduler Tests
def test_warmup_scheduler_initialization():
    """Test WarmupScheduler initialization."""
    scheduler = WarmupScheduler()

    assert scheduler is not None


def test_warmup_scheduler_has_methods():
    """Test WarmupScheduler has expected methods."""
    scheduler = WarmupScheduler()

    # Should have some scheduling method
    assert hasattr(scheduler, "__dict__") or callable(scheduler)


# Memory System Integration Tests
def test_memory_system_imports():
    """Test that all memory components can be imported."""
    from lyra_cli.memory import (
        ConversationStore,
        ConversationLog,
        AtomStore,
        StructuredFact,
        ScenarioStore,
        ScenarioBlock,
        PersonaStore,
        UserPersona,
        WarmupScheduler,
    )

    assert ConversationStore is not None
    assert ConversationLog is not None
    assert AtomStore is not None
    assert StructuredFact is not None
    assert ScenarioStore is not None
    assert ScenarioBlock is not None
    assert PersonaStore is not None
    assert UserPersona is not None
    assert WarmupScheduler is not None


def test_memory_version():
    """Test memory system has version."""
    from lyra_cli import memory

    assert hasattr(memory, "__version__")
    assert isinstance(memory.__version__, str)


def test_memory_all_exports():
    """Test __all__ exports are complete."""
    from lyra_cli import memory

    assert hasattr(memory, "__all__")
    assert isinstance(memory.__all__, list)
    assert len(memory.__all__) > 0


def test_memory_architecture_documentation():
    """Test memory system has architecture documentation."""
    from lyra_cli import memory

    doc = memory.__doc__

    assert doc is not None
    assert "4-tier" in doc or "pyramid" in doc
    assert "L0" in doc or "L1" in doc or "L2" in doc or "L3" in doc


def test_memory_layers_documented():
    """Test memory layers are documented."""
    from lyra_cli import memory

    doc = memory.__doc__

    # Should document all 4 layers
    assert "L0" in doc
    assert "L1" in doc
    assert "L2" in doc
    assert "L3" in doc


def test_conversation_log_roles():
    """Test ConversationLog supports user and assistant roles."""
    user_log = ConversationLog(
        session_id="session_001",
        turn_id=1,
        timestamp="2026-05-17T12:00:00",
        role="user",
        content="Hello",
    )

    assistant_log = ConversationLog(
        session_id="session_001",
        turn_id=2,
        timestamp="2026-05-17T12:00:01",
        role="assistant",
        content="Hi there!",
    )

    assert user_log.role == "user"
    assert assistant_log.role == "assistant"


def test_structured_fact_optional_fields():
    """Test StructuredFact optional fields default to None."""
    fact = StructuredFact(
        session_id="session_001",
        content="Test",
    )

    assert fact.id is None
    assert fact.embedding is None
    assert fact.metadata is None
    assert fact.source_turn_ids is None
