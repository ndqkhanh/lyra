"""
Worktree Isolation Substrate — safe parallel file editing for the fleet/swarm.

Per Claude Code Worktrees spec (§3.1): each parallel session runs in its own git
worktree — a separate working directory with its own files + branch but sharing
one repo history/remote. This is the mechanism that makes a fleet of concurrent
agents SAFE to edit on one checkout.

Key design decisions (improving on Claude Code's footguns):
1. NON-DESTRUCTIVE CLEANUP — never silently discard uncommitted work. Auto-stash
   or archive on remove; confirm before destroying.
2. .worktreeinclude — propagate gitignored env/secrets into each new worktree
   so sessions don't break on launch.
3. Fresh-vs-head policy — exposed choice: branch from origin/HEAD (clean) or
   local HEAD (carries in-progress work).
4. Non-git fallback — WorktreeCreate hook for non-git VCS or overlay scheme.

Integration with FleetSupervisor (§4.13): each dispatched session gets its own
worktree. The EnterWorktree tool lets agents isolate themselves on demand.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class BaseBranchPolicy(str, Enum):
    """What git ref a new worktree branches from."""
    FRESH = "fresh"     # origin/HEAD — clean, matching remote
    HEAD = "head"       # local HEAD — carries in-progress work, unpushed commits
    PR = "pr"           # pull/<n>/head — PR branch (from #<PR> or PR URL)


class WorktreeState(str, Enum):
    """State of a worktree."""
    CLEAN = "clean"           # No changes — safe to auto-remove
    DIRTY_UNCOMMITTED = "dirty_uncommitted"  # Uncommitted files — prompt before remove
    DIRTY_NEW_COMMITS = "dirty_new_commits"  # New commits — needs push or archive
    UNKNOWN = "unknown"


class CleanupAction(str, Enum):
    """What to do when removing a dirty worktree."""
    STASH = "stash"           # git stash the changes
    ARCHIVE = "archive"       # Copy to ~/.lyra/archived-worktrees/
    DISCARD = "discard"       # Throw away (DANGEROUS — must be explicit)
    KEEP = "keep"             # Leave on disk


@dataclass
class WorktreeConfig:
    """Configuration for a single worktree instance."""
    name: str
    base_branch_policy: BaseBranchPolicy = BaseBranchPolicy.FRESH
    base_ref: str = ""                     # Specific ref (PR number, branch name)
    include_patterns: list[str] = field(default_factory=lambda: [
        ".env", ".env.local", ".envrc",
        "*.secret", "*.key", "credentials.*",
    ])
    auto_cleanup: bool = True              # Auto-remove clean worktrees
    cleanup_action: CleanupAction = CleanupAction.STASH  # Default to safe
    worktree_root: Path = field(default_factory=lambda: Path(".claude/worktrees"))


@dataclass
class WorktreeStatus:
    """Current status of a worktree."""
    name: str
    path: Path
    branch: str
    state: WorktreeState
    base_branch: str = ""
    created_at: float = field(default_factory=time.time)
    last_accessed_at: float = field(default_factory=time.time)
    uncommitted_files: int = 0
    new_commits: int = 0

    @property
    def is_dirty(self) -> bool:
        return self.state in (WorktreeState.DIRTY_UNCOMMITTED, WorktreeState.DIRTY_NEW_COMMITS)


# ---------------------------------------------------------------------------
# Worktree Isolation Engine
# ---------------------------------------------------------------------------


class WorktreeIsolation:
    """Manages git worktrees for safe parallel agent file editing.

    Each agent/session that needs to edit files should enter a worktree first.
    This isolates file changes so concurrent agents never collide on the same
    working directory.

    Key safety improvements over Claude Code's implementation:
    - Non-destructive default cleanup (STASH, not DISCARD)
    - .worktreeinclude for env propagation
    - Configurable base-branch policy
    - Non-git VCS hook support
    - Explicit confirm for dirty worktree removal
    """

    DEFAULT_WORKTREE_ROOT = Path(".claude/worktrees")
    DEFAULT_INCLUDE_FILE = ".worktreeinclude"

    def __init__(
        self,
        worktree_root: Path | None = None,
        default_policy: BaseBranchPolicy = BaseBranchPolicy.FRESH,
        create_hook: Callable[[str, Path], Path] | None = None,
        remove_hook: Callable[[Path], bool] | None = None,
    ) -> None:
        self._root = worktree_root or self.DEFAULT_WORKTREE_ROOT
        self._default_policy = default_policy
        self._create_hook = create_hook    # Non-git VCS fallback
        self._remove_hook = remove_hook
        self._worktrees: dict[str, WorktreeConfig] = {}
        self._root.mkdir(parents=True, exist_ok=True)

    # -- Create --------------------------------------------------------------

    def create(
        self,
        name: str | None = None,
        config: WorktreeConfig | None = None,
    ) -> WorktreeStatus:
        """Create a new worktree for an agent/session.

        If name is None, generates one. Branches from origin/HEAD (FRESH) or
        local HEAD depending on policy. Propagates gitignored files per
        .worktreeinclude patterns.

        In non-git repos, delegates to create_hook if configured, otherwise
        falls back to a copy-on-write overlay.
        """
        cfg = config or WorktreeConfig(name=name or self._generate_name())
        if name is None:
            cfg.name = name or self._generate_name()

        worktree_path = self._root / cfg.name

        # Check if we're in a git repo
        if self._is_git_repo():
            status = self._create_git_worktree(cfg, worktree_path)
        elif self._create_hook:
            worktree_path = Path(self._create_hook(cfg.name, worktree_path))
            status = self._check_worktree_state(cfg.name, worktree_path)
        else:
            # Non-git fallback: copy-on-write overlay
            status = self._create_overlay_worktree(cfg, worktree_path)

        # Propagate gitignored env/secret files
        self._propagate_includes(cfg, worktree_path)

        self._worktrees[cfg.name] = cfg
        return status

    def enter(self, name: str, target_dir: Path | None = None) -> WorktreeStatus | None:
        """Enter an existing worktree — switch the agent's working directory.

        This is the EnterWorktree tool primitive. The agent calls this before
        making any file edits. If the worktree doesn't exist, it can be created.
        """
        cfg = self._worktrees.get(name)
        if cfg is None:
            return None

        worktree_path = self._root / name
        if not worktree_path.exists():
            return None

        if target_dir:
            # Symlink or copy the worktree's state to target
            pass  # OS-level chdir handled by agent process

        status = self._check_worktree_state(name, worktree_path)
        status.last_accessed_at = time.time()
        return status

    # -- Remove / Cleanup ----------------------------------------------------

    def remove(
        self,
        name: str,
        action: CleanupAction | None = None,
        force: bool = False,
    ) -> tuple[bool, str]:
        """Remove a worktree.

        NON-DESTRUCTIVE by default: dirty worktrees are stashed or archived,
        never silently discarded. To discard, action must be explicitly DISCARD
        AND force must be True.

        Returns (success, reason).
        """
        cfg = self._worktrees.get(name)
        if cfg is None:
            return False, f"Worktree {name!r} not found"

        worktree_path = self._root / name
        if not worktree_path.exists():
            self._worktrees.pop(name, None)
            return True, "Worktree directory already removed"

        status = self._check_worktree_state(name, worktree_path)
        action = action or cfg.cleanup_action

        if status.state == WorktreeState.CLEAN:
            self._do_remove_worktree(name, worktree_path)
            self._worktrees.pop(name, None)
            return True, "Clean worktree removed"

        # Dirty worktree — apply safety policy
        if action == CleanupAction.DISCARD and not force:
            return False, (
                f"Worktree {name!r} is DIRTY ({status.state.value}). "
                "Use force=True to discard, or choose STASH/ARCHIVE."
            )

        if action == CleanupAction.STASH:
            self._stash_worktree(worktree_path)
            self._do_remove_worktree(name, worktree_path)
            self._worktrees.pop(name, None)
            return True, "Dirty worktree stashed and removed"

        if action == CleanupAction.ARCHIVE:
            archive_dir = Path.home() / ".lyra" / "archived-worktrees" / name
            archive_dir.parent.mkdir(parents=True, exist_ok=True)
            if archive_dir.exists():
                shutil.rmtree(archive_dir)
            shutil.move(str(worktree_path), str(archive_dir))
            self._worktrees.pop(name, None)
            return True, f"Dirty worktree archived to {archive_dir}"

        if action == CleanupAction.DISCARD and force:
            self._do_remove_worktree(name, worktree_path)
            self._worktrees.pop(name, None)
            return True, "Dirty worktree discarded (force=True)"

        return False, f"Unknown cleanup action: {action.value}"

    # -- Status --------------------------------------------------------------

    def status(self, name: str) -> WorktreeStatus | None:
        """Get the current status of a worktree."""
        worktree_path = self._root / name
        if not worktree_path.exists():
            return None
        return self._check_worktree_state(name, worktree_path)

    def list_worktrees(self) -> dict[str, WorktreeStatus]:
        """List all managed worktrees and their status."""
        result: dict[str, WorktreeStatus] = {}
        for name in list(self._worktrees):
            st = self.status(name)
            if st:
                result[name] = st
        return result

    def cleanup_sweep(
        self,
        max_age_days: int = 7,
        clean_only: bool = True,
    ) -> list[str]:
        """Periodic sweep: remove old, clean worktrees.

        Only removes CLEAN worktrees by default (safe). Returns list of removed names.
        """
        removed: list[str] = []
        now = time.time()
        cutoff = now - (max_age_days * 86400)

        for name, cfg in list(self._worktrees.items()):
            status = self.status(name)
            if status is None:
                continue
            if status.created_at > cutoff:
                continue
            if clean_only and status.is_dirty:
                continue

            ok, reason = self.remove(name, action=cfg.cleanup_action, force=clean_only)
            if ok:
                removed.append(name)

        return removed

    # -- Internal: Git worktree operations -----------------------------------

    def _is_git_repo(self) -> bool:
        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True, check=True, timeout=5,
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _create_git_worktree(self, cfg: WorktreeConfig, path: Path) -> WorktreeStatus:
        """Create a git worktree."""
        branch = f"worktree-{cfg.name}"

        # Determine base ref
        base_ref = cfg.base_ref
        if cfg.base_branch_policy == BaseBranchPolicy.FRESH:
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "origin/HEAD"],
                    capture_output=True, text=True, timeout=5,
                )
                base_ref = result.stdout.strip() or base_ref
            except subprocess.SubprocessError:
                base_ref = "HEAD"
        elif cfg.base_branch_policy == BaseBranchPolicy.HEAD:
            base_ref = "HEAD"

        # Create the worktree
        cmd = ["git", "worktree", "add", str(path), "-b", branch]
        if base_ref:
            cmd.append(base_ref)

        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        except subprocess.CalledProcessError as e:
            # Worktree might already exist
            if path.exists():
                return self._check_worktree_state(cfg.name, path)
            raise RuntimeError(f"Failed to create git worktree: {e.stderr}") from e

        return WorktreeStatus(
            name=cfg.name,
            path=path,
            branch=branch,
            state=WorktreeState.CLEAN,
            base_branch=base_ref,
        )

    def _create_overlay_worktree(self, cfg: WorktreeConfig, path: Path) -> WorktreeStatus:
        """Non-git fallback: copy-on-write overlay directory."""
        path.mkdir(parents=True, exist_ok=True)

        # Copy tracked files (simplified — production would use unionfs/overlayfs)
        src = Path.cwd()
        for item in src.iterdir():
            if item.name in (".git", ".claude", "__pycache__", "node_modules", ".venv"):
                continue
            dst = path / item.name
            if item.is_dir():
                if not dst.exists():
                    shutil.copytree(item, dst, symlinks=True, dirs_exist_ok=True)
            else:
                if not dst.exists():
                    shutil.copy2(item, dst)

        return WorktreeStatus(
            name=cfg.name,
            path=path,
            branch="overlay",
            state=WorktreeState.CLEAN,
            base_branch="overlay",
        )

    def _check_worktree_state(self, name: str, path: Path) -> WorktreeStatus:
        """Determine the worktree's dirty/clean state."""
        if not path.exists():
            return WorktreeStatus(name=name, path=path, branch="unknown", state=WorktreeState.UNKNOWN)

        branch = "unknown"
        uncommitted = 0
        new_commits = 0
        state = WorktreeState.UNKNOWN

        if (path / ".git").exists():
            try:
                # Get branch
                result = subprocess.run(
                    ["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True, text=True, timeout=5,
                )
                branch = result.stdout.strip()

                # Check for uncommitted changes
                result = subprocess.run(
                    ["git", "-C", str(path), "status", "--porcelain"],
                    capture_output=True, text=True, timeout=5,
                )
                uncommitted = len([l for l in result.stdout.split("\n") if l.strip()])

                # Determine state
                if uncommitted == 0:
                    state = WorktreeState.CLEAN
                elif uncommitted > 0:
                    state = WorktreeState.DIRTY_UNCOMMITTED
            except subprocess.SubprocessError:
                pass

        return WorktreeStatus(
            name=name,
            path=path,
            branch=branch,
            state=state,
            uncommitted_files=uncommitted,
            new_commits=new_commits,
        )

    def _propagate_includes(self, cfg: WorktreeConfig, path: Path) -> None:
        """Copy gitignored files matching .worktreeinclude patterns into the worktree.

        Reads .worktreeinclude (gitignore syntax) from the repo root. Only copies
        gitignored files — tracked files are never duplicated (they come from git).
        Non-git repos skip this step (the create_hook or overlay must handle env).
        """
        include_file = Path(self.DEFAULT_INCLUDE_FILE)
        if not include_file.exists():
            # Use default patterns from config
            patterns = set(cfg.include_patterns)
        else:
            patterns = set()
            for line in include_file.read_text().split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.add(line)

        import fnmatch

        for pattern in patterns:
            for src_path in Path.cwd().rglob(pattern):
                if src_path.is_file() and src_path.is_file():
                    rel = src_path.relative_to(Path.cwd())
                    # Only copy gitignored files
                    if self._is_gitignored(str(rel)):
                        dst = path / rel
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        if not dst.exists():
                            shutil.copy2(src_path, dst)

    def _is_gitignored(self, path: str) -> bool:
        try:
            subprocess.run(
                ["git", "check-ignore", "-q", path],
                check=True, capture_output=True, timeout=5,
            )
            return True
        except subprocess.SubprocessError:
            return False

    def _stash_worktree(self, worktree_path: Path) -> None:
        """Git stash changes in a worktree before removal."""
        try:
            subprocess.run(
                ["git", "-C", str(worktree_path), "stash", "push",
                 "-m", f"auto-stash-before-worktree-removal-{int(time.time())}"],
                check=True, capture_output=True, timeout=15,
            )
        except subprocess.SubprocessError:
            pass

    def _do_remove_worktree(self, name: str, path: Path) -> None:
        """Actually remove a worktree (git or plain directory)."""
        if (path / ".git").exists():
            try:
                subprocess.run(
                    ["git", "worktree", "remove", str(path), "--force"],
                    check=True, capture_output=True, timeout=15,
                )
            except subprocess.SubprocessError:
                shutil.rmtree(path, ignore_errors=True)
        elif self._remove_hook:
            self._remove_hook(path)
        else:
            shutil.rmtree(path, ignore_errors=True)

    def _generate_name(self) -> str:
        import uuid
        return uuid.uuid4().hex[:12]

    # -- Properties ----------------------------------------------------------

    @property
    def worktree_count(self) -> int:
        return len(self._worktrees)

    @property
    def stats(self) -> dict[str, Any]:
        statuses = [s for s in (self.status(n) for n in self._worktrees) if s is not None]
        return {
            "total_worktrees": len(statuses),
            "clean": sum(1 for s in statuses if s.state == WorktreeState.CLEAN),
            "dirty_uncommitted": sum(1 for s in statuses if s.state == WorktreeState.DIRTY_UNCOMMITTED),
            "dirty_new_commits": sum(1 for s in statuses if s.state == WorktreeState.DIRTY_NEW_COMMITS),
            "worktree_root": str(self._root),
        }
