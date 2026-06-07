"""
Tests for Adversarial Verification Panel (P4).

Covers:
- All five lenses produce a ReviewerVote
- Majority vote aggregation (passed vs refuted)
- Unanimous-required mode
- Custom lens subset via judge_custom
- Default lens list (all five)
- review_fn / async_reviewer_fn dispatch
- Consensus summary formatting
"""

import pytest

from src.verification.panel import (
    AdversarialPanel,
    Lens,
    LENS_DESCRIPTIONS,
    ReviewResult,
    ReviewerVote,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pass_fn(custom: dict[Lens, bool] | None = None) -> callable:
    """Return a sync reviewer_fn that passes everything by default."""

    def fn(subject: str, lens: Lens) -> ReviewerVote:
        passed = True
        if custom and lens in custom:
            passed = custom[lens]
        reason = "Looks correct." if passed else f"{lens.value} issue detected."
        return ReviewerVote(lens=lens, passed=passed, reason=reason)

    return fn


def _make_async_pass_fn(custom: dict[Lens, bool] | None = None) -> callable:
    """Return an async reviewer_fn for testing the async branch."""

    async def fn(subject: str, lens: Lens) -> ReviewerVote:
        passed = True
        if custom and lens in custom:
            passed = custom[lens]
        reason = "Looks correct." if passed else f"{lens.value} issue detected."
        return ReviewerVote(lens=lens, passed=passed, reason=reason)

    return fn


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLensEnum:
    """Verify the Lens enum and descriptions."""

    def test_all_lenses_have_descriptions(self):
        assert len(list(Lens)) == len(LENS_DESCRIPTIONS)
        for lens in Lens:
            assert lens in LENS_DESCRIPTIONS
            assert len(LENS_DESCRIPTIONS[lens]) > 20

    def test_lens_values_unique(self):
        values = [lens.value for lens in Lens]
        assert len(values) == len(set(values))


class TestReviewerVote:
    """Verify dataclass creation."""

    def test_basic_vote_creation(self):
        vote = ReviewerVote(lens=Lens.CORRECTNESS, passed=True, reason="OK")
        assert vote.lens == Lens.CORRECTNESS
        assert vote.passed is True
        assert vote.confidence == 1.0  # default

    def test_refuted_vote(self):
        vote = ReviewerVote(
            lens=Lens.SECURITY, passed=False, reason="SQL injection risk",
            confidence=0.95,
        )
        assert vote.passed is False
        assert vote.confidence == 0.95


class TestAdversarialPanelSync:
    """Test AdversarialPanel with a synchronous reviewer_fn."""

    def test_all_lenses_default(self):
        """Default lenses should include all five."""
        panel = AdversarialPanel(reviewer_fn=_make_pass_fn())
        assert len(panel._lenses) == 5

    def test_custom_lenses(self):
        """Non-default lens list is accepted."""
        panel = AdversarialPanel(
            lenses=[Lens.CORRECTNESS, Lens.SECURITY],
            reviewer_fn=_make_pass_fn(),
        )
        assert len(panel._lenses) == 2

    @pytest.mark.asyncio
    async def test_judge_all_pass(self):
        """When all reviewers pass, majority passes."""
        panel = AdversarialPanel(reviewer_fn=_make_pass_fn())
        result = await panel.judge("def foo(): pass")

        assert result.passed_count == 5
        assert result.refuted_count == 0
        assert result.majority_passed is True
        assert result.majority_refutes is False
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_judge_majority_refutes(self):
        """When 3+ out of 5 refute, majority_refutes is True."""
        custom = {
            Lens.CORRECTNESS: False,
            Lens.SECURITY: False,
            Lens.PERFORMANCE: False,
            Lens.STYLE: True,
            Lens.CONSISTENCY: True,
        }
        panel = AdversarialPanel(reviewer_fn=_make_pass_fn(custom))
        result = await panel.judge("some bad code")

        assert result.refuted_count == 3
        assert result.passed_count == 2
        assert result.majority_refutes is True
        assert result.passed is False  # convenience property

    @pytest.mark.asyncio
    async def test_judge_tie_does_not_refute(self):
        """A 2-2-1 tie (or 2-pass 2-refute 1-neutral) should not refute
        if refuted <= half."""
        custom = {
            Lens.CORRECTNESS: False,
            Lens.SECURITY: False,
            Lens.STYLE: True,
            Lens.CONSISTENCY: True,
            Lens.PERFORMANCE: True,  # 3 pass, 2 refute — majority passes
        }
        panel = AdversarialPanel(reviewer_fn=_make_pass_fn(custom))
        result = await panel.judge("tie")

        assert result.passed_count == 3
        assert result.refuted_count == 2
        assert result.majority_refutes is False
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_unanimous_mode_single_refute_fails(self):
        """require_unanimous=True means 1 refute is enough to fail."""
        custom = {
            Lens.SECURITY: False,  # only one refute
        }
        panel = AdversarialPanel(
            reviewer_fn=_make_pass_fn(custom),
            require_unanimous=True,
        )
        result = await panel.judge("code")

        assert result.refuted_count == 1
        assert result.majority_refutes is True
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_unanimous_all_pass(self):
        """require_unanimous=True, all pass -> majority_passed True."""
        panel = AdversarialPanel(
            reviewer_fn=_make_pass_fn(),
            require_unanimous=True,
        )
        result = await panel.judge("perfect code")

        assert result.passed_count == 5
        assert result.refuted_count == 0
        assert result.majority_passed is True
        assert result.majority_refutes is False

    @pytest.mark.asyncio
    async def test_judge_custom_lenses_subset(self):
        """judge_custom with only 2 lenses should return 2 votes."""
        panel = AdversarialPanel(reviewer_fn=_make_pass_fn())
        result = await panel.judge_custom(
            "code", lenses=[Lens.CORRECTNESS, Lens.STYLE]
        )

        assert result.total_reviewers == 2
        assert len(result.votes) == 2
        assert result.passed_count == 2


class TestAdversarialPanelAsync:
    """Test AdversarialPanel with an async reviewer_fn."""

    @pytest.mark.asyncio
    async def test_async_reviewer_dispatch(self):
        """Async reviewer function should be used when provided."""
        panel = AdversarialPanel(async_reviewer_fn=_make_async_pass_fn())
        result = await panel.judge("test")

        assert result.passed_count == 5
        assert result.majority_passed is True

    @pytest.mark.asyncio
    async def test_async_precedence_over_sync(self):
        """Async fn takes precedence over sync fn when both provided."""

        async def async_fn(subject: str, lens: Lens) -> ReviewerVote:
            return ReviewerVote(lens=lens, passed=True, reason="async")

        def sync_fn(subject: str, lens: Lens) -> ReviewerVote:
            return ReviewerVote(lens=lens, passed=False, reason="sync")

        panel = AdversarialPanel(
            reviewer_fn=sync_fn,
            async_reviewer_fn=async_fn,
        )
        result = await panel.judge("test")

        # Should use async_fn which passes
        assert result.passed_count == 5
        # "async" contains "sync" as substring, so check the reason field directly
        for vote in result.votes:
            assert vote.reason == "async"


class TestAdversarialPanelErrors:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_no_reviewer_raises(self):
        """judge() without any reviewer_fn configured should raise."""
        panel = AdversarialPanel()

        with pytest.raises(RuntimeError, match="No reviewer_fn"):
            await panel.judge("anything")


class TestReviewResult:
    """Verify ReviewResult helpers."""

    def test_consensus_summary_refutes(self):
        result = ReviewResult(
            votes=(
                ReviewerVote(Lens.SECURITY, False, "Risk found"),
                ReviewerVote(Lens.CORRECTNESS, True, "Correct"),
            ),
            majority_passed=False,
            majority_refutes=True,
            total_reviewers=2,
            passed_count=1,
            refuted_count=1,
        )
        summary = result.consensus_summary
        assert "REFUTES" in summary
        assert "SECURITY" in summary.upper()
        assert "Risk found" in summary

    def test_consensus_summary_passes(self):
        result = ReviewResult(
            votes=(
                ReviewerVote(Lens.STYLE, True, "Clean code"),
                ReviewerVote(Lens.PERFORMANCE, True, "Fast"),
            ),
            majority_passed=True,
            majority_refutes=False,
            total_reviewers=2,
            passed_count=2,
            refuted_count=0,
        )
        summary = result.consensus_summary
        assert "PASSES" in summary
        assert "Clean code" in summary
