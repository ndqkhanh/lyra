"""Multi-agent voting, confidence-weighted aggregation, and consensus building."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from lyra_agent_swarm.exceptions import ConsensusError


class VoteChoice(Enum):
    """Available vote options for a consensus proposal."""

    APPROVE = auto()
    REJECT = auto()
    ABSTAIN = auto()
    NEEDS_DISCUSSION = auto()


class AggregationMethod(Enum):
    """Method used to aggregate votes into a consensus result."""

    MAJORITY = auto()
    SUPERMAJORITY = auto()
    WEIGHTED = auto()
    UNANIMOUS = auto()


@dataclass(frozen=True)
class Proposal:
    """A proposal submitted for multi-agent consensus."""

    proposal_id: str
    content: str
    proposer: str
    deadline: float | None = None


@dataclass(frozen=True)
class Vote:
    """A single agent's vote on a proposal."""

    agent_id: str
    proposal_id: str
    choice: VoteChoice
    confidence: float = 1.0
    reasoning: str = ""


@dataclass(frozen=True)
class ConsensusResult:
    """Outcome of a consensus building process."""

    proposal: Proposal
    votes: tuple[Vote, ...]
    passed: bool
    confidence: float
    dissenting_opinions: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConsensusConfig:
    """Configuration governing consensus behaviour."""

    method: AggregationMethod = AggregationMethod.MAJORITY
    min_participation: float = 0.5
    timeout: float = 300.0


class ConsensusBuilder:
    """Collects votes and builds consensus results using configurable aggregation."""

    def __init__(self, config: ConsensusConfig | None = None) -> None:
        self._config = config or ConsensusConfig()
        self._proposals: dict[str, Proposal] = {}
        self._votes: dict[str, list[Vote]] = {}

    @property
    def config(self) -> ConsensusConfig:
        return self._config

    def submit_proposal(self, proposal: Proposal) -> None:
        if proposal.proposal_id in self._proposals:
            raise ConsensusError(f"Proposal '{proposal.proposal_id}' already exists")
        self._proposals[proposal.proposal_id] = proposal
        self._votes[proposal.proposal_id] = []

    def cast_vote(self, vote: Vote) -> None:
        if vote.proposal_id not in self._proposals:
            raise ConsensusError(f"Unknown proposal '{vote.proposal_id}'")
        proposal = self._proposals[vote.proposal_id]
        if proposal.deadline is not None and time.time() > proposal.deadline:
            raise ConsensusError(f"Proposal '{vote.proposal_id}' has passed its deadline")
        self._votes[vote.proposal_id].append(vote)

    def build_consensus(
        self,
        proposal: Proposal,
        agents: list[Any],
        method: AggregationMethod | None = None,
    ) -> ConsensusResult:
        """Aggregate votes for a proposal using the specified method."""
        method = method or self._config.method
        stored_votes = self._votes.get(proposal.proposal_id, [])

        # Check minimum participation
        if len(stored_votes) < max(1, int(len(agents) * self._config.min_participation)):
            raise ConsensusError(
                f"Insufficient participation: {len(stored_votes)} of {len(agents)} agents voted"
            )

        if method == AggregationMethod.MAJORITY:
            return self._majority(proposal, stored_votes)
        elif method == AggregationMethod.SUPERMAJORITY:
            return self._supermajority(proposal, stored_votes)
        elif method == AggregationMethod.WEIGHTED:
            return self.weighted_vote(stored_votes, proposal)
        elif method == AggregationMethod.UNANIMOUS:
            return self._unanimous(proposal, stored_votes)
        else:
            raise ConsensusError(f"Unknown aggregation method '{method}'")

    def weighted_vote(
        self,
        votes: list[Vote],
        proposal: Proposal | None = None,
    ) -> ConsensusResult:
        """Confidence-weighted vote aggregation."""
        if not votes:
            raise ConsensusError("No votes to aggregate")

        resolved = proposal
        if resolved is None:
            first = votes[0]
            stored = self._proposals.get(first.proposal_id)
            if stored is None:
                raise ConsensusError("Cannot determine proposal from votes and no proposal provided")
            resolved = stored

        total_weight = sum(v.confidence for v in votes if v.choice != VoteChoice.ABSTAIN)
        approve_weight = sum(
            v.confidence for v in votes if v.choice == VoteChoice.APPROVE
        )
        if total_weight == 0:
            return ConsensusResult(
                proposal=resolved,
                votes=tuple(votes),
                passed=False,
                confidence=0.0,
                dissenting_opinions=tuple(
                    v.reasoning for v in votes if v.choice == VoteChoice.REJECT and v.reasoning
                ),
            )

        confidence = approve_weight / total_weight
        passed = confidence > 0.5
        dissenting = tuple(
            v.reasoning for v in votes if v.choice == VoteChoice.REJECT and v.reasoning
        )
        return ConsensusResult(
            proposal=resolved,
            votes=tuple(votes),
            passed=passed,
            confidence=confidence,
            dissenting_opinions=dissenting,
        )

    def _majority(self, proposal: Proposal, votes: list[Vote]) -> ConsensusResult:
        active_votes = [v for v in votes if v.choice != VoteChoice.ABSTAIN]
        if not active_votes:
            return ConsensusResult(
                proposal=proposal,
                votes=tuple(votes),
                passed=False,
                confidence=0.0,
            )
        approve_count = sum(1 for v in active_votes if v.choice == VoteChoice.APPROVE)
        passed = approve_count > len(active_votes) / 2
        return ConsensusResult(
            proposal=proposal,
            votes=tuple(votes),
            passed=passed,
            confidence=approve_count / len(active_votes),
            dissenting_opinions=tuple(
                v.reasoning for v in votes if v.choice == VoteChoice.REJECT and v.reasoning
            ),
        )

    def _supermajority(self, proposal: Proposal, votes: list[Vote]) -> ConsensusResult:
        active_votes = [v for v in votes if v.choice != VoteChoice.ABSTAIN]
        if not active_votes:
            return ConsensusResult(
                proposal=proposal,
                votes=tuple(votes),
                passed=False,
                confidence=0.0,
            )
        approve_count = sum(1 for v in active_votes if v.choice == VoteChoice.APPROVE)
        passed = approve_count >= len(active_votes) * 2 / 3
        return ConsensusResult(
            proposal=proposal,
            votes=tuple(votes),
            passed=passed,
            confidence=approve_count / len(active_votes),
            dissenting_opinions=tuple(
                v.reasoning for v in votes if v.choice == VoteChoice.REJECT and v.reasoning
            ),
        )

    def _unanimous(self, proposal: Proposal, votes: list[Vote]) -> ConsensusResult:
        active_votes = [v for v in votes if v.choice != VoteChoice.ABSTAIN]
        if not active_votes:
            return ConsensusResult(
                proposal=proposal,
                votes=tuple(votes),
                passed=False,
                confidence=0.0,
            )
        approve_count = sum(1 for v in active_votes if v.choice == VoteChoice.APPROVE)
        passed = approve_count == len(active_votes)
        return ConsensusResult(
            proposal=proposal,
            votes=tuple(votes),
            passed=passed,
            confidence=1.0 if passed else 0.0,
            dissenting_opinions=tuple(
                v.reasoning for v in votes if v.choice == VoteChoice.REJECT and v.reasoning
            ),
        )

    def get_votes(self, proposal_id: str) -> list[Vote]:
        return list(self._votes.get(proposal_id, []))

    def get_proposal(self, proposal_id: str) -> Proposal | None:
        return self._proposals.get(proposal_id)
