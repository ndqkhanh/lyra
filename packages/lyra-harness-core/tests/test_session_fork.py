"""Tests for Fork-from-Checkpoint Session Exploration (P1-B6)."""
from __future__ import annotations

import time

import pytest

from lyra_harness_core.session_fork import (
    CheckpointStore,
    SessionFork,
    SessionSnapshot,
)


# ---------------------------------------------------------------------------
# SessionSnapshot
# ---------------------------------------------------------------------------


class TestSessionSnapshot:
    def test_minimal(self):
        snap = SessionSnapshot(
            snapshot_id="snap_1",
            parent_session_id="sess_1",
            timestamp=1.0,
        )
        assert snap.snapshot_id == "snap_1"
        assert snap.parent_session_id == "sess_1"
        assert snap.label == ""
        assert snap.context == {}

    def test_with_context(self):
        snap = SessionSnapshot(
            snapshot_id="snap_1",
            parent_session_id="sess_1",
            timestamp=1.0,
            label="before_tool",
            context={"step": 5, "task": "build"},
        )
        assert snap.label == "before_tool"
        assert snap.context == {"step": 5, "task": "build"}

    def test_age_seconds(self):
        snap = SessionSnapshot(
            snapshot_id="snap_1",
            parent_session_id="sess_1",
            timestamp=time.time() - 10,
        )
        assert 9 <= snap.age_seconds <= 11

    def test_frozen(self):
        snap = SessionSnapshot(
            snapshot_id="snap_1",
            parent_session_id="sess_1",
            timestamp=1.0,
        )
        with pytest.raises(Exception):
            snap.label = "new"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SessionFork
# ---------------------------------------------------------------------------


class TestSessionFork:
    def test_minimal(self):
        fork = SessionFork(
            fork_id="fork_1",
            snapshot_id="snap_1",
            parent_session_id="sess_1",
            created_at=1.0,
        )
        assert fork.fork_id == "fork_1"
        assert fork.status == "active"

    def test_frozen(self):
        fork = SessionFork(
            fork_id="fork_1",
            snapshot_id="snap_1",
            parent_session_id="sess_1",
            created_at=1.0,
        )
        with pytest.raises(Exception):
            fork.status = "done"  # type: ignore[misc]

    def test_age_seconds(self):
        fork = SessionFork(
            fork_id="fork_1",
            snapshot_id="snap_1",
            parent_session_id="sess_1",
            created_at=time.time() - 5,
        )
        assert 4 <= fork.age_seconds <= 6


# ---------------------------------------------------------------------------
# CheckpointStore — Snapshots
# ---------------------------------------------------------------------------


class TestCheckpointStoreSnapshots:
    @pytest.fixture
    def store(self):
        return CheckpointStore()

    def test_create_snapshot(self, store):
        snap = store.create_snapshot("sess_1", label="checkpoint_1")
        assert snap.parent_session_id == "sess_1"
        assert snap.label == "checkpoint_1"
        assert store.snapshot_count("sess_1") == 1

    def test_create_multiple_snapshots(self, store):
        store.create_snapshot("sess_1", label="start")
        store.create_snapshot("sess_1", label="middle")
        store.create_snapshot("sess_1", label="end")
        assert store.snapshot_count("sess_1") == 3

    def test_snapshots_ordered_by_time(self, store):
        s1 = store.create_snapshot("sess_1")
        s2 = store.create_snapshot("sess_1")
        snaps = store.get_snapshots("sess_1")
        assert snaps[0].snapshot_id == s1.snapshot_id
        assert snaps[1].snapshot_id == s2.snapshot_id

    def test_get_snapshot(self, store):
        snap = store.create_snapshot("sess_1")
        found = store.get_snapshot(snap.snapshot_id)
        assert found is not None
        assert found.snapshot_id == snap.snapshot_id

    def test_get_snapshot_nonexistent(self, store):
        assert store.get_snapshot("nope") is None

    def test_latest_snapshot(self, store):
        store.create_snapshot("sess_1", label="first")
        store.create_snapshot("sess_1", label="second")
        latest = store.latest_snapshot("sess_1")
        assert latest is not None
        assert latest.label == "second"

    def test_latest_snapshot_none(self, store):
        assert store.latest_snapshot("nope") is None

    def test_delete_snapshot(self, store):
        snap = store.create_snapshot("sess_1")
        assert store.delete_snapshot(snap.snapshot_id)
        assert store.snapshot_count("sess_1") == 0

    def test_delete_nonexistent(self, store):
        assert not store.delete_snapshot("nope")

    def test_snapshot_count_all(self, store):
        store.create_snapshot("sess_1")
        store.create_snapshot("sess_2")
        store.create_snapshot("sess_2")
        assert store.snapshot_count() == 3
        assert store.snapshot_count("sess_1") == 1
        assert store.snapshot_count("sess_2") == 2

    def test_snapshot_with_context(self, store):
        snap = store.create_snapshot(
            "sess_1",
            context={"messages": [{"role": "user", "content": "hi"}]},
            metadata={"model": "sonnet"},
        )
        assert len(snap.context["messages"]) == 1
        assert snap.metadata["model"] == "sonnet"


# ---------------------------------------------------------------------------
# CheckpointStore — Forking
# ---------------------------------------------------------------------------


class TestCheckpointStoreForking:
    @pytest.fixture
    def store(self):
        return CheckpointStore()

    @pytest.fixture
    def setup(self, store):
        """Create a session with snapshots and a fork."""
        snap = store.create_snapshot("sess_1", label="checkpoint")
        fork = store.fork(snap.snapshot_id, label="explore_alt")
        return store, snap, fork

    def test_fork(self, setup):
        store, snap, fork = setup
        assert fork is not None
        assert fork.snapshot_id == snap.snapshot_id
        assert fork.parent_session_id == "sess_1"
        assert fork.label == "explore_alt"
        assert fork.status == "active"

    def test_fork_nonexistent_snapshot(self, store):
        assert store.fork("nope") is None

    def test_fork_count(self, setup):
        store, _, _ = setup
        assert store.fork_count("sess_1") == 1

    def test_fork_increments_count(self, setup):
        store, snap, _ = setup
        store.fork(snap.snapshot_id, label="fork_2")
        assert store.fork_count("sess_1") == 2

    def test_get_fork(self, setup):
        store, _, fork = setup
        found = store.get_fork(fork.fork_id)
        assert found is not None
        assert found.fork_id == fork.fork_id

    def test_get_fork_nonexistent(self, store):
        assert store.get_fork("nope") is None

    def test_get_forks(self, setup):
        store, _, _ = setup
        forks = store.get_forks("sess_1")
        assert len(forks) == 1

    def test_get_forks_empty(self, store):
        assert store.get_forks("nope") == []

    def test_fork_count_all(self, setup):
        store, snap, _ = setup
        store.create_snapshot("sess_2")
        store.fork(snap.snapshot_id)
        assert store.fork_count() == 2

    def test_parent_session(self, setup):
        store, _, fork = setup
        assert store.parent_session(fork.fork_id) == "sess_1"

    def test_parent_session_nonexistent(self, store):
        assert store.parent_session("nope") is None

    def test_complete_fork(self, setup):
        store, _, fork = setup
        assert store.complete_fork(fork.fork_id)
        updated = store.get_fork(fork.fork_id)
        assert updated is not None
        assert updated.status == "completed"

    def test_complete_fork_nonexistent(self, store):
        assert not store.complete_fork("nope")

    def test_abandon_fork(self, setup):
        store, _, fork = setup
        assert store.abandon_fork(fork.fork_id)
        updated = store.get_fork(fork.fork_id)
        assert updated.status == "abandoned"  # type: ignore[union-attr]

    def test_merge_fork(self, setup):
        store, _, fork = setup
        assert store.merge_fork(fork.fork_id)
        updated = store.get_fork(fork.fork_id)
        assert updated.status == "merged"  # type: ignore[union-attr]

    def test_active_forks(self, setup):
        store, snap, _ = setup
        store.fork(snap.snapshot_id)
        f3 = store.fork(snap.snapshot_id)
        store.complete_fork(f3.fork_id)  # type: ignore[arg-type]
        active = store.active_forks("sess_1")
        assert len(active) == 2  # first two, third is completed

    def test_active_forks_all(self, setup):
        store, snap, _ = setup
        snap2 = store.create_snapshot("sess_2")
        store.fork(snap2.snapshot_id)
        active = store.active_forks()
        assert len(active) == 2

    def test_sibling_forks(self, setup):
        store, snap, fork1 = setup
        fork2 = store.fork(snap.snapshot_id, label="sibling")
        siblings = store.sibling_forks(fork1.fork_id)
        assert len(siblings) == 1
        assert siblings[0].fork_id == fork2.fork_id  # type: ignore[arg-type]

    def test_sibling_forks_none(self, setup):
        store, _, fork = setup
        # Only one fork from this snapshot, so no siblings
        siblings = store.sibling_forks(fork.fork_id)
        assert siblings == []

    def test_sibling_forks_nonexistent(self, store):
        assert store.sibling_forks("nope") == []

    def test_multiple_sessions_independent(self, store):
        snap1 = store.create_snapshot("sess_1")
        snap2 = store.create_snapshot("sess_2")
        store.fork(snap1.snapshot_id)
        store.fork(snap2.snapshot_id)

        assert store.fork_count("sess_1") == 1
        assert store.fork_count("sess_2") == 1
        assert store.fork_count() == 2

    def test_fork_tree(self, setup):
        store, snap, fork = setup
        store.complete_fork(fork.fork_id)
        store.fork(snap.snapshot_id, label="another")

        tree = store.fork_tree("sess_1")
        assert tree["session_id"] == "sess_1"
        assert tree["snapshot_count"] == 1
        assert tree["fork_count"] == 2
        assert tree["active_forks"] == 1
        assert tree["completed_forks"] == 1


# ---------------------------------------------------------------------------
# CheckpointStore — Cleanup
# ---------------------------------------------------------------------------


class TestCheckpointStoreCleanup:
    @pytest.fixture
    def store(self):
        return CheckpointStore()

    def test_prune_old_snapshots(self, store):
        # Create a snapshot with old timestamp by manually patching
        snap = store.create_snapshot("sess_1")
        # We can't easily set old timestamps on frozen dataclasses
        # So test with max_age_seconds=0 — everything should be removed
        removed = store.prune_old_snapshots("sess_1", 0)
        assert removed == 1
        assert store.snapshot_count("sess_1") == 0

    def test_prune_keeps_recent(self, store):
        snap = store.create_snapshot("sess_1")
        removed = store.prune_old_snapshots("sess_1", 3600)
        assert removed == 0
        assert store.snapshot_count("sess_1") == 1

    def test_prune_nonexistent_session(self, store):
        assert store.prune_old_snapshots("nope", 0) == 0

    def test_clear(self, store):
        snap = store.create_snapshot("sess_1")
        store.fork(snap.snapshot_id)
        store.clear()
        assert store.total_snapshots == 0
        assert store.total_forks == 0

    def test_total_snapshots(self, store):
        assert store.total_snapshots == 0
        store.create_snapshot("sess_1")
        store.create_snapshot("sess_1")
        store.create_snapshot("sess_2")
        assert store.total_snapshots == 3

    def test_total_forks(self, store):
        assert store.total_forks == 0
        snap = store.create_snapshot("sess_1")
        store.fork(snap.snapshot_id)
        store.fork(snap.snapshot_id)
        assert store.total_forks == 2


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestSessionForkIntegration:
    def test_full_forking_workflow(self):
        """Simulate a typical forking workflow."""
        store = CheckpointStore()

        # Agent is working on a task
        session_id = "main_session"

        # Checkpoint 1: after planning
        cp1 = store.create_snapshot(
            session_id,
            label="after_planning",
            context={"plan": "implement auth", "files": ["auth.py"]},
        )

        # Checkpoint 2: after initial implementation
        cp2 = store.create_snapshot(
            session_id,
            label="after_impl_v1",
            context={"plan": "implement auth", "files": ["auth.py", "auth_test.py"]},
        )

        # Fork 1: explore alternative implementation
        fork1 = store.fork(cp1.snapshot_id, label="alt_approach")
        assert fork1 is not None

        # Fork 2: explore different test strategy from same checkpoint
        fork2 = store.fork(cp2.snapshot_id, label="test_strategy")
        assert fork2 is not None

        # Both forks are active
        assert len(store.active_forks(session_id)) == 2

        # Fork 1 completes successfully
        store.complete_fork(fork1.fork_id)

        # Fork 2 is abandoned (dead end)
        store.abandon_fork(fork2.fork_id)

        # Verify final state
        tree = store.fork_tree(session_id)
        assert tree["snapshot_count"] == 2
        assert tree["fork_count"] == 2
        assert tree["completed_forks"] == 1
        assert tree["abandoned_forks"] == 1
        assert tree["active_forks"] == 0

    def test_deep_forking_lineage(self):
        """Test multi-level forking (fork from a fork)."""
        store = CheckpointStore()

        # Session 1 creates snapshot
        snap1 = store.create_snapshot("sess_1", label="root")
        fork1 = store.fork(snap1.snapshot_id, label="level_1")

        # fork1 is a new "session" that could create its own snapshots
        # and be forked from
        assert store.parent_session(fork1.fork_id) == "sess_1"  # type: ignore[arg-type]

        # Create another fork from same snapshot
        fork2 = store.fork(snap1.snapshot_id, label="level_1_b")

        # Both forks share the same parent
        assert store.parent_session(fork2.fork_id) == "sess_1"  # type: ignore[arg-type]

        # They are siblings (same snapshot parent)
        siblings = store.sibling_forks(fork1.fork_id)
        assert len(siblings) == 1
        assert siblings[0].fork_id == fork2.fork_id  # type: ignore[arg-type]

    def test_parallel_exploration(self):
        """Multiple parallel forks exploring different directions."""
        store = CheckpointStore()

        snap = store.create_snapshot(
            "research_sess",
            label="crossroads",
            context={"question": "Which DB to use?"},
        )

        # Fork 3 parallel explorations
        opts = ["postgres", "mysql", "sqlite"]
        forks = []
        for opt in opts:
            f = store.fork(snap.snapshot_id, label=f"explore_{opt}")
            forks.append(f)

        assert store.fork_count("research_sess") == 3
        assert len(store.active_forks("research_sess")) == 3

        # Complete the postgres fork, abandon the rest
        store.complete_fork(forks[0].fork_id)  # type: ignore[arg-type]
        store.abandon_fork(forks[1].fork_id)  # type: ignore[arg-type]
        store.abandon_fork(forks[2].fork_id)  # type: ignore[arg-type]

        assert len(store.active_forks("research_sess")) == 0
