"""Tests for ConsensusProtocol."""

from __future__ import annotations

import pytest

from lyra_cli.swarm.consensus import (
    ConsensusConfig,
    ConsensusProtocol,
    NodeState,
    ConsensusRole,
    LogEntry,
)


@pytest.mark.asyncio
async def test_initial_state_is_follower() -> None:
    """A new consensus node should start as FOLLOWER."""
    node = ConsensusProtocol(node_id="node_0")
    assert node.state == NodeState.FOLLOWER
    assert node.role == ConsensusRole.VOTER


@pytest.mark.asyncio
async def test_request_vote_granted() -> None:
    """A candidate with a higher term should get the vote."""
    node = ConsensusProtocol(node_id="node_0")
    node.set_node_count(3)

    result = await node.request_vote(
        candidate_id="node_1",
        candidate_term=1,
        last_log_index=0,
        last_log_term=0,
    )
    assert result["vote_granted"] is True
    assert node.voted_for == "node_1"


@pytest.mark.asyncio
async def test_request_vote_denied_lower_term() -> None:
    """A candidate with a lower term should be denied."""
    node = ConsensusProtocol(node_id="node_0")
    node.current_term = 5
    node.set_node_count(3)

    result = await node.request_vote(
        candidate_id="node_1",
        candidate_term=3,
        last_log_index=0,
        last_log_term=0,
    )
    assert result["vote_granted"] is False


@pytest.mark.asyncio
async def test_receive_heartbeat_from_leader() -> None:
    """Receiving a heartbeat should update leader and term."""
    node = ConsensusProtocol(node_id="node_0")
    node.set_node_count(3)

    result = await node.receive_heartbeat(
        leader_id="node_leader",
        leader_term=2,
    )
    assert result["success"] is True
    assert node.leader_id == "node_leader"
    assert node.current_term == 2


@pytest.mark.asyncio
async def test_append_entry_leader_only() -> None:
    """Only the leader should be able to append log entries."""
    node = ConsensusProtocol(node_id="node_follower")
    node.set_node_count(3)

    index = await node.append_entry("test_command")
    assert index is None

    node.state = NodeState.LEADER
    index = await node.append_entry("test_command", {"key": "value"})
    assert index is not None
    assert index >= 0

    entry = node.log[index]
    assert entry.command == "test_command"
    assert entry.data["key"] == "value"


@pytest.mark.asyncio
async def test_byzantine_detection() -> None:
    """Repeated reports should mark a node as Byzantine."""
    node = ConsensusProtocol(node_id="node_0")
    node.set_node_count(5)

    assert node.is_byzantine("node_bad") is False

    for _ in range(node.config.byzantine_threshold):
        await node.report_byzantine("node_bad", "suspicious behavior")

    assert node.is_byzantine("node_bad") is True
    assert node._stats["byzantine_detections"] == 1


@pytest.mark.asyncio
async def test_quorum_decision() -> None:
    """A leader should be able to reach quorum decisions."""
    node = ConsensusProtocol(node_id="node_leader")
    node.state = NodeState.LEADER
    node.set_node_count(5)

    decision = await node.make_decision({"action": "deploy"})
    assert decision is True

    entry = node.log[-1]
    assert entry.command == "decision"
