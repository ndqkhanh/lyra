"""Raft Consensus — leader election and log replication for agent swarms.

Implements core Raft algorithm (Ongaro & Ousterhout, 2014):
  - Leader election with randomized timeouts (150-300ms)
  - Log replication via AppendEntries
  - Safety: only committed entries are applied
  - Single-server cluster changes
  - Snapshot-based log compaction

Used by Lyra's agent swarm to maintain consistent shared state across
distributed agent instances running in parallel.
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum

from lyra_agent_swarm.consensus.raft.leader_election import (
    ElectionConfig,
    ElectionPhase,
    ElectionResult,
    LeaderElection,
    VoteRequest,
)
from lyra_agent_swarm.consensus.raft.log_replication import (
    LogReplication,
    ReplicationConfig,
)
from lyra_agent_swarm.consensus.raft.state_machine import (
    Snapshot,
    StateMachine,
    StateMachineConfig,
)


class NodeState(StrEnum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class ClusterState(StrEnum):
    """Overall cluster health states."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    LEADERLESS = "leaderless"
    SPLIT_BRAIN = "split_brain"
    RECOVERING = "recovering"


@dataclass(frozen=True)
class LogEntry:
    term: int
    index: int
    command: str
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class RaftConfig:
    election_timeout_min_ms: float = 150.0
    election_timeout_max_ms: float = 300.0
    heartbeat_interval_ms: float = 50.0
    max_log_batch: int = 100
    snapshot_interval: int = 10_000


@dataclass
class ClusterConfig:
    """Configuration for a Raft cluster."""

    cluster_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    election: ElectionConfig = field(default_factory=ElectionConfig)
    replication: ReplicationConfig = field(default_factory=ReplicationConfig)
    state_machine: StateMachineConfig = field(default_factory=StateMachineConfig)


@dataclass
class RaftNode:
    """A single Raft node — starts as follower, may become candidate/leader."""

    node_id: str
    peer_ids: list[str] = field(default_factory=list)
    config: RaftConfig = field(default_factory=RaftConfig)

    _current_term: int = 0
    _voted_for: str | None = None
    _log: list[LogEntry] = field(default_factory=list)
    _state: NodeState = NodeState.FOLLOWER
    _commit_index: int = -1
    _last_applied: int = -1
    _next_index: dict[str, int] = field(default_factory=dict)
    _match_index: dict[str, int] = field(default_factory=dict)
    _election_deadline: float = 0.0
    _last_heartbeat: float = 0.0

    def __post_init__(self) -> None:
        self._reset_election_timeout()
        self._last_heartbeat = time.time()

    @property
    def state(self) -> NodeState:
        return self._state

    @property
    def current_term(self) -> int:
        return self._current_term

    @property
    def commit_index(self) -> int:
        return self._commit_index

    @property
    def log_size(self) -> int:
        return len(self._log)

    @property
    def is_leader(self) -> bool:
        return self._state == NodeState.LEADER

    def tick(self) -> list[str]:
        events: list[str] = []
        now = time.time()

        if self._state == NodeState.LEADER:
            if now - self._last_heartbeat >= self.config.heartbeat_interval_ms / 1000.0:
                self._send_heartbeats()
                self._last_heartbeat = now
                events.append("heartbeat_sent")
            return events

        if now >= self._election_deadline:
            events.extend(self._start_election())
        return events

    def receive_heartbeat(self, _from_leader: str, leader_term: int) -> None:
        if leader_term < self._current_term:
            return
        if leader_term > self._current_term:
            self._current_term = leader_term
            self._voted_for = None
        self._state = NodeState.FOLLOWER
        self._last_heartbeat = time.time()
        self._reset_election_timeout()

    def receive_vote_request(
        self,
        candidate_id: str,
        candidate_term: int,
        last_log_index: int,
        last_log_term: int,
    ) -> bool:
        if candidate_term < self._current_term:
            return False
        if candidate_term > self._current_term:
            self._current_term = candidate_term
            self._voted_for = None
            self._state = NodeState.FOLLOWER
        if self._voted_for is not None and self._voted_for != candidate_id:
            return False

        my_last = len(self._log) - 1
        my_term = self._log[my_last].term if my_last >= 0 else 0
        if last_log_term < my_term:
            return False
        if last_log_term == my_term and last_log_index < my_last:
            return False

        self._voted_for = candidate_id
        self._reset_election_timeout()
        return True

    def propose(self, command: str) -> LogEntry | None:
        if not self.is_leader:
            return None
        entry = LogEntry(term=self._current_term, index=len(self._log), command=command)
        self._log.append(entry)
        self._match_index[self.node_id] = len(self._log) - 1
        self._next_index[self.node_id] = len(self._log)
        return entry

    def get_committed_commands(self) -> list[str]:
        if self._commit_index <= self._last_applied:
            return []
        cmds = [
            self._log[i].command
            for i in range(self._last_applied + 1, min(self._commit_index + 1, len(self._log)))
        ]
        self._last_applied = self._commit_index
        return cmds

    def _reset_election_timeout(self) -> None:
        ms = random.uniform(
            self.config.election_timeout_min_ms, self.config.election_timeout_max_ms
        )
        self._election_deadline = time.time() + ms / 1000.0

    def _start_election(self) -> list[str]:
        self._state = NodeState.CANDIDATE
        self._current_term += 1
        self._voted_for = self.node_id
        self._reset_election_timeout()

        votes = 1
        quorum = (len(self.peer_ids) + 1) // 2 + 1
        for _ in self.peer_ids:
            votes += 1

        if votes >= quorum:
            self._state = NodeState.LEADER
            self._next_index = {p: len(self._log) for p in self.peer_ids}
            self._match_index = dict.fromkeys(self.peer_ids, -1)
            self._last_heartbeat = time.time()
            return [f"elected_leader_term_{self._current_term}"]
        self._state = NodeState.FOLLOWER
        return ["election_timeout"]

    def _send_heartbeats(self) -> None:
        for peer_id in self.peer_ids:
            match = self._match_index.get(peer_id, -1)
            nxt = self._next_index.get(peer_id, 0)
            if match < len(self._log) - 1:
                batch = self._log[nxt : nxt + self.config.max_log_batch]
                if batch:
                    self._match_index[peer_id] = batch[-1].index
                    self._next_index[peer_id] = batch[-1].index + 1
        self._advance_commit_index()

    def _advance_commit_index(self) -> None:
        quorum = (len(self.peer_ids) + 1) // 2 + 1
        for idx in range(self._commit_index + 1, len(self._log)):
            replicated = 1
            for peer_id in self.peer_ids:
                if self._match_index.get(peer_id, -1) >= idx:
                    replicated += 1
            if replicated >= quorum and self._log[idx].term == self._current_term:
                self._commit_index = idx


class RaftCluster:
    """Manages a cluster of Raft nodes with full RPC simulation.

    Ties together LeaderElection, LogReplication, and StateMachine
    into a complete Raft consensus cluster. Provides:

    - Multi-node lifecycle management (add/remove nodes)
    - Simulated RPC layer for leader election and log replication
    - Command proposal with automatic replication
    - Commit index tracking and state machine application
    - Snapshot creation, installation, and log compaction
    - Cluster health monitoring and diagnostics

    Usage::

        cluster = RaftCluster(node_count=3)
        cluster.start()
        leader = cluster.current_leader
        cluster.propose("set theme=dark")
        cluster.tick()  # Drives replication and commit
        committed = cluster.get_committed_commands()
    """

    def __init__(
        self,
        node_count: int = 3,
        config: ClusterConfig | None = None,
        node_ids: list[str] | None = None,
    ) -> None:
        if node_count < 1:
            raise ValueError(f"Cluster requires at least 1 node, got {node_count}")

        self.config = config or ClusterConfig()
        node_ids = node_ids or [f"node-{i}" for i in range(node_count)]

        self._nodes: dict[str, RaftNode] = {}
        self._elections: dict[str, LeaderElection] = {}
        self._replications: dict[str, LogReplication] = {}
        self._state_machines: dict[str, StateMachine] = {}
        self._node_order: list[str] = []

        for nid in node_ids:
            peer_ids = [p for p in node_ids if p != nid]
            self._add_node_internal(nid, peer_ids)

        self._started: bool = False
        self._tick_count: int = 0
        self._command_history: list[str] = []

    # ── Properties ───────────────────────────────────────────────

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def started(self) -> bool:
        return self._started

    @property
    def current_leader(self) -> str | None:
        for nid, election in self._elections.items():
            if election.is_leader:
                return nid
        return None

    @property
    def cluster_state(self) -> ClusterState:
        leader = self.current_leader
        if leader is None:
            return ClusterState.LEADERLESS if self._started else ClusterState.RECOVERING

        # Check if multiple nodes think they're leaders (split brain)
        leaders = sum(1 for e in self._elections.values() if e.is_leader)
        if leaders > 1:
            return ClusterState.SPLIT_BRAIN

        # Check commit index consistency
        commit_indices = {n._commit_index for n in self._nodes.values()}
        if len(commit_indices) > 1 and max(commit_indices) - min(commit_indices) > 10:
            return ClusterState.DEGRADED

        return ClusterState.HEALTHY

    # ── Public API ───────────────────────────────────────────────

    def start(self) -> None:
        """Start the cluster — initializes leader election."""
        self._started = True
        now = time.monotonic()
        for nid in self._node_order:
            self._elections[nid]._state.election_deadline = now - 0.001

    def stop(self) -> None:
        """Stop the cluster gracefully."""
        for nid, election in self._elections.items():
            if election.is_leader:
                election.step_down()
        self._started = False

    def tick(self) -> list[str]:
        """Advance the cluster by one tick — drives election, replication, commit.

        Returns list of event strings.
        """
        if not self._started:
            return []

        self._tick_count += 1
        events: list[str] = []

        # 1. Leader election ticks
        for nid in self._node_order:
            node = self._nodes[nid]
            election = self._elections[nid]
            log_last_term = node._log[-1].term if node._log else 0
            e_events = election.tick(len(node._log), log_last_term)
            events.extend(f"{nid}:{e}" for e in e_events)

        # 2. Run elections — simulate RPCs
        for nid in self._node_order:
            election = self._elections[nid]
            if election.phase == ElectionPhase.CANDIDATE:
                node = self._nodes[nid]
                log_last_term = node._log[-1].term if node._log else 0
                _, request = election.start_election(len(node._log), log_last_term)
                if request:
                    self._simulate_vote_requests(request, election)

                result = election.try_claim_leadership()
                if result:
                    events.append(f"{nid}:elected_leader_term_{result.term}")
                    self._on_leader_elected(nid, result)
                    break  # Only one leader per term — exit election loop

        # 3. Leader replication and heartbeat
        leader = self.current_leader
        if leader:
            leader_node = self._nodes[leader]
            repl = self._replications[leader]
            leader_election = self._elections[leader]

            for peer_id in self._node_order:
                if peer_id == leader:
                    continue

                req = repl.build_append_entries(
                    peer=peer_id,
                    log=leader_node._log,
                    current_term=leader_election.current_term,
                    leader_commit=leader_node._commit_index,
                )
                if req:
                    follower = self._nodes[peer_id]
                    follower_election = self._elections[peer_id]
                    follower_election.receive_heartbeat(leader, req.term)

                    resp, updated_log = self._replications[peer_id].handle_append_entries(
                        req, follower._log,
                        follower_election.current_term,
                        follower._commit_index,
                    )
                    repl.process_response(peer_id, resp)

                    if updated_log is not None:
                        follower._log = updated_log
                        follower._commit_index = req.leader_commit

            # Advance commit index
            new_commit = repl.advance_commit_index(
                leader_node._log,
                leader_election.current_term,
                leader_node._commit_index,
            )
            if new_commit > leader_node._commit_index:
                leader_node._commit_index = new_commit
                events.append(f"commit_index_advanced_to_{new_commit}")

            # Apply committed commands to state machines
            for nid in self._node_order:
                node = self._nodes[nid]
                sm = self._state_machines[nid]
                cmds = node.get_committed_commands()
                if cmds:
                    sm.apply_batch(cmds)

        return events

    def propose(self, command: str) -> bool:
        """Propose a command to be replicated across the cluster.

        Returns True if accepted by the leader, False otherwise.
        """
        leader = self.current_leader
        if leader is None:
            return False

        node = self._nodes[leader]
        entry = node.propose(command)
        if entry is None:
            return False

        self._command_history.append(command)
        return True

    def get_committed_commands(self) -> list[str]:
        """Get all committed commands from the leader."""
        leader = self.current_leader
        if leader is None:
            return []
        return self._nodes[leader].get_committed_commands()

    def get_state(self, node_id: str | None = None) -> dict:
        """Get the state machine state for a node (or the leader)."""
        target = node_id or self.current_leader
        if target is None or target not in self._state_machines:
            return {}
        return self._state_machines[target].state

    def add_node(self, node_id: str) -> bool:
        """Add a new node to the cluster (membership change)."""
        if node_id in self._nodes:
            return False

        all_peers = list(self._node_order)
        self._add_node_internal(node_id, all_peers)

        # Update all existing nodes to include the new peer
        for nid in all_peers:
            if node_id not in self._nodes[nid].peer_ids:
                self._nodes[nid].peer_ids.append(node_id)
                self._elections[nid].peer_ids.append(node_id)
                self._replications[nid].add_peer(node_id)

        return True

    def remove_node(self, node_id: str) -> bool:
        """Remove a node from the cluster."""
        if node_id not in self._nodes:
            return False

        self._nodes.pop(node_id)
        self._elections.pop(node_id)
        self._replications.pop(node_id)
        self._state_machines.pop(node_id)
        self._node_order.remove(node_id)

        for nid in self._node_order:
            if node_id in self._nodes[nid].peer_ids:
                self._nodes[nid].peer_ids.remove(node_id)
            if node_id in self._elections[nid].peer_ids:
                self._elections[nid].peer_ids.remove(node_id)
            self._replications[nid].remove_peer(node_id)

        return True

    def create_snapshot(self, node_id: str | None = None) -> Snapshot | None:
        """Create a state machine snapshot for log compaction."""
        target = node_id or self.current_leader
        if target is None:
            return None

        node = self._nodes[target]
        sm = self._state_machines[target]
        last_term = node._log[node._commit_index].term if node._commit_index >= 0 else 0

        return sm.create_snapshot(
            last_included_index=node._commit_index,
            last_included_term=last_term,
            peers=list(self._node_order),
        )

    def get_cluster_status(self) -> dict:
        """Return comprehensive cluster status for monitoring."""
        leader = self.current_leader
        status = {
            "cluster_state": self.cluster_state.value,
            "current_leader": leader,
            "node_count": self.node_count,
            "tick_count": self._tick_count,
            "nodes": {},
        }
        for nid in self._node_order:
            node = self._nodes[nid]
            election = self._elections[nid]
            repl = self._replications[nid]
            status["nodes"][nid] = {
                "state": node.state.value,
                "term": node.current_term,
                "commit_index": node.commit_index,
                "log_size": node.log_size,
                "is_leader": election.is_leader,
                "phase": election.phase.value,
                "match_index": repl.match_index,
                "quorum_size": election.get_quorum_size(),
            }
        return status

    # ── Private ───────────────────────────────────────────────────

    def _add_node_internal(self, node_id: str, peer_ids: list[str]) -> None:
        """Add a node and all its associated sub-systems."""
        raft_config = RaftConfig(
            election_timeout_min_ms=self.config.election.election_timeout_min_ms,
            election_timeout_max_ms=self.config.election.election_timeout_max_ms,
            heartbeat_interval_ms=self.config.election.heartbeat_interval_ms,
        )
        node = RaftNode(node_id=node_id, peer_ids=list(peer_ids), config=raft_config)
        self._nodes[node_id] = node
        self._elections[node_id] = LeaderElection(
            node_id=node_id,
            peer_ids=list(peer_ids),
            config=self.config.election,
        )
        self._replications[node_id] = LogReplication(
            node_id=node_id,
            peer_ids=list(peer_ids),
            config=self.config.replication,
        )
        self._state_machines[node_id] = StateMachine(config=self.config.state_machine)
        self._node_order.append(node_id)

    def _simulate_vote_requests(self, request: VoteRequest, candidate_election: LeaderElection) -> None:
        """Simulate broadcasting a vote request to all peers and tallying results."""
        for peer_id in self._node_order:
            if peer_id == candidate_election.node_id:
                continue
            peer_election = self._elections[peer_id]
            peer_node = self._nodes[peer_id]
            log_last_term = peer_node._log[-1].term if peer_node._log else 0
            response = peer_election.request_vote(
                request, len(peer_node._log), log_last_term
            )
            candidate_election.record_vote(peer_id, response.vote_granted)

    def _on_leader_elected(self, node_id: str, result: ElectionResult) -> None:
        """Handle post-election setup — reset replication state for new leader."""
        node = self._nodes[node_id]
        node._state = NodeState.LEADER
        node._current_term = result.term
        log_size = len(node._log)
        self._replications[node_id].reset(log_size)

        # Notify all other nodes that this node is the leader
        for peer_id in self._node_order:
            if peer_id != node_id:
                self._elections[peer_id].receive_heartbeat(node_id, result.term)
                self._nodes[peer_id]._state = NodeState.FOLLOWER
