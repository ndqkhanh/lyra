"""RED-proof evidence validator.

A ``RedProof`` is the agent's claim that a given test *genuinely* failed.
The validator rejects fabrications (zero exit code, passed status, missing
duration, unknown test file).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class RedProofError(Exception):
    """Raised when a RedProof fails validation."""


@dataclass
class RedProof:
    test_id: str              # "<path>::<nodeid>"
    status: str               # "failed" | "error" | "skipped" | "passed"
    exit_code: int
    duration_ms: int
    stderr: str | None = None


def _split_test_id(test_id: str) -> tuple[str, str]:
    if "::" not in test_id:
        raise RedProofError(f"test_id missing '::' separator: {test_id!r}")
    path, node = test_id.split("::", 1)
    if not path or not node:
        raise RedProofError(f"malformed test_id: {test_id!r}")
    return path, node


def validate_red_proof(proof: RedProof, *, repo_root: Path) -> None:
    path_str, _node = _split_test_id(proof.test_id)

    test_path = Path(path_str)
    if not test_path.is_absolute():
        test_path = repo_root / test_path
    if not test_path.exists():
        raise RedProofError(f"test file not found: {test_path}")

    if proof.status != "failed":
        raise RedProofError(
            f"RED proof requires status='failed'; got {proof.status!r}"
        )
    if proof.exit_code == 0:
        raise RedProofError("RED proof requires non-zero exit_code")
    if proof.duration_ms <= 0:
        raise RedProofError(
            "RED proof requires duration_ms > 0 (test must have actually run)"
        )
