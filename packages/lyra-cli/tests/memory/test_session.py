"""Tests for session system."""

import pytest
from datetime import datetime
from lyra_cli.core.session_state import SessionState
from lyra_cli.core.session_storage import SessionStorage
from lyra_cli.core.session_manager import SessionManager


def test_session_state_creation():
    """Test creating SessionState."""
    session = SessionState(
        session_id="test-id",
        created_at=datetime.now(),
        last_updated=datetime.now(),
        conversation_history=[],
        context={}
    )
    assert session.session_id == "test-id"
    assert len(session.conversation_history) == 0


def test_session_storage_save_load(tmp_path):
    """Test saving and loading sessions."""
    storage = SessionStorage(tmp_path)
    session = SessionState(
        session_id="test-id",
        created_at=datetime.now(),
        last_updated=datetime.now(),
        conversation_history=["msg1", "msg2"],
        context={"key": "value"}
    )

    storage.save(session)
    loaded = storage.load("test-id")

    assert loaded is not None
    assert loaded.session_id == "test-id"
    assert len(loaded.conversation_history) == 2


def test_session_manager_create(tmp_path):
    """Test creating sessions."""
    storage = SessionStorage(tmp_path)
    manager = SessionManager(storage)

    session = manager.create()

    assert session.session_id is not None
    assert len(session.conversation_history) == 0


def test_session_manager_save_load(tmp_path):
    """Test saving and loading sessions."""
    storage = SessionStorage(tmp_path)
    manager = SessionManager(storage)

    session = manager.create()
    session.conversation_history.append("test message")
    manager.save(session)

    loaded = manager.load(session.session_id)
    assert loaded is not None
    assert len(loaded.conversation_history) == 1
