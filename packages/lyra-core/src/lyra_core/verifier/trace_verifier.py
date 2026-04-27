"""Wave-F Task 2 — trace-vs-reality verifier.

Catches the hallucination failure mode where the model narrates:

    "I edited `foo.py:34` so the parser now handles UTF-8."

…but (a) the line number is wrong, (b) the file doesn't exist, or
(c) the file does exist but doesn't contain the claimed content.

The verifier cross-checks three channels:

1. The model's narration (a free-form string).
2. The filesystem (current state of the cited file).
3. Optionally, a git-style unified diff fragment the caller
   provides (e.g. from ``git diff --unified=0``).

When no diff is provided the verifier degrades gracefully —
only the trace-vs-FS check runs. Neither channel requires
network or shell access, so the whole module is sandbox-safe.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence


__all__ = [
    "MiscitedClaim",
    "TraceClaim",
    "TraceVerification",
    "extract_claims",
    "verify_trace",
]


# Regex matches "foo/bar.py:34" or "foo/bar.py" (the latter is
# still a claim — the verifier just checks file existence).
_FILE_LINE_RE = re.compile(
    r"`?(?P<path>[\w./\-+]+\.(?:py|ts|tsx|js|jsx|rs|go|md|toml|yaml|yml|json))"
    r"(?::(?P<line>\d+))?`?",
)


@dataclass(frozen=True)
class TraceClaim:
    """One parsed claim out of the narration.

    ``snippet`` is optional — the substring the model put in
    backticks right after the citation. When present, the verifier
    also checks that the snippet appears verbatim in the cited
    file (or in the diff when one is supplied).
    """

    path: str
    line: int | None = None
    snippet: str | None = None


@dataclass(frozen=True)
class MiscitedClaim:
    claim: TraceClaim
    reason: str


@dataclass(frozen=True)
class TraceVerification:
    """Aggregate verdict."""

    claims: tuple[TraceClaim, ...]
    miscited: tuple[MiscitedClaim, ...] = field(default_factory=tuple)
    checked_diff: bool = False

    @property
    def passed(self) -> bool:
        return not self.miscited

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "checked_diff": self.checked_diff,
            "claims": [
                {"path": c.path, "line": c.line, "snippet": c.snippet}
                for c in self.claims
            ],
            "miscited": [
                {"path": m.claim.path, "line": m.claim.line, "reason": m.reason}
                for m in self.miscited
            ],
        }


# ---- extraction ----------------------------------------------------


def extract_claims(narration: str) -> list[TraceClaim]:
    """Pull ``path[:line]`` citations out of a narration string."""
    claims: list[TraceClaim] = []
    for m in _FILE_LINE_RE.finditer(narration):
        line_s = m.group("line")
        line = int(line_s) if line_s is not None else None
        claims.append(TraceClaim(path=m.group("path"), line=line))
    return claims


# ---- checks --------------------------------------------------------


def _read_lines(path: Path) -> list[str] | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None


def _check_fs(claim: TraceClaim, repo_root: Path) -> str | None:
    target = (repo_root / claim.path).resolve()
    try:
        target.relative_to(repo_root.resolve())
    except ValueError:
        return f"path {claim.path!r} escapes repo_root"
    if not target.exists():
        return f"file does not exist: {claim.path!r}"
    if claim.line is None:
        return None
    lines = _read_lines(target)
    if lines is None:
        return f"cannot read file: {claim.path!r}"
    if claim.line < 1 or claim.line > len(lines):
        return (
            f"line {claim.line} out of range for {claim.path!r} "
            f"({len(lines)} lines on disk)"
        )
    if claim.snippet is not None:
        body = lines[claim.line - 1]
        if claim.snippet not in body:
            return (
                f"snippet not found at {claim.path}:{claim.line}: "
                f"expected {claim.snippet!r}"
            )
    return None


def _check_diff(claim: TraceClaim, diff: str) -> str | None:
    # Any mention of the claimed path in the diff counts as
    # coverage — callers can tighten this for their own pipelines
    # but this is the minimal "was the file actually changed"
    # question.
    if claim.path not in diff:
        return f"claimed change to {claim.path!r} but diff does not mention it"
    if claim.snippet is not None and claim.snippet not in diff:
        return (
            f"snippet not found in diff for {claim.path!r}: "
            f"expected {claim.snippet!r}"
        )
    return None


def verify_trace(
    *,
    narration: str,
    repo_root: Path | str,
    diff: str | None = None,
    extra_claims: Sequence[TraceClaim] | None = None,
) -> TraceVerification:
    """Cross-check *narration* against *repo_root* (and optionally *diff*)."""
    root = Path(repo_root).resolve()
    claims = list(extract_claims(narration))
    if extra_claims:
        claims.extend(extra_claims)
    miscited: list[MiscitedClaim] = []
    for claim in claims:
        reason = _check_fs(claim, root)
        if reason is None and diff is not None:
            reason = _check_diff(claim, diff)
        if reason is not None:
            miscited.append(MiscitedClaim(claim=claim, reason=reason))
    return TraceVerification(
        claims=tuple(claims),
        miscited=tuple(miscited),
        checked_diff=diff is not None,
    )
