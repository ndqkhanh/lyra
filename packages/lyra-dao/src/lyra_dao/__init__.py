"""DAO Governance — decentralized voting, proposals, collective decision-making for agents.

Agents vote on decisions that affect the collective. Proposals, voting, execution.
"""
from __future__ import annotations
import logging, time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

logger = logging.getLogger(__name__)
__all__ = ["ProposalStatus", "Proposal", "DAOManager"]

class ProposalStatus(Enum):
    PENDING = auto()
    VOTING = auto()
    PASSED = auto()
    REJECTED = auto()
    EXECUTED = auto()

@dataclass
class Proposal:
    id: str
    title: str
    description: str
    proposer: str
    status: ProposalStatus = ProposalStatus.PENDING
    votes_for: int = 0
    votes_against: int = 0
    created_at: float = 0.0

class DAOManager:
    def __init__(self, quorum: int = 3, approval_threshold: float = 0.5):
        self.proposals: dict[str, Proposal] = {}
        self.voters: set[str] = set()
        self.quorum = quorum
        self.approval_threshold = approval_threshold
        self._counter = 0

    def register_voter(self, agent_id: str) -> None:
        self.voters.add(agent_id)

    def propose(self, title: str, description: str, proposer: str) -> Proposal:
        self._counter += 1
        proposal = Proposal(id=f"prop_{self._counter}", title=title, description=description, proposer=proposer, created_at=time.time())
        self.proposals[proposal.id] = proposal
        return proposal

    def vote(self, proposal_id: str, in_favor: bool) -> bool:
        proposal = self.proposals.get(proposal_id)
        if not proposal or proposal.status != ProposalStatus.VOTING:
            return False
        if in_favor: proposal.votes_for += 1
        else: proposal.votes_against += 1
        total = proposal.votes_for + proposal.votes_against
        if total >= self.quorum:
            if proposal.votes_for / total >= self.approval_threshold:
                proposal.status = ProposalStatus.PASSED
            else:
                proposal.status = ProposalStatus.REJECTED
        return True

    @property
    def stats(self) -> dict[str, Any]:
        return {"total_proposals": len(self.proposals), "passed": sum(1 for p in self.proposals.values() if p.status == ProposalStatus.PASSED), "voters": len(self.voters)}
