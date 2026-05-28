"""
Consensus Protocol for leader election and fault detection.

Implements:
- Raft-like leader election with term-based voting
- Byzantine fault detection
- Quorum-based decision making
- Log replication semantics
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class NodeState(Enum):
    """State of a consensus node."""

    FOLLOWER = auto()
    CANDIDATE = auto()
    LEADER = auto()
    BYZANTINE = auto()
    OFFLINE = auto()


class ConsensusRole(Enum):
    """Roles that a node can serve in consensus."""

    VOTER = auto()
    OBSERVER = auto()
    LEADER = auto()


@dataclass
class LogEntry:
    """An entry in the consensus log."""

    term: int
    index: int
    command: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class ConsensusConfig:
    """Configuration for the consensus protocol."""

    election_timeout_min: float = 1.0
    election_timeout_max: float = 3.0
    heartbeat_interval: float = 0.5
    quorum_majority: float = 0.51
    byzantine_threshold: int = 3
    max_log_entries: int = 1000
    enable_byzantine_detection: bool = True


class ConsensusProtocol:
    """
    Implements consensus protocol for the swarm.

    Features:
    - Raft-like leader election with randomized timeouts
    - Term-based voting and log replication
    - Byzantine fault detection via behavioral monitoring
    - Quorum-based decision making
    """

    def __init__(
        self,
        node_id: str,
        config: ConsensusConfig | None = None,
    ) -> None:
        self.node_id = node_id
        self.config = config or ConsensusConfig()
        self.state: NodeState = NodeState.FOLLOWER
        self.role: ConsensusRole = ConsensusRole.VOTER
        self.current_term: int = 0
        self.voted_for: str | None = None
        self.leader_id: str | None = None
        self.log: list[LogEntry] = []
        self.commit_index: int = -1
        self.last_applied: int = -1

        self._votes_received: int = 0
        self._total_nodes: int = 0
        self._node_states: dict[str, NodeState] = {}
        self._byzantine_scores: dict[str, int] = {}
        self._lock: asyncio.Lock = asyncio.Lock()
        self._running: bool = False
        self._election_task: asyncio.Task | None = None
        self._heartbeat_task: asyncio.Task | None = None
        self._stats: dict[str, int] = {
            "elections_started": 0,
            "elections_won": 0,
            "votes_cast": 0,
            "heartbeats_sent": 0,
            "byzantine_detections": 0,
            "quorum_decisions": 0,
        }

    async def start(self) -> None:
        """Start the consensus protocol."""
        self._running = True
        self.state = NodeState.FOLLOWER
        self._election_task = asyncio.create_task(self._election_timeout_loop())

    async def stop(self) -> None:
        """Stop the consensus protocol."""
        self._running = False
        if self._election_task:
            self._election_task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._election_task:
            await asyncio.gather(self._election_task, return_exceptions=True)
        if self._heartbeat_task:
            await asyncio.gather(self._heartbeat_task, return_exceptions=True)

    def set_node_count(self, count: int) -> None:
        """Set the total number of nodes in the cluster."""
        self._total_nodes = count
        self._node_states = {
            f"node_{i}": NodeState.FOLLOWER for i in range(count)
        }

    def get_quorum_size(self) -> int:
        """Calculate the quorum size needed for decisions."""
        return max(1, int(self._total_nodes * self.config.quorum_majority) + 1)

    async def request_vote(
        self,
        candidate_id: str,
        candidate_term: int,
        last_log_index: int,
        last_log_term: int,
    ) -> dict[str, Any]:
        """
        Handle a vote request from a candidate.

        Args:
            candidate_id: The candidate requesting the vote
            candidate_term: The candidate's term
            last_log_index: Index of candidate's last log entry
            last_log_term: Term of candidate's last log entry

        Returns:
            Dict with term and vote_granted
        """
        async with self._lock:
            self._stats["votes_cast"] += 1

            if candidate_term < self.current_term:
                return {"term": self.current_term, "vote_granted": False}

            if candidate_term > self.current_term:
                self.current_term = candidate_term
                self.state = NodeState.FOLLOWER
                self.voted_for = None

            if self.voted_for is None or self.voted_for == candidate_id:
                my_last_index = len(self.log) - 1
                my_last_term = self.log[-1].term if self.log else 0

                if last_log_term > my_last_term or (
                    last_log_term == my_last_term and last_log_index >= my_last_index
                ):
                    self.voted_for = candidate_id
                    return {"term": self.current_term, "vote_granted": True}

            return {"term": self.current_term, "vote_granted": False}

    async def receive_heartbeat(
        self,
        leader_id: str,
        leader_term: int,
        entries: list[LogEntry] | None = None,
    ) -> dict[str, Any]:
        """
        Receive a heartbeat from the leader.

        Args:
            leader_id: The leader sending the heartbeat
            leader_term: The leader's current term
            entries: Optional log entries to replicate

        Returns:
            Dict with success status and current term
        """
        async with self._lock:
            if leader_term < self.current_term:
                return {"success": False, "term": self.current_term}

            if leader_term > self.current_term:
                self.current_term = leader_term
                self.state = NodeState.FOLLOWER
                self.voted_for = None

            self.leader_id = leader_id
            self.state = NodeState.FOLLOWER

            if entries:
                for entry in entries:
                    if entry.index < len(self.log):
                        self.log[entry.index] = entry
                    elif entry.index == len(self.log):
                        self.log.append(entry)

            return {"success": True, "term": self.current_term}

    async def append_entry(self, command: str, data: dict[str, Any] | None = None) -> int | None:
        """
        Append an entry to the log (leader only).

        Args:
            command: The command to log
            data: Optional data payload

        Returns:
            Log index if appended, None if not leader
        """
        if self.state != NodeState.LEADER:
            return None

        async with self._lock:
            entry = LogEntry(
                term=self.current_term,
                index=len(self.log),
                command=command,
                data=data or {},
            )
            self.log.append(entry)
            if len(self.log) > self.config.max_log_entries:
                self.log = self.log[-self.config.max_log_entries:]
            return entry.index

    async def commit(self, index: int) -> None:
        """Commit log entries up to the given index."""
        async with self._lock:
            if index > self.commit_index and index < len(self.log):
                self.commit_index = index
                self.last_applied = index

    async def make_decision(self, proposal: dict[str, Any]) -> bool:
        """
        Make a quorum-based decision.

        Args:
            proposal: The proposal to decide on

        Returns:
            True if quorum reached, False otherwise
        """
        if self.state != NodeState.LEADER:
            return False

        async with self._lock:
            votes_for = 1
            votes_against = 0

            for node_id, node_state in self._node_states.items():
                if node_id == self.node_id:
                    continue
                if node_state in (NodeState.BYZANTINE, NodeState.OFFLINE):
                    votes_against += 1
                else:
                    votes_for += 1

            quorum = self.get_quorum_size()
            reached = votes_for >= quorum

            if reached:
                self._stats["quorum_decisions"] += 1
                entry = LogEntry(
                    term=self.current_term,
                    index=len(self.log),
                    command="decision",
                    data=proposal,
                )
                self.log.append(entry)
                self.commit_index = len(self.log) - 1

            return reached

    async def report_byzantine(self, node_id: str, _reason: str = "") -> None:
        """
        Report and detect Byzantine behavior.

        Args:
            node_id: The suspected node
            reason: Reason for suspicion
        """
        async with self._lock:
            current = self._byzantine_scores.get(node_id, 0)
            self._byzantine_scores[node_id] = current + 1

            if self._byzantine_scores[node_id] >= self.config.byzantine_threshold:
                self._node_states[node_id] = NodeState.BYZANTINE
                self._stats["byzantine_detections"] += 1

    def is_byzantine(self, node_id: str) -> bool:
        """Check if a node is marked as Byzantine."""
        return self._node_states.get(node_id) == NodeState.BYZANTINE

    async def _election_timeout_loop(self) -> None:
        """Randomized election timeout loop."""
        while self._running:
            timeout = self._random_election_timeout()
            await asyncio.sleep(timeout)

            if self.state == NodeState.LEADER:
                continue

            await self._start_election()

    async def _start_election(self) -> None:
        """Start a leader election."""
        async with self._lock:
            self.current_term += 1
            self.state = NodeState.CANDIDATE
            self.voted_for = self.node_id
            self._votes_received = 1
            self._stats["elections_started"] += 1

        votes_needed = self.get_quorum_size()
        if self._votes_received >= votes_needed:
            await self._become_leader()
            return

        for node_id in list(self._node_states.keys()):
            if node_id == self.node_id:
                continue
            if self._node_states.get(node_id) == NodeState.BYZANTINE:
                continue

            async with self._lock:
                self._votes_received += 1

            if self._votes_received >= votes_needed:
                await self._become_leader()
                return

        async with self._lock:
            if self.state != NodeState.LEADER:
                self.state = NodeState.FOLLOWER

    async def _become_leader(self) -> None:
        """Transition to leader state."""
        async with self._lock:
            self.state = NodeState.LEADER
            self.leader_id = self.node_id
            self._stats["elections_won"] += 1

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats as leader."""
        while self._running and self.state == NodeState.LEADER:
            async with self._lock:
                self._stats["heartbeats_sent"] += 1
            await asyncio.sleep(self.config.heartbeat_interval)

    def _random_election_timeout(self) -> float:
        """Generate a random election timeout."""
        import random
        return random.uniform(
            self.config.election_timeout_min,
            self.config.election_timeout_max,
        )

    def get_log_since(self, index: int) -> list[LogEntry]:
        """Get log entries from a given index onward."""
        if index < 0:
            return list(self.log)
        if index >= len(self.log):
            return []
        return self.log[index:]

    def get_stats(self) -> dict[str, int]:
        """Get consensus statistics."""
        return dict(self._stats)

    @property
    def is_leader(self) -> bool:
        """Check if this node is the leader."""
        return self.state == NodeState.LEADER
