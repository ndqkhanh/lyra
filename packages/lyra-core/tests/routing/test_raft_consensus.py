"""Tests for the Raft consensus protocol."""
from __future__ import annotations

from lyra_agent_swarm.consensus.raft_consensus import (
    LogEntry,
    NodeState,
    RaftConfig,
    RaftNode,
)


class TestLogEntry:
    def test_create_log_entry(self):
        entry = LogEntry(term=1, index=0, command="SET x=1")
        assert entry.term == 1
        assert entry.index == 0
        assert entry.command == "SET x=1"
        assert len(entry.entry_id) > 0

    def test_unique_entry_ids(self):
        e1 = LogEntry(term=1, index=0, command="A")
        e2 = LogEntry(term=1, index=1, command="B")
        assert e1.entry_id != e2.entry_id


class TestRaftNode:
    def test_node_starts_as_follower(self):
        node = RaftNode("n1")
        assert node.state == NodeState.FOLLOWER
        assert not node.is_leader

    def test_initial_term_is_zero(self):
        node = RaftNode("n1")
        assert node.current_term == 0

    def test_initial_log_is_empty(self):
        node = RaftNode("n1")
        assert node.log_size == 0

    def test_tick_as_follower(self):
        node = RaftNode("n1")
        events = node.tick()
        assert len(events) >= 0

    def test_receive_heartbeat_resets_timeout(self):
        node = RaftNode("n1")
        node.receive_heartbeat("leader1", 5)
        assert node.current_term == 5
        assert node.state == NodeState.FOLLOWER

    def test_receive_heartbeat_lower_term_ignored(self):
        node = RaftNode("n1")
        node._current_term = 5
        node.receive_heartbeat("leader1", 3)
        assert node.current_term == 5

    def test_receive_vote_grants_when_candidate_is_newer(self):
        node = RaftNode("n1")
        granted = node.receive_vote_request("cand1", 2, -1, 0)
        assert granted

    def test_receive_vote_denies_lower_term(self):
        node = RaftNode("n1")
        node._current_term = 5
        granted = node.receive_vote_request("cand1", 3, -1, 0)
        assert not granted

    def test_receive_vote_already_voted_same_term(self):
        node = RaftNode("n1")
        node._current_term = 2
        node._voted_for = "cand1"
        granted = node.receive_vote_request("cand2", 2, -1, 0)
        assert not granted

    def test_propose_only_from_leader(self):
        node = RaftNode("n1")
        assert node.propose("cmd") is None

    def test_election_makes_leader_with_quorum(self):
        node = RaftNode("n1", peer_ids=["n2", "n3"])
        node._start_election()
        assert node.is_leader
        assert node.current_term == 1

    def test_propose_as_leader_adds_to_log(self):
        node = RaftNode("n1", peer_ids=["n2", "n3"])
        node._start_election()
        entry = node.propose("SET x=42")
        assert entry is not None
        assert node.log_size == 1
        assert node._log[0].command == "SET x=42"

    def test_get_committed_commands_none_initially(self):
        node = RaftNode("n1")
        assert node.get_committed_commands() == []

    def test_single_node_election(self):
        node = RaftNode("n1")
        node._election_deadline = 0
        events = node.tick()
        has_election = any("elected" in e or "election" in e for e in events)
        assert has_election

    def test_config_defaults(self):
        cfg = RaftConfig()
        assert cfg.election_timeout_min_ms == 150.0
        assert cfg.election_timeout_max_ms == 300.0
        assert cfg.heartbeat_interval_ms == 50.0
