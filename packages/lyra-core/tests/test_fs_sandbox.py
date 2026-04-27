"""Red tests for filesystem sandbox: writes outside scope rejected."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.subagent.fs_sandbox import (
    FsSandbox,
    FsSandboxViolation,
)


def test_write_inside_scope_allowed(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    box = FsSandbox(repo_root=tmp_path, scope_globs=["src/**"])
    box.check_write(tmp_path / "src" / "a.py")


def test_write_outside_scope_rejected(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "secrets").mkdir()
    box = FsSandbox(repo_root=tmp_path, scope_globs=["src/**"])
    with pytest.raises(FsSandboxViolation):
        box.check_write(tmp_path / "secrets" / "x")


def test_read_outside_scope_logged_not_blocked(tmp_path: Path) -> None:
    box = FsSandbox(repo_root=tmp_path, scope_globs=["src/**"])
    warned: list[str] = []
    box.on_read_outside = warned.append  # type: ignore[assignment]
    box.check_read(tmp_path / "README.md")
    assert warned  # the access was recorded


def test_write_outside_repo_root_rejected(tmp_path: Path) -> None:
    box = FsSandbox(repo_root=tmp_path, scope_globs=["**"])
    other = tmp_path.parent / "evil.txt"
    with pytest.raises(FsSandboxViolation):
        box.check_write(other)


def test_symlink_escape_rejected(tmp_path: Path) -> None:
    (tmp_path / "inside").mkdir()
    (tmp_path / "outside").mkdir()
    link = tmp_path / "inside" / "escape"
    link.symlink_to(tmp_path / "outside")
    box = FsSandbox(repo_root=tmp_path, scope_globs=["inside/**"])
    with pytest.raises(FsSandboxViolation):
        box.check_write(link / "stolen.txt")
