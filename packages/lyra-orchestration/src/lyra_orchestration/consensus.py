"""
Consensus Protocol - Voting mechanism for agent decisions.

Supports multiple voting strategies:
- Majority: >50% approval required
- Unanimous: 100% approval required
- Weighted: Votes weighted by agent expertise
- Quorum: Minimum participation threshold
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4


class VotingStrategy(Enum):
    """Voting strategy types."""

    MAJORITY = "majority"  # >50% approval
    UNANIMOUS = "unanimous"  # 100% approval
    WEIGHTED = "weighted"  # Weighted by expertise
    QUORUM = "quorum"  # Minimum participation threshold


class VoteChoice(Enum):
    """Vote choices."""

    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


@dataclass(frozen=True)
class Vote:
    """Individual vote."""

    voter_id: str
    choice: VoteChoice
    weight: float = 1.0
    reason: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class Proposal:
    """Consensus proposal."""

    proposal_id: str
    topic: str
    description: str
    options: List[str]
    proposer_id: str
    voters: Set[str]
    strategy: VotingStrategy
    quorum: float = 0.5  # Minimum participation (0.0-1.0)
    timeout: int = 300  # Seconds
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ProposalState:
    """Mutable proposal state."""

    proposal: Proposal
    votes: Dict[str, Vote] = field(default_factory=dict)
    decided: bool = False
    decision: Optional[str] = None
    decided_at: Optional[datetime] = None


class ConsensusProtocol:
    """
    Consensus protocol for agent decision-making.

    Features:
    - Multiple voting strategies
    - Quorum requirements
    - Weighted voting
    - Timeout handling
    - Conflict resolution
    """

    def __init__(self):
        """Initialize consensus protocol."""
        self._proposals: Dict[str, ProposalState] = {}
        self._decision_events: Dict[str, asyncio.Event] = {}

    async def propose(
        self,
        topic: str,
        description: str,
        options: List[str],
        proposer_id: str,
        voters: Set[str],
        strategy: VotingStrategy = VotingStrategy.MAJORITY,
        quorum: float = 0.5,
        timeout: int = 300,
    ) -> str:
        """
        Create a new proposal.

        Args:
            topic: Proposal topic
            description: Detailed description
            options: List of options to vote on
            proposer_id: ID of proposing agent
            voters: Set of eligible voter IDs
            strategy: Voting strategy
            quorum: Minimum participation (0.0-1.0)
            timeout: Timeout in seconds

        Returns:
            Proposal ID
        """
        proposal_id = str(uuid4())

        proposal = Proposal(
            proposal_id=proposal_id,
            topic=topic,
            description=description,
            options=options,
            proposer_id=proposer_id,
            voters=voters,
            strategy=strategy,
            quorum=quorum,
            timeout=timeout,
        )

        self._proposals[proposal_id] = ProposalState(proposal=proposal)
        self._decision_events[proposal_id] = asyncio.Event()

        # Start timeout task
        asyncio.create_task(self._handle_timeout(proposal_id, timeout))

        return proposal_id

    async def vote(
        self,
        proposal_id: str,
        voter_id: str,
        choice: VoteChoice,
        weight: float = 1.0,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Cast a vote on a proposal.

        Args:
            proposal_id: Proposal ID
            voter_id: Voter ID
            choice: Vote choice
            weight: Vote weight (for weighted voting)
            reason: Optional reason for vote

        Returns:
            True if vote accepted, False otherwise
        """
        if proposal_id not in self._proposals:
            return False

        state = self._proposals[proposal_id]

        # Check if already decided
        if state.decided:
            return False

        # Check if voter is eligible
        if voter_id not in state.proposal.voters:
            return False

        # Check if already voted
        if voter_id in state.votes:
            return False

        # Record vote
        vote = Vote(
            voter_id=voter_id,
            choice=choice,
            weight=weight,
            reason=reason,
        )
        state.votes[voter_id] = vote

        # Check if decision can be made
        await self._check_decision(proposal_id)

        return True

    async def wait_for_decision(
        self,
        proposal_id: str,
        timeout: Optional[int] = None,
    ) -> Optional[str]:
        """
        Wait for proposal decision.

        Args:
            proposal_id: Proposal ID
            timeout: Optional timeout in seconds

        Returns:
            Decision result or None if timeout
        """
        if proposal_id not in self._proposals:
            return None

        event = self._decision_events[proposal_id]

        try:
            if timeout:
                await asyncio.wait_for(event.wait(), timeout=timeout)
            else:
                await event.wait()

            state = self._proposals[proposal_id]
            return state.decision
        except asyncio.TimeoutError:
            return None

    async def _check_decision(self, proposal_id: str):
        """
        Check if proposal can be decided.

        Args:
            proposal_id: Proposal ID
        """
        state = self._proposals[proposal_id]
        proposal = state.proposal

        # Check quorum
        participation = len(state.votes) / len(proposal.voters)
        if participation < proposal.quorum:
            return

        # Apply voting strategy
        decision = None

        if proposal.strategy == VotingStrategy.MAJORITY:
            decision = self._majority_decision(state)
        elif proposal.strategy == VotingStrategy.UNANIMOUS:
            decision = self._unanimous_decision(state)
        elif proposal.strategy == VotingStrategy.WEIGHTED:
            decision = self._weighted_decision(state)
        elif proposal.strategy == VotingStrategy.QUORUM:
            decision = self._quorum_decision(state)

        if decision:
            state.decided = True
            state.decision = decision
            state.decided_at = datetime.now()
            self._decision_events[proposal_id].set()

    def _majority_decision(self, state: ProposalState) -> Optional[str]:
        """
        Majority voting: >50% approval required.

        Args:
            state: Proposal state

        Returns:
            Decision or None
        """
        approvals = sum(1 for v in state.votes.values() if v.choice == VoteChoice.APPROVE)
        rejections = sum(1 for v in state.votes.values() if v.choice == VoteChoice.REJECT)

        total_votes = len(state.votes)
        if approvals > total_votes / 2:
            return "approved"
        elif rejections > total_votes / 2:
            return "rejected"

        # Check if all votes are in
        if len(state.votes) == len(state.proposal.voters):
            # Tie or majority abstain
            return "rejected"

        return None

    def _unanimous_decision(self, state: ProposalState) -> Optional[str]:
        """
        Unanimous voting: 100% approval required.

        Args:
            state: Proposal state

        Returns:
            Decision or None
        """
        # Any rejection means rejected
        if any(v.choice == VoteChoice.REJECT for v in state.votes.values()):
            return "rejected"

        # All votes in and all approved
        if len(state.votes) == len(state.proposal.voters):
            if all(v.choice == VoteChoice.APPROVE for v in state.votes.values()):
                return "approved"
            return "rejected"

        return None

    def _weighted_decision(self, state: ProposalState) -> Optional[str]:
        """
        Weighted voting: Votes weighted by expertise.

        Args:
            state: Proposal state

        Returns:
            Decision or None
        """
        approve_weight = sum(
            v.weight for v in state.votes.values() if v.choice == VoteChoice.APPROVE
        )
        reject_weight = sum(
            v.weight for v in state.votes.values() if v.choice == VoteChoice.REJECT
        )
        total_weight = approve_weight + reject_weight

        if total_weight > 0 and approve_weight > total_weight / 2:
            return "approved"

        # Check if all votes are in
        if len(state.votes) == len(state.proposal.voters):
            return "rejected"

        return None

    def _quorum_decision(self, state: ProposalState) -> Optional[str]:
        """
        Quorum voting: Minimum participation threshold.

        Args:
            state: Proposal state

        Returns:
            Decision or None
        """
        # Quorum already checked in _check_decision
        # Use majority among participants
        return self._majority_decision(state)

    async def _handle_timeout(self, proposal_id: str, timeout: int):
        """
        Handle proposal timeout.

        Args:
            proposal_id: Proposal ID
            timeout: Timeout in seconds
        """
        await asyncio.sleep(timeout)

        if proposal_id not in self._proposals:
            return

        state = self._proposals[proposal_id]

        if not state.decided:
            # Timeout - reject proposal
            state.decided = True
            state.decision = "timeout"
            state.decided_at = datetime.now()
            self._decision_events[proposal_id].set()

    def get_proposal(self, proposal_id: str) -> Optional[Proposal]:
        """
        Get proposal by ID.

        Args:
            proposal_id: Proposal ID

        Returns:
            Proposal or None
        """
        if proposal_id not in self._proposals:
            return None
        return self._proposals[proposal_id].proposal

    def get_votes(self, proposal_id: str) -> Dict[str, Vote]:
        """
        Get votes for proposal.

        Args:
            proposal_id: Proposal ID

        Returns:
            Dictionary of votes
        """
        if proposal_id not in self._proposals:
            return {}
        return self._proposals[proposal_id].votes.copy()

    def get_stats(self, proposal_id: str) -> Dict[str, Any]:
        """
        Get proposal statistics.

        Args:
            proposal_id: Proposal ID

        Returns:
            Statistics dictionary
        """
        if proposal_id not in self._proposals:
            return {}

        state = self._proposals[proposal_id]
        proposal = state.proposal

        approvals = sum(1 for v in state.votes.values() if v.choice == VoteChoice.APPROVE)
        rejections = sum(1 for v in state.votes.values() if v.choice == VoteChoice.REJECT)
        abstentions = sum(1 for v in state.votes.values() if v.choice == VoteChoice.ABSTAIN)

        return {
            "proposal_id": proposal_id,
            "topic": proposal.topic,
            "total_voters": len(proposal.voters),
            "votes_cast": len(state.votes),
            "participation": len(state.votes) / len(proposal.voters) if len(proposal.voters) > 0 else 0,
            "approvals": approvals,
            "rejections": rejections,
            "abstentions": abstentions,
            "decided": state.decided,
            "decision": state.decision,
        }
