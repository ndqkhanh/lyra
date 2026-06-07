"""
Tests for the session checkpoint and crash-recovery module.
"""

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lyra.sessions.checkpoint import (
    CheckpointManager,
    CheckpointRecord,
    DEFAULT_STALE_MINUTES,
    MAX_CHECKPOINTS_PER_SESSION,
)
from lyra.sessions.persist import SessionManager, SessionStatus


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    """Provide a temporary database path."""
    return str(tmp_path / "test_checkpoints.db")


@pytest.fixture
def manager(db_path: str) -> SessionManager:
    """Provide a fresh SessionManager."""
    mgr = SessionManager(db_path)
    yield mgr
    mgr.close()


@pytest.fixture
def ckpt_mgr(manager: SessionManager) -> CheckpointManager:
    """Provide a CheckpointManager wrapping the SessionManager."""
    return CheckpointManager(manager)


# ------------------------------------------------------------------
# CheckpointRecord tests
# ------------------------------------------------------------------


class TestCheckpointRecord:
    """Tests for the CheckpointRecord dataclass."""

    def test_fields(self):
        """CheckpointRecord should hold all expected fields."""
        now = datetime.now(timezone.utc)
        cp = CheckpointRecord(
            checkpoint_id=1,
            session_id="sess-001",
            checkpoint_index=0,
            state={"turn": 3, "memory": {"x": 1}},
            created_at=now,
        )
        assert cp.checkpoint_id == 1
        assert cp.session_id == "sess-001"
        assert cp.checkpoint_index == 0
        assert cp.state["turn"] == 3
        assert cp.created_at == now


# ------------------------------------------------------------------
# Save / restore cycle
# ------------------------------------------------------------------


class TestSaveRestore:
    """Checkpoint save and restore round-trips."""

    def test_save_and_restore(self, manager: SessionManager, ckpt_mgr: CheckpointManager):
        """Saving a checkpoint and restoring it should return the same state."""
        manager.create_session("sess-cp-01", agent_id="agent-a")
        state = {"turn": 0, "memory": {"last_query": "hello"}, "stack": []}

        cp = ckpt_mgr.save_checkpoint("sess-cp-01", state)
        assert cp is not None
        assert cp.session_id == "sess-cp-01"
        assert cp.checkpoint_index == 0
        assert cp.state["turn"] == 0

        restored = ckpt_mgr.restore_checkpoint("sess-cp-01")
        assert restored is not None
        assert restored["turn"] == 0
        assert restored["memory"]["last_query"] == "hello"

    def test_save_multiple_checkpoints(self, manager: SessionManager, ckpt_mgr: CheckpointManager):
        """Multiple checkpoints should be stored and retrievable in order."""
        manager.create_session("sess-cp-multi")
        for i in range(3):
            ckpt_mgr.save_checkpoint("sess-cp-multi", {"turn": i, "data": f"state-{i}"})

        checkpoints = ckpt_mgr.list_checkpoints("sess-cp-multi")
        assert len(checkpoints) == 3
        assert [c.state["turn"] for c in checkpoints] == [0, 1, 2]

    def test_restore_from_latest(self, manager: SessionManager, ckpt_mgr: CheckpointManager):
        """restore_checkpoint should return the most recent checkpoint."""
        manager.create_session("sess-cp-latest")
        ckpt_mgr.save_checkpoint("sess-cp-latest", {"turn": 0})
        ckpt_mgr.save_checkpoint("sess-cp-latest", {"turn": 1})
        ckpt_mgr.save_checkpoint("sess-cp-latest", {"turn": 2})

        restored = ckpt_mgr.restore_checkpoint("sess-cp-latest")
        assert restored is not None
        assert restored["turn"] == 2

    def test_restore_nonexistent_session(self, ckpt_mgr: CheckpointManager):
        """Restoring a session with no checkpoints returns None."""
        state = ckpt_mgr.restore_checkpoint("ghost-session")
        assert state is None

    def test_save_nonexistent_session_returns_none(self, ckpt_mgr: CheckpointManager):
        """Saving a checkpoint for a nonexistent session returns None."""
        result = ckpt_mgr.save_checkpoint("no-such-session", {"data": 1})
        assert result is None

    def test_list_checkpoints_empty(self, manager: SessionManager, ckpt_mgr: CheckpointManager):
        """Listing checkpoints for a session with none should return empty list."""
        manager.create_session("sess-empty-cp")
        checkpoints = ckpt_mgr.list_checkpoints("sess-empty-cp")
        assert checkpoints == []

    def test_list_checkpoints_nonexistent(self, ckpt_mgr: CheckpointManager):
        """Listing checkpoints for a nonexistent session returns empty list."""
        checkpoints = ckpt_mgr.list_checkpoints("ghost")
        assert checkpoints == []


# ------------------------------------------------------------------
# Crash recovery detection
# ------------------------------------------------------------------


class TestCrashDetection:
    """Interrupted session detection."""

    def test_no_interrupted_when_recent(self, manager: SessionManager, ckpt_mgr: CheckpointManager):
        """An active session with a recent checkpoint should not be flagged."""
        manager.create_session("sess-recent")
        ckpt_mgr.save_checkpoint("sess-recent", {"turn": 0})
        assert ckpt_mgr.detect_interrupted(stale_minutes=10) == []

    def test_detect_interrupted_session(self, manager: SessionManager, ckpt_mgr: CheckpointManager):
        """An old active session with a checkpoint should be flagged."""
        manager.create_session("sess-stale")
        ckpt_mgr.save_checkpoint("sess-stale", {"turn": 0})

        # Manually push the updated_at back in time
        old_ts = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        manager._conn.execute(
            "UPDATE sessions SET updated_at=? WHERE session_id=?",
            (old_ts, "sess-stale"),
        )
        manager._conn.commit()
        # Also push checkpoint created_at back
        manager._conn.execute(
            "UPDATE session_checkpoints SET created_at=? WHERE session_id=?",
            (old_ts, "sess-stale"),
        )
        manager._conn.commit()

        interrupted = ckpt_mgr.detect_interrupted(stale_minutes=5)
        assert "sess-stale" in interrupted

    def test_not_interrupted_without_checkpoint(self, manager: SessionManager, ckpt_mgr: CheckpointManager):
        """An old active session *without* a checkpoint should NOT be flagged."""
        manager.create_session("sess-old-nockpt")
        old_ts = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        manager._conn.execute(
            "UPDATE sessions SET updated_at=? WHERE session_id=?",
            (old_ts, "sess-old-nockpt"),
        )
        manager._conn.commit()

        interrupted = ckpt_mgr.detect_interrupted(stale_minutes=5)
        assert "sess-old-nockpt" not in interrupted

    def test_not_interrupted_completed(self, manager: SessionManager, ckpt_mgr: CheckpointManager):
        """A completed session should never be flagged regardless of age."""
        manager.create_session("sess-complete")
        ckpt_mgr.save_checkpoint("sess-complete", {"turn": 0})
        manager.update_session("sess-complete", status=SessionStatus.COMPLETED)
        old_ts = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        manager._conn.execute(
            "UPDATE sessions SET updated_at=? WHERE session_id=?",
            (old_ts, "sess-complete"),
        )
        manager._conn.commit()

        interrupted = ckpt_mgr.detect_interrupted(stale_minutes=5)
        assert "sess-complete" not in interrupted

    def test_detect_respects_custom_threshold(self, manager: SessionManager, ckpt_mgr: CheckpointManager):
        """detect_interrupted should accept a custom stale_minutes override."""
        manager.create_session("sess-custom")
        ckpt_mgr.save_checkpoint("sess-custom", {"turn": 0})
        old_ts = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        manager._conn.execute(
            "UPDATE sessions SET updated_at=? WHERE session_id=?",
            (old_ts, "sess-custom"),
        )
        manager._conn.commit()

        # With a 15-minute threshold the session should NOT be flagged
        assert ckpt_mgr.detect_interrupted(stale_minutes=15) == []
        # With a 5-minute threshold it should be flagged
        interrupted = ckpt_mgr.detect_interrupted(stale_minutes=5)
        assert "sess-custom" in interrupted


# ------------------------------------------------------------------
# Recovery
# ------------------------------------------------------------------


class TestRecovery:
    """Replay / recovery from checkpoint."""

    def test_recover_restores_state(self, manager: SessionManager, ckpt_mgr: CheckpointManager):
        """recover() should return the latest checkpoint state."""
        manager.create_session("sess-recover")
        ckpt_mgr.save_checkpoint("sess-recover", {"turn": 1, "data": "test"})

        state = ckpt_mgr.recover("sess-recover", mark_paused=False)
        assert state is not None
        assert state["turn"] == 1
        assert state["data"] == "test"

    def test_recover_marks_paused(self, manager: SessionManager, ckpt_mgr: CheckpointManager):
        """recover() should mark the session as PAUSED by default."""
        manager.create_session("sess-pause")
        ckpt_mgr.save_checkpoint("sess-pause", {"turn": 0})

        ckpt_mgr.recover("sess-pause", mark_paused=True)
        record = manager.get_session("sess-pause")
        assert record is not None
        assert record.status == SessionStatus.PAUSED

    def test_recover_no_checkpoint_returns_none(self, ckpt_mgr: CheckpointManager):
        """recover() on a session with no checkpoints returns None."""
        state = ckpt_mgr.recover("no-ckpt", mark_paused=False)
        assert state is None

    def test_recover_replay_from_checkpoint(self, manager: SessionManager, ckpt_mgr: CheckpointManager):
        """After recovery the session should be resumable from the checkpointed state."""
        manager.create_session("sess-replay")
        # Simulate 3 turns of progression
        ckpt_mgr.save_checkpoint("sess-replay", {"turn": 0, "conversation": []})
        ckpt_mgr.save_checkpoint("sess-replay", {"turn": 1, "conversation": ["hi"]})
        ckpt_mgr.save_checkpoint("sess-replay", {"turn": 2, "conversation": ["hi", "how are you"]})

        # Recover (should get turn 2)
        state = ckpt_mgr.recover("sess-replay", mark_paused=False)
        assert state is not None
        assert state["turn"] == 2
        assert len(state["conversation"]) == 2


# ------------------------------------------------------------------
# Pruning
# ------------------------------------------------------------------


class TestPruning:
    """Auto-pruning of old checkpoints."""

    def test_does_not_prune_below_limit(self, manager: SessionManager, ckpt_mgr: CheckpointManager):
        """Saving fewer checkpoints than the max should not prune anything."""
        manager.create_session("sess-noprune")
        for i in range(3):
            ckpt_mgr.save_checkpoint("sess-noprune", {"turn": i})

        checkpoints = ckpt_mgr.list_checkpoints("sess-noprune")
        assert len(checkpoints) == 3

    def test_prunes_excess_checkpoints(self, manager: SessionManager):
        """Saving more than max_checkpoints should remove oldest ones."""
        ckpt_mgr = CheckpointManager(manager, max_checkpoints=3)
        manager.create_session("sess-prune")
        for i in range(5):
            ckpt_mgr.save_checkpoint("sess-prune", {"turn": i})

        checkpoints = ckpt_mgr.list_checkpoints("sess-prune")
        assert len(checkpoints) == 3
        # Only the last 3 should remain (turns 2, 3, 4)
        assert [c.state["turn"] for c in checkpoints] == [2, 3, 4]

    def test_pruning_keeps_most_recent(self, manager: SessionManager):
        """After pruning, the latest checkpoint should remain accessible."""
        ckpt_mgr = CheckpointManager(manager, max_checkpoints=2)
        manager.create_session("sess-keep-latest")
        for i in range(4):
            ckpt_mgr.save_checkpoint("sess-keep-latest", {"turn": i, "payload": f"step-{i}"})

        restored = ckpt_mgr.restore_checkpoint("sess-keep-latest")
        assert restored is not None
        assert restored["turn"] == 3
        assert restored["payload"] == "step-3"

    def test_default_max_checkpoints(self, manager: SessionManager, ckpt_mgr: CheckpointManager):
        """Default max_checkpoints should be MAX_CHECKPOINTS_PER_SESSION."""
        assert ckpt_mgr._max_checkpoints == MAX_CHECKPOINTS_PER_SESSION


# ------------------------------------------------------------------
# Integration: save → detect → recover cycle
# ------------------------------------------------------------------


class TestCrashRecoveryCycle:
    """End-to-end crash recovery lifecycle."""

    def test_full_crash_cycle(self, manager: SessionManager, ckpt_mgr: CheckpointManager):
        """Simulate a crash and full recovery cycle."""
        # 1. Agent starts a session
        manager.create_session("sess-cycle", agent_id="agent-alpha")

        # 2. Agent saves checkpoints as it works
        for i in range(3):
            ckpt_mgr.save_checkpoint("sess-cycle", {"turn": i, "result": f"step-{i}"})

        # 3. Simulate crash: manually age the session timestamp
        old_ts = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        manager._conn.execute(
            "UPDATE sessions SET updated_at=? WHERE session_id=?",
            (old_ts, "sess-cycle"),
        )
        manager._conn.commit()

        # 4. Recovery system detects interrupted sessions
        interrupted = ckpt_mgr.detect_interrupted(stale_minutes=5)
        assert "sess-cycle" in interrupted

        # 5. Recovery restores from last checkpoint
        state = ckpt_mgr.recover("sess-cycle", mark_paused=True)
        assert state is not None
        assert state["turn"] == 2
        assert state["result"] == "step-2"

        # 6. Session is now paused (not picked up again)
        record = manager.get_session("sess-cycle")
        assert record is not None
        assert record.status == SessionStatus.PAUSED

        interrupted_after = ckpt_mgr.detect_interrupted(stale_minutes=5)
        assert "sess-cycle" not in interrupted_after


# ------------------------------------------------------------------
# Persistence across manager instances
# ------------------------------------------------------------------


class TestPersistence:
    """Checkpoints survive SessionManager close/reopen."""

    def test_checkpoints_persist_across_reopen(self, db_path: str):
        """Checkpoints should survive closing and reopening the DB."""
        mgr1 = SessionManager(db_path)
        cm1 = CheckpointManager(mgr1)
        mgr1.create_session("sess-persist-cp")
        cm1.save_checkpoint("sess-persist-cp", {"turn": 2})
        mgr1.close()

        mgr2 = SessionManager(db_path)
        cm2 = CheckpointManager(mgr2)

        checkpoints = cm2.list_checkpoints("sess-persist-cp")
        assert len(checkpoints) == 1
        assert checkpoints[0].state["turn"] == 2

        restored = cm2.restore_checkpoint("sess-persist-cp")
        assert restored is not None
        assert restored["turn"] == 2

        mgr2.close()
