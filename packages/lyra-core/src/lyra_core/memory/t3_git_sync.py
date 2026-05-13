"""T3 Memory Git Sync (Phase M8).

Provides git integration for T3 memory files (user.md, team.md) to enable:
  - Version control and history tracking
  - Team collaboration via git push/pull
  - Automatic sync on file changes
  - Conflict detection and resolution

Research grounding:
  - CoALA T3 procedural memory (git-synced)
  - Collaborative Memory (team sharing via git)
"""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class GitSyncConfig:
    """Configuration for T3 git sync."""

    auto_commit: bool = True
    auto_push: bool = False  # Conservative default: don't auto-push
    auto_pull: bool = True
    commit_message_template: str = "chore(memory): update T3 {file_type} memory"
    conflict_strategy: Literal["ours", "theirs", "manual"] = "manual"


@dataclass
class GitSyncResult:
    """Result of a git sync operation."""

    success: bool
    operation: str  # "pull", "commit", "push"
    message: str
    conflicts: list[str] | None = None


class T3GitSync:
    """Git sync manager for T3 memory files.

    Features:
      - Pull before reload (get team updates)
      - Auto-commit on changes (optional)
      - Auto-push after commit (optional)
      - Conflict detection and resolution
      - Graceful degradation (no-op if not a git repo)
    """

    def __init__(
        self,
        repo_root: Path,
        config: GitSyncConfig | None = None,
    ):
        """Initialize T3 git sync.

        Args:
            repo_root: Repository root directory
            config: Git sync configuration (uses defaults if None)
        """
        self.repo_root = repo_root
        self.config = config or GitSyncConfig()
        self.memory_dir = repo_root / ".lyra" / "memory"
        self._is_git_repo = self._check_git_repo()

    def _check_git_repo(self) -> bool:
        """Check if repo_root is a git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _run_git_command(
        self, args: list[str], timeout: int = 30
    ) -> subprocess.CompletedProcess:
        """Run a git command in the repo root.

        Args:
            args: Git command arguments (e.g., ["status", "--short"])
            timeout: Command timeout in seconds

        Returns:
            CompletedProcess with stdout/stderr
        """
        return subprocess.run(
            ["git"] + args,
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def pull(self) -> GitSyncResult:
        """Pull latest changes from remote.

        Returns:
            GitSyncResult with pull status and any conflicts
        """
        if not self._is_git_repo:
            return GitSyncResult(
                success=True,
                operation="pull",
                message="Not a git repo, skipping pull",
            )

        try:
            # Check if remote exists
            result = self._run_git_command(["remote", "show"])
            if not result.stdout.strip():
                return GitSyncResult(
                    success=True,
                    operation="pull",
                    message="No remote configured, skipping pull",
                )

            # Pull with rebase to avoid merge commits
            result = self._run_git_command(["pull", "--rebase"])

            if result.returncode == 0:
                return GitSyncResult(
                    success=True,
                    operation="pull",
                    message="Pulled successfully",
                )

            # Check for conflicts
            if "CONFLICT" in result.stdout or "CONFLICT" in result.stderr:
                conflicts = self._detect_conflicts()
                return GitSyncResult(
                    success=False,
                    operation="pull",
                    message="Pull failed: conflicts detected",
                    conflicts=conflicts,
                )

            return GitSyncResult(
                success=False,
                operation="pull",
                message=f"Pull failed: {result.stderr}",
            )

        except subprocess.TimeoutExpired:
            return GitSyncResult(
                success=False,
                operation="pull",
                message="Pull timed out",
            )
        except Exception as e:
            logger.error(f"Pull failed: {e}", exc_info=True)
            return GitSyncResult(
                success=False,
                operation="pull",
                message=f"Pull failed: {e}",
            )

    def _detect_conflicts(self) -> list[str]:
        """Detect conflicted files.

        Returns:
            List of file paths with conflicts
        """
        try:
            result = self._run_git_command(["diff", "--name-only", "--diff-filter=U"])
            if result.returncode == 0:
                return [f.strip() for f in result.stdout.split("\n") if f.strip()]
            return []
        except Exception:
            return []

    def commit(self, file_type: Literal["user", "team"]) -> GitSyncResult:
        """Commit changes to T3 memory file.

        Args:
            file_type: "user" or "team"

        Returns:
            GitSyncResult with commit status
        """
        if not self._is_git_repo:
            return GitSyncResult(
                success=True,
                operation="commit",
                message="Not a git repo, skipping commit",
            )

        if not self.config.auto_commit:
            return GitSyncResult(
                success=True,
                operation="commit",
                message="Auto-commit disabled, skipping",
            )

        try:
            file_path = self.memory_dir / f"{file_type}.md"
            if not file_path.exists():
                return GitSyncResult(
                    success=True,
                    operation="commit",
                    message=f"{file_type}.md does not exist, skipping commit",
                )

            # Check if file has changes
            result = self._run_git_command(["status", "--short", str(file_path)])
            if not result.stdout.strip():
                return GitSyncResult(
                    success=True,
                    operation="commit",
                    message=f"No changes to {file_type}.md, skipping commit",
                )

            # Stage the file
            result = self._run_git_command(["add", str(file_path)])
            if result.returncode != 0:
                return GitSyncResult(
                    success=False,
                    operation="commit",
                    message=f"Failed to stage {file_type}.md: {result.stderr}",
                )

            # Commit with timestamp
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            commit_msg = self.config.commit_message_template.format(
                file_type=file_type
            )
            commit_msg += f"\n\nAuto-committed at {timestamp}"

            result = self._run_git_command(["commit", "-m", commit_msg])
            if result.returncode != 0:
                return GitSyncResult(
                    success=False,
                    operation="commit",
                    message=f"Commit failed: {result.stderr}",
                )

            return GitSyncResult(
                success=True,
                operation="commit",
                message=f"Committed {file_type}.md",
            )

        except subprocess.TimeoutExpired:
            return GitSyncResult(
                success=False,
                operation="commit",
                message="Commit timed out",
            )
        except Exception as e:
            logger.error(f"Commit failed: {e}", exc_info=True)
            return GitSyncResult(
                success=False,
                operation="commit",
                message=f"Commit failed: {e}",
            )

    def push(self) -> GitSyncResult:
        """Push committed changes to remote.

        Returns:
            GitSyncResult with push status
        """
        if not self._is_git_repo:
            return GitSyncResult(
                success=True,
                operation="push",
                message="Not a git repo, skipping push",
            )

        if not self.config.auto_push:
            return GitSyncResult(
                success=True,
                operation="push",
                message="Auto-push disabled, skipping",
            )

        try:
            # Check if remote exists
            result = self._run_git_command(["remote", "show"])
            if not result.stdout.strip():
                return GitSyncResult(
                    success=True,
                    operation="push",
                    message="No remote configured, skipping push",
                )

            # Push to remote
            result = self._run_git_command(["push"])

            if result.returncode == 0:
                return GitSyncResult(
                    success=True,
                    operation="push",
                    message="Pushed successfully",
                )

            return GitSyncResult(
                success=False,
                operation="push",
                message=f"Push failed: {result.stderr}",
            )

        except subprocess.TimeoutExpired:
            return GitSyncResult(
                success=False,
                operation="push",
                message="Push timed out",
            )
        except Exception as e:
            logger.error(f"Push failed: {e}", exc_info=True)
            return GitSyncResult(
                success=False,
                operation="push",
                message=f"Push failed: {e}",
            )

    def sync_before_reload(self) -> GitSyncResult:
        """Sync before reloading T3 memory (pull from remote).

        Returns:
            GitSyncResult with sync status
        """
        if not self.config.auto_pull:
            return GitSyncResult(
                success=True,
                operation="sync_before_reload",
                message="Auto-pull disabled, skipping",
            )

        return self.pull()

    def sync_after_change(
        self, file_type: Literal["user", "team"]
    ) -> list[GitSyncResult]:
        """Sync after T3 memory file changes (commit + push).

        Args:
            file_type: "user" or "team"

        Returns:
            List of GitSyncResult for commit and push operations
        """
        results: list[GitSyncResult] = []

        # Commit changes
        commit_result = self.commit(file_type)
        results.append(commit_result)

        # Push if commit succeeded
        if commit_result.success and self.config.auto_push:
            push_result = self.push()
            results.append(push_result)

        return results


__all__ = [
    "GitSyncConfig",
    "GitSyncResult",
    "T3GitSync",
]
