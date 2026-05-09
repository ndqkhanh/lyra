"""``/worktree`` slash command tests (v3.7 L37-5)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from lyra_cli.interactive.worktree_command import (
    CopyPolicy,
    WorktreeCommand,
    WorktreeCommandResult,
)


@dataclass
class FakeWorktree:
    scope_id: str
    path: Path
    branch: str


@dataclass
class FakeManager:
    """Drop-in for WorktreeManager that does not require a git repo."""

    repo_root: Path
    _active: dict[str, FakeWorktree] = field(default_factory=dict)
    cleaned: list[FakeWorktree] = field(default_factory=list)

    def allocate(self, *, scope_id: str) -> FakeWorktree:
        if scope_id in self._active:
            return self._active[scope_id]
        path = self.repo_root / "worktrees" / scope_id
        path.mkdir(parents=True, exist_ok=True)
        wt = FakeWorktree(scope_id=scope_id, path=path,
                          branch=f"lyra/subagent/{scope_id}-fake")
        self._active[scope_id] = wt
        return wt

    def cleanup(self, wt: FakeWorktree) -> None:
        self.cleaned.append(wt)
        self._active.pop(wt.scope_id, None)


def _command(tmp_path: Path) -> WorktreeCommand:
    return WorktreeCommand(manager=FakeManager(repo_root=tmp_path))


def test_create_default_name(tmp_path: Path) -> None:
    cmd = _command(tmp_path)
    out = cmd.dispatch("create")
    assert out.ok
    assert "name" in out.payload
    assert out.payload["name"].startswith("wt-")


def test_create_named(tmp_path: Path) -> None:
    cmd = _command(tmp_path)
    out = cmd.dispatch("create feature-x")
    assert out.ok
    assert out.payload["name"] == "feature-x"


def test_create_rejects_invalid_name(tmp_path: Path) -> None:
    cmd = _command(tmp_path)
    out = cmd.dispatch("create bad/name")
    assert not out.ok
    assert "invalid" in out.message


def test_list_empty(tmp_path: Path) -> None:
    cmd = _command(tmp_path)
    out = cmd.dispatch("list")
    assert out.ok
    assert out.payload["worktrees"] == []


def test_list_shows_active(tmp_path: Path) -> None:
    cmd = _command(tmp_path)
    cmd.dispatch("create alpha")
    cmd.dispatch("create beta")
    out = cmd.dispatch("list")
    names = {w["name"] for w in out.payload["worktrees"]}
    assert names == {"alpha", "beta"}


def test_remove_known_worktree(tmp_path: Path) -> None:
    cmd = _command(tmp_path)
    cmd.dispatch("create alpha")
    out = cmd.dispatch("remove alpha")
    assert out.ok
    list_out = cmd.dispatch("list")
    assert list_out.payload["worktrees"] == []


def test_remove_unknown_returns_error(tmp_path: Path) -> None:
    cmd = _command(tmp_path)
    out = cmd.dispatch("remove ghost")
    assert not out.ok


def test_unknown_subcommand_returns_error(tmp_path: Path) -> None:
    cmd = _command(tmp_path)
    out = cmd.dispatch("frobnicate")
    assert not out.ok
    assert "unknown" in out.message


def test_no_args_prints_usage(tmp_path: Path) -> None:
    cmd = _command(tmp_path)
    out = cmd.dispatch("")
    assert not out.ok
    assert "usage" in out.message


def test_copy_node_modules_succeeds(tmp_path: Path) -> None:
    # Set up source root with a node_modules dir to copy.
    src_node = tmp_path / "node_modules"
    src_node.mkdir()
    (src_node / "fakelib").mkdir()
    (src_node / "fakelib" / "index.js").write_text("module.exports = 1\n")

    cmd = _command(tmp_path)
    cmd.dispatch("create alpha")
    out = cmd.dispatch("copy node_modules")
    assert out.ok
    # Copied into worktree.
    assert (tmp_path / "worktrees" / "alpha" / "node_modules" / "fakelib" / "index.js").exists()


def test_copy_pattern_not_in_policy_rejected(tmp_path: Path) -> None:
    cmd = _command(tmp_path)
    cmd.dispatch("create alpha")
    out = cmd.dispatch("copy /etc/passwd")
    assert not out.ok
    assert "not allowed" in out.message


def test_copy_with_multiple_worktrees_requires_name(tmp_path: Path) -> None:
    cmd = _command(tmp_path)
    cmd.dispatch("create alpha")
    cmd.dispatch("create beta")
    out = cmd.dispatch("copy node_modules")
    assert not out.ok
    assert "supply <name> explicitly" in out.message


def test_copy_skips_when_source_missing(tmp_path: Path) -> None:
    cmd = _command(tmp_path)
    cmd.dispatch("create alpha")
    out = cmd.dispatch("copy .venv")            # no .venv exists
    assert out.ok
    assert out.payload["copied"] == []
    assert out.payload["skipped"]


def test_copy_policy_default_patterns_include_node_modules() -> None:
    policy = CopyPolicy()
    assert "node_modules" in policy.patterns
    assert ".venv" in policy.patterns
