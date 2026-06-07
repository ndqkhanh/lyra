"""
Maker-Checker — two-role proposal workflow for safe self-evolution.

In a maker-checker pattern, one role (Maker) proposes changes and a
second role (Checker) independently verifies them. A change is only
promoted when **both** passes are successful. Rejected proposals
carry a full audit trail.

This implementation applies the pattern to ``Gene`` evolution:
    - Maker proposes a gene mutation with supporting evidence.
    - Checker verifies the proposal (regression safety, evidence
      quality, constraint compliance).
    - Promotion requires BOTH passes; rejection records the reason.

References
----------
    MARS²: Multi-Agent Reinforcement Learning from Automated
        Refinement and Synthetic Data (2026). arXiv:2604.14564v1 —
        two-role verification for safe agent self-evolution.
    SkillOpt: Validation-Gated Text Optimization for Large Language
        Model Skills — Microsoft Research, arXiv:2605.23904v2 —
        gated promotion with independent verification.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from lyra.rl_optimizer.gepa_optimizer import Gene

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAKER_CHECKER_VERSION: str = "1.0.0"
"""Version identifier for the maker-checker protocol."""

DEFAULT_VERIFICATION_DEADLINE_S: float = 86400.0
"""Default deadline (24 hours) for a checker to verify a proposal."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ProposalStatus(Enum):
    """Status of a maker-checker proposal."""

    PENDING = "pending"           # Submitted, awaiting verification
    VERIFIED = "verified"         # Checker approved
    REJECTED = "rejected"         # Checker disapproved
    EXPIRED = "expired"           # Verification deadline passed


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Proposal:
    """A maker's proposal to evolve a gene.

    Attributes:
        proposal_id: Unique identifier for this proposal.
        maker_id: Identifier of the agent that created the proposal.
        gene: The proposed gene (the evolved variant).
        evidence: List of evidence strings supporting the proposal
            (e.g., evaluation scores, trajectory excerpts).
        maker_signature: Cryptographic-style signature (content hash)
            created by the maker to attest the proposal.
        status: Current status of the proposal.
        created_at: Unix timestamp when the proposal was created.
        expires_at: Unix timestamp after which the proposal expires.
        metadata: Optional arbitrary context.
    """

    proposal_id: str
    maker_id: str
    gene: Gene
    evidence: tuple[str, ...] = ()
    maker_signature: str = ""
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: float = 0.0
    expires_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        now = time.time()
        # Use object.__setattr__ because frozen=True
        object.__setattr__(self, "created_at", now if self.created_at == 0.0 else self.created_at)
        object.__setattr__(self, "expires_at", (
            self.created_at + DEFAULT_VERIFICATION_DEADLINE_S
            if self.expires_at == 0.0
            else self.expires_at
        ))

    @property
    def is_expired(self) -> bool:
        """Whether this proposal has passed its verification deadline."""
        return time.time() > self.expires_at


@dataclass(frozen=True)
class CheckResult:
    """Result of a checker's verification of a proposal.

    Attributes:
        passed: ``True`` if the checker approved the proposal.
        checker_id: Identifier of the checker agent.
        evidence: List of evidence strings supporting the verdict.
        reason: Explanation of the verdict (especially useful when
            ``passed=False``).
        checked_at: Unix timestamp of the verification.
        metadata: Optional arbitrary context.
    """

    passed: bool
    checker_id: str
    evidence: tuple[str, ...] = ()
    reason: str = ""
    checked_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.checked_at == 0.0:
            object.__setattr__(self, "checked_at", time.time())


# ---------------------------------------------------------------------------
# MakerChecker
# ---------------------------------------------------------------------------


@dataclass
class MakerChecker:
    """Two-role proposal workflow for safe gene evolution.

    The maker proposes a gene mutation, and an independent checker
    verifies it. A proposal is only promoted when both passes succeed.
    Every rejection records the reason for a full audit trail.

    Usage::

        mc = MakerChecker()

        # Maker proposes
        proposal = await mc.propose(
            maker_id="agent-alpha",
            gene=evolved_gene,
            evidence=["eval_score: 0.92", "no_regression"],
        )

        # Checker verifies
        result = await mc.verify(
            proposal_id=proposal.proposal_id,
            checker_id="agent-beta",
        )
        # result.passed is True/False

    References
    ----------
        MARS² (arXiv:2604.14564v1) — two-role safe evolution.
    """

    proposals: dict[str, Proposal] = field(default_factory=dict)
    check_results: dict[str, list[CheckResult]] = field(default_factory=dict)

    async def propose(
        self,
        maker_id: str,
        gene: Gene,
        evidence: list[str] | None = None,
    ) -> Proposal:
        """Create a new proposal from a maker.

        The proposal is automatically signed with a content hash and
        stored in ``self.proposals``.

        Args:
            maker_id: Identifier of the maker agent.
            gene: The proposed gene (evolved variant).
            evidence: Optional list of supporting evidence strings.

        Returns:
            The created ``Proposal``.
        """
        evidence_tuple = tuple(evidence) if evidence else ()
        proposal_id = str(uuid.uuid4())

        # Create a content signature from the gene and evidence
        signature_content = json.dumps(
            {
                "maker_id": maker_id,
                "gene": {
                    "summary": gene.summary,
                    "signals": list(gene.matching_signals),
                    "steps": list(gene.strategy_steps),
                    "avoid": list(gene.avoid_cues),
                    "constraints": list(gene.constraints),
                },
                "evidence": evidence_tuple,
            },
            sort_keys=True,
        )
        maker_signature = hashlib.sha256(signature_content.encode()).hexdigest()[:16]

        proposal = Proposal(
            proposal_id=proposal_id,
            maker_id=maker_id,
            gene=gene,
            evidence=evidence_tuple,
            maker_signature=maker_signature,
            status=ProposalStatus.PENDING,
            metadata={"maker_checker_version": MAKER_CHECKER_VERSION},
        )
        self.proposals[proposal_id] = proposal
        return proposal

    async def verify(
        self,
        proposal_id: str,
        checker_id: str,
        passed: bool = True,
        evidence: list[str] | None = None,
        reason: str = "",
    ) -> CheckResult:
        """Verify a proposal as a checker.

        The checker evaluates the proposal and records either a pass
        or rejection. The proposal's status is updated accordingly.

        Args:
            proposal_id: The proposal to verify.
            checker_id: Identifier of the checker agent.
            passed: Whether the checker approves the proposal.
            evidence: Optional list of evidence strings supporting
                the verdict.
            reason: Explanation of the verdict (required when
                ``passed=False``).

        Returns:
            A ``CheckResult`` with the verification outcome.

        Raises:
            KeyError: If the proposal does not exist.
            ValueError: If ``reason`` is empty when ``passed=False``.
        """
        proposal = self.proposals.get(proposal_id)
        if proposal is None:
            raise KeyError(f"Proposal '{proposal_id}' not found.")

        if not passed and not reason:
            raise ValueError("A rejection reason is required when passed=False.")

        evidence_tuple = tuple(evidence) if evidence else ()
        result = CheckResult(
            passed=passed,
            checker_id=checker_id,
            evidence=evidence_tuple,
            reason=reason,
        )

        # Update proposal status
        new_status = ProposalStatus.VERIFIED if passed else ProposalStatus.REJECTED
        self.proposals[proposal_id] = Proposal(
            proposal_id=proposal.proposal_id,
            maker_id=proposal.maker_id,
            gene=proposal.gene,
            evidence=proposal.evidence,
            maker_signature=proposal.maker_signature,
            status=new_status,
            created_at=proposal.created_at,
            expires_at=proposal.expires_at,
            metadata=proposal.metadata,
        )

        # Record check result
        if proposal_id not in self.check_results:
            self.check_results[proposal_id] = []
        self.check_results[proposal_id].append(result)

        return result

    def get_proposal(self, proposal_id: str) -> Proposal | None:
        """Look up a proposal by ID.

        Args:
            proposal_id: The proposal identifier.

        Returns:
            The ``Proposal``, or ``None`` if not found.
        """
        return self.proposals.get(proposal_id)

    def get_check_results(self, proposal_id: str) -> list[CheckResult]:
        """Return all verification results for a proposal.

        Args:
            proposal_id: The proposal identifier.

        Returns:
            List of ``CheckResult`` instances (one per verification).
        """
        return self.check_results.get(proposal_id, [])

    def get_pending_proposals(self) -> list[Proposal]:
        """Return all proposals awaiting verification.

        Expired proposals are filtered out.

        Returns:
            List of pending ``Proposal`` instances.
        """
        return [
            p for p in self.proposals.values()
            if p.status == ProposalStatus.PENDING and not p.is_expired
        ]

    def get_audit_trail(self, proposal_id: str) -> dict[str, Any]:
        """Return a full audit trail for a proposal.

        Includes the original proposal, all check results, and the
        final status.

        Args:
            proposal_id: The proposal identifier.

        Returns:
            Dict with ``proposal``, ``check_results``, and
            ``final_status`` keys.
        """
        proposal = self.proposals.get(proposal_id)
        if proposal is None:
            return {"error": f"Proposal '{proposal_id}' not found."}

        return {
            "proposal": {
                "proposal_id": proposal.proposal_id,
                "maker_id": proposal.maker_id,
                "gene_summary": proposal.gene.summary,
                "maker_signature": proposal.maker_signature,
                "evidence_count": len(proposal.evidence),
                "created_at": proposal.created_at,
                "expires_at": proposal.expires_at,
            },
            "check_results": [
                {
                    "passed": r.passed,
                    "checker_id": r.checker_id,
                    "reason": r.reason,
                    "evidence_count": len(r.evidence),
                    "checked_at": r.checked_at,
                }
                for r in self.get_check_results(proposal_id)
            ],
            "final_status": proposal.status.value,
        }

    def get_statistics(self) -> dict[str, Any]:
        """Return summary statistics for the maker-checker system.

        Returns:
            Dict with proposal counts by status and verification
            metrics.
        """
        status_counts: dict[str, int] = {}
        for p in self.proposals.values():
            status_counts[p.status.value] = status_counts.get(p.status.value, 0) + 1

        total_checks = sum(len(v) for v in self.check_results.values())
        passed_checks = sum(
            1 for results in self.check_results.values()
            for r in results if r.passed
        )

        return {
            "total_proposals": len(self.proposals),
            "status_counts": status_counts,
            "total_verifications": total_checks,
            "passed_verifications": passed_checks,
            "protocol_version": MAKER_CHECKER_VERSION,
        }
