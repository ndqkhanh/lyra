"""UltraReview pipeline tests (v3.7 L37-7)."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from lyra_core.brains.ultrareview import (
    CrossFamilyError,
    DiffHunk,
    ReviewFinding,
    Reviewer,
    Severity,
    UltraReviewPipeline,
    aggregate,
    render_summary_md,
)


@dataclass
class StaticReviewer(Reviewer):
    name: str = "static"
    family: str = "default"
    findings: tuple[ReviewFinding, ...] = ()

    def review(self, hunks):                          # noqa: ARG002
        return list(self.findings)


def _hunks() -> list[DiffHunk]:
    return [
        DiffHunk(path="src/a.py", added_lines=("def x(): pass",)),
        DiffHunk(path="src/b.py", added_lines=("import os",)),
    ]


# --- Cross-family invariant -------------------------------------------------


def test_pipeline_refuses_single_family() -> None:
    r1 = StaticReviewer(name="r1", family="anthropic")
    r2 = StaticReviewer(name="r2", family="anthropic")
    with pytest.raises(CrossFamilyError):
        UltraReviewPipeline(reviewers=(r1, r2))


def test_pipeline_admits_two_families() -> None:
    r1 = StaticReviewer(name="r1", family="anthropic")
    r2 = StaticReviewer(name="r2", family="openai")
    pipe = UltraReviewPipeline(reviewers=(r1, r2))
    summary = pipe.run(_hunks())
    assert summary.findings == ()


# --- Aggregation ------------------------------------------------------------


def test_aggregate_groups_by_path_and_severity() -> None:
    findings = [
        ReviewFinding(reviewer="r1", path="a.py", severity=Severity.WARN,  message="x"),
        ReviewFinding(reviewer="r2", path="a.py", severity=Severity.BLOCKER, message="y"),
        ReviewFinding(reviewer="r1", path="b.py", severity=Severity.INFO,  message="z"),
    ]
    summary = aggregate(findings)
    assert summary.by_path["a.py"][0].path == "a.py"
    assert len(summary.by_path["a.py"]) == 2
    assert summary.by_severity[Severity.BLOCKER] == 1
    assert summary.has_blockers


def test_aggregate_no_blockers_when_no_findings() -> None:
    assert aggregate([]).has_blockers is False


# --- Pipeline.run -----------------------------------------------------------


def test_pipeline_collects_findings_from_all_reviewers() -> None:
    f1 = ReviewFinding(reviewer="r1", path="a.py", severity=Severity.WARN, message="warn-from-r1")
    f2 = ReviewFinding(reviewer="r2", path="a.py", severity=Severity.BLOCKER, message="block-from-r2")
    r1 = StaticReviewer(name="r1", family="anthropic", findings=(f1,))
    r2 = StaticReviewer(name="r2", family="openai", findings=(f2,))
    pipe = UltraReviewPipeline(reviewers=(r1, r2))
    summary = pipe.run(_hunks())
    assert {f.reviewer for f in summary.findings} == {"r1", "r2"}
    assert summary.has_blockers


# --- Markdown rendering -----------------------------------------------------


def test_render_no_findings_is_concise() -> None:
    md = render_summary_md(aggregate([]))
    assert "no findings" in md


def test_render_groups_by_file() -> None:
    findings = [
        ReviewFinding(reviewer="r1", path="a.py", severity=Severity.WARN, message="watch out", line=42),
        ReviewFinding(reviewer="r2", path="b.py", severity=Severity.BLOCKER, message="never do this"),
    ]
    md = render_summary_md(aggregate(findings))
    assert "## a.py" in md
    assert "## b.py" in md
    assert "[blocker]" in md
    assert "L42" in md
