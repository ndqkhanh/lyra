"""Integration tests for T3 Watcher with Git Sync (Phase M8)."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path
from textwrap import dedent

import pytest

from lyra_core.memory.schema import Fragment
from lyra_core.memory.t3_git_sync import GitSyncConfig, T3GitSync
from lyra_core.memory.t3_watcher import WATCHDOG_AVAILABLE, start_t3_watcher


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository."""
    repo = tmp_path / "test_repo"
    repo.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create .lyra/memory directory
    memory_dir = repo / ".lyra" / "memory"
    memory_dir.mkdir(parents=True)

    # Create initial user.md
    user_file = memory_dir / "user.md"
    user_file.write_text("# Initial content")

    # Initial commit
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    return repo


@pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not installed")
def test_watcher_with_git_sync_auto_commit(git_repo: Path):
    """Test watcher with git sync auto-commit enabled."""
    reload_count = 0
    last_fragments: list[Fragment] = []

    def on_reload(fragments: list[Fragment]) -> None:
        nonlocal reload_count, last_fragments
        reload_count += 1
        last_fragments = fragments

    # Create git sync with auto-commit enabled
    config = GitSyncConfig(auto_commit=True, auto_push=False)
    git_sync = T3GitSync(git_repo, config)

    # Start watcher with git sync
    watcher = start_t3_watcher(git_repo, on_reload, debounce_seconds=0.1, git_sync=git_sync)
    assert watcher is not None

    try:
        # Modify user.md
        user_file = git_repo / ".lyra" / "memory" / "user.md"
        user_file.write_text(
            dedent("""
            # Preferences
            I prefer pytest over unittest.

            # Decisions

            ## Use TypeScript
            **Rationale:** Type safety reduces runtime errors.
            **Conclusion:** Use TypeScript for all new services.
        """).strip()
        )

        # Wait for debounce + reload + git commit
        time.sleep(0.5)

        # Should have triggered reload
        assert reload_count >= 1
        assert len(last_fragments) >= 1

        # Verify git commit was created
        log_result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert "update T3 user memory" in log_result.stdout

    finally:
        watcher.stop()


@pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not installed")
def test_watcher_with_git_sync_disabled(git_repo: Path):
    """Test watcher with git sync disabled."""
    reload_count = 0

    def on_reload(fragments: list[Fragment]) -> None:
        nonlocal reload_count
        reload_count += 1

    # Create git sync with auto-commit disabled
    config = GitSyncConfig(auto_commit=False)
    git_sync = T3GitSync(git_repo, config)

    # Start watcher with git sync
    watcher = start_t3_watcher(git_repo, on_reload, debounce_seconds=0.1, git_sync=git_sync)
    assert watcher is not None

    try:
        # Get initial commit count
        log_result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        initial_commit_count = len(log_result.stdout.strip().split("\n"))

        # Modify user.md
        user_file = git_repo / ".lyra" / "memory" / "user.md"
        user_file.write_text("# Updated content")

        # Wait for debounce + reload
        time.sleep(0.5)

        # Should have triggered reload
        assert reload_count >= 1

        # Verify no new commit was created (auto-commit disabled)
        log_result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        final_commit_count = len(log_result.stdout.strip().split("\n"))
        assert final_commit_count == initial_commit_count

    finally:
        watcher.stop()


@pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not installed")
def test_watcher_without_git_sync(git_repo: Path):
    """Test watcher without git sync (backward compatibility)."""
    reload_count = 0

    def on_reload(fragments: list[Fragment]) -> None:
        nonlocal reload_count
        reload_count += 1

    # Start watcher without git sync
    watcher = start_t3_watcher(git_repo, on_reload, debounce_seconds=0.1)
    assert watcher is not None

    try:
        # Modify user.md
        user_file = git_repo / ".lyra" / "memory" / "user.md"
        user_file.write_text("# Updated content")

        # Wait for debounce + reload
        time.sleep(0.5)

        # Should have triggered reload
        assert reload_count >= 1

    finally:
        watcher.stop()


@pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not installed")
def test_watcher_git_sync_team_file(git_repo: Path):
    """Test watcher with git sync for team.md file."""
    reload_count = 0

    def on_reload(fragments: list[Fragment]) -> None:
        nonlocal reload_count
        reload_count += 1

    # Create team.md
    team_file = git_repo / ".lyra" / "memory" / "team.md"
    team_file.write_text("# Team rules")

    # Commit initial team.md
    subprocess.run(
        ["git", "add", str(team_file)], cwd=git_repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Add team.md"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    # Create git sync with auto-commit enabled
    config = GitSyncConfig(auto_commit=True, auto_push=False)
    git_sync = T3GitSync(git_repo, config)

    # Start watcher with git sync
    watcher = start_t3_watcher(git_repo, on_reload, debounce_seconds=0.1, git_sync=git_sync)
    assert watcher is not None

    try:
        # Modify team.md
        team_file.write_text("# Updated team rules")

        # Wait for debounce + reload + git commit
        time.sleep(0.5)

        # Should have triggered reload
        assert reload_count >= 1

        # Verify git commit was created with "team" in message
        log_result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        assert "team" in log_result.stdout.lower()

    finally:
        watcher.stop()
