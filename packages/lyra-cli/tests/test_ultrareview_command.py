"""``/ultrareview`` slash tests (v3.7 L37-7)."""
from __future__ import annotations

from dataclasses import dataclass

from lyra_cli.interactive.ultrareview_command import UltraReviewCommand
from lyra_core.brains.ultrareview import (
    DiffHunk,
    ReviewFinding,
    Reviewer,
    Severity,
    UltraReviewPipeline,
)


@dataclass
class StubReviewer(Reviewer):
    name: str = "stub"
    family: str = "default"
    finding_severity: Severity = Severity.WARN

    def review(self, hunks):
        out = []
        for h in hunks:
            out.append(ReviewFinding(
                reviewer=self.name, path=h.path,
                severity=self.finding_severity, message=f"comment on {h.path}",
            ))
        return out


def _pipe() -> UltraReviewPipeline:
    return UltraReviewPipeline(reviewers=(
        StubReviewer(name="r1", family="anthropic", finding_severity=Severity.WARN),
        StubReviewer(name="r2", family="openai",   finding_severity=Severity.BLOCKER),
    ))


def test_dispatch_no_args_calls_fetcher_with_none() -> None:
    captured: list[str | None] = []

    def fetcher(pr_id):
        captured.append(pr_id)
        return [DiffHunk(path="a.py")]

    cmd = UltraReviewCommand(pipeline=_pipe(), diff_fetcher=fetcher)
    out = cmd.dispatch("")
    assert out.ok
    assert captured == [None]


def test_dispatch_with_pr_id_passes_through() -> None:
    captured: list[str | None] = []

    def fetcher(pr_id):
        captured.append(pr_id)
        return [DiffHunk(path="x.py")]

    cmd = UltraReviewCommand(pipeline=_pipe(), diff_fetcher=fetcher)
    cmd.dispatch("123")
    assert captured == ["123"]


def test_dispatch_collects_findings_in_summary() -> None:
    cmd = UltraReviewCommand(
        pipeline=_pipe(),
        diff_fetcher=lambda _pr: [DiffHunk(path="x.py"), DiffHunk(path="y.py")],
    )
    out = cmd.dispatch("")
    assert out.ok
    assert out.summary is not None
    # Each hunk gets a finding from each of two reviewers.
    assert len(out.summary.findings) == 4
    assert out.summary.has_blockers


def test_dispatch_diff_fetch_failure_returns_error() -> None:
    def fetcher(_pr):
        raise RuntimeError("git not found")

    cmd = UltraReviewCommand(pipeline=_pipe(), diff_fetcher=fetcher)
    out = cmd.dispatch("")
    assert not out.ok
    assert "git not found" in out.message
