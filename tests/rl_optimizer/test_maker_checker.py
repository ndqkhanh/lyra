"""
Tests for MakerChecker — two-role proposal workflow for safe self-evolution.

Covers:
- Proposal and CheckResult construction (including __post_init__)
- MakerChecker propose / verify lifecycle
- Status transitions (PENDING -> VERIFIED, PENDING -> REJECTED)
- Error paths (missing proposal, missing rejection reason)
- Query methods (get_proposal, get_check_results, get_pending_proposals)
- Audit trail export
- Statistics aggregation
"""

from __future__ import annotations

import time

import pytest

from lyra.rl_optimizer.gepa_optimizer import Gene
from lyra.rl_optimizer.maker_checker import (
    CheckResult,
    MakerChecker,
    Proposal,
    ProposalStatus,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def gene() -> Gene:
    return Gene(
        summary="test gene",
        matching_signals=("signal_a", "signal_b"),
        strategy_steps=("step_1", "step_2"),
        avoid_cues=("avoid_this",),
        constraints=("constraint_1",),
    )


@pytest.fixture
def sample_proposal(gene: Gene) -> Proposal:
    return Proposal(
        proposal_id="prop-001",
        maker_id="agent-alpha",
        gene=gene,
        evidence=("score=0.95", "no_regression"),
        maker_signature="abc123",
        status=ProposalStatus.PENDING,
        created_at=1000.0,
        expires_at=2000.0,
    )


# =============================================================================
# Proposal
# =============================================================================


class TestProposal:
    def test_minimal_construction(self, gene: Gene) -> None:
        proposal = Proposal(
            proposal_id="p1",
            maker_id="m1",
            gene=gene,
        )
        assert proposal.proposal_id == "p1"
        assert proposal.maker_id == "m1"
        assert proposal.status == ProposalStatus.PENDING
        assert proposal.evidence == ()
        assert proposal.maker_signature == ""
        assert proposal.metadata == {}
        assert proposal.created_at > 0
        assert proposal.expires_at > proposal.created_at

    def test_post_init_sets_created_at(self, gene: Gene) -> None:
        """created_at defaults to time.time() when left as 0.0."""
        before = time.time()
        proposal = Proposal(
            proposal_id="p2", maker_id="m2", gene=gene,
        )
        after = time.time()
        assert before <= proposal.created_at <= after

    def test_post_init_sets_expires_at(self, gene: Gene) -> None:
        """expires_at defaults to created_at + deadline when left as 0.0."""
        proposal = Proposal(
            proposal_id="p3", maker_id="m3", gene=gene,
            created_at=5000.0,
        )
        assert proposal.expires_at > proposal.created_at

    def test_is_expired_true(self, gene: Gene) -> None:
        proposal = Proposal(
            proposal_id="p4", maker_id="m4", gene=gene,
            created_at=1.0,
            expires_at=1.0,  # already past
        )
        assert proposal.is_expired

    def test_is_expired_false(self, gene: Gene) -> None:
        proposal = Proposal(
            proposal_id="p5", maker_id="m5", gene=gene,
            created_at=time.time(),
            expires_at=time.time() + 3600,
        )
        assert not proposal.is_expired

    def test_frozen(self, gene: Gene) -> None:
        proposal = Proposal(
            proposal_id="p6", maker_id="m6", gene=gene,
        )
        with pytest.raises(AttributeError):
            proposal.status = ProposalStatus.VERIFIED  # type: ignore[misc]


# =============================================================================
# CheckResult
# =============================================================================


class TestCheckResult:
    def test_minimal(self) -> None:
        result = CheckResult(passed=True, checker_id="checker-01")
        assert result.passed
        assert result.checker_id == "checker-01"
        assert result.evidence == ()
        assert result.reason == ""
        assert result.checked_at > 0
        assert result.metadata == {}

    def test_post_init_sets_checked_at(self) -> None:
        before = time.time()
        result = CheckResult(passed=False, checker_id="c1", reason="bad")
        after = time.time()
        assert before <= result.checked_at <= after

    def test_rejection_reason(self) -> None:
        result = CheckResult(
            passed=False,
            checker_id="c2",
            reason="Evidence quality too low",
            evidence=("score=0.3",),
        )
        assert not result.passed
        assert "Evidence quality" in result.reason
        assert len(result.evidence) == 1

    def test_frozen(self) -> None:
        result = CheckResult(passed=True, checker_id="c3")
        with pytest.raises(AttributeError):
            result.passed = False  # type: ignore[misc]


# =============================================================================
# MakerChecker
# =============================================================================


class TestMakerCheckerPropose:
    async def test_propose_creates_proposal(self, gene: Gene) -> None:
        mc = MakerChecker()
        proposal = await mc.propose(
            maker_id="agent-alpha",
            gene=gene,
            evidence=["score=0.95", "no_regression"],
        )
        assert proposal.proposal_id is not None
        assert proposal.maker_id == "agent-alpha"
        assert proposal.gene is gene
        assert len(proposal.evidence) == 2
        assert proposal.status == ProposalStatus.PENDING
        assert proposal.maker_signature != ""
        assert len(proposal.maker_signature) == 16
        assert proposal.metadata.get("maker_checker_version") is not None

    async def test_propose_without_evidence(self, gene: Gene) -> None:
        mc = MakerChecker()
        proposal = await mc.propose(maker_id="agent-alpha", gene=gene)
        assert proposal.evidence == ()
        assert proposal.maker_signature != ""

    async def test_propose_stores_in_registry(self, gene: Gene) -> None:
        mc = MakerChecker()
        proposal = await mc.propose(maker_id="agent-alpha", gene=gene)
        assert mc.proposals[proposal.proposal_id] is proposal


class TestMakerCheckerVerify:
    async def test_verify_passed(self, gene: Gene) -> None:
        mc = MakerChecker()
        proposal = await mc.propose(maker_id="maker", gene=gene)
        result = await mc.verify(
            proposal_id=proposal.proposal_id,
            checker_id="checker",
            passed=True,
            evidence=["all_good"],
            reason="All checks passed",
        )
        assert result.passed
        assert result.checker_id == "checker"
        assert len(result.evidence) == 1
        assert mc.proposals[proposal.proposal_id].status == ProposalStatus.VERIFIED

    async def test_verify_rejected(self, gene: Gene) -> None:
        mc = MakerChecker()
        proposal = await mc.propose(maker_id="maker", gene=gene)
        result = await mc.verify(
            proposal_id=proposal.proposal_id,
            checker_id="checker",
            passed=False,
            reason="Regression detected",
        )
        assert not result.passed
        assert mc.proposals[proposal.proposal_id].status == ProposalStatus.REJECTED

    async def test_verify_rejection_requires_reason(self, gene: Gene) -> None:
        mc = MakerChecker()
        proposal = await mc.propose(maker_id="maker", gene=gene)
        with pytest.raises(ValueError, match="rejection reason"):
            await mc.verify(
                proposal_id=proposal.proposal_id,
                checker_id="checker",
                passed=False,
                reason="",
            )

    async def test_verify_nonexistent_proposal(self, gene: Gene) -> None:
        mc = MakerChecker()
        with pytest.raises(KeyError, match="nonexistent"):
            await mc.verify(
                proposal_id="nonexistent",
                checker_id="checker",
                passed=True,
            )

    async def test_verify_appends_check_results(self, gene: Gene) -> None:
        mc = MakerChecker()
        proposal = await mc.propose(maker_id="maker", gene=gene)
        await mc.verify(proposal_id=proposal.proposal_id, checker_id="c1", passed=True)
        await mc.verify(proposal_id=proposal.proposal_id, checker_id="c2", passed=False, reason="bad")
        results = mc.check_results[proposal.proposal_id]
        assert len(results) == 2
        assert results[0].checker_id == "c1"
        assert results[1].checker_id == "c2"


class TestMakerCheckerQueries:
    async def test_get_proposal_found(self, gene: Gene) -> None:
        mc = MakerChecker()
        prop = await mc.propose(maker_id="m", gene=gene)
        assert mc.get_proposal(prop.proposal_id) is prop

    async def test_get_proposal_not_found(self) -> None:
        mc = MakerChecker()
        assert mc.get_proposal("nope") is None

    async def test_get_check_results_found(self, gene: Gene) -> None:
        mc = MakerChecker()
        prop = await mc.propose(maker_id="m", gene=gene)
        await mc.verify(prop.proposal_id, "c1", passed=False, reason="bad")
        results = mc.get_check_results(prop.proposal_id)
        assert len(results) == 1

    async def test_get_check_results_not_found(self) -> None:
        mc = MakerChecker()
        assert mc.get_check_results("nope") == []

    async def test_get_pending_proposals(self, gene: Gene) -> None:
        mc = MakerChecker()
        p1 = await mc.propose(maker_id="m1", gene=gene)
        p2 = await mc.propose(maker_id="m2", gene=gene)
        await mc.verify(p1.proposal_id, "c1", passed=True)
        pending = mc.get_pending_proposals()
        assert p1 not in pending
        assert p2 in pending

    async def test_get_pending_proposals_expired_is_filtered(self, gene: Gene) -> None:
        mc = MakerChecker()
        prop = Proposal(
            proposal_id="expired",
            maker_id="m",
            gene=gene,
            created_at=1.0,
            expires_at=1.0,
        )
        mc.proposals["expired"] = prop
        pending = mc.get_pending_proposals()
        assert prop not in pending

    async def test_get_audit_trail(self, gene: Gene) -> None:
        mc = MakerChecker()
        prop = await mc.propose(maker_id="m", gene=gene)
        await mc.verify(prop.proposal_id, "c1", passed=False, reason="bad")
        trail = mc.get_audit_trail(prop.proposal_id)
        assert trail["final_status"] == "rejected"
        assert trail["proposal"]["maker_id"] == "m"
        assert len(trail["check_results"]) == 1
        assert trail["check_results"][0]["passed"] is False

    async def test_get_audit_trail_missing(self) -> None:
        mc = MakerChecker()
        trail = mc.get_audit_trail("nonexistent")
        assert "error" in trail

    async def test_get_statistics(self, gene: Gene) -> None:
        mc = MakerChecker()
        p1 = await mc.propose(maker_id="m1", gene=gene)
        p2 = await mc.propose(maker_id="m2", gene=gene)
        p3 = await mc.propose(maker_id="m3", gene=gene)
        await mc.verify(p1.proposal_id, "c1", passed=True)
        await mc.verify(p2.proposal_id, "c2", passed=False, reason="bad")
        # p3 stays pending
        stats = mc.get_statistics()
        assert stats["total_proposals"] == 3
        assert stats["status_counts"]["pending"] == 1
        assert stats["status_counts"]["verified"] == 1
        assert stats["status_counts"]["rejected"] == 1
        assert stats["total_verifications"] == 2
        assert stats["passed_verifications"] == 1
        assert stats["protocol_version"] == "1.0.0"


# =============================================================================
# ProposalStatus enum
# =============================================================================


class TestProposalStatus:
    def test_values(self) -> None:
        assert ProposalStatus.PENDING.value == "pending"
        assert ProposalStatus.VERIFIED.value == "verified"
        assert ProposalStatus.REJECTED.value == "rejected"
        assert ProposalStatus.EXPIRED.value == "expired"
