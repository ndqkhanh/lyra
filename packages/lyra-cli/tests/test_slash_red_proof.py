"""Tests for ``/red-proof`` (Wave-C Task 13).

Contract:

1. ``run_red_proof(target, repo_root)`` shells out to ``pytest <target>``
   and returns a :class:`RedProofResult` whose ``passed`` is ``True``
   iff the exit code is **non-zero** (i.e. the test failed → it really
   is RED, which is what we want).
2. When the target is missing or pytest isn't installed we surface a
   friendly error rather than a traceback.
3. The slash ``/red-proof <pytest target>`` integrates the same path
   and renders ``"RED ✓"`` / ``"unexpectedly passed"`` summaries.

This exists so the TDD discipline ("write a failing test first") is
*provable* inside the REPL — you can paste a snippet of pytest output
and get a one-liner confirmation that you really did go RED.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_cli.interactive.red_proof import RedProofResult, run_red_proof
from lyra_cli.interactive.session import InteractiveSession


# ---------------------------------------------------------------------------
# Pure function: run_red_proof
# ---------------------------------------------------------------------------


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_run_red_proof_passing_target_is_unexpected(tmp_path: Path) -> None:
    """A test target that PASSES is BAD news — it means the user
    didn't really go RED. Surface the surprise loudly."""
    _write(
        tmp_path / "test_hi.py",
        "def test_hi():\n    assert 1 == 1\n",
    )
    result = run_red_proof("test_hi.py", repo_root=tmp_path)
    assert isinstance(result, RedProofResult)
    assert result.passed is False
    assert "unexpected" in result.message.lower() or "green" in result.message.lower()


def test_run_red_proof_failing_target_is_proof(tmp_path: Path) -> None:
    _write(
        tmp_path / "test_red.py",
        "def test_red():\n    assert False, 'this is the red proof'\n",
    )
    result = run_red_proof("test_red.py", repo_root=tmp_path)
    assert result.passed is True
    assert "RED" in result.message or "red" in result.message


def test_run_red_proof_missing_target(tmp_path: Path) -> None:
    """Pytest's collection-error exit code (2) still proves RED for
    our purposes: nothing collected → no GREEN → safe to call this a
    failing target. We intentionally surface it as such, not as a
    user error, because a typo in the path should never silently
    convert RED to GREEN."""
    result = run_red_proof("nonexistent_target.py", repo_root=tmp_path)
    # We accept either "passed" (pytest exited non-zero, so RED) OR a
    # friendly error — anything other than a crash is acceptable.
    assert isinstance(result, RedProofResult)
    assert result.exit_code != 0


def test_run_red_proof_pytest_missing(tmp_path: Path, monkeypatch) -> None:
    """When pytest can't be invoked we should not raise."""
    import lyra_cli.interactive.red_proof as rp

    def _boom(*_args, **_kwargs):
        raise FileNotFoundError("python3: command not found")

    monkeypatch.setattr(rp, "_invoke_pytest", _boom)
    result = run_red_proof("anything", repo_root=tmp_path)
    assert result.passed is False
    assert "pytest" in result.message.lower()


# ---------------------------------------------------------------------------
# Slash integration
# ---------------------------------------------------------------------------


def _session(tmp_path: Path) -> InteractiveSession:
    return InteractiveSession(repo_root=tmp_path)


def test_slash_red_proof_no_args(tmp_path: Path) -> None:
    out = _session(tmp_path).dispatch("/red-proof").output or ""
    assert "usage" in out.lower() or "target" in out.lower()


def test_slash_red_proof_failing_target(tmp_path: Path) -> None:
    _write(tmp_path / "test_red.py", "def test_red():\n    assert False\n")
    out = _session(tmp_path).dispatch("/red-proof test_red.py").output or ""
    assert "RED" in out or "✓" in out


def test_slash_red_proof_passing_target(tmp_path: Path) -> None:
    _write(tmp_path / "test_green.py", "def test_green():\n    assert True\n")
    out = _session(tmp_path).dispatch("/red-proof test_green.py").output or ""
    assert "unexpected" in out.lower() or "green" in out.lower()
