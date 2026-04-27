"""Git-worktree management for isolated subagent scopes."""
from __future__ import annotations

import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path


class WorktreeError(Exception):
    pass


@dataclass
class Worktree:
    scope_id: str
    path: Path
    branch: str


class WorktreeManager:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root).resolve()
        if not (self.repo_root / ".git").exists():
            raise WorktreeError(f"not a git repo: {self.repo_root}")
        self._state_dir = self.repo_root / ".lyra" / "worktrees"
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._active: dict[str, Worktree] = {}

    # ------------------------------------------------------------------ allocate
    def allocate(self, *, scope_id: str) -> Worktree:
        if scope_id in self._active:
            return self._active[scope_id]
        token = uuid.uuid4().hex[:8]
        branch = f"lyra/subagent/{scope_id}-{token}"
        path = self._state_dir / f"{scope_id}-{token}"
        path.parent.mkdir(parents=True, exist_ok=True)

        res = subprocess.run(
            [
                "git", "-C", str(self.repo_root),
                "worktree", "add", "-b", branch, str(path),
            ],
            capture_output=True, text=True,
        )
        if res.returncode != 0:
            raise WorktreeError(
                f"git worktree add failed: {res.stderr.strip() or res.stdout.strip()}"
            )

        wt = Worktree(scope_id=scope_id, path=path, branch=branch)
        self._active[scope_id] = wt
        return wt

    # ------------------------------------------------------------------ cleanup
    def cleanup(self, wt: Worktree) -> None:
        if wt.path.exists():
            res = subprocess.run(
                ["git", "-C", str(self.repo_root),
                 "worktree", "remove", "--force", str(wt.path)],
                capture_output=True, text=True,
            )
            if res.returncode != 0 and wt.path.exists():
                shutil.rmtree(wt.path, ignore_errors=True)
        # Best-effort branch delete.
        subprocess.run(
            ["git", "-C", str(self.repo_root), "branch", "-D", wt.branch],
            capture_output=True, text=True,
        )
        self._active.pop(wt.scope_id, None)

    # ------------------------------------------------------------------ reconcile
    def reconcile_orphans(self) -> list[Path]:
        """Remove worktree directories in state_dir that we don't track."""
        active_paths = {wt.path for wt in self._active.values()}
        removed: list[Path] = []
        for child in self._state_dir.iterdir():
            if child.is_dir() and child not in active_paths:
                subprocess.run(
                    ["git", "-C", str(self.repo_root),
                     "worktree", "remove", "--force", str(child)],
                    capture_output=True, text=True,
                )
                if child.exists():
                    shutil.rmtree(child, ignore_errors=True)
                removed.append(child)
        return removed

    # --------------------------------------------------------------------- test
    def _forget_for_test(self, wt: Worktree) -> None:
        """Test hook: drop in-memory record without disk cleanup."""
        self._active.pop(wt.scope_id, None)
