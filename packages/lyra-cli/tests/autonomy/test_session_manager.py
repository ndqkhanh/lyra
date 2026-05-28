"""Tests for the session manager."""

from __future__ import annotations

from pathlib import Path

import pytest
from lyra_cli.autonomy.session_manager import (
    CheckpointNotFoundError,
    SessionCheckpoint,
    SessionManager,
)


class TestSessionManager:
    """Suite: SessionManager checkpoint save/load/list/delete."""

    def test_save_and_load_checkpoint(self, tmp_path: Path) -> None:
        mgr = SessionManager(checkpoint_dir=tmp_path)
        cp = SessionCheckpoint(
            session_id="sess_1",
            state="planning",
            goal="Test goal",
        )
        mgr.save_checkpoint(cp)
        loaded = mgr.load_checkpoint("sess_1")
        assert loaded.session_id == "sess_1"
        assert loaded.state == "planning"
        assert loaded.goal == "Test goal"

    def test_load_missing_raises(self, tmp_path: Path) -> None:
        mgr = SessionManager(checkpoint_dir=tmp_path)
        with pytest.raises(CheckpointNotFoundError):
            mgr.load_checkpoint("nonexistent")

    def test_list_all_checkpoints(self, tmp_path: Path) -> None:
        mgr = SessionManager(checkpoint_dir=tmp_path)
        mgr.save_checkpoint(SessionCheckpoint(session_id="s1", state="idle"))
        mgr.save_checkpoint(SessionCheckpoint(session_id="s2", state="planning"))
        all_cps = mgr.list_checkpoints()
        assert len(all_cps) == 2

    def test_list_filtered_by_session(self, tmp_path: Path) -> None:
        mgr = SessionManager(checkpoint_dir=tmp_path)
        mgr.save_checkpoint(SessionCheckpoint(session_id="s1", state="idle"))
        mgr.save_checkpoint(SessionCheckpoint(session_id="s2", state="planning"))
        filtered = mgr.list_checkpoints("s1")
        assert len(filtered) == 1
        assert filtered[0].session_id == "s1"

    def test_delete_checkpoint(self, tmp_path: Path) -> None:
        mgr = SessionManager(checkpoint_dir=tmp_path)
        mgr.save_checkpoint(SessionCheckpoint(session_id="del_me", state="idle"))
        assert mgr.checkpoint_exists("del_me") is True
        deleted = mgr.delete_checkpoint("del_me")
        assert deleted >= 1
        assert mgr.checkpoint_exists("del_me") is False

    def test_checkpoint_exists(self, tmp_path: Path) -> None:
        mgr = SessionManager(checkpoint_dir=tmp_path)
        assert mgr.checkpoint_exists("ghost") is False
        mgr.save_checkpoint(SessionCheckpoint(session_id="ghost", state="idle"))
        assert mgr.checkpoint_exists("ghost") is True

    def test_to_dict_round_trip(self) -> None:
        cp = SessionCheckpoint(
            session_id="rt",
            state="executing",
            context={"key": "val"},
            goal="Round trip",
        )
        d = cp.to_dict()
        restored = SessionCheckpoint.from_dict(d)
        assert restored.session_id == "rt"
        assert restored.state == "executing"
        assert restored.context == {"key": "val"}

    def test_checkpoint_dir_created(self, tmp_path: Path) -> None:
        check_dir = tmp_path / "custom_checkpoints"
        assert check_dir.exists() is False
        SessionManager(checkpoint_dir=check_dir)
        assert check_dir.exists() is True
