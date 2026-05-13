"""Tests for T3 Memory Git Sync (Phase M8)."""
from __future__ import annotations

import subprocess
from pathlib import Path
from textwrap import dedent

import pytest

from lyra_core.memory.t3_git_sync import GitSyncConfig, GitSyncResult, T3GitSync


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

    return repo


@pytest.fixture
def non_git_repo(tmp_path: Path) -> Path:
    """Create a temporary non-git directory."""
    repo = tmp_path / "non_git_repo"
    repo.mkdir()

    # Create .lyra/memory directory
    memory_dir = repo / ".lyra" / "memory"
    memory_dir.mkdir(parents=True)

    return repo


def test_git_sync_detects_git_repo(git_repo: Path):
    """Test that git sync correctly detects a git repository."""
    sync = T3GitSync(git_repo)
    assert sync._is_git_repo is True


def test_git_sync_detects_non_git_repo(non_git_repo: Path):
    """Test that git sync correctly detects a non-git directory."""
    sync = T3GitSync(non_git_repo)
    assert sync._is_git_repo is False


def test_git_sync_pull_no_remote(git_repo: Path):
    """Test pull when no remote is configured."""
    sync = T3GitSync(git_repo)
    result = sync.pull()

    assert result.success is True
    assert result.operation == "pull"
    assert "No remote" in result.message


def test_git_sync_commit_no_changes(git_repo: Path):
    """Test commit when there are no changes."""
    # Create and commit initial user.md
    user_file = git_repo / ".lyra" / "memory" / "user.md"
    user_file.write_text("# Initial content")

    subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    # Try to commit again with no changes
    config = GitSyncConfig(auto_commit=True)
    sync = T3GitSync(git_repo, config)
    result = sync.commit("user")

    assert result.success is True
    assert "No changes" in result.message


def test_git_sync_commit_with_changes(git_repo: Path):
    """Test commit when there are changes."""
    # Create initial commit
    user_file = git_repo / ".lyra" / "memory" / "user.md"
    user_file.write_text("# Initial content")

    subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    # Modify user.md
    user_file.write_text("# Updated content")

    # Commit changes
    config = GitSyncConfig(auto_commit=True)
    sync = T3GitSync(git_repo, config)
    result = sync.commit("user")

    assert result.success is True
    assert result.operation == "commit"
    assert "Committed user.md" in result.message

    # Verify commit was created
    log_result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=git_repo,
        capture_output=True,
        text=True,
    )
    assert "update T3 user memory" in log_result.stdout


def test_git_sync_commit_disabled(git_repo: Path):
    """Test that commit is skipped when auto_commit is disabled."""
    user_file = git_repo / ".lyra" / "memory" / "user.md"
    user_file.write_text("# Content")

    config = GitSyncConfig(auto_commit=False)
    sync = T3GitSync(git_repo, config)
    result = sync.commit("user")

    assert result.success is True
    assert "disabled" in result.message


def test_git_sync_push_no_remote(git_repo: Path):
    """Test push when no remote is configured."""
    config = GitSyncConfig(auto_push=True)
    sync = T3GitSync(git_repo, config)
    result = sync.push()

    assert result.success is True
    assert "No remote" in result.message


def test_git_sync_push_disabled(git_repo: Path):
    """Test that push is skipped when auto_push is disabled."""
    config = GitSyncConfig(auto_push=False)
    sync = T3GitSync(git_repo, config)
    result = sync.push()

    assert result.success is True
    assert "disabled" in result.message


def test_git_sync_non_git_repo_operations(non_git_repo: Path):
    """Test that all operations gracefully handle non-git repos."""
    sync = T3GitSync(non_git_repo)

    # Pull
    pull_result = sync.pull()
    assert pull_result.success is True
    assert "Not a git repo" in pull_result.message

    # Commit
    commit_result = sync.commit("user")
    assert commit_result.success is True
    assert "Not a git repo" in commit_result.message

    # Push
    push_result = sync.push()
    assert push_result.success is True
    assert "Not a git repo" in push_result.message


def test_git_sync_before_reload(git_repo: Path):
    """Test sync_before_reload pulls from remote."""
    config = GitSyncConfig(auto_pull=True)
    sync = T3GitSync(git_repo, config)
    result = sync.sync_before_reload()

    assert result.success is True
    assert result.operation == "pull"


def test_git_sync_before_reload_disabled(git_repo: Path):
    """Test sync_before_reload when auto_pull is disabled."""
    config = GitSyncConfig(auto_pull=False)
    sync = T3GitSync(git_repo, config)
    result = sync.sync_before_reload()

    assert result.success is True
    assert "disabled" in result.message


def test_git_sync_after_change(git_repo: Path):
    """Test sync_after_change commits and optionally pushes."""
    # Create initial commit
    user_file = git_repo / ".lyra" / "memory" / "user.md"
    user_file.write_text("# Initial")

    subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    # Modify file
    user_file.write_text("# Updated")

    # Sync with auto_commit=True, auto_push=False
    config = GitSyncConfig(auto_commit=True, auto_push=False)
    sync = T3GitSync(git_repo, config)
    results = sync.sync_after_change("user")

    # Should have 1 result (commit only, no push)
    assert len(results) == 1
    assert results[0].operation == "commit"
    assert results[0].success is True


def test_git_sync_after_change_with_push(git_repo: Path):
    """Test sync_after_change with auto_push enabled."""
    # Create initial commit
    user_file = git_repo / ".lyra" / "memory" / "user.md"
    user_file.write_text("# Initial")

    subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    # Modify file
    user_file.write_text("# Updated")

    # Sync with auto_commit=True, auto_push=True
    config = GitSyncConfig(auto_commit=True, auto_push=True)
    sync = T3GitSync(git_repo, config)
    results = sync.sync_after_change("user")

    # Should have 2 results (commit + push)
    assert len(results) == 2
    assert results[0].operation == "commit"
    assert results[0].success is True
    assert results[1].operation == "push"
    # Push will fail (no remote), but should be attempted
    assert results[1].success is True  # Success because no remote is OK


def test_git_sync_custom_commit_message(git_repo: Path):
    """Test custom commit message template."""
    # Create initial commit
    user_file = git_repo / ".lyra" / "memory" / "user.md"
    user_file.write_text("# Initial")

    subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    # Modify file
    user_file.write_text("# Updated")

    # Sync with custom message
    config = GitSyncConfig(
        auto_commit=True,
        commit_message_template="feat(memory): update {file_type} preferences",
    )
    sync = T3GitSync(git_repo, config)
    result = sync.commit("user")

    assert result.success is True

    # Verify custom message
    log_result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=git_repo,
        capture_output=True,
        text=True,
    )
    assert "update user preferences" in log_result.stdout


def test_git_sync_team_file(git_repo: Path):
    """Test git sync with team.md file."""
    # Create initial commit
    team_file = git_repo / ".lyra" / "memory" / "team.md"
    team_file.write_text("# Team rules")

    subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    # Modify team.md
    team_file.write_text("# Updated team rules")

    # Commit changes
    config = GitSyncConfig(auto_commit=True)
    sync = T3GitSync(git_repo, config)
    result = sync.commit("team")

    assert result.success is True
    assert "Committed team.md" in result.message

    # Verify commit message mentions "team"
    log_result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=git_repo,
        capture_output=True,
        text=True,
    )
    assert "team" in log_result.stdout.lower()
