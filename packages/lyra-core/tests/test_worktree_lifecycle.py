"""Red tests for worktree lifecycle: allocate, run, cleanup; no orphans."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from lyra_core.subagent.worktree import (
    WorktreeError,
    WorktreeManager,
)


def _init_repo(p: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(p)], check=True)
    (p / "README.md").write_text("hello\n")
    subprocess.run(["git", "-C", str(p), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(p), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "-m", "init"],
        check=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    p = tmp_path / "repo"
    p.mkdir()
    _init_repo(p)
    return p


def test_allocate_returns_isolated_worktree(repo: Path) -> None:
    mgr = WorktreeManager(repo_root=repo)
    wt = mgr.allocate(scope_id="feat-a")
    assert wt.path.exists()
    assert (wt.path / "README.md").exists()
    assert wt.path != repo
    mgr.cleanup(wt)
    assert not wt.path.exists()


def test_allocate_twice_produces_distinct_paths(repo: Path) -> None:
    mgr = WorktreeManager(repo_root=repo)
    a = mgr.allocate(scope_id="feat-a")
    b = mgr.allocate(scope_id="feat-b")
    assert a.path != b.path
    mgr.cleanup(a)
    mgr.cleanup(b)


def test_reconciler_removes_orphans(repo: Path) -> None:
    mgr = WorktreeManager(repo_root=repo)
    wt = mgr.allocate(scope_id="orphaned")
    # Simulate orphan: drop our in-memory record but keep the worktree on disk.
    mgr._forget_for_test(wt)  # type: ignore[attr-defined]
    removed = mgr.reconcile_orphans()
    assert wt.path in removed
    assert not wt.path.exists()


def test_cleanup_is_idempotent(repo: Path) -> None:
    mgr = WorktreeManager(repo_root=repo)
    wt = mgr.allocate(scope_id="idem")
    mgr.cleanup(wt)
    # Second cleanup is a noop, not an error.
    mgr.cleanup(wt)


def test_allocate_rejects_outside_repo(tmp_path: Path) -> None:
    not_a_repo = tmp_path / "nope"
    not_a_repo.mkdir()
    with pytest.raises(WorktreeError):
        WorktreeManager(repo_root=not_a_repo).allocate(scope_id="x")
