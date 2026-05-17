"""Tests for memory system."""

import pytest
from pathlib import Path
from datetime import datetime
from lyra_cli.core.memory_metadata import MemoryMetadata, MemoryType
from lyra_cli.core.memory_storage import MemoryStorage
from lyra_cli.core.memory_manager import MemoryManager


def test_memory_metadata_creation():
    """Test creating MemoryMetadata."""
    memory = MemoryMetadata(
        id="test-id",
        content="Test content",
        memory_type=MemoryType.CONVERSATION,
        timestamp=datetime.now(),
        tags=["test"]
    )
    assert memory.id == "test-id"
    assert memory.content == "Test content"
    assert memory.memory_type == MemoryType.CONVERSATION


def test_memory_storage_save_load(tmp_path):
    """Test saving and loading memories."""
    storage = MemoryStorage(tmp_path)
    memory = MemoryMetadata(
        id="test-id",
        content="Test content",
        memory_type=MemoryType.PROJECT,
        timestamp=datetime.now(),
        tags=["test"]
    )

    storage.save(memory)
    loaded = storage.load("test-id")

    assert loaded is not None
    assert loaded.id == "test-id"
    assert loaded.content == "Test content"


def test_memory_manager_add(tmp_path):
    """Test adding memories."""
    storage = MemoryStorage(tmp_path)
    manager = MemoryManager(storage)

    memory = manager.add("Test content", MemoryType.PREFERENCE, ["test"])

    assert memory.content == "Test content"
    assert memory.memory_type == MemoryType.PREFERENCE


def test_memory_manager_search(tmp_path):
    """Test searching memories."""
    storage = MemoryStorage(tmp_path)
    manager = MemoryManager(storage)

    manager.add("Python code", MemoryType.CONVERSATION, ["python"])
    manager.add("JavaScript code", MemoryType.CONVERSATION, ["javascript"])

    results = manager.search("python")
    assert len(results) == 1
    assert "Python" in results[0].content
