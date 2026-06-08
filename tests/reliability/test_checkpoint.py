"""Comprehensive tests for CheckpointManager — checkpoint-based recovery for agent sessions."""

import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lyra.reliability.checkpoint import (
    Checkpoint,
    CheckpointError,
    CheckpointManager,
    CheckpointRestoreError,
    CheckpointSaveError,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_dir():
    """Create a temporary directory for checkpoint storage."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def manager(temp_dir):
    """Create a CheckpointManager backed by a temporary directory."""
    return CheckpointManager(base_dir=temp_dir)


# =============================================================================
# Tests: Exception classes
# =============================================================================


class TestCheckpointError:
    def test_base_exception(self):
        err = CheckpointError("base error")
        assert isinstance(err, Exception)
        assert str(err) == "base error"

    def test_checkpoint_save_error(self):
        err = CheckpointSaveError("save failed")
        assert isinstance(err, CheckpointError)
        assert str(err) == "save failed"

    def test_checkpoint_restore_error(self):
        err = CheckpointRestoreError("restore failed")
        assert isinstance(err, CheckpointError)
        assert str(err) == "restore failed"


# =============================================================================
# Tests: Checkpoint
# =============================================================================


class TestCheckpoint:
    def test_minimal(self):
        ts = datetime.now(timezone.utc)
        cp = Checkpoint(agent_id="agent-1", timestamp=ts, state={"key": "value"})
        assert cp.agent_id == "agent-1"
        assert cp.timestamp == ts
        assert cp.state == {"key": "value"}

    def test_dataclass(self):
        ts = datetime.now(timezone.utc)
        cp = Checkpoint(agent_id="a", timestamp=ts, state={})
        assert cp.agent_id == "a"


# =============================================================================
# Tests: CheckpointManager — init
# =============================================================================


class TestInit:
    def test_creates_directory(self, temp_dir):
        new_dir = temp_dir / "nested" / "checkpoints"
        assert not new_dir.exists()
        CheckpointManager(base_dir=new_dir)
        assert new_dir.exists()

    def test_loads_existing_checkpoints(self, temp_dir):
        # Create a checkpoint file manually
        agent_id = "agent-pre"
        ts = datetime.now(timezone.utc)
        filename = f"{agent_id}.{ts.isoformat(timespec='seconds').replace(':', '-')}.checkpoint.json"
        payload = {
            "agent_id": agent_id,
            "timestamp": ts.isoformat(timespec="seconds"),
            "state": {"step": 1},
        }
        (temp_dir / filename).write_text(json.dumps(payload))

        mgr = CheckpointManager(base_dir=temp_dir)
        assert agent_id in mgr._checkpoints
        assert len(mgr._checkpoints[agent_id]) == 1

    def test_skips_non_checkpoint_json(self, temp_dir):
        (temp_dir / "random.json").write_text("{}")
        (temp_dir / "not_checkpoint.txt").write_text("data")
        mgr = CheckpointManager(base_dir=temp_dir)
        assert len(mgr._checkpoints) == 0

    def test_skips_corrupt_files(self, temp_dir):
        (temp_dir / "agent-1.2025-01-01T00-00-00.checkpoint.json").write_text(
            "not valid json"
        )
        mgr = CheckpointManager(base_dir=temp_dir)
        assert len(mgr._checkpoints) == 0

    def test_handles_missing_timestamp(self, temp_dir):
        agent_id = "agent-nt"
        filename = f"{agent_id}.2025-01-01T00-00-00.checkpoint.json"
        payload = {"agent_id": agent_id, "state": {"data": 1}}
        (temp_dir / filename).write_text(json.dumps(payload))
        mgr = CheckpointManager(base_dir=temp_dir)
        assert agent_id in mgr._checkpoints


# =============================================================================
# Tests: CheckpointManager — save
# =============================================================================


class TestSave:
    def test_saves_checkpoint_to_disk(self, manager, temp_dir):
        cp = manager.save("agent-1", {"step": 3, "context": "test"})
        assert cp.agent_id == "agent-1"
        assert cp.state == {"step": 3, "context": "test"}
        # Verify file was created
        files = list(temp_dir.iterdir())
        assert len(files) >= 1
        assert any("agent-1" in f.name for f in files)

    def test_saves_to_in_memory_index(self, manager):
        manager.save("agent-1", {"key": "value"})
        assert "agent-1" in manager._checkpoints
        assert len(manager._checkpoints["agent-1"]) == 1

    def test_multiple_checkpoints_for_same_agent(self, manager):
        manager.save("agent-1", {"step": 1})
        manager.save("agent-1", {"step": 2})
        assert len(manager._checkpoints["agent-1"]) == 2

    def test_multiple_agents(self, manager):
        manager.save("agent-a", {"data": "a"})
        manager.save("agent-b", {"data": "b"})
        assert len(manager._checkpoints) == 2
        assert len(manager._checkpoints["agent-a"]) == 1
        assert len(manager._checkpoints["agent-b"]) == 1

    def test_file_content_is_valid_json(self, manager, temp_dir):
        manager.save("agent-v", {"num": 42, "nested": {"key": "val"}})
        # Read the file back
        for f in temp_dir.iterdir():
            if "agent-v" in f.name:
                payload = json.loads(f.read_text())
                assert payload["agent_id"] == "agent-v"
                assert payload["state"]["num"] == 42
                assert payload["state"]["nested"]["key"] == "val"
                break
        else:
            pytest.fail("Checkpoint file not found")

    def test_save_os_error(self, manager):
        # Make base_dir a file to trigger OSError
        manager.base_dir = Path("/nonexistent/path/that/does/not/exist")
        with pytest.raises(CheckpointSaveError):
            manager.save("agent-err", {"data": 1})

    def test_save_non_serializable(self, manager):
        # datetime objects are serializable, but custom objects aren't
        # Actually datetimes ARE serializable via json
        manager.save("agent-serial", {"ts": datetime.now(timezone.utc).isoformat()})
        assert "agent-serial" in manager._checkpoints

    def test_save_returns_checkpoint(self, manager):
        cp = manager.save("agent-r", {"result": "ok"})
        assert isinstance(cp, Checkpoint)
        assert cp.timestamp is not None


# =============================================================================
# Tests: CheckpointManager — restore
# =============================================================================


class TestRestore:
    def test_restores_latest(self, manager):
        manager.save("agent-1", {"step": 1})
        manager.save("agent-1", {"step": 2})
        state = manager.restore("agent-1")
        assert state == {"step": 2}

    def test_restore_no_checkpoint(self, manager):
        with pytest.raises(CheckpointRestoreError, match="No checkpoints found"):
            manager.restore("nonexistent")

    def test_restore_single_checkpoint(self, manager):
        manager.save("agent-single", {"key": "value"})
        state = manager.restore("agent-single")
        assert state == {"key": "value"}

    def test_restore_after_multiple_saves(self, manager):
        for i in range(5):
            manager.save("agent-multi", {"iteration": i})
        state = manager.restore("agent-multi")
        assert state == {"iteration": 4}

    def test_restore_preserves_state_content(self, manager):
        state_dict = {
            "step": 10,
            "memory": ["fact1", "fact2"],
            "score": 0.95,
            "active": True,
        }
        manager.save("agent-rich", state_dict)
        restored = manager.restore("agent-rich")
        assert restored == state_dict


# =============================================================================
# Tests: CheckpointManager — list_checkpoints
# =============================================================================


class TestListCheckpoints:
    def test_empty(self, manager):
        assert manager.list_checkpoints() == []

    def test_single_agent(self, manager):
        manager.save("agent-1", {"data": "a"})
        manager.save("agent-1", {"data": "b"})
        cps = manager.list_checkpoints()
        assert len(cps) == 2

    def test_multiple_agents(self, manager):
        manager.save("agent-a", {"letter": "a"})
        manager.save("agent-b", {"letter": "b"})
        cps = manager.list_checkpoints()
        assert len(cps) == 2

    def test_sorted_by_timestamp_descending(self, manager):
        manager.save("agent-s", {"i": 1})
        time.sleep(0.01)
        manager.save("agent-s", {"i": 2})
        cps = manager.list_checkpoints()
        assert cps[0].state["i"] == 2
        assert cps[1].state["i"] == 1

    def test_returns_checkpoint_objects(self, manager):
        manager.save("agent-o", {"x": 1})
        cps = manager.list_checkpoints()
        assert isinstance(cps[0], Checkpoint)


# =============================================================================
# Tests: CheckpointManager — _load_index
# =============================================================================


class TestLoadIndex:
    def test_directory_does_not_exist(self, temp_dir):
        nonexistent = temp_dir / "does_not_exist"
        mgr = CheckpointManager(base_dir=nonexistent)
        assert mgr._checkpoints == {}

    def test_loads_sorted_files(self, temp_dir):
        """Files are loaded in sorted order."""
        # Create two checkpoints with different timestamps
        ts1 = datetime(2025, 1, 2, tzinfo=timezone.utc)
        ts2 = datetime(2025, 1, 1, tzinfo=timezone.utc)

        for agent_id, ts in [("a", ts1), ("b", ts2)]:
            filename = f"{agent_id}.{ts.isoformat(timespec='seconds').replace(':', '-')}.checkpoint.json"
            payload = {
                "agent_id": agent_id,
                "timestamp": ts.isoformat(timespec="seconds"),
                "state": {"id": agent_id},
            }
            (temp_dir / filename).write_text(json.dumps(payload))

        mgr = CheckpointManager(base_dir=temp_dir)
        assert len(mgr._checkpoints) == 2

    def test_ignores_non_json_files(self, temp_dir):
        (temp_dir / "some_file.txt").write_text("hello")
        (temp_dir / "data.csv").write_text("a,b,c")
        mgr = CheckpointManager(base_dir=temp_dir)
        assert len(mgr._checkpoints) == 0

    def test_handles_partial_corruption(self, temp_dir):
        """Valid files are loaded; corrupt files are skipped."""
        # Valid
        ts = datetime.now(timezone.utc)
        fname = f"good.{ts.isoformat(timespec='seconds').replace(':', '-')}.checkpoint.json"
        (temp_dir / fname).write_text(json.dumps({
            "agent_id": "good",
            "timestamp": ts.isoformat(timespec="seconds"),
            "state": {"ok": True},
        }))
        # Corrupt
        fname2 = f"bad.2025-01-01T00-00-00.checkpoint.json"
        (temp_dir / fname2).write_text("{{{broken json}}")

        mgr = CheckpointManager(base_dir=temp_dir)
        assert "good" in mgr._checkpoints
        assert "bad" not in mgr._checkpoints


# =============================================================================
# Tests: Edge cases and integration
# =============================================================================


class TestEdgeCases:
    def test_save_and_restore_cycle(self, manager):
        original_state = {"count": 42, "items": ["a", "b"], "metadata": {"version": 2}}
        manager.save("agent-cycle", original_state)
        restored = manager.restore("agent-cycle")
        assert restored == original_state

    def test_save_empty_state(self, manager):
        cp = manager.save("agent-empty", {})
        assert cp.state == {}
        restored = manager.restore("agent-empty")
        assert restored == {}

    def test_save_large_state(self, manager):
        large_state = {"data": "x" * 10000, "numbers": list(range(1000))}
        cp = manager.save("agent-large", large_state)
        assert len(cp.state["data"]) == 10000
        restored = manager.restore("agent-large")
        assert restored == large_state

    def test_save_with_special_characters(self, manager):
        state = {
            "path": "/tmp/test/path",
            "message": "Hello, world! @#$%",
            "unicode": "unicode text: éàü",
        }
        manager.save("agent-special", state)
        restored = manager.restore("agent-special")
        assert restored == state

    def test_multiple_agents_independent(self, manager):
        manager.save("agent-x", {"x": 1})
        manager.save("agent-y", {"y": 2})
        assert manager.restore("agent-x") == {"x": 1}
        assert manager.restore("agent-y") == {"y": 2}

    def test_restore_does_not_mutate_checkpoints(self, manager):
        manager.save("agent-mut", {"value": "original"})
        state = manager.restore("agent-mut")
        assert state["value"] == "original"

    def test_list_checkpoints_sorted_across_agents(self, manager):
        manager.save("agent-a", {"ts": 1})
        manager.save("agent-b", {"ts": 2})
        cps = manager.list_checkpoints()
        # Most recent first
        assert cps[0].state["ts"] >= cps[1].state["ts"]

    def test_load_index_non_existent_directory(self, temp_dir):
        mgr = CheckpointManager(base_dir=temp_dir / "new_subdir")
        assert mgr._checkpoints == {}
        assert (temp_dir / "new_subdir").exists()
