"""Filesystem sandbox for subagents: writes restricted to scope globs."""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


class FsSandboxViolation(Exception):
    pass


@dataclass
class FsSandbox:
    repo_root: Path
    scope_globs: list[str]
    on_read_outside: Callable[[str], None] | None = field(default=None)

    # ------------------------------------------------------------------ helpers
    def _resolve_inside(self, path: Path) -> Path:
        p = Path(path)
        try:
            resolved = p.resolve()
        except (OSError, RuntimeError) as e:
            raise FsSandboxViolation(f"cannot resolve {p}: {e}") from e
        root = Path(self.repo_root).resolve()
        try:
            resolved.relative_to(root)
        except ValueError as e:
            raise FsSandboxViolation(
                f"path {p} resolves outside repo_root {root}"
            ) from e
        return resolved

    def _in_scope(self, path: Path) -> bool:
        root = Path(self.repo_root).resolve()
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            return False
        return any(fnmatch.fnmatch(rel, g) for g in self.scope_globs)

    # ------------------------------------------------------------------ checks
    def check_write(self, path: Path) -> None:
        resolved = self._resolve_inside(path)
        if not self._in_scope(resolved):
            raise FsSandboxViolation(
                f"write outside scope: {path} not in {self.scope_globs}"
            )

    def check_read(self, path: Path) -> None:
        try:
            resolved = self._resolve_inside(path)
        except FsSandboxViolation:
            if self.on_read_outside:
                self.on_read_outside(str(path))
            return
        if not self._in_scope(resolved) and self.on_read_outside:
            self.on_read_outside(str(path))
