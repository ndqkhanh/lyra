"""
WorktreeManager: git worktree isolation for parallel agent sessions.

Each session gets its own worktree and branch. Supports configurable
base-ref policies (FRESH from origin/main, HEAD from current HEAD).
"""

from __future__ import annotations

import logging
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

BaseRefPolicy = Literal["fresh", "head"]


class WorktreeError(Exception):
    """Base exception for worktree operations."""


class WorktreeCreateError(WorktreeError):
    """Raised when worktree creation fails."""


class WorktreeCleanupError(WorktreeError):
    """Raised when worktree cleanup fails."""


class WorktreeSwitchError(WorktreeError):
    """Raised when switching to a worktree fails."""


@dataclass
class WorktreeInfo:
    """Information about a tracked worktree."""

    session_id: str
    branch_name: str
    worktree_path: Path
    base_ref: str
    is_dirty: bool = False


@dataclass
class WorktreeManager:
    """Manages git worktrees for isolated agent sessions.

    Each session gets a dedicated branch and worktree directory,
    enabling parallel agent runs without interfering with each other.

    Usage::

        manager = WorktreeManager(repo_root=Path("/path/to/repo"))
        info = manager.create("session-123", base_ref="fresh")
        manager.switch("session-123")
        manager.cleanup("session-123")
    """

    repo_root: Path
    worktrees_dir: Path = field(init=False)
    _worktrees: dict[str, WorktreeInfo] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self.worktrees_dir = self.repo_root / ".claude" / "worktrees"
        self._refresh_tracked()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(
        self,
        session_id: str,
        base_ref: BaseRefPolicy = "fresh",
    ) -> WorktreeInfo:
        """Create a new worktree for *session_id*.

        Parameters
        ----------
        session_id:
            Unique identifier for the session (used as branch suffix).
        base_ref:
            * ``"fresh"`` -- branch from ``origin/main`` (default).
            * ``"head"``  -- branch from current HEAD.

        Returns
        -------
        WorktreeInfo describing the created worktree.

        Raises
        ------
        WorktreeCreateError
            If the git worktree command fails or the session already exists.
        """
        if session_id in self._worktrees:
            raise WorktreeCreateError(f"Session '{session_id}' already has a worktree")

        branch_name = _sanitize_branch(f"lyra-session-{session_id}-{uuid.uuid4().hex[:8]}")
        worktree_path = self.worktrees_dir / _sanitize_path(session_id)

        if base_ref == "fresh":
            self._git("fetch", "origin")
            self._git("branch", branch_name, "origin/main")
        else:
            self._git("branch", branch_name)

        try:
            self._git("worktree", "add", str(worktree_path), branch_name)
        except subprocess.CalledProcessError as exc:
            # Clean up the dangling branch on failure
            try:
                self._git("branch", "-D", branch_name)
            except subprocess.CalledProcessError:
                pass
            raise WorktreeCreateError(
                f"Failed to create worktree for session '{session_id}': {exc.stderr.decode().strip()}"
            ) from exc

        info = WorktreeInfo(
            session_id=session_id,
            branch_name=branch_name,
            worktree_path=worktree_path.resolve(),
            base_ref=base_ref,
        )
        self._worktrees[session_id] = info
        return info

    def switch(self, session_id: str) -> Path:
        """Switch to the worktree for *session_id*.

        Returns the worktree's absolute path.

        Raises
        ------
        WorktreeSwitchError
            If the session has no tracked worktree.
        """
        info = self._worktrees.get(session_id)
        if info is None:
            raise WorktreeSwitchError(f"Session '{session_id}' has no tracked worktree")
        return info.worktree_path

    def cleanup(self, session_id: str, force: bool = False) -> None:
        """Remove the worktree for *session_id*.

        Parameters
        ----------
        session_id:
            Session to clean up.
        force:
            If True, remove even if the worktree is dirty.
            If False, refuse removal when the worktree is dirty.

        Raises
        ------
        WorktreeCleanupError
            If the session has no tracked worktree, the worktree is dirty
            and *force* is False, or the git command fails.
        """
        info = self._worktrees.get(session_id)
        if info is None:
            raise WorktreeCleanupError(f"Session '{session_id}' has no tracked worktree")

        is_dirty = self._is_dirty(info.worktree_path)
        if is_dirty and not force:
            raise WorktreeCleanupError(
                f"Worktree for session '{session_id}' has uncommitted changes. "
                "Use force=True to remove anyway."
            )

        try:
            git_args = ["worktree", "remove"]
            if force:
                git_args.append("--force")
            git_args.append(str(info.worktree_path))
            self._git(*git_args)
            self._git("branch", "-D", info.branch_name)
        except subprocess.CalledProcessError as exc:
            raise WorktreeCleanupError(
                f"Failed to clean up session '{session_id}': {exc.stderr.decode().strip()}"
            ) from exc

        del self._worktrees[session_id]

    def list_worktrees(self) -> list[WorktreeInfo]:
        """Return a list of all tracked worktrees."""
        return list(self._worktrees.values())

    def list_git_worktrees(self) -> list[dict[str, str]]:
        """Return all git worktrees as reported by ``git worktree list``.

        This queries the actual git repository rather than the internal
        tracker.
        """
        result = self._git("worktree", "list")
        lines = result.stdout.decode().strip().splitlines()
        worktrees: list[dict[str, str]] = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 2:
                worktrees.append({"path": parts[0], "branch": parts[1]})
        return worktrees

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refresh_tracked(self) -> None:
        """Re-populate internal ``_worktrees`` from the filesystem.

        Scans the worktrees directory for existing worktrees and registers
        them by a derived session id.
        """
        if not self.worktrees_dir.is_dir():
            return
        for child in sorted(self.worktrees_dir.iterdir()):
            if child.is_dir() and (child / ".git").is_dir() if child.is_dir() else False:
                session_id = child.name
                if session_id not in self._worktrees:
                    self._worktrees[session_id] = WorktreeInfo(
                        session_id=session_id,
                        branch_name=f"lyra-session-{session_id}",
                        worktree_path=child.resolve(),
                        base_ref="fresh",
                    )

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run a git command in the repo root."""
        return subprocess.run(
            ("git",) + args,
            cwd=str(self.repo_root),
            capture_output=True,
            check=True,
        )

    def _is_dirty(self, path: Path) -> bool:
        """Check whether the worktree at *path* has uncommitted changes."""
        try:
            result = subprocess.run(
                ("git", "-C", str(path), "status", "--porcelain"),
                capture_output=True,
                check=True,
            )
            return bool(result.stdout.decode().strip())
        except subprocess.CalledProcessError:
            return True  # assume dirty on error


def _sanitize_branch(name: str) -> str:
    """Replace invalid branch characters with hyphens."""
    import re

    return re.sub(r"[^a-zA-Z0-9_\-/.]", "-", name)[:255]


def _sanitize_path(name: str) -> str:
    """Replace characters unsafe for directory names."""
    import re

    return re.sub(r"[^a-zA-Z0-9_\-.]", "_", name)[:128]
