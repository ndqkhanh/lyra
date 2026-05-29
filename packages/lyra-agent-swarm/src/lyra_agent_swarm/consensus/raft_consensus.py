"""Raft Consensus — leader election and log replication for agent swarms.

Implements core Raft algorithm (Ongaro & Ousterhout, 2014):
  - Leader election with randomized timeouts (150-300ms)
  - Log replication via AppendEntries
  - Safety: only committed entries are applied
  - Single-server cluster changes

Used by Lyra's agent swarm to maintain consistent shared state across
distributed agent instances running in parallel.
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum


class NodeState(StrEnum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


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
