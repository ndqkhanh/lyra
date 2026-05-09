"""``/ultrareview`` multi-agent review pipeline (v3.7 L37-7).

Anthropic's Claude Code "Code review" auto-reviews PRs and supports
``/ultrareview`` for adversarial cross-family review. Lyra ships the
*pipeline* — collect git diff → multi-agent review → aggregate →
summarise — that the CLI slash command and any GitHub-PR webhook
trigger drive.

The pipeline is reviewer-agnostic: callers supply :class:`Reviewer`
instances (production wiring uses cross-family LLM reviewers via
``lyra-cli/llm_factory.py``); tests use deterministic stubs.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable


class Severity(str, enum.Enum):
    INFO = "info"
    WARN = "warn"
    BLOCKER = "blocker"


@dataclass(frozen=True)
class DiffHunk:
    """One file's diff — minimal surface the reviewers consume."""

    path: str
    added_lines: tuple[str, ...] = ()
    removed_lines: tuple[str, ...] = ()
    extra: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class ReviewFinding:
    """One per-reviewer per-file finding."""

    reviewer: str                  # reviewer family/name
    path: str
    severity: Severity
    message: str
    line: int | None = None


class Reviewer:
    """Reviewer protocol — deterministic stub by default."""

    name: str = "reviewer-default"
    family: str = "default"

    def review(self, hunks: Iterable[DiffHunk]) -> list[ReviewFinding]:    # pragma: no cover
        raise NotImplementedError


@dataclass
class CrossFamilyError(RuntimeError):
    """Raised when the pipeline lacks ≥ 2 distinct reviewer families."""

    families: tuple[str, ...]

    def __str__(self) -> str:                                    # pragma: no cover
        return (
            f"UltraReview requires ≥ 2 distinct reviewer families; "
            f"got {self.families!r}"
        )


@dataclass(frozen=True)
class ReviewSummary:
    """Aggregated outcome of a ``/ultrareview`` run."""

    findings: tuple[ReviewFinding, ...]
    by_path: dict[str, tuple[ReviewFinding, ...]]
    by_severity: dict[Severity, int]
    blockers: int
    has_blockers: bool


@dataclass
class UltraReviewPipeline:
    """End-to-end ``/ultrareview``: diff → reviewers → summary."""

    reviewers: tuple[Reviewer, ...]

    def __post_init__(self) -> None:
        families = tuple({r.family for r in self.reviewers})
        if len(families) < 2:
            raise CrossFamilyError(families=families)

    def run(self, hunks: Iterable[DiffHunk]) -> ReviewSummary:
        hunks_list = list(hunks)
        all_findings: list[ReviewFinding] = []
        for reviewer in self.reviewers:
            for finding in reviewer.review(hunks_list):
                all_findings.append(finding)
        return aggregate(all_findings)


def aggregate(findings: Iterable[ReviewFinding]) -> ReviewSummary:
    findings_t = tuple(findings)
    by_path: dict[str, list[ReviewFinding]] = {}
    by_sev: dict[Severity, int] = {Severity.INFO: 0, Severity.WARN: 0,
                                    Severity.BLOCKER: 0}
    for f in findings_t:
        by_path.setdefault(f.path, []).append(f)
        by_sev[f.severity] = by_sev.get(f.severity, 0) + 1
    blockers = by_sev[Severity.BLOCKER]
    return ReviewSummary(
        findings=findings_t,
        by_path={k: tuple(v) for k, v in by_path.items()},
        by_severity=dict(by_sev),
        blockers=blockers,
        has_blockers=blockers > 0,
    )


def render_summary_md(summary: ReviewSummary) -> str:
    """Render the summary as a Markdown comment for PRs / CLI output."""
    if not summary.findings:
        return "✅ /ultrareview: no findings.\n"
    lines = [
        "# /ultrareview summary",
        "",
        f"- blockers: **{summary.by_severity.get(Severity.BLOCKER, 0)}**",
        f"- warnings: **{summary.by_severity.get(Severity.WARN, 0)}**",
        f"- info: **{summary.by_severity.get(Severity.INFO, 0)}**",
        "",
    ]
    for path in sorted(summary.by_path.keys()):
        lines.append(f"## {path}")
        for finding in summary.by_path[path]:
            tag = f"[{finding.severity.value}]"
            who = f"({finding.reviewer})"
            loc = f"L{finding.line}" if finding.line is not None else ""
            lines.append(f"- {tag} {loc} {finding.message} {who}".rstrip())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


__all__ = [
    "CrossFamilyError",
    "DiffHunk",
    "ReviewFinding",
    "ReviewSummary",
    "Reviewer",
    "Severity",
    "UltraReviewPipeline",
    "aggregate",
    "render_summary_md",
]
