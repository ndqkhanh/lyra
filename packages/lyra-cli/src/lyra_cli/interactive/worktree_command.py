"""``/worktree`` slash command (v3.7 L37-5).

Wraps :class:`lyra_core.subagent.worktree.WorktreeManager` so the user
can drive worktrees directly from the REPL.

Sub-commands:

* ``/worktree create [name]`` — allocate a new worktree (branch + path).
* ``/worktree list`` — show active worktrees.
* ``/worktree remove <name>`` — detach + clean up the worktree.
* ``/worktree copy <pattern>`` — apply the copy policy (node_modules /
  .venv / dist) from the source repo into the named worktree.
"""
from __future__ import annotations

import re
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Protocol


_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")

# Default copy patterns — directories the user typically wants pre-
# populated in a fresh worktree to avoid re-running install / build.
_DEFAULT_COPY_PATTERNS: tuple[str, ...] = (
    "node_modules",
    ".venv",
    "dist",
    ".pytest_cache",
)


class _ManagerLike(Protocol):
    """Subset of :class:`WorktreeManager` the command consumes."""

    repo_root: Path

    def allocate(self, *, scope_id: str) -> object: ...
    def cleanup(self, wt: object) -> None: ...
    @property
    def _active(self) -> dict[str, object]: ...     # type: ignore[override]


@dataclass(frozen=True)
class CopyResult:
    """Outcome of one ``copy`` call."""

    pattern: str
    copied: tuple[Path, ...]
    skipped: tuple[Path, ...]


@dataclass
class CopyPolicy:
    """File-copy policy applied when populating a fresh worktree."""

    patterns: tuple[str, ...] = _DEFAULT_COPY_PATTERNS

    def copy(self, *, source_root: Path, worktree_path: Path,
             pattern: str) -> CopyResult:
        if pattern not in self.patterns:
            raise ValueError(
                f"pattern {pattern!r} not in policy patterns {self.patterns}"
            )
        src = source_root / pattern
        dst = worktree_path / pattern
        if not src.exists():
            return CopyResult(pattern=pattern, copied=(), skipped=(src,))
        if dst.exists():
            return CopyResult(pattern=pattern, copied=(), skipped=(dst,))
        if src.is_dir():
            shutil.copytree(src, dst, symlinks=True)
        else:
            shutil.copy2(src, dst)
        return CopyResult(pattern=pattern, copied=(dst,), skipped=())


@dataclass(frozen=True)
class WorktreeCommandResult:
    """Outcome of one ``/worktree`` invocation."""

    ok: bool
    message: str
    payload: dict[str, object] = field(default_factory=dict)


@dataclass
class WorktreeCommand:
    """``/worktree`` REPL slash."""

    manager: _ManagerLike
    copy_policy: CopyPolicy = field(default_factory=CopyPolicy)

    def dispatch(self, args: str) -> WorktreeCommandResult:
        tokens = args.strip().split()
        if not tokens:
            return WorktreeCommandResult(
                ok=False,
                message=(
                    "usage: /worktree create [name] | list | "
                    "remove <name> | copy <pattern> [name]"
                ),
            )
        sub = tokens[0]
        rest = tokens[1:]
        if sub == "create":
            return self._create(rest)
        if sub == "list":
            return self._list()
        if sub == "remove":
            return self._remove(rest)
        if sub == "copy":
            return self._copy(rest)
        return WorktreeCommandResult(
            ok=False, message=f"unknown /worktree sub-command {sub!r}",
        )

    # --- sub-commands --------------------------------------------------

    def _create(self, args: list[str]) -> WorktreeCommandResult:
        name = args[0] if args else f"wt-{uuid.uuid4().hex[:6]}"
        if not _NAME_RE.match(name):
            return WorktreeCommandResult(
                ok=False, message=f"invalid worktree name {name!r}",
            )
        wt = self.manager.allocate(scope_id=name)
        return WorktreeCommandResult(
            ok=True,
            message=f"worktree {name!r} allocated at {wt.path}",
            payload={"name": name, "path": str(wt.path), "branch": wt.branch},
        )

    def _list(self) -> WorktreeCommandResult:
        active = list(self.manager._active.values())   # type: ignore[attr-defined]
        return WorktreeCommandResult(
            ok=True,
            message=f"{len(active)} active worktree(s)",
            payload={
                "worktrees": [
                    {"name": wt.scope_id, "path": str(wt.path), "branch": wt.branch}
                    for wt in active
                ],
            },
        )

    def _remove(self, args: list[str]) -> WorktreeCommandResult:
        if not args:
            return WorktreeCommandResult(
                ok=False, message="usage: /worktree remove <name>",
            )
        name = args[0]
        active = self.manager._active     # type: ignore[attr-defined]
        wt = active.get(name)
        if wt is None:
            return WorktreeCommandResult(
                ok=False, message=f"no active worktree named {name!r}",
            )
        self.manager.cleanup(wt)
        return WorktreeCommandResult(
            ok=True, message=f"worktree {name!r} removed",
        )

    def _copy(self, args: list[str]) -> WorktreeCommandResult:
        if not args:
            return WorktreeCommandResult(
                ok=False, message="usage: /worktree copy <pattern> [name]",
            )
        pattern = args[0]
        name = args[1] if len(args) > 1 else None
        active = self.manager._active     # type: ignore[attr-defined]
        if name is None:
            if len(active) != 1:
                return WorktreeCommandResult(
                    ok=False,
                    message="multiple worktrees active; supply <name> explicitly",
                )
            name = next(iter(active.keys()))
        wt = active.get(name)
        if wt is None:
            return WorktreeCommandResult(
                ok=False, message=f"no active worktree named {name!r}",
            )
        if pattern not in self.copy_policy.patterns:
            return WorktreeCommandResult(
                ok=False,
                message=(
                    f"pattern {pattern!r} not allowed; allowed: "
                    f"{self.copy_policy.patterns}"
                ),
            )
        result = self.copy_policy.copy(
            source_root=self.manager.repo_root,
            worktree_path=wt.path,
            pattern=pattern,
        )
        return WorktreeCommandResult(
            ok=True,
            message=f"copied {len(result.copied)} item(s) for pattern {pattern!r}",
            payload={
                "copied": [str(p) for p in result.copied],
                "skipped": [str(p) for p in result.skipped],
            },
        )


__all__ = [
    "CopyPolicy",
    "CopyResult",
    "WorktreeCommand",
    "WorktreeCommandResult",
]
