"""Evidence-citation validator: reject hallucinated file:line citations."""
from __future__ import annotations

from pathlib import Path


class EvidenceError(Exception):
    """Raised when evidence cannot be validated against the repo state."""


def validate_file_line(path: Path, *, line: int, repo_root: Path) -> None:
    path = Path(path)
    if not path.is_absolute():
        path = repo_root / path
    if not path.exists():
        raise EvidenceError(f"evidence file not found: {path}")
    try:
        n = sum(1 for _ in path.open("r", encoding="utf-8", errors="replace"))
    except OSError as e:
        raise EvidenceError(f"cannot read evidence file {path}: {e}") from e
    if line < 1 or line > n:
        raise EvidenceError(
            f"evidence line {line} out of range for {path} (has {n} lines)"
        )
