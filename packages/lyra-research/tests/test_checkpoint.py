"""
Tests for checkpoint system.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from lyra_research.checkpoint import ResearchCheckpoint, ResearchState


def test_research_state_to_dict():
    """Test ResearchState serialization."""
    state = ResearchState(
        session_id="test-123",
        topic="Test Topic",
        depth="standard",
        current_step=3,
        current_step_name="Analyzing",
        started_at=datetime.now(timezone.utc),
        last_checkpoint_at=datetime.now(timezone.utc),
        sources_found={"arxiv": 10, "github": 5},
        papers_analyzed=8,
    )

    data = state.to_dict()

    assert data["session_id"] == "test-123"
    assert data["topic"] == "Test Topic"
    assert isinstance(data["started_at"], str)
    assert data["papers_analyzed"] == 8


def test_research_state_from_dict():
    """Test ResearchState deserialization."""
    now = datetime.now(timezone.utc)
    data = {
        "session_id": "test-123",
        "topic": "Test Topic",
        "depth": "standard",
        "current_step": 3,
        "current_step_name": "Analyzing",
        "started_at": now.isoformat(),
        "last_checkpoint_at": now.isoformat(),
        "sources_found": {"arxiv": 10},
        "papers_analyzed": 8,
        "repos_analyzed": 0,
        "gaps_found": 0,
        "raw_results": {},
        "ranked_sources": [],
        "paper_analyses": [],
        "repo_analyses": [],
        "synthesis_result": None,
        "report_data": None,
        "completed": False,
        "error": None,
    }

    state = ResearchState.from_dict(data)

    assert state.session_id == "test-123"
    assert state.topic == "Test Topic"
    assert isinstance(state.started_at, datetime)
    assert state.papers_analyzed == 8


def test_checkpoint_save_and_load(tmp_path):
    """Test saving and loading checkpoints."""
    checkpoint = ResearchCheckpoint(checkpoint_dir=tmp_path)

    state = ResearchState(
        session_id="test-123",
        topic="Test Topic",
        depth="standard",
        current_step=3,
        current_step_name="Analyzing",
        started_at=datetime.now(timezone.utc),
        last_checkpoint_at=datetime.now(timezone.utc),
        papers_analyzed=8,
    )

    # Save checkpoint
    checkpoint.save_checkpoint("test-123", state)

    # Load checkpoint
    loaded_state = checkpoint.load_checkpoint("test-123")

    assert loaded_state is not None
    assert loaded_state.session_id == "test-123"
    assert loaded_state.topic == "Test Topic"
    assert loaded_state.papers_analyzed == 8


def test_checkpoint_load_nonexistent(tmp_path):
    """Test loading nonexistent checkpoint."""
    checkpoint = ResearchCheckpoint(checkpoint_dir=tmp_path)

    loaded_state = checkpoint.load_checkpoint("nonexistent")

    assert loaded_state is None


def test_checkpoint_resume_incomplete(tmp_path):
    """Test resuming incomplete research."""
    checkpoint = ResearchCheckpoint(checkpoint_dir=tmp_path)

    state = ResearchState(
        session_id="test-123",
        topic="Test Topic",
        depth="standard",
        current_step=3,
        current_step_name="Analyzing",
        started_at=datetime.now(timezone.utc),
        last_checkpoint_at=datetime.now(timezone.utc),
        completed=False,
    )

    checkpoint.save_checkpoint("test-123", state)

    # Resume
    resumed_state = checkpoint.resume_research("test-123")

    assert resumed_state is not None
    assert resumed_state.session_id == "test-123"
    assert resumed_state.completed is False


def test_checkpoint_resume_completed(tmp_path):
    """Test resuming completed research returns None."""
    checkpoint = ResearchCheckpoint(checkpoint_dir=tmp_path)

    state = ResearchState(
        session_id="test-123",
        topic="Test Topic",
        depth="standard",
        current_step=10,
        current_step_name="Complete",
        started_at=datetime.now(timezone.utc),
        last_checkpoint_at=datetime.now(timezone.utc),
        completed=True,
    )

    checkpoint.save_checkpoint("test-123", state)

    # Resume should return None for completed
    resumed_state = checkpoint.resume_research("test-123")

    assert resumed_state is None


def test_checkpoint_list_checkpoints(tmp_path):
    """Test listing all checkpoints."""
    checkpoint = ResearchCheckpoint(checkpoint_dir=tmp_path)

    # Create multiple checkpoints
    for i in range(3):
        state = ResearchState(
            session_id=f"test-{i}",
            topic=f"Topic {i}",
            depth="standard",
            current_step=1,
            current_step_name="Starting",
            started_at=datetime.now(timezone.utc),
            last_checkpoint_at=datetime.now(timezone.utc),
        )
        checkpoint.save_checkpoint(f"test-{i}", state)

    # List checkpoints
    session_ids = checkpoint.list_checkpoints()

    assert len(session_ids) == 3
    assert "test-0" in session_ids
    assert "test-1" in session_ids
    assert "test-2" in session_ids


def test_checkpoint_delete(tmp_path):
    """Test deleting checkpoint."""
    checkpoint = ResearchCheckpoint(checkpoint_dir=tmp_path)

    state = ResearchState(
        session_id="test-123",
        topic="Test Topic",
        depth="standard",
        current_step=1,
        current_step_name="Starting",
        started_at=datetime.now(timezone.utc),
        last_checkpoint_at=datetime.now(timezone.utc),
    )

    checkpoint.save_checkpoint("test-123", state)

    # Delete
    deleted = checkpoint.delete_checkpoint("test-123")

    assert deleted is True
    assert checkpoint.load_checkpoint("test-123") is None


def test_checkpoint_delete_nonexistent(tmp_path):
    """Test deleting nonexistent checkpoint."""
    checkpoint = ResearchCheckpoint(checkpoint_dir=tmp_path)

    deleted = checkpoint.delete_checkpoint("nonexistent")

    assert deleted is False


def test_checkpoint_auto_checkpoint(tmp_path):
    """Test auto-checkpointing."""
    checkpoint = ResearchCheckpoint(checkpoint_dir=tmp_path)

    state = ResearchState(
        session_id="test-123",
        topic="Test Topic",
        depth="standard",
        current_step=1,
        current_step_name="Starting",
        started_at=datetime.now(timezone.utc),
        last_checkpoint_at=datetime.now(timezone.utc),
    )

    # State getter that returns current state
    def get_state():
        return state

    # Start auto-checkpoint with 1 second interval
    checkpoint.auto_checkpoint("test-123", get_state, interval_seconds=1)

    # Wait for checkpoint
    time.sleep(1.5)

    # Stop auto-checkpoint
    checkpoint.stop_auto_checkpoint()

    # Verify checkpoint was saved
    loaded_state = checkpoint.load_checkpoint("test-123")
    assert loaded_state is not None


def test_checkpoint_auto_checkpoint_updates(tmp_path):
    """Test auto-checkpoint captures state updates."""
    checkpoint = ResearchCheckpoint(checkpoint_dir=tmp_path)

    state = ResearchState(
        session_id="test-123",
        topic="Test Topic",
        depth="standard",
        current_step=1,
        current_step_name="Starting",
        started_at=datetime.now(timezone.utc),
        last_checkpoint_at=datetime.now(timezone.utc),
        papers_analyzed=0,
    )

    def get_state():
        return state

    # Start auto-checkpoint
    checkpoint.auto_checkpoint("test-123", get_state, interval_seconds=1)

    # Update state
    state.papers_analyzed = 5
    state.current_step = 3

    # Wait for checkpoint
    time.sleep(1.5)

    # Stop auto-checkpoint
    checkpoint.stop_auto_checkpoint()

    # Verify updated state was saved
    loaded_state = checkpoint.load_checkpoint("test-123")
    assert loaded_state.papers_analyzed == 5
    assert loaded_state.current_step == 3


def test_checkpoint_auto_checkpoint_stops_on_completion(tmp_path):
    """Test auto-checkpoint stops when research completes."""
    checkpoint = ResearchCheckpoint(checkpoint_dir=tmp_path)

    state = ResearchState(
        session_id="test-123",
        topic="Test Topic",
        depth="standard",
        current_step=1,
        current_step_name="Starting",
        started_at=datetime.now(timezone.utc),
        last_checkpoint_at=datetime.now(timezone.utc),
        completed=False,
    )

    def get_state():
        return state

    # Start auto-checkpoint
    checkpoint.auto_checkpoint("test-123", get_state, interval_seconds=1)

    # Wait for first checkpoint
    time.sleep(1.5)

    # Mark as completed
    state.completed = True

    # Wait for another checkpoint attempt
    time.sleep(1.5)

    # Stop auto-checkpoint
    checkpoint.stop_auto_checkpoint()

    # Verify checkpoint exists but resume returns None (because completed=True)
    loaded = checkpoint.load_checkpoint("test-123")
    assert loaded is not None
    assert loaded.completed is True
    assert checkpoint.resume_research("test-123") is None
