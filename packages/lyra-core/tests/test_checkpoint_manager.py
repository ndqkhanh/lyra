"""Dedicated tests for checkpoint/checkpoint_manager.py."""

from __future__ import annotations

import os
import tempfile
import time

import pytest
from lyra_core.checkpoint.checkpoint_manager import (
    Checkpoint,
    CheckpointConfig,
    CheckpointManager,
    CheckpointStats,
    CheckpointType,
    RewindResult,
    RewindTarget,
)


class TestCheckpointType:
    def test_values(self):
        assert CheckpointType.FILE_SNAPSHOT.value == "file_snapshot"
        assert CheckpointType.CONVERSATION.value == "conversation"
        assert CheckpointType.FULL.value == "full"


class TestRewindTarget:
    def test_values(self):
        assert RewindTarget.CODE.value == "code"
        assert RewindTarget.CONVERSATION.value == "conversation"
        assert RewindTarget.BOTH.value == "both"


class TestCheckpoint:
    def test_create(self):
        cp = Checkpoint(
            checkpoint_id="abc123",
            timestamp=1234567890.0,
            checkpoint_type=CheckpointType.FILE_SNAPSHOT,
            file_path="src/main.py",
            content_hash="def456",
            content="print('hello')",
        )
        assert cp.checkpoint_id == "abc123"
        assert cp.file_path == "src/main.py"
        assert cp.content == "print('hello')"
        assert cp.conversation_state == {}
        assert cp.metadata == ()

    def test_create_with_conversation(self):
        cp = Checkpoint(
            checkpoint_id="cp1",
            timestamp=time.time(),
            checkpoint_type=CheckpointType.FULL,
            file_path="src/app.py",
            content_hash="abc",
            content="x = 1",
            conversation_state={"turn": 5, "context": "debugging"},
            metadata=(("tag", "critical"),),
        )
        assert cp.conversation_state == {"turn": 5, "context": "debugging"}
        assert cp.metadata == (("tag", "critical"),)

    def test_is_frozen(self):
        cp = Checkpoint(
            checkpoint_id="abc",
            timestamp=time.time(),
            checkpoint_type=CheckpointType.FILE_SNAPSHOT,
            file_path="f.py",
            content_hash="h",
            content="c",
        )
        with pytest.raises(Exception):  # noqa: B017
            cp.file_path = "g.py"  # type: ignore[misc]


class TestCheckpointConfig:
    def test_defaults(self):
        cfg = CheckpointConfig()
        assert cfg.max_checkpoints == 100
        assert cfg.retention_days == 30
        assert cfg.auto_checkpoint is True
        assert cfg.storage_dir == "."

    def test_custom(self):
        cfg = CheckpointConfig(max_checkpoints=10, retention_days=7)
        assert cfg.max_checkpoints == 10
        assert cfg.retention_days == 7

    def test_is_frozen(self):
        cfg = CheckpointConfig()
        with pytest.raises(Exception):  # noqa: B017
            cfg.max_checkpoints = 50  # type: ignore[misc]


class TestRewindResult:
    def test_success(self):
        result = RewindResult(
            success=True,
            checkpoint_id="cp1",
            restored_files=("src/main.py",),
            message="Rewound successfully",
        )
        assert result.success is True
        assert result.restored_files == ("src/main.py",)

    def test_failure(self):
        result = RewindResult(
            success=False,
            checkpoint_id="cp1",
            restored_files=(),
            message="Checkpoint not found",
        )
        assert result.success is False
        assert len(result.restored_files) == 0

    def test_is_frozen(self):
        result = RewindResult(success=True, checkpoint_id="cp1", restored_files=(), message="ok")
        with pytest.raises(Exception):  # noqa: B017
            result.success = False  # type: ignore[misc]


class TestCheckpointStats:
    def test_create(self):
        stats = CheckpointStats(
            total_checkpoints=5,
            total_size_bytes=1024,
            oldest_timestamp=100.0,
            newest_timestamp=200.0,
        )
        assert stats.total_checkpoints == 5
        assert stats.total_size_bytes == 1024
        assert stats.oldest_timestamp == 100.0

    def test_is_frozen(self):
        stats = CheckpointStats(
            total_checkpoints=0, total_size_bytes=0, oldest_timestamp=0.0, newest_timestamp=0.0
        )
        with pytest.raises(Exception):  # noqa: B017
            stats.total_checkpoints = 10  # type: ignore[misc]


class TestCheckpointManager:
    @pytest.fixture
    def tmpdir(self):
        with tempfile.TemporaryDirectory() as td:
            yield td

    @pytest.fixture
    def mgr(self, tmpdir):
        config = CheckpointConfig(storage_dir=tmpdir)
        return CheckpointManager(config)

    def test_create_checkpoint(self, mgr):
        cp = mgr.create_checkpoint("src/main.py", "print('hello')")
        assert cp.file_path == "src/main.py"
        assert cp.content == "print('hello')"
        assert cp.checkpoint_type == CheckpointType.FILE_SNAPSHOT
        assert len(cp.checkpoint_id) == 32

    def test_create_checkpoint_with_conversation(self, mgr):
        cp = mgr.create_checkpoint(
            "src/app.py",
            "x = 1",
            conversation_state={"turn": 3},
        )
        assert cp.conversation_state == {"turn": 3}

    def test_get_checkpoint(self, mgr):
        cp = mgr.create_checkpoint("f.py", "data")
        retrieved = mgr.get_checkpoint(cp.checkpoint_id)
        assert retrieved is not None
        assert retrieved.checkpoint_id == cp.checkpoint_id
        assert retrieved.content == "data"

    def test_get_checkpoint_missing(self, mgr):
        assert mgr.get_checkpoint("nonexistent") is None

    def test_list_checkpoints(self, mgr):
        mgr.create_checkpoint("a.py", "1")
        time.sleep(0.01)
        mgr.create_checkpoint("b.py", "2")
        cps = mgr.list_checkpoints()
        assert len(cps) >= 2
        assert cps[0].timestamp >= cps[-1].timestamp

    def test_list_checkpoints_filtered(self, mgr):
        mgr.create_checkpoint("a.py", "1")
        mgr.create_checkpoint("b.py", "2")
        filtered = mgr.list_checkpoints(file_path="a.py")
        assert len(filtered) == 1
        assert filtered[0].file_path == "a.py"

    def test_list_checkpoints_limit(self, mgr):
        for i in range(10):
            mgr.create_checkpoint(f"f{i}.py", f"content{i}")
        cps = mgr.list_checkpoints(limit=3)
        assert len(cps) == 3

    def test_restore_code(self, mgr):
        cp = mgr.create_checkpoint("src/main.py", "print('hello world')")
        content = mgr.restore_code(cp.checkpoint_id)
        assert content == "print('hello world')"

    def test_restore_code_missing(self, mgr):
        with pytest.raises(ValueError, match="Checkpoint not found"):
            mgr.restore_code("nonexistent")

    def test_restore_conversation(self, mgr):
        cp = mgr.create_checkpoint(
            "f.py",
            "data",
            conversation_state={"turn": 7, "notes": "important"},
        )
        state = mgr.restore_conversation(cp.checkpoint_id)
        assert state == {"turn": 7, "notes": "important"}

    def test_restore_conversation_returns_copy(self, mgr):
        cp = mgr.create_checkpoint(
            "f.py",
            "data",
            conversation_state={"x": 1},
        )
        state = mgr.restore_conversation(cp.checkpoint_id)
        state["x"] = 999
        state2 = mgr.restore_conversation(cp.checkpoint_id)
        assert state2["x"] == 1

    def test_restore_conversation_missing(self, mgr):
        with pytest.raises(ValueError, match="Checkpoint not found"):
            mgr.restore_conversation("nonexistent")

    def test_rewind_code(self, mgr):
        cp = mgr.create_checkpoint("src/main.py", "old content")
        result = mgr.rewind(cp.checkpoint_id, RewindTarget.CODE)
        assert result.success is True
        assert result.restored_files == ("src/main.py",)

    def test_rewind_both(self, mgr):
        cp = mgr.create_checkpoint("src/app.py", "code")
        result = mgr.rewind(cp.checkpoint_id, RewindTarget.BOTH)
        assert result.success is True

    def test_rewind_missing(self, mgr):
        result = mgr.rewind("nonexistent")
        assert result.success is False
        assert "not found" in result.message.lower()

    def test_prune_expired(self, mgr):
        cp = mgr.create_checkpoint("old.py", "old")
        cpath = os.path.join(mgr._config.storage_dir, f"{cp.checkpoint_id}.json")
        old_time = time.time() - (31 * 86400)
        os.utime(cpath, (old_time, old_time))
        removed = mgr.prune_expired()
        assert removed >= 1

    def test_prune_none_expired(self, mgr):
        mgr.create_checkpoint("new.py", "new")
        removed = mgr.prune_expired()
        assert removed == 0

    def test_get_stats(self, mgr):
        mgr.create_checkpoint("a.py", "x")
        mgr.create_checkpoint("b.py", "y")
        stats = mgr.get_stats()
        assert stats.total_checkpoints == 2
        assert stats.total_size_bytes > 0
        assert stats.oldest_timestamp > 0
        assert stats.newest_timestamp > 0

    def test_get_stats_empty(self, mgr):
        stats = mgr.get_stats()
        assert stats.total_checkpoints == 0

    def test_clear_all(self, mgr):
        mgr.create_checkpoint("a.py", "1")
        mgr.create_checkpoint("b.py", "2")
        mgr.clear()
        assert mgr.get_stats().total_checkpoints == 0

    def test_clear_filtered(self, mgr):
        mgr.create_checkpoint("a.py", "1")
        mgr.create_checkpoint("b.py", "2")
        mgr.clear(file_path="a.py")
        cps = mgr.list_checkpoints()
        assert len(cps) == 1
        assert cps[0].file_path == "b.py"

    def test_max_checkpoints_enforced(self, mgr):
        mgr._config = CheckpointConfig(
            storage_dir=mgr._config.storage_dir,
            max_checkpoints=3,
        )
        for i in range(6):
            mgr.create_checkpoint(f"f{i}.py", f"c{i}")
        assert mgr.get_stats().total_checkpoints <= 3

    def test_content_hash_is_stable(self, mgr):
        cp1 = mgr.create_checkpoint("f.py", "hello")
        cp2 = mgr.create_checkpoint("f.py", "hello")
        assert cp1.content_hash == cp2.content_hash

    def test_content_hash_differs(self, mgr):
        cp1 = mgr.create_checkpoint("f.py", "hello")
        cp2 = mgr.create_checkpoint("f.py", "world")
        assert cp1.content_hash != cp2.content_hash
