"""
WorktreeManager: git worktree isolation for parallel agent sessions.

Each session gets its own worktree and branch. Supports configurable
base-ref policies (FRESH from origin/main, HEAD from current HEAD).

For non-git repositories a copy-on-write fallback (:meth:`create_fallback`)
provides directory-level isolation using symlinks for space efficiency
and copies for files that change.

Session binding (:meth:`bind_session` / :meth:`unbind_session`) tracks
which session id is associated with which worktree, allowing ``auto-switch``
semantics.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

import structlog

from lyra.worktree.lyrainclude import LyraInclude

logger = structlog.get_logger(__name__)

BaseRefPolicy = Literal["fresh", "head"]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class WorktreeError(Exception):
    """Base exception for worktree operations."""


class WorktreeCreateError(WorktreeError):
    """Raised when worktree creation fails."""


class WorktreeCleanupError(WorktreeError):
    """Raised when worktree cleanup fails."""


class WorktreeSwitchError(WorktreeError):
    """Raised when switching to a worktree fails."""


class WorktreeFallbackError(WorktreeError):
    """Raised when the non-git fallback worktree mechanism fails."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class WorktreeInfo:
    """Information about a tracked worktree."""

    session_id: str
    branch_name: str
    worktree_path: Path
    base_ref: str
    is_dirty: bool = False


@dataclass
class SessionBindInfo:
    """Information about a session-bound worktree (git or fallback)."""

    session_id: str
    worktree_path: Path
    is_fallback: bool = False
    base_dir: Optional[Path] = None


# ---------------------------------------------------------------------------
# WorktreeManager
# ---------------------------------------------------------------------------


@dataclass
class WorktreeManager:
    """Manages git worktrees for isolated agent sessions.

    Each session gets a dedicated branch and worktree directory,
    enabling parallel agent runs without interfering with each other.

    For non-git repos, :meth:`create_fallback` provides directory-level
    isolation with copy-on-write semantics.

    Usage::

        manager = WorktreeManager(repo_root=Path("/path/to/repo"))
        info = manager.create("session-123", base_ref="fresh")
        manager.switch("session-123")
        manager.cleanup("session-123")
    """

    repo_root: Path
    worktrees_dir: Path = field(init=False)
    _worktrees: dict[str, WorktreeInfo] = field(default_factory=dict, init=False, repr=False)
    _session_binds: dict[str, SessionBindInfo] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self.worktrees_dir = self.repo_root / ".claude" / "worktrees"
        self._refresh_tracked()

    # ------------------------------------------------------------------
    # Git check
    # ------------------------------------------------------------------

    def is_git_repo(self) -> bool:
        """Check whether ``repo_root`` is a git repository.

        Returns ``True`` if the directory contains a valid ``.git`` entry
        and ``git rev-parse`` succeeds.
        """
        try:
            result = subprocess.run(
                ("git", "-C", str(self.repo_root), "rev-parse", "--git-dir"),
                capture_output=True,
                check=True,
            )
            return bool(result.stdout.decode().strip())
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    # ------------------------------------------------------------------
    # Public API -- git worktrees
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

        if not self.is_git_repo():
            raise WorktreeCreateError(
                f"Cannot create git worktree: '{self.repo_root}' is not a git repository"
            )

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
        self._session_binds.pop(session_id, None)

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
    # Public API -- non-git fallback
    # ------------------------------------------------------------------

    def create_fallback(self, session_id: str, base_dir: Optional[Path] = None) -> SessionBindInfo:
        """Create a copy-on-write worktree for a non-git repository.

        Creates a snapshot of ``repo_root`` (or *base_dir*) into a dedicated
        directory under the worktrees tree. Files are symlinked by default
        for space efficiency; when a session modifies a file, the link is
        replaced with an independent copy (copy-on-write semantics provided
        by the session, not enforced here).

        If a ``.lyrainclude`` file exists, only matching files are brought
        into the snapshot (the same filter used for git worktrees).

        Parameters
        ----------
        session_id:
            Unique identifier for the session.
        base_dir:
            Directory to snapshot. Defaults to ``repo_root``.

        Returns
        -------
        SessionBindInfo describing the isolated directory.

        Raises
        ------
        WorktreeFallbackError
            If creation fails.
        """
        if session_id in self._session_binds:
            raise WorktreeFallbackError(f"Session '{session_id}' already has a bound worktree")

        source = base_dir.resolve() if base_dir else self.repo_root.resolve()
        if not source.is_dir():
            raise WorktreeFallbackError(f"Base directory does not exist: {source}")

        worktree_path = self.worktrees_dir / _sanitize_path(session_id)
        try:
            worktree_path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise WorktreeFallbackError(
                f"Failed to create fallback directory for session '{session_id}': {exc}"
            ) from exc

        # Load lyrainclude to decide what to include
        inc = LyraInclude.load(self.repo_root)

        # Populate the fallback directory
        self._populate_fallback(source, worktree_path, inc)

        bind_info = SessionBindInfo(
            session_id=session_id,
            worktree_path=worktree_path.resolve(),
            is_fallback=True,
            base_dir=source,
        )
        self._session_binds[session_id] = bind_info

        logger.info(
            "created fallback worktree for session %s at %s",
            session_id,
            worktree_path,
        )
        return bind_info

    def cleanup_fallback(self, session_id: str, force: bool = False) -> None:
        """Remove a fallback worktree for *session_id*.

        Parameters
        ----------
        session_id:
            Session to clean up.
        force:
            If True, remove even if dirty (no-op for fallback; always
            removed). Kept for API compatibility with :meth:`cleanup`.

        Raises
        ------
        WorktreeFallbackError
            If the session has no fallback worktree.
        """
        bind = self._session_binds.get(session_id)
        if bind is None or not bind.is_fallback:
            raise WorktreeFallbackError(f"Session '{session_id}' has no fallback worktree")

        try:
            shutil.rmtree(bind.worktree_path)
        except OSError as exc:
            raise WorktreeFallbackError(
                f"Failed to remove fallback worktree for session '{session_id}': {exc}"
            ) from exc

        del self._session_binds[session_id]
        logger.info("removed fallback worktree for session %s", session_id)

    def list_fallbacks(self) -> list[SessionBindInfo]:
        """Return all active fallback worktrees."""
        return [b for b in self._session_binds.values() if b.is_fallback]

    # ------------------------------------------------------------------
    # Public API -- session binding
    # ------------------------------------------------------------------

    def bind_session(self, session_id: str, worktree_path: Path) -> SessionBindInfo:
        """Bind a *session_id* to an arbitrary worktree path.

        This is useful for auto-binding after a worktree has been created
        externally, allowing the manager to track it regardless of whether
        it is a git worktree or a fallback directory.

        Parameters
        ----------
        session_id:
            Session identifier to bind.
        worktree_path:
            Absolute path to the worktree directory.

        Returns
        -------
        SessionBindInfo for the bound session.

        Raises
        ------
        WorktreeError
            If the session is already bound or the path does not exist.
        """
        if session_id in self._session_binds:
            raise WorktreeError(f"Session '{session_id}' is already bound")

        resolved = worktree_path.resolve()
        if not resolved.is_dir():
            raise WorktreeError(f"Worktree path does not exist: {resolved}")

        is_git = (resolved / ".git").exists()
        bind_info = SessionBindInfo(
            session_id=session_id,
            worktree_path=resolved,
            is_fallback=not is_git,
            base_dir=self.repo_root if not is_git else None,
        )
        self._session_binds[session_id] = bind_info

        # Also track in the git worktree dict if applicable
        if is_git and session_id not in self._worktrees:
            self._worktrees[session_id] = WorktreeInfo(
                session_id=session_id,
                branch_name=f"lyra-session-{session_id}",
                worktree_path=resolved,
                base_ref="fresh",
            )

        logger.info("bound session %s to worktree %s", session_id, resolved)
        return bind_info

    def unbind_session(self, session_id: str) -> Optional[SessionBindInfo]:
        """Unbind a *session_id* without removing its worktree.

        Unlike :meth:`cleanup` or :meth:`cleanup_fallback`, this only
        removes the internal tracking. The filesystem is not touched.

        Parameters
        ----------
        session_id:
            Session identifier to unbind.

        Returns
        -------
        The removed ``SessionBindInfo``, or ``None`` if the session was not
        bound.
        """
        bind = self._session_binds.pop(session_id, None)
        self._worktrees.pop(session_id, None)
        if bind is not None:
            logger.info("unbound session %s", session_id)
        return bind

    def get_bind(self, session_id: str) -> Optional[SessionBindInfo]:
        """Look up the bind info for *session_id*.

        Returns ``None`` if the session is not bound.
        """
        return self._session_binds.get(session_id)

    def list_binds(self) -> list[SessionBindInfo]:
        """Return all session-to-worktree bindings."""
        return list(self._session_binds.values())

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

    def _populate_fallback(
        self,
        source: Path,
        dest: Path,
        inc: LyraInclude,
    ) -> None:
        """Populate *dest* as a snapshot of *source* using lyrainclude filtering.

        When a ``.lyrainclude`` is present, only matching files are
        snapshot.  Without it, all files are symlinked (respecting a basic
        skip list for dot-directories).
        """
        skip_dirs: set[str] = {".git", "__pycache__", ".claude", ".lyra"}

        for dirpath, dirnames, filenames in os.walk(source):
            dirpath_p = Path(dirpath)
            rel_dir = dirpath_p.relative_to(source)

            # Skip directories we never want to duplicate
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]

            for filename in filenames:
                src_file = dirpath_p / filename
                rel_path = rel_dir / filename

                # When lyrainclude is active, skip non-matching files
                if inc.include_spec is not None and not inc.should_include(rel_path):
                    continue

                dest_file = dest / rel_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)

                try:
                    os.symlink(src_file, dest_file)
                except FileExistsError:
                    # If the file already exists (e.g. from a parent run), skip
                    pass
                except OSError:
                    # Symlink may fail across filesystems; fall back to copy
                    shutil.copy2(src_file, dest_file)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _sanitize_branch(name: str) -> str:
    """Replace invalid branch characters with hyphens."""
    import re

    return re.sub(r"[^a-zA-Z0-9_\-/.]", "-", name)[:255]


def _sanitize_path(name: str) -> str:
    """Replace characters unsafe for directory names."""
    import re

    return re.sub(r"[^a-zA-Z0-9_\-.]", "_", name)[:128]
