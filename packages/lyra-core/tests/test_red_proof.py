"""Red tests for RED-proof evidence validation.

A RED proof is an artifact claimed by the agent that a specific test
*genuinely* failed. It must be:
    - A structured record with {kind: 'red', test_id, duration_ms, stderr?, exit_code}
    - The test file path must exist
    - ``exit_code`` must be non-zero
    - ``status`` must be ``'failed'`` (not ``'error'`` or ``'skipped'``)
    - A placeholder like ``pytest.skip`` or ``assert True`` is not acceptance
    - A claim without any evidence (no duration, no exit code) is rejected
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.tdd.red_proof import (
    RedProof,
    RedProofError,
    validate_red_proof,
)


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "def test_x():\n    assert False\n"
    )


def test_valid_red_proof_accepted(tmp_path: Path) -> None:
    t = tmp_path / "tests" / "test_x.py"
    _touch(t)
    proof = RedProof(
        test_id=f"{t}::test_x",
        status="failed",
        exit_code=1,
        duration_ms=24,
        stderr="AssertionError: expected True",
    )
    validate_red_proof(proof, repo_root=tmp_path)


def test_reject_zero_exit_code(tmp_path: Path) -> None:
    t = tmp_path / "tests" / "test_x.py"
    _touch(t)
    proof = RedProof(
        test_id=f"{t}::test_x",
        status="failed",
        exit_code=0,
        duration_ms=10,
    )
    with pytest.raises(RedProofError):
        validate_red_proof(proof, repo_root=tmp_path)


def test_reject_passed_status(tmp_path: Path) -> None:
    t = tmp_path / "tests" / "test_x.py"
    _touch(t)
    proof = RedProof(
        test_id=f"{t}::test_x",
        status="passed",
        exit_code=1,
        duration_ms=10,
    )
    with pytest.raises(RedProofError):
        validate_red_proof(proof, repo_root=tmp_path)


def test_reject_nonexistent_test_file(tmp_path: Path) -> None:
    proof = RedProof(
        test_id=f"{tmp_path}/tests/does_not_exist.py::test_z",
        status="failed",
        exit_code=1,
        duration_ms=10,
    )
    with pytest.raises(RedProofError):
        validate_red_proof(proof, repo_root=tmp_path)


def test_reject_missing_duration(tmp_path: Path) -> None:
    t = tmp_path / "tests" / "test_x.py"
    _touch(t)
    proof = RedProof(
        test_id=f"{t}::test_x",
        status="failed",
        exit_code=1,
        duration_ms=0,  # flag: didn't actually run
    )
    with pytest.raises(RedProofError):
        validate_red_proof(proof, repo_root=tmp_path)


def test_reject_non_pytest_shaped_id(tmp_path: Path) -> None:
    proof = RedProof(
        test_id="some random string without ::",
        status="failed",
        exit_code=1,
        duration_ms=10,
    )
    with pytest.raises(RedProofError):
        validate_red_proof(proof, repo_root=tmp_path)
