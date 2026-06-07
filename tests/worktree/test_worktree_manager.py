"""
Tests for the WorktreeManager.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from lyra.worktree.manager import (
    WorktreeCleanupError,
    WorktreeCreateError,
    WorktreeManager,
    WorktreeSwitchError,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """Create a minimal git repository for testing."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@test.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "commit", "--allow-empty", "-m", "initial")
    # Simulate origin/main
    _git(repo, "remote", "add", "origin", str(repo))
    _git(repo, "fetch", "origin")
    return repo


@pytest.fixture
def manager(fake_repo: Path) -> WorktreeManager:
    return WorktreeManager(repo_root=fake_repo)


# ------------------------------------------------------------------
# Helper
# ------------------------------------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", "-C", str(repo)) + args,
        capture_output=True,
        check=True,
    )


# ------------------------------------------------------------------
# Tests: create
# ------------------------------------------------------------------


class TestWorktreeManagerCreate:
    """WorktreeManager.create() behaviour."""

    def test_create_fresh_success(self, manager: WorktreeManager, fake_repo: Path):
        """A worktree created with base_ref='fresh' is set up correctly."""
        info = manager.create("test-sess", base_ref="fresh")

        assert info.session_id == "test-sess"
        assert info.branch_name.startswith("lyra-session-test-sess")
        assert info.worktree_path.is_dir()
        assert (info.worktree_path / ".git").exists()

    def test_create_head_success(self, manager: WorktreeManager, fake_repo: Path):
        """A worktree created with base_ref='head' branches from current HEAD."""
        info = manager.create("test-sess-2", base_ref="head")

        assert info.session_id == "test-sess-2"
        assert info.worktree_path.is_dir()
        assert (info.worktree_path / ".git").exists()

    def test_create_duplicate_session_raises(self, manager: WorktreeManager):
        """Creating a duplicate session raises WorktreeCreateError."""
        manager.create("dup-sess")
        with pytest.raises(WorktreeCreateError, match="already has a worktree"):
            manager.create("dup-sess")

    def test_create_adds_to_internal_tracker(self, manager: WorktreeManager):
        """create() registers the session in the internal tracker."""
        assert len(manager.list_worktrees()) == 0
        manager.create("track-me")
        assert len(manager.list_worktrees()) == 1


# ------------------------------------------------------------------
# Tests: switch
# ------------------------------------------------------------------


class TestWorktreeManagerSwitch:
    """WorktreeManager.switch() behaviour."""

    def test_switch_returns_path(self, manager: WorktreeManager):
        """switch() returns the worktree path for a known session."""
        info = manager.create("sess-a")
        path = manager.switch("sess-a")
        assert path == info.worktree_path

    def test_switch_unknown_session_raises(self, manager: WorktreeManager):
        """switch() raises for an untracked session id."""
        with pytest.raises(WorktreeSwitchError, match="no tracked worktree"):
            manager.switch("does-not-exist")


# ------------------------------------------------------------------
# Tests: cleanup
# ------------------------------------------------------------------


class TestWorktreeManagerCleanup:
    """WorktreeManager.cleanup() behaviour."""

    def test_cleanup_removes_worktree_and_branch(self, manager: WorktreeManager, fake_repo: Path):
        """cleanup() deletes both the worktree and the branch."""
        info = manager.create("clean-me")
        assert info.worktree_path.is_dir()

        manager.cleanup("clean-me")

        assert not info.worktree_path.is_dir()
        assert "clean-me" not in {w.session_id for w in manager.list_worktrees()}

    def test_cleanup_unknown_session_raises(self, manager: WorktreeManager):
        """cleanup() raises for an untracked session id."""
        with pytest.raises(WorktreeCleanupError, match="no tracked worktree"):
            manager.cleanup("does-not-exist")

    def test_cleanup_dirty_without_force_raises(self, manager: WorktreeManager, fake_repo: Path):
        """cleanup() raises if the worktree is dirty and force=False."""
        info = manager.create("dirty-sess")
        # Make the worktree dirty
        dirty_file = info.worktree_path / "new_file.txt"
        dirty_file.write_text("dirty")

        with pytest.raises(WorktreeCleanupError, match="uncommitted changes"):
            manager.cleanup("dirty-sess")

    def test_cleanup_dirty_with_force_succeeds(self, manager: WorktreeManager, fake_repo: Path):
        """cleanup(force=True) removes a dirty worktree."""
        info = manager.create("force-dirty")
        dirty_file = info.worktree_path / "new_file.txt"
        dirty_file.write_text("dirty")

        manager.cleanup("force-dirty", force=True)

        assert not info.worktree_path.is_dir()
        assert "force-dirty" not in {w.session_id for w in manager.list_worktrees()}


# ------------------------------------------------------------------
# Tests: list
# ------------------------------------------------------------------


class TestWorktreeManagerList:
    """WorktreeManager.list_worktrees() and list_git_worktrees()."""

    def test_list_worktrees_empty(self, manager: WorktreeManager):
        """A fresh manager has no tracked worktrees."""
        assert manager.list_worktrees() == []

    def test_list_worktrees_after_creates(self, manager: WorktreeManager):
        """list_worktrees() reflects created sessions."""
        manager.create("a")
        manager.create("b")
        assert len(manager.list_worktrees()) == 2

    def test_list_git_worktrees_includes_main(self, manager: WorktreeManager):
        """list_git_worktrees() always includes the main worktree."""
        all_wts = manager.list_git_worktrees()
        paths = {w["path"] for w in all_wts}
        assert str(manager.repo_root) in paths
