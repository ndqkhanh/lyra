"""T3 Memory Git Sync Usage Examples.

This module demonstrates how to use git sync with T3 memory files.
"""
from pathlib import Path

from lyra_core.memory.schema import Fragment
from lyra_core.memory.t3_git_sync import GitSyncConfig, T3GitSync
from lyra_core.memory.t3_watcher import start_t3_watcher


def example_basic_git_sync():
    """Example: Basic git sync with default configuration."""
    repo_root = Path("/path/to/repo")

    # Create git sync with defaults (auto-commit enabled, auto-push disabled)
    git_sync = T3GitSync(repo_root)

    # Manual sync operations
    pull_result = git_sync.pull()
    if pull_result.success:
        print("Pulled successfully")

    commit_result = git_sync.commit("user")
    if commit_result.success:
        print("Committed user.md")

    push_result = git_sync.push()
    if push_result.success:
        print("Pushed to remote")


def example_custom_config():
    """Example: Custom git sync configuration."""
    repo_root = Path("/path/to/repo")

    # Custom configuration
    config = GitSyncConfig(
        auto_commit=True,
        auto_push=True,  # Enable auto-push for team collaboration
        auto_pull=True,
        commit_message_template="docs(memory): update {file_type} preferences",
        conflict_strategy="manual",
    )

    git_sync = T3GitSync(repo_root, config)

    # Sync after change (commits and pushes if enabled)
    results = git_sync.sync_after_change("user")
    for result in results:
        print(f"{result.operation}: {result.message}")


def example_watcher_with_git_sync():
    """Example: Filesystem watcher with git sync integration."""
    repo_root = Path("/path/to/repo")

    def on_reload(fragments: list[Fragment]) -> None:
        """Callback invoked after T3 memory reload."""
        print(f"Reloaded {len(fragments)} fragments")
        for fragment in fragments:
            print(f"  - {fragment.type.value}: {fragment.content[:50]}...")

    # Create git sync
    config = GitSyncConfig(
        auto_commit=True,
        auto_push=False,  # Conservative: don't auto-push
    )
    git_sync = T3GitSync(repo_root, config)

    # Start watcher with git sync
    watcher = start_t3_watcher(
        repo_root,
        on_reload,
        debounce_seconds=0.5,
        git_sync=git_sync,
    )

    if watcher:
        print("T3 memory watcher started with git sync")
        # Watcher will:
        # 1. Pull before reload (get team updates)
        # 2. Reload T3 memory from disk
        # 3. Commit changes after reload (if auto_commit=True)
        # 4. Push changes (if auto_push=True)

        # Keep watcher running...
        # watcher.stop()  # Call when done


def example_team_collaboration():
    """Example: Team collaboration workflow with git sync."""
    repo_root = Path("/path/to/repo")

    # Team member A: Enable auto-push for sharing
    config_a = GitSyncConfig(
        auto_commit=True,
        auto_push=True,  # Share changes with team
        auto_pull=True,  # Get team updates
    )
    git_sync_a = T3GitSync(repo_root, config_a)

    # Team member B: Pull-only mode (read team updates, don't push)
    config_b = GitSyncConfig(
        auto_commit=False,  # Don't commit local changes
        auto_push=False,
        auto_pull=True,  # Get team updates
    )
    git_sync_b = T3GitSync(repo_root, config_b)

    # Both can use the same watcher setup
    def on_reload(fragments: list[Fragment]) -> None:
        print(f"Reloaded {len(fragments)} fragments")

    watcher_a = start_t3_watcher(repo_root, on_reload, git_sync=git_sync_a)
    # watcher_b = start_t3_watcher(repo_root, on_reload, git_sync=git_sync_b)


def example_conflict_handling():
    """Example: Handling git conflicts."""
    repo_root = Path("/path/to/repo")

    git_sync = T3GitSync(repo_root)

    # Pull may return conflicts
    pull_result = git_sync.pull()
    if not pull_result.success and pull_result.conflicts:
        print("Conflicts detected:")
        for conflict_file in pull_result.conflicts:
            print(f"  - {conflict_file}")

        # Manual resolution required
        # 1. Resolve conflicts in files
        # 2. Stage resolved files: git add <file>
        # 3. Continue rebase: git rebase --continue
        # 4. Or abort: git rebase --abort


def example_disable_git_sync():
    """Example: Disable git sync (backward compatibility)."""
    repo_root = Path("/path/to/repo")

    def on_reload(fragments: list[Fragment]) -> None:
        print(f"Reloaded {len(fragments)} fragments")

    # Start watcher without git sync (git_sync=None is default)
    watcher = start_t3_watcher(repo_root, on_reload)

    if watcher:
        print("T3 memory watcher started without git sync")
        # Watcher will only reload from disk, no git operations


if __name__ == "__main__":
    print("T3 Memory Git Sync Usage Examples")
    print("=" * 50)
    print("\nSee function docstrings for usage patterns:")
    print("  - example_basic_git_sync()")
    print("  - example_custom_config()")
    print("  - example_watcher_with_git_sync()")
    print("  - example_team_collaboration()")
    print("  - example_conflict_handling()")
    print("  - example_disable_git_sync()")
