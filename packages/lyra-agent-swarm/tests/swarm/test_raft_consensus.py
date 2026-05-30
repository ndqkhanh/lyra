"""Comprehensive tests for Raft Consensus Protocol.

Tests cover: LeaderElection, LogReplication, StateMachine, RaftNode,
RaftCluster integration, edge cases, and membership changes.
"""

from __future__ import annotations

import pytest

from lyra_agent_swarm.consensus.raft.leader_election import (
    CandidateNomination,
    ElectionConfig,
    ElectionPhase,
    LeaderElection,
    VoteRequest,
    VoteResponse,
)
from lyra_agent_swarm.consensus.raft.log_replication import (
    AppendEntriesRequest,
    AppendEntriesResponse,
    LogReplication,
    ReplicationConfig,
)
from lyra_agent_swarm.consensus.raft.state_machine import (
    ApplyResult,
    CommandResult,
    Snapshot,
    StateMachine,
    StateMachineConfig,
)
from lyra_agent_swarm.consensus.raft_consensus import (
    ClusterConfig,
    ClusterState,
    LogEntry,
    NodeState,
    RaftCluster,
    RaftConfig,
    RaftNode,
)


# ── Fixtures ───────────────────────────────────────────────────────


@pytest.fixture
def raft_config() -> RaftConfig:
    return RaftConfig(
        election_timeout_min_ms=10.0,
        election_timeout_max_ms=20.0,
        heartbeat_interval_ms=5.0,
    )


@pytest.fixture
def cluster_config() -> ClusterConfig:
    return ClusterConfig(
        election=ElectionConfig(
            election_timeout_min_ms=10.0,
            election_timeout_max_ms=20.0,
            heartbeat_interval_ms=5.0,
        ),
    )


# ── LeaderElection Tests ───────────────────────────────────────────


class TestLeaderElection:
    def test_initial_state_is_idle(self):
        le = LeaderElection(node_id="n1", peer_ids=["n2", "n3"])
        assert le.phase == ElectionPhase.IDLE
        assert le.current_term == 0
        assert not le.is_leader
        assert le.current_leader is None

    def test_receive_heartbeat_from_higher_term(self):
        le = LeaderElection(node_id="n1", peer_ids=["n2", "n3"])
        accepted = le.receive_heartbeat("n2", 5)
        assert accepted is True
        assert le.current_term == 5
        assert le.current_leader == "n2"

    def test_reject_heartbeat_from_lower_term(self):
        le = LeaderElection(node_id="n1", peer_ids=["n2", "n3"])
        le.receive_heartbeat("n2", 5)
        accepted = le.receive_heartbeat("n3", 3)
        assert accepted is False
        assert le.current_term == 5

    def test_start_election_increments_term(self):
        le = LeaderElection(node_id="n1", peer_ids=["n2", "n3"])
        phase, request = le.start_election()
        assert phase == ElectionPhase.CANDIDATE
        assert le.current_term == 1
        assert request is not None
        assert request.candidate_id == "n1"
        assert request.term == 1

    def test_vote_granted_to_current_candidate(self):
        le = LeaderElection(node_id="n2", peer_ids=["n1", "n3"])
        request = VoteRequest(term=3, candidate_id="n1", last_log_index=5, last_log_term=3)
        response = le.request_vote(request, log_size=6, log_last_term=3)
        assert response.vote_granted is True
        assert response.voter_id == "n2"

    def test_vote_denied_stale_term(self):
        le = LeaderElection(node_id="n2", peer_ids=["n1", "n3"])
        le.receive_heartbeat("n1", 5)
        request = VoteRequest(term=3, candidate_id="n3", last_log_index=10, last_log_term=5)
        response = le.request_vote(request, log_size=6, log_last_term=4)
        assert response.vote_granted is False

    def test_vote_denied_already_voted(self):
        le = LeaderElection(node_id="n2", peer_ids=["n1", "n3"])
        request1 = VoteRequest(term=3, candidate_id="n1", last_log_index=5, last_log_term=3)
        le.request_vote(request1, log_size=6, log_last_term=3)
        request2 = VoteRequest(term=3, candidate_id="n3", last_log_index=5, last_log_term=3)
        response = le.request_vote(request2, log_size=6, log_last_term=3)
        assert response.vote_granted is False

    def test_vote_denied_candidate_log_behind(self):
        le = LeaderElection(node_id="n2", peer_ids=["n1", "n3"])
        request = VoteRequest(term=3, candidate_id="n1", last_log_index=2, last_log_term=1)
        response = le.request_vote(request, log_size=6, log_last_term=3)
        assert response.vote_granted is False

    def test_try_claim_leadership_with_quorum(self):
        le = LeaderElection(node_id="n1", peer_ids=["n2", "n3"])
        le.start_election()
        le.record_vote("n2", True)
        le.record_vote("n3", True)
        result = le.try_claim_leadership()
        assert result is not None
        assert result.leader_id == "n1"
        assert result.term == 1
        assert le.is_leader

    def test_try_claim_leadership_insufficient_votes(self):
        le = LeaderElection(node_id="n1", peer_ids=["n2", "n3", "n4", "n5"])
        le.start_election()
        le.record_vote("n2", True)
        result = le.try_claim_leadership()
        assert result is None
        assert not le.is_leader

    def test_step_down(self):
        le = LeaderElection(node_id="n1", peer_ids=["n2", "n3"])
        le.start_election()
        le.record_vote("n2", True)
        le.record_vote("n3", True)
        le.try_claim_leadership()
        assert le.is_leader
        le.step_down()
        assert not le.is_leader
        assert le.phase == ElectionPhase.STEPPED_DOWN

    def test_capability_scoring(self):
        le = LeaderElection(node_id="n1", peer_ids=["n2"])
        le.update_scores(capability=0.9, health=0.8)
        assert le.capability_score == 0.9
        assert le.health_score == 0.8

    def test_clamp_scores_to_range(self):
        le = LeaderElection(node_id="n1")
        le.update_scores(capability=1.5, health=-0.5)
        assert le.capability_score == 1.0
        assert le.health_score == 0.0

    def test_get_quorum_size(self):
        le = LeaderElection(node_id="n1", peer_ids=["n2", "n3", "n4", "n5"])
        assert le.get_quorum_size() == 3  # (5+1)//2 + 1 = 3

    def test_stagnation_check(self):
        le = LeaderElection(node_id="n1", peer_ids=["n2"])
        le.start_election()
        le.record_vote("n2", True)
        le.try_claim_leadership()
        assert not le.check_stagnation(5000.0)
        assert le.check_stagnation(15000.0)

    def test_max_election_retries_exceeded(self):
        config = ElectionConfig(max_election_retries=1)
        le = LeaderElection(node_id="n1", peer_ids=["n2", "n3"], config=config)
        # First attempt
        phase, req = le.start_election()
        assert phase == ElectionPhase.CANDIDATE
        # Reset and try again (simulating timeout)
        le._state.phase = ElectionPhase.IDLE
        phase, req = le.start_election()
        assert phase == ElectionPhase.SETTLED  # Exceeded retries

    def test_tick_signals_election_on_timeout(self):
        import time

        le = LeaderElection(node_id="n1", peer_ids=["n2", "n3"])
        le._state.election_deadline = time.monotonic() - 10.0  # Force immediate timeout
        events = le.tick()
        assert any("election_timeout" in e for e in events)
        assert le.phase == ElectionPhase.CANDIDATE

    def test_reset(self):
        le = LeaderElection(node_id="n1", peer_ids=["n2", "n3"])
        le.start_election()
        le.record_vote("n2", True)
        le.record_vote("n3", True)
        le.try_claim_leadership()
        le.reset()
        assert le.phase == ElectionPhase.IDLE
        assert le.current_term == 0
        assert not le.is_leader

    def test_candidate_nomination_composite_score(self):
        nom = CandidateNomination(
            agent_id="agent-1", term=3, capability_score=0.9, health_score=0.8
        )
        assert nom.composite_score == pytest.approx(0.86)  # 0.9*0.6 + 0.8*0.4


# ── LogReplication Tests ───────────────────────────────────────────


class TestLogReplication:
    def test_initial_state(self):
        repl = LogReplication(node_id="n1", peer_ids=["n2", "n3"])
        assert repl.next_index == {"n2": 0, "n3": 0}
        assert repl.match_index == {"n2": -1, "n3": -1}

    def test_build_append_entries_empty_log(self):
        repl = LogReplication(node_id="n1", peer_ids=["n2"])
        log: list = []
        req = repl.build_append_entries("n2", log, current_term=1, leader_commit=-1)
        assert req is not None
        assert req.term == 1
        assert req.leader_id == "n1"
        assert len(req.entries) == 0

    def test_build_append_entries_with_entries(self):
        repl = LogReplication(node_id="n1", peer_ids=["n2"])
        log = [
            LogEntry(term=1, index=0, command="set a=1"),
            LogEntry(term=1, index=1, command="set b=2"),
        ]
        req = repl.build_append_entries("n2", log, current_term=1, leader_commit=-1)
        assert req is not None
        assert len(req.entries) == 2

    def test_handle_append_entries_success(self):
        repl = LogReplication(node_id="n2", peer_ids=["n1"])
        log: list = []
        req = AppendEntriesRequest(
            term=1,
            leader_id="n1",
            prev_log_index=-1,
            prev_log_term=0,
            entries=((0, "set x=1"),),
            leader_commit=-1,
        )
        resp, updated_log = repl.handle_append_entries(req, log, current_term=0, commit_index=-1)
        assert resp.success is True
        assert updated_log is not None
        assert len(updated_log) == 1
        assert updated_log[0].command == "set x=1"

    def test_handle_append_entries_stale_term(self):
        repl = LogReplication(node_id="n2", peer_ids=["n1"])
        req = AppendEntriesRequest(
            term=2,
            leader_id="n1",
            prev_log_index=-1,
            prev_log_term=0,
            entries=(),
            leader_commit=-1,
        )
        resp, updated_log = repl.handle_append_entries(req, [], current_term=5, commit_index=-1)
        assert resp.success is False

    def test_handle_append_entries_consistency_fail(self):
        repl = LogReplication(node_id="n2", peer_ids=["n1"])
        log = [LogEntry(term=1, index=0, command="set a=1")]
        req = AppendEntriesRequest(
            term=2,
            leader_id="n1",
            prev_log_index=0,
            prev_log_term=99,  # Wrong term
            entries=(),
            leader_commit=-1,
        )
        resp, updated_log = repl.handle_append_entries(req, log, current_term=1, commit_index=-1)
        assert resp.success is False
        assert resp.conflict_term is not None or resp.conflict_index >= 0

    def test_handle_append_entries_conflict_truncation(self):
        """Follower truncates conflicting entries when leader's log diverges."""
        repl = LogReplication(node_id="n2", peer_ids=["n1"])
        log = [
            LogEntry(term=1, index=0, command="a"),
            LogEntry(term=1, index=1, command="b"),
            LogEntry(term=2, index=2, command="c"),
        ]
        req = AppendEntriesRequest(
            term=2,
            leader_id="n1",
            prev_log_index=0,
            prev_log_term=1,
            entries=((1, "b-prime"), (2, "c-prime")),
            leader_commit=-1,
        )
        resp, updated_log = repl.handle_append_entries(req, log, current_term=1, commit_index=-1)
        assert resp.success is True
        assert updated_log is not None
        assert len(updated_log) == 3  # kept [0], replaced [1,2]
        assert updated_log[1].command == "b-prime"
        assert updated_log[2].command == "c-prime"

    def test_process_response_success(self):
        repl = LogReplication(node_id="n1", peer_ids=["n2"])
        resp = AppendEntriesResponse(
            term=1, success=True, follower_id="n2",
            request_id="req-1", match_index=3,
        )
        repl.process_response("n2", resp)
        assert repl.match_index["n2"] == 3
        assert repl.next_index["n2"] == 4

    def test_process_response_failure_decrements_next_index(self):
        repl = LogReplication(node_id="n1", peer_ids=["n2"])
        repl._next_index["n2"] = 5
        resp = AppendEntriesResponse(
            term=1, success=False, follower_id="n2",
            request_id="req-1", conflict_index=2,
        )
        repl.process_response("n2", resp)
        assert repl.next_index["n2"] == 2

    def test_advance_commit_index(self):
        repl = LogReplication(node_id="n1", peer_ids=["n2", "n3"])
        log = [
            LogEntry(term=1, index=0, command="a"),
            LogEntry(term=1, index=1, command="b"),
            LogEntry(term=1, index=2, command="c"),
        ]
        repl._match_index = {"n2": 2, "n3": 2}
        new_commit = repl.advance_commit_index(log, current_term=1, current_commit=-1)
        assert new_commit == 2

    def test_advance_commit_only_current_term(self):
        """Only entries from the leader's current term commit via quorum."""
        repl = LogReplication(node_id="n1", peer_ids=["n2", "n3"])
        log = [
            LogEntry(term=1, index=0, command="a"),  # Previous term
            LogEntry(term=2, index=1, command="b"),  # Current term
        ]
        repl._match_index = {"n2": 1, "n3": 1}
        new_commit = repl.advance_commit_index(log, current_term=2, current_commit=-1)
        assert new_commit == 1  # Only index 1 commits (current term)

    def test_add_remove_peer(self):
        repl = LogReplication(node_id="n1", peer_ids=["n2"])
        repl.add_peer("n3", log_size=5)
        assert "n3" in repl.peer_ids
        assert repl.next_index["n3"] == 5
        repl.remove_peer("n2")
        assert "n2" not in repl.peer_ids

    def test_get_replication_status(self):
        repl = LogReplication(node_id="n1", peer_ids=["n2", "n3"])
        repl._match_index = {"n2": 5, "n3": 3}
        status = repl.get_replication_status()
        assert status["committed_count"] == 6
        assert "n3" in status["behind_peers"]
        assert not status["fully_replicated"]

    def test_reset(self):
        repl = LogReplication(node_id="n1", peer_ids=["n2"])
        repl._next_index["n2"] = 10
        repl.reset(log_size=0)
        assert repl.next_index["n2"] == 0
        assert repl.match_index["n2"] == -1

    def test_build_heartbeat(self):
        repl = LogReplication(node_id="n1", peer_ids=["n2", "n3"])
        heartbeats = repl.build_heartbeat(current_term=1, leader_commit=5)
        assert len(heartbeats) == 2
        for peer_id, req in heartbeats:
            assert req.term == 1
            assert len(req.entries) == 0


# ── StateMachine Tests ─────────────────────────────────────────────


class TestStateMachine:
    def test_initial_state(self):
        sm = StateMachine()
        assert sm.last_applied == -1
        assert sm.state == {}
        assert sm.snapshot_count == 0

    def test_apply_key_value(self):
        sm = StateMachine()
        result = sm.apply("set theme=dark")
        assert result.success is True
        assert sm.state == {"theme": "dark"}

    def test_apply_delete(self):
        sm = StateMachine()
        sm.apply("set key=value")
        result = sm.apply("delete key")
        assert result.success is True
        assert "key" not in sm.state

    def test_apply_delete_missing_key(self):
        sm = StateMachine()
        result = sm.apply("delete nonexistent")
        assert result.success is False

    def test_apply_get(self):
        sm = StateMachine()
        sm.apply("set name=lyra")
        result = sm.apply("get name")
        assert result.success is True
        assert result.output == "lyra"

    def test_apply_get_missing_key(self):
        sm = StateMachine()
        result = sm.apply("get missing")
        assert result.success is False

    def test_apply_increment(self):
        sm = StateMachine()
        sm.apply("set counter=0")
        result = sm.apply("increment counter")
        assert result.success is True
        assert sm.state["counter"] == 1

    def test_apply_unknown_command(self):
        sm = StateMachine()
        result = sm.apply("unknown operation here")
        assert result.success is True
        assert "_cmd_0" in sm.state

    def test_apply_command_too_large(self):
        sm = StateMachine(config=StateMachineConfig(max_command_size=10))
        result = sm.apply("this is a very long command that exceeds the size limit")
        assert result.success is False

    def test_apply_batch(self):
        sm = StateMachine()
        result = sm.apply_batch(["set a=1", "set b=2", "set c=3"])
        assert result.entries_applied == 3
        assert result.entries_failed == 0
        assert sm.last_applied == 2
        assert len(result.state_hash) > 0

    def test_apply_batch_mixed_results(self):
        sm = StateMachine()
        result = sm.apply_batch(["set a=1", "get missing", "set b=2"])
        assert result.entries_applied == 2
        assert result.entries_failed == 1

    def test_custom_handler(self):
        sm = StateMachine()

        def uppercase_handler(state: dict, cmd: str) -> tuple[bool, str]:
            key = cmd.split(" ", 1)[1]
            state[key] = state.get(key, "").upper() if isinstance(state.get(key), str) else ""
            return True, f"Uppercased {key}"

        sm.register_handler("upper ", uppercase_handler)
        sm.apply("set name=hello")
        result = sm.apply("upper name")
        assert result.success is True
        assert sm.state["name"] == "HELLO"

    def test_should_snapshot(self):
        sm = StateMachine(config=StateMachineConfig(snapshot_interval_entries=100))
        assert not sm.should_snapshot(50)
        assert sm.should_snapshot(100)
        assert sm.should_snapshot(200)

    def test_create_and_install_snapshot(self):
        sm = StateMachine()
        sm.apply_batch(["set a=1", "set b=2", "set c=3"])
        snap = sm.create_snapshot(
            last_included_index=2,
            last_included_term=1,
            peers=["n1", "n2"],
        )
        assert snap.metadata.last_included_index == 2
        assert snap.state == {"a": "1", "b": "2", "c": "3"}
        assert len(snap.cluster_config) == 2

        # Install on a new state machine
        sm2 = StateMachine()
        sm2.install_snapshot(snap)
        assert sm2.state == {"a": "1", "b": "2", "c": "3"}
        assert sm2.last_applied == 2

    def test_restore_from_snapshot_and_log(self):
        sm = StateMachine()
        sm.apply_batch(["set a=1", "set b=2"])
        snap = sm.create_snapshot(last_included_index=1, last_included_term=1)

        sm2 = StateMachine()
        # Log entries: snapshot covers [0,1], we replay entry 2
        log = [
            LogEntry(term=1, index=0, command="set a=old"),
            LogEntry(term=1, index=1, command="set b=old"),
            LogEntry(term=1, index=2, command="set c=3"),
        ]
        result = sm2.restore_from_snapshot_and_log(snap, log)
        assert result.entries_applied == 1
        assert sm2.state == {"a": "1", "b": "2", "c": "3"}

    def test_snapshot_pruning(self):
        sm = StateMachine(config=StateMachineConfig(max_snapshots=2))
        for i in range(5):
            sm.apply(f"set key{i}={i}")
            sm.create_snapshot(last_included_index=i, last_included_term=1)
        assert sm.snapshot_count == 2

    def test_latest_snapshot_returns_none_when_empty(self):
        sm = StateMachine()
        assert sm.latest_snapshot() is None

    def test_reset(self):
        sm = StateMachine()
        sm.apply("set a=1")
        sm.reset()
        assert sm.last_applied == -1
        assert sm.state == {}

    def test_get_state_since(self):
        sm = StateMachine()
        sm.apply_batch(["set a=1", "set b=2", "set c=3"])
        changes = sm.get_state_since(0)
        assert len(changes) == 2


# ── RaftNode Tests ─────────────────────────────────────────────────


class TestRaftNode:
    def test_initial_state_is_follower(self):
        node = RaftNode(node_id="n1")
        assert node.state == NodeState.FOLLOWER
        assert node.current_term == 0
        assert node.commit_index == -1
        assert node.log_size == 0
        assert not node.is_leader

    def test_receive_heartbeat_updates_term(self):
        node = RaftNode(node_id="n1")
        node.receive_heartbeat("leader", 5)
        assert node.current_term == 5
        assert node.state == NodeState.FOLLOWER

    def test_reject_heartbeat_lower_term(self):
        node = RaftNode(node_id="n1")
        node._current_term = 5
        node.receive_heartbeat("leader", 3)
        assert node.current_term == 5

    def test_vote_request_current_candidate(self):
        node = RaftNode(node_id="n1")
        granted = node.receive_vote_request(
            "candidate", candidate_term=3, last_log_index=0, last_log_term=0
        )
        assert granted is True

    def test_vote_request_stale_term(self):
        node = RaftNode(node_id="n1")
        node._current_term = 5
        granted = node.receive_vote_request(
            "candidate", candidate_term=3, last_log_index=10, last_log_term=5
        )
        assert granted is False

    def test_vote_request_already_voted_same_term(self):
        node = RaftNode(node_id="n1")
        node._current_term = 3
        node._voted_for = "other"
        granted = node.receive_vote_request(
            "candidate", candidate_term=3, last_log_index=0, last_log_term=0
        )
        assert granted is False

    def test_leader_can_propose(self):
        node = RaftNode(node_id="n1", peer_ids=["n2", "n3"])
        node._state = NodeState.LEADER
        node._current_term = 1
        entry = node.propose("set x=1")
        assert entry is not None
        assert entry.command == "set x=1"
        assert entry.term == 1
        assert node.log_size == 1

    def test_follower_cannot_propose(self):
        node = RaftNode(node_id="n1")
        entry = node.propose("set x=1")
        assert entry is None

    def test_start_election_becomes_leader_with_quorum(self):
        node = RaftNode(node_id="n1", peer_ids=["n2"])
        events = node._start_election()
        assert any("elected_leader" in e for e in events)
        assert node.state == NodeState.LEADER

    def test_start_election_with_peers_becomes_leader(self):
        """RaftNode simulates all peers voting yes, so should always become leader."""
        node = RaftNode(node_id="n1", peer_ids=["n2", "n3", "n4", "n5"])
        events = node._start_election()
        assert any("elected_leader" in e for e in events)
        assert node.state == NodeState.LEADER

    def test_get_committed_commands(self):
        node = RaftNode(node_id="n1", peer_ids=["n2", "n3"])
        node._state = NodeState.LEADER
        node._current_term = 1
        node.propose("cmd1")
        node.propose("cmd2")
        node._commit_index = 1
        cmds = node.get_committed_commands()
        assert len(cmds) == 2

    def test_get_committed_commands_no_new(self):
        node = RaftNode(node_id="n1")
        node._last_applied = 5
        node._commit_index = 5
        cmds = node.get_committed_commands()
        assert len(cmds) == 0

    def test_tick_leader_sends_heartbeat(self):
        node = RaftNode(
            node_id="n1", peer_ids=["n2", "n3"],
            config=RaftConfig(heartbeat_interval_ms=0.0),
        )
        node._state = NodeState.LEADER
        node._last_heartbeat = 0.0
        events = node.tick()
        assert "heartbeat_sent" in events

    def test_tick_follower_starts_election_on_timeout(self):
        node = RaftNode(node_id="n1", peer_ids=["n2", "n3"])
        node._election_deadline = 0.0
        events = node.tick()
        assert len(events) > 0

    def test_send_heartbeats_advances_match_index(self):
        node = RaftNode(node_id="n1", peer_ids=["n2"])
        node._state = NodeState.LEADER
        node._current_term = 1
        node.propose("cmd1")
        node.propose("cmd2")
        node._match_index["n2"] = -1
        node._next_index["n2"] = 0
        node._send_heartbeats()
        assert node._match_index["n2"] >= 0

    def test_advance_commit_index_single_node(self):
        """Single node cluster — leader commits immediately."""
        node = RaftNode(node_id="n1", peer_ids=[])
        node._state = NodeState.LEADER
        node._current_term = 1
        node.propose("cmd1")
        node._commit_index = -1
        node._advance_commit_index()
        assert node._commit_index == 0

    def test_advance_commit_index_quorum_not_met(self):
        node = RaftNode(node_id="n1", peer_ids=["n2", "n3"])
        node._state = NodeState.LEADER
        node._current_term = 1
        node.propose("cmd1")
        node._match_index = {"n2": -1, "n3": -1}
        node._advance_commit_index()
        assert node._commit_index == -1

    def test_log_entry_frozen(self):
        entry = LogEntry(term=1, index=0, command="test")
        with pytest.raises(Exception):
            entry.term = 2  # type: ignore[misc]


# ── RaftCluster Integration Tests ──────────────────────────────────


class TestRaftCluster:
    def test_create_cluster(self):
        cluster = RaftCluster(node_count=3)
        assert cluster.node_count == 3
        assert cluster.current_leader is None
        assert not cluster.started

    def test_start_cluster(self):
        cluster = RaftCluster(node_count=3)
        cluster.start()
        assert cluster.started

    def test_cluster_elects_leader(self):
        config = ClusterConfig(
            election=ElectionConfig(
                election_timeout_min_ms=1.0,
                election_timeout_max_ms=5.0,
                heartbeat_interval_ms=2.0,
            ),
        )
        cluster = RaftCluster(node_count=3, config=config)
        cluster.start()
        # Run enough ticks for election
        for _ in range(5):
            cluster.tick()
        leader = cluster.current_leader
        assert leader is not None
        assert leader.startswith("node-")

    def test_cluster_propose_and_commit(self):
        config = ClusterConfig(
            election=ElectionConfig(
                election_timeout_min_ms=1.0,
                election_timeout_max_ms=5.0,
                heartbeat_interval_ms=2.0,
            ),
        )
        cluster = RaftCluster(node_count=3, config=config)
        cluster.start()
        for _ in range(5):
            cluster.tick()

        assert cluster.current_leader is not None
        cluster.propose("set theme=dark")
        # Drive replication and commit
        for _ in range(5):
            cluster.tick()
        state = cluster.get_state()
        assert state.get("theme") == "dark"

    def test_cluster_state_machine(self):
        config = ClusterConfig(
            election=ElectionConfig(
                election_timeout_min_ms=1.0,
                election_timeout_max_ms=5.0,
                heartbeat_interval_ms=2.0,
            ),
        )
        cluster = RaftCluster(node_count=3, config=config)
        cluster.start()
        for _ in range(5):
            cluster.tick()

        cluster.propose("set key=lyra")
        cluster.propose("set version=1.0")
        for _ in range(10):
            cluster.tick()

        state = cluster.get_state()
        assert "key" in state or "version" in state

    def test_cluster_stop(self):
        cluster = RaftCluster(node_count=3)
        cluster.start()
        for _ in range(3):
            cluster.tick()
        cluster.stop()
        assert not cluster.started

    def test_cluster_single_node(self):
        cluster = RaftCluster(node_count=1)
        cluster.start()
        for _ in range(3):
            cluster.tick()
        leader = cluster.current_leader
        assert leader is not None
        cluster.propose("set mode=solo")
        for _ in range(3):
            cluster.tick()
        state = cluster.get_state()
        assert state.get("mode") == "solo"

    def test_cluster_add_node(self):
        cluster = RaftCluster(node_count=2)
        cluster.start()
        assert cluster.add_node("node-new") is True
        assert cluster.node_count == 3
        assert cluster.add_node("node-new") is False  # Duplicate

    def test_cluster_remove_node(self):
        cluster = RaftCluster(node_count=3)
        cluster.start()
        assert cluster.remove_node("node-1") is True
        assert cluster.node_count == 2
        assert cluster.remove_node("ghost") is False

    def test_cluster_remove_then_elect(self):
        import time

        config = ClusterConfig(
            election=ElectionConfig(
                election_timeout_min_ms=1.0,
                election_timeout_max_ms=5.0,
                heartbeat_interval_ms=2.0,
            ),
        )
        cluster = RaftCluster(node_count=3, config=config)
        cluster.start()
        for _ in range(5):
            cluster.tick()
        leader_before = cluster.current_leader
        if leader_before == "node-1":
            cluster.remove_node("node-1")
        else:
            cluster.remove_node("node-0")

        # Force election timeout on remaining nodes
        now = time.monotonic()
        for nid in cluster._node_order:
            cluster._elections[nid]._state.election_deadline = now - 0.001

        for _ in range(10):
            cluster.tick()
        assert cluster.current_leader is not None

    def test_cluster_health_reporting(self):
        cluster = RaftCluster(node_count=3)
        cluster.start()
        for _ in range(3):
            cluster.tick()
        status = cluster.get_cluster_status()
        assert "cluster_state" in status
        assert "nodes" in status
        assert len(status["nodes"]) == 3
        for nid, info in status["nodes"].items():
            assert "state" in info
            assert "term" in info
            assert "commit_index" in info

    def test_create_snapshot(self):
        config = ClusterConfig(
            election=ElectionConfig(
                election_timeout_min_ms=1.0,
                election_timeout_max_ms=5.0,
                heartbeat_interval_ms=2.0,
            ),
        )
        cluster = RaftCluster(node_count=3, config=config)
        cluster.start()
        for _ in range(5):
            cluster.tick()
        cluster.propose("set data=snapshot-test")
        for _ in range(5):
            cluster.tick()

        snap = cluster.create_snapshot()
        if snap is not None:
            assert snap.metadata.last_included_index >= -1
            assert len(snap.cluster_config) == 3

    def test_cluster_zero_nodes_raises(self):
        with pytest.raises(ValueError):
            RaftCluster(node_count=0)

    def test_cluster_with_custom_node_ids(self):
        cluster = RaftCluster(node_count=3, node_ids=["alpha", "beta", "gamma"])
        assert cluster.node_count == 3
        status = cluster.get_cluster_status()
        assert "alpha" in status["nodes"]
        assert "beta" in status["nodes"]
        assert "gamma" in status["nodes"]

    def test_cluster_propose_no_leader(self):
        cluster = RaftCluster(node_count=3)
        assert cluster.propose("set x=1") is False

    def test_cluster_tick_events(self):
        cluster = RaftCluster(node_count=3)
        cluster.start()
        events = cluster.tick()
        assert isinstance(events, list)
