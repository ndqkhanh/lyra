"""
Adversarial Verification Panel (P4).

Spawns N independent reviewer agents, each operating through a different
analytical lens (correctness, security, performance, style, consistency).
Votes are aggregated into a majority verdict.

Inspired by constitutional AI / recursive critique patterns:
instead of a single reviewer, use a panel to surface diverse failure modes.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class Lens(str, Enum):
    """Analytical lens that a reviewer agent applies."""

    CORRECTNESS = "correctness"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    CONSISTENCY = "consistency"


LENS_DESCRIPTIONS: dict[Lens, str] = {
    Lens.CORRECTNESS: (
        "Evaluate whether the output is factually correct, logically sound, "
        "and free of reasoning errors. Flag any hallucinated claims or "
        "contradictions."
    ),
    Lens.SECURITY: (
        "Evaluate the output for security vulnerabilities: injection risks, "
        "hardcoded secrets, unsafe deserialisation, path traversal, "
        "auth bypass, or prompt-injection weakness."
    ),
    Lens.PERFORMANCE: (
        "Evaluate the output for performance concerns: unnecessary "
        "computation, large payloads, blocking calls in hot paths, "
        "N+1 queries, and memory leaks."
    ),
    Lens.STYLE: (
        "Evaluate the output for code style, readability, consistency with "
        "project conventions, documentation quality, and adherence to "
        "PEP 8 / type annotation standards."
    ),
    Lens.CONSISTENCY: (
        "Evaluate whether the output is internally consistent: no "
        "self-contradictions, consistent terminology, aligned with "
        "earlier findings, and matching the original specification."
    ),
}


@dataclass(frozen=True)
class ReviewerVote:
    """A single reviewer's assessment through a particular lens."""

    lens: Lens
    passed: bool
    reason: str
    confidence: float = 1.0


@dataclass(frozen=True)
class ReviewResult:
    """Aggregated result from the adversarial panel."""

    votes: tuple[ReviewerVote, ...]
    majority_passed: bool
    majority_refutes: bool
    total_reviewers: int
    passed_count: int
    refuted_count: int

    @property
    def passed(self) -> bool:
        """Convenience: True when the majority does NOT refute the output."""
        return not self.majority_refutes

    @property
    def consensus_summary(self) -> str:
        """Human-readable summary of the panel verdict."""
        if self.majority_refutes:
            refuting = [
                f"[{v.lens.value.upper()}] {v.reason}"
                for v in self.votes
                if not v.passed
            ]
            return (
                f"Panel REFUTES ({self.refuted_count}/{self.total_reviewers}):\n"
                + "\n".join(refuting)
            )
        return (
            f"Panel PASSES ({self.passed_count}/{self.total_reviewers}):\n"
            + "\n".join(f"[{v.lens.value.upper()}] {v.reason}" for v in self.votes if v.passed)
        )


ReviewerFn = Callable[[str, Lens], ReviewerVote]

# ---------------------------------------------------------------------------
# AdversarialPanel
# ---------------------------------------------------------------------------


class AdversarialPanel:
    """
    Spawn N independent reviewer agents, each with a distinct analytical lens.

    Usage::

        panel = AdversarialPanel(reviewer_fn=my_async_reviewer)
        result = await panel.judge("def foo(): pass")

    The caller supplies a ``reviewer_fn`` that, given a subject string and a
    ``Lens``, returns a ``ReviewerVote``.  In production this function would
    invoke an LLM; in tests a simple rule-based mock works.
    """

    def __init__(
        self,
        lenses: list[Lens] | None = None,
        reviewer_fn: ReviewerFn | None = None,
        async_reviewer_fn: Callable[[str, Lens], Any] | None = None,
        require_unanimous: bool = False,
    ) -> None:
        """
        Args:
            lenses: The set of lenses to apply.  Defaults to all five.
            reviewer_fn: Synchronous callable ``(subject, lens) -> ReviewerVote``.
            async_reviewer_fn: Async callable ``(subject, lens) -> ReviewerVote``.
                Takes precedence over ``reviewer_fn`` when provided.
            require_unanimous: If True, a single refute is enough to fail.
        """
        self._lenses = lenses or list(Lens)
        self._reviewer_fn = reviewer_fn
        self._async_reviewer_fn = async_reviewer_fn
        self._require_unanimous = require_unanimous

    # -- Public API -----------------------------------------------------------

    async def judge(self, subject: str) -> ReviewResult:
        """
        Run all reviewers against *subject* and return an aggregated verdict.

        Args:
            subject: The text, code, or output to be reviewed.

        Returns:
            ``ReviewResult`` with individual votes and majority verdict.
        """
        votes = await asyncio.gather(
            *[self._review_lens(subject, lens) for lens in self._lenses]
        )

        passed = [v for v in votes if v.passed]
        refuted = [v for v in votes if not v.passed]

        total = len(votes)
        passed_count = len(passed)
        refuted_count = len(refuted)

        if self._require_unanimous:
            majority_refutes = refuted_count > 0
            majority_passed = refuted_count == 0
        else:
            majority_refutes = refuted_count > total / 2
            majority_passed = passed_count > total / 2

        return ReviewResult(
            votes=tuple(votes),
            majority_passed=majority_passed,
            majority_refutes=majority_refutes,
            total_reviewers=total,
            passed_count=passed_count,
            refuted_count=refuted_count,
        )

    async def judge_custom(
        self, subject: str, lenses: list[Lens]
    ) -> ReviewResult:
        """
        Run only a subset of lenses against *subject*.

        Useful when the caller already knows which lenses are relevant.
        """
        votes = await asyncio.gather(
            *[self._review_lens(subject, lens) for lens in lenses]
        )

        passed = [v for v in votes if v.passed]
        refuted = [v for v in votes if not v.passed]
        total = len(votes)

        if self._require_unanimous:
            majority_refutes = refuted_count_final if (refuted_count_final := len(refuted)) > 0 else False
            majority_passed = len(refuted) == 0
        else:
            majority_refutes = len(refuted) > total / 2
            majority_passed = len(passed) > total / 2

        return ReviewResult(
            votes=tuple(votes),
            majority_passed=majority_passed,
            majority_refutes=majority_refutes,
            total_reviewers=total,
            passed_count=len(passed),
            refuted_count=len(refuted),
        )

    # -- Private helpers ------------------------------------------------------

    async def _review_lens(self, subject: str, lens: Lens) -> ReviewerVote:
        """Review *subject* through a single lens."""
        if self._async_reviewer_fn is not None:
            return await self._async_reviewer_fn(subject, lens)

        if self._reviewer_fn is not None:
            # Run sync reviewer in a thread to avoid blocking the event loop.
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None, self._reviewer_fn, subject, lens
            )

        raise RuntimeError(
            "No reviewer_fn or async_reviewer_fn configured on AdversarialPanel."
        )
