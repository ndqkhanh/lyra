"""``/ultrareview`` slash command (v3.7 L37-7).

Drives :class:`lyra_core.brains.ultrareview.UltraReviewPipeline` from
the REPL. Two forms:

* ``/ultrareview`` — review the current branch's diff vs ``main``.
* ``/ultrareview <pr-id>`` — review the diff of a GitHub PR (the
  diff fetcher is operator-supplied so tests don't hit GitHub).
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from lyra_core.brains.ultrareview import (
    DiffHunk,
    ReviewSummary,
    UltraReviewPipeline,
    render_summary_md,
)

# Caller-supplied diff fetchers. Production wires git + gh; tests inject
# deterministic fakes.
DiffFetcher = Callable[[str | None], Iterable[DiffHunk]]


@dataclass(frozen=True)
class UltraReviewCommandResult:
    ok: bool
    message: str
    summary: ReviewSummary | None = None


@dataclass
class UltraReviewCommand:
    """``/ultrareview`` slash."""

    pipeline: UltraReviewPipeline
    diff_fetcher: DiffFetcher

    def dispatch(self, args: str) -> UltraReviewCommandResult:
        parts = args.strip().split()
        pr_id: str | None = parts[0] if parts else None
        try:
            hunks = list(self.diff_fetcher(pr_id))
        except Exception as exc:                       # noqa: BLE001 — surface
            return UltraReviewCommandResult(
                ok=False, message=f"diff fetch failed: {exc!r}",
            )
        summary = self.pipeline.run(hunks)
        return UltraReviewCommandResult(
            ok=True,
            message=render_summary_md(summary),
            summary=summary,
        )


__all__ = ["UltraReviewCommand", "UltraReviewCommandResult"]
