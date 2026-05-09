"""`/diff` shows git diff --stat + per-file unified diffs."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from lyra_cli.interactive.session import InteractiveSession


def _init_repo(tmp_path: Path) -> Path:
    """Create a one-commit git repo at ``tmp_path``.

    Skips the calling test if git is unavailable or the sandbox blocks
    the ``.git/hooks`` write — both are environmental, not regressions.
    """
    try:
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "T"], cwd=tmp_path, check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError, PermissionError):
        pytest.skip("git not available in sandbox")
    (tmp_path / "foo.txt").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init", "-q"], cwd=tmp_path, check=True
    )
    return tmp_path


def test_diff_shows_stat_and_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_repo(tmp_path)
    (repo / "foo.txt").write_text("hello\nworld\n")
    monkeypatch.chdir(repo)
    session = InteractiveSession(repo_root=repo)
    out = session._cmd_diff_text("")
    assert "foo.txt" in out
    assert "+world" in out


def test_diff_in_clean_tree_returns_friendly_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_repo(tmp_path)
    monkeypatch.chdir(repo)
    session = InteractiveSession(repo_root=repo)
    out = session._cmd_diff_text("")
    lower = out.lower()
    assert "no changes" in lower or "clean" in lower


def test_diff_outside_git_repo_returns_friendly_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    session = InteractiveSession(repo_root=tmp_path)
    out = session._cmd_diff_text("")
    lower = out.lower()
    assert "not a git" in lower or "no repo" in lower
