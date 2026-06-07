"""
Tests for the session persistence module.
"""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path

from src.sessions.persist import SessionManager, SessionRecord, SessionStatus


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    """Provide a temporary database path."""
    return str(tmp_path / "test_sessions.db")


@pytest.fixture
def manager(db_path: str) -> SessionManager:
    """Provide a fresh SessionManager for each test."""
    mgr = SessionManager(db_path)
    yield mgr
    mgr.close()


class TestSessionRecord:
    """Tests for the SessionRecord dataclass."""

    def test_to_dict_round_trip(self):
        """to_dict and from_dict should round-trip cleanly."""
        record = SessionRecord(
            session_id="sess-001",
            status=SessionStatus.ACTIVE,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
            agent_id="agent-alpha",
            metadata={"user": "test-user"},
            steps=[{"action": "run", "index": 0}],
            context={"memory": {"key": "value"}},
        )
        d = record.to_dict()
        restored = SessionRecord.from_dict(d)
        assert restored.session_id == "sess-001"
        assert restored.status == SessionStatus.ACTIVE
        assert restored.agent_id == "agent-alpha"
        assert restored.metadata["user"] == "test-user"
        assert len(restored.steps) == 1
        assert restored.context["memory"]["key"] == "value"

    def test_default_status_is_active(self):
        """A freshly built record should default to ACTIVE."""
        now = datetime.now(timezone.utc)
        record = SessionRecord(
            session_id="sess-default",
            created_at=now,
            updated_at=now,
        )
        assert record.status == SessionStatus.ACTIVE


class TestSessionManager:
    """Tests for SessionManager CRUD and step management."""

    def test_create_and_get_session(self, manager: SessionManager):
        """Creating a session and retrieving it should return matching data."""
        record = manager.create_session(
            session_id="sess-001",
            agent_id="agent-alpha",
            metadata={"env": "test"},
        )
        assert record.session_id == "sess-001"
        assert record.agent_id == "agent-alpha"
        assert record.status == SessionStatus.ACTIVE

        fetched = manager.get_session("sess-001")
        assert fetched is not None
        assert fetched.session_id == "sess-001"
        assert fetched.agent_id == "agent-alpha"

    def test_get_nonexistent_session_returns_none(self, manager: SessionManager):
        """Getting a session that does not exist should return None."""
        fetched = manager.get_session("nonexistent")
        assert fetched is None

    def test_update_session_status(self, manager: SessionManager):
        """Updating a session's status should persist."""
        manager.create_session("sess-002")
        updated = manager.update_session(
            "sess-002",
            status=SessionStatus.COMPLETED,
        )
        assert updated is not None
        assert updated.status == SessionStatus.COMPLETED

        fetched = manager.get_session("sess-002")
        assert fetched is not None
        assert fetched.status == SessionStatus.COMPLETED

    def test_update_session_metadata(self, manager: SessionManager):
        """Updating metadata should merge with existing."""
        manager.create_session(
            "sess-003",
            metadata={"initial": True},
        )
        updated = manager.update_session(
            "sess-003",
            metadata={"extra": "value"},
        )
        assert updated is not None
        assert updated.metadata["initial"] is True
        assert updated.metadata["extra"] == "value"

    def test_update_nonexistent_returns_none(self, manager: SessionManager):
        """Updating a session that does not exist should return None."""
        result = manager.update_session("ghost", status=SessionStatus.FAILED)
        assert result is None

    def test_delete_session(self, manager: SessionManager):
        """Deleting a session should remove it and its steps."""
        manager.create_session("sess-004")
        manager.append_step("sess-004", {"index": 0})
        assert manager.get_session("sess-004") is not None

        deleted = manager.delete_session("sess-004")
        assert deleted is True
        assert manager.get_session("sess-004") is None

    def test_delete_nonexistent_returns_false(self, manager: SessionManager):
        """Deleting a nonexistent session should return False."""
        assert manager.delete_session("ghost") is False

    def test_append_and_get_steps(self, manager: SessionManager):
        """Steps should be appended and retrievable in order."""
        manager.create_session("sess-005")
        for i in range(3):
            manager.append_step("sess-005", {"index": i, "action": f"step-{i}"})

        steps = manager.get_steps("sess-005")
        assert len(steps) == 3
        assert steps[0]["index"] == 0
        assert steps[1]["action"] == "step-1"
        assert steps[2]["index"] == 2

    def test_append_step_updates_timestamp(self, manager: SessionManager):
        """Appending a step should update the session's updated_at."""
        manager.create_session("sess-006")
        before = manager.get_session("sess-006")
        assert before is not None
        old_ts = before.updated_at

        manager.append_step("sess-006", {"index": 0})
        after = manager.get_session("sess-006")
        assert after is not None
        assert after.updated_at > old_ts

    def test_append_step_to_nonexistent_returns_false(
        self, manager: SessionManager
    ):
        """Appending a step to a nonexistent session should return False."""
        result = manager.append_step("ghost", {"index": 0})
        assert result is False

    def test_list_sessions(self, manager: SessionManager):
        """list_sessions should return all sessions or filtered by status."""
        manager.create_session("sess-a", metadata={"env": "test"})
        manager.create_session("sess-b", metadata={"env": "prod"})
        manager.update_session("sess-b", status=SessionStatus.COMPLETED)

        all_sessions = manager.list_sessions()
        assert len(all_sessions) == 2

        active = manager.list_sessions(status=SessionStatus.ACTIVE)
        assert len(active) == 1
        assert active[0].session_id == "sess-a"

        completed = manager.list_sessions(status=SessionStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0].session_id == "sess-b"

    def test_list_sessions_pagination(self, manager: SessionManager):
        """list_sessions should support limit and offset."""
        for i in range(10):
            manager.create_session(f"sess-pag-{i:02d}")

        page1 = manager.list_sessions(limit=3, offset=0)
        assert len(page1) == 3

        page2 = manager.list_sessions(limit=3, offset=3)
        assert len(page2) == 3
        # Second page should have different IDs than first
        page1_ids = {s.session_id for s in page1}
        page2_ids = {s.session_id for s in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_count_sessions(self, manager: SessionManager):
        """count_sessions should return correct counts."""
        assert manager.count_sessions() == 0

        manager.create_session("sess-count-1")
        manager.create_session("sess-count-2")
        assert manager.count_sessions() == 2

        manager.create_session("sess-count-3")
        manager.update_session("sess-count-3", status=SessionStatus.FAILED)
        assert manager.count_sessions(status=SessionStatus.FAILED) == 1

    def test_close_and_reopen(self, db_path: str):
        """Closing and reopening the manager should preserve data."""
        mgr1 = SessionManager(db_path)
        mgr1.create_session("sess-persist", metadata={"key": "val"})
        mgr1.append_step("sess-persist", {"index": 0})
        mgr1.close()

        mgr2 = SessionManager(db_path)
        fetched = mgr2.get_session("sess-persist")
        assert fetched is not None
        assert fetched.metadata["key"] == "val"
        steps = mgr2.get_steps("sess-persist")
        assert len(steps) == 1
        mgr2.close()
