"""Tests for consensus protocol."""

import asyncio

import pytest

from lyra_orchestration.consensus import (
    ConsensusProtocol,
    VoteChoice,
    VotingStrategy,
)


@pytest.mark.asyncio
async def test_majority_voting_approved():
    """Test majority voting with approval."""
    protocol = ConsensusProtocol()

    # Create proposal
    proposal_id = await protocol.propose(
        topic="database_choice",
        description="Choose database for project",
        options=["PostgreSQL", "MongoDB"],
        proposer_id="agent1",
        voters={"agent1", "agent2", "agent3"},
        strategy=VotingStrategy.MAJORITY,
    )

    # Cast votes (2 approve, 1 reject)
    await protocol.vote(proposal_id, "agent1", VoteChoice.APPROVE)
    await protocol.vote(proposal_id, "agent2", VoteChoice.APPROVE)

    # Decision should be made after 2 approvals (>50%)
    decision = await protocol.wait_for_decision(proposal_id, timeout=1)

    assert decision == "approved"

    # Check stats
    stats = protocol.get_stats(proposal_id)
    assert stats["approvals"] == 2
    assert stats["decided"] is True


@pytest.mark.asyncio
async def test_majority_voting_rejected():
    """Test majority voting with rejection."""
    protocol = ConsensusProtocol()

    proposal_id = await protocol.propose(
        topic="tech_stack",
        description="Choose tech stack",
        options=["React", "Vue"],
        proposer_id="agent1",
        voters={"agent1", "agent2", "agent3"},
        strategy=VotingStrategy.MAJORITY,
    )

    # Cast votes (1 approve, 2 reject)
    await protocol.vote(proposal_id, "agent1", VoteChoice.APPROVE)
    await protocol.vote(proposal_id, "agent2", VoteChoice.REJECT)
    await protocol.vote(proposal_id, "agent3", VoteChoice.REJECT)

    decision = await protocol.wait_for_decision(proposal_id, timeout=1)

    assert decision == "rejected"


@pytest.mark.asyncio
async def test_unanimous_voting_approved():
    """Test unanimous voting with all approvals."""
    protocol = ConsensusProtocol()

    proposal_id = await protocol.propose(
        topic="critical_decision",
        description="Critical architectural decision",
        options=["Option A", "Option B"],
        proposer_id="agent1",
        voters={"agent1", "agent2", "agent3"},
        strategy=VotingStrategy.UNANIMOUS,
    )

    # All approve
    await protocol.vote(proposal_id, "agent1", VoteChoice.APPROVE)
    await protocol.vote(proposal_id, "agent2", VoteChoice.APPROVE)
    await protocol.vote(proposal_id, "agent3", VoteChoice.APPROVE)

    decision = await protocol.wait_for_decision(proposal_id, timeout=1)

    assert decision == "approved"


@pytest.mark.asyncio
async def test_unanimous_voting_rejected():
    """Test unanimous voting with one rejection."""
    protocol = ConsensusProtocol()

    proposal_id = await protocol.propose(
        topic="critical_decision",
        description="Critical architectural decision",
        options=["Option A", "Option B"],
        proposer_id="agent1",
        voters={"agent1", "agent2", "agent3"},
        strategy=VotingStrategy.UNANIMOUS,
    )

    # One rejects
    await protocol.vote(proposal_id, "agent1", VoteChoice.APPROVE)
    await protocol.vote(proposal_id, "agent2", VoteChoice.REJECT)

    decision = await protocol.wait_for_decision(proposal_id, timeout=1)

    assert decision == "rejected"


@pytest.mark.asyncio
async def test_weighted_voting():
    """Test weighted voting."""
    protocol = ConsensusProtocol()

    proposal_id = await protocol.propose(
        topic="architecture",
        description="Architecture decision",
        options=["Microservices", "Monolith"],
        proposer_id="agent1",
        voters={"senior", "junior1", "junior2"},
        strategy=VotingStrategy.WEIGHTED,
    )

    # Senior has weight 3.0, juniors have 1.0 each
    await protocol.vote(proposal_id, "senior", VoteChoice.APPROVE, weight=3.0)
    await protocol.vote(proposal_id, "junior1", VoteChoice.REJECT, weight=1.0)
    await protocol.vote(proposal_id, "junior2", VoteChoice.REJECT, weight=1.0)

    decision = await protocol.wait_for_decision(proposal_id, timeout=1)

    # Approve weight: 3.0, Reject weight: 2.0, total: 5.0
    # 3.0 > 2.5 (50% of 5.0), so approved
    assert decision == "approved"


@pytest.mark.asyncio
async def test_quorum_not_met():
    """Test quorum requirement not met."""
    protocol = ConsensusProtocol()

    proposal_id = await protocol.propose(
        topic="minor_decision",
        description="Minor decision",
        options=["A", "B"],
        proposer_id="agent1",
        voters={"agent1", "agent2", "agent3", "agent4"},
        strategy=VotingStrategy.QUORUM,
        quorum=0.75,  # Need 3 out of 4 votes
    )

    # Only 2 votes (50% participation)
    await protocol.vote(proposal_id, "agent1", VoteChoice.APPROVE)
    await protocol.vote(proposal_id, "agent2", VoteChoice.APPROVE)

    # Should not decide yet
    await asyncio.sleep(0.1)

    stats = protocol.get_stats(proposal_id)
    assert stats["decided"] is False


@pytest.mark.asyncio
async def test_quorum_met():
    """Test quorum requirement met."""
    protocol = ConsensusProtocol()

    proposal_id = await protocol.propose(
        topic="minor_decision",
        description="Minor decision",
        options=["A", "B"],
        proposer_id="agent1",
        voters={"agent1", "agent2", "agent3", "agent4"},
        strategy=VotingStrategy.QUORUM,
        quorum=0.75,  # Need 3 out of 4 votes
    )

    # 3 votes (75% participation)
    await protocol.vote(proposal_id, "agent1", VoteChoice.APPROVE)
    await protocol.vote(proposal_id, "agent2", VoteChoice.APPROVE)
    await protocol.vote(proposal_id, "agent3", VoteChoice.REJECT)

    decision = await protocol.wait_for_decision(proposal_id, timeout=1)

    assert decision == "approved"  # Majority among participants


@pytest.mark.asyncio
async def test_vote_rejection_invalid_voter():
    """Test vote rejection for invalid voter."""
    protocol = ConsensusProtocol()

    proposal_id = await protocol.propose(
        topic="decision",
        description="Test decision",
        options=["A", "B"],
        proposer_id="agent1",
        voters={"agent1", "agent2"},
        strategy=VotingStrategy.MAJORITY,
    )

    # Try to vote with non-eligible voter
    result = await protocol.vote(proposal_id, "agent3", VoteChoice.APPROVE)

    assert result is False


@pytest.mark.asyncio
async def test_vote_rejection_duplicate():
    """Test vote rejection for duplicate vote."""
    protocol = ConsensusProtocol()

    proposal_id = await protocol.propose(
        topic="decision",
        description="Test decision",
        options=["A", "B"],
        proposer_id="agent1",
        voters={"agent1", "agent2"},
        strategy=VotingStrategy.MAJORITY,
    )

    # First vote succeeds
    result1 = await protocol.vote(proposal_id, "agent1", VoteChoice.APPROVE)
    assert result1 is True

    # Second vote fails
    result2 = await protocol.vote(proposal_id, "agent1", VoteChoice.REJECT)
    assert result2 is False


@pytest.mark.asyncio
async def test_timeout():
    """Test proposal timeout."""
    protocol = ConsensusProtocol()

    proposal_id = await protocol.propose(
        topic="decision",
        description="Test decision",
        options=["A", "B"],
        proposer_id="agent1",
        voters={"agent1", "agent2", "agent3"},
        strategy=VotingStrategy.MAJORITY,
        timeout=1,  # 1 second timeout
    )

    # Don't vote, wait for timeout
    decision = await protocol.wait_for_decision(proposal_id, timeout=2)

    assert decision == "timeout"


@pytest.mark.asyncio
async def test_abstain_votes():
    """Test abstain votes."""
    protocol = ConsensusProtocol()

    proposal_id = await protocol.propose(
        topic="decision",
        description="Test decision",
        options=["A", "B"],
        proposer_id="agent1",
        voters={"agent1", "agent2", "agent3"},
        strategy=VotingStrategy.MAJORITY,
    )

    # One abstains
    await protocol.vote(proposal_id, "agent1", VoteChoice.APPROVE)
    await protocol.vote(proposal_id, "agent2", VoteChoice.ABSTAIN)
    await protocol.vote(proposal_id, "agent3", VoteChoice.REJECT)

    decision = await protocol.wait_for_decision(proposal_id, timeout=1)

    # With abstain, 1 approve vs 1 reject, but all votes in -> rejected
    assert decision == "rejected"

    stats = protocol.get_stats(proposal_id)
    assert stats["abstentions"] == 1


@pytest.mark.asyncio
async def test_get_proposal():
    """Test get proposal."""
    protocol = ConsensusProtocol()

    proposal_id = await protocol.propose(
        topic="test",
        description="Test proposal",
        options=["A", "B"],
        proposer_id="agent1",
        voters={"agent1", "agent2"},
        strategy=VotingStrategy.MAJORITY,
    )

    proposal = protocol.get_proposal(proposal_id)

    assert proposal is not None
    assert proposal.topic == "test"
    assert proposal.proposer_id == "agent1"


@pytest.mark.asyncio
async def test_get_votes():
    """Test get votes."""
    protocol = ConsensusProtocol()

    proposal_id = await protocol.propose(
        topic="test",
        description="Test proposal",
        options=["A", "B"],
        proposer_id="agent1",
        voters={"agent1", "agent2", "agent3"},  # Need 3 voters to avoid early decision
        strategy=VotingStrategy.MAJORITY,
    )

    await protocol.vote(proposal_id, "agent1", VoteChoice.APPROVE, reason="Good idea")

    # Wait a bit to ensure vote is processed
    await asyncio.sleep(0.1)

    votes = protocol.get_votes(proposal_id)
    assert len(votes) == 1
    assert votes["agent1"].choice == VoteChoice.APPROVE
    assert votes["agent1"].reason == "Good idea"

    # Cast second vote
    await protocol.vote(proposal_id, "agent2", VoteChoice.REJECT, reason="Bad idea")

    votes = protocol.get_votes(proposal_id)
    assert len(votes) == 2
    assert votes["agent2"].choice == VoteChoice.REJECT
    assert votes["agent2"].reason == "Bad idea"
