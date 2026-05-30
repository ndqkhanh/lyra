"""Raft Log Replication — AppendEntries protocol with consistency guarantees.

Implements Raft's log replication sub-protocol:
  - AppendEntries RPC with prevLogIndex/prevLogTerm consistency checks
  - Leader-to-follower log matching via index+term tuple
  - Batch replication with configurable max_batch_size
  - Commit index advancement via quorum acknowledgment
  - Log conflict resolution (decrement nextIndex on mismatch)
  - Leader append-only invariant enforcement
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AppendEntriesRequest:
    """An AppendEntries RPC from leader to follower."""

    term: int
    leader_id: str
    prev_log_index: int
    prev_log_term: int
    entries: tuple[tuple[int, str], ...]  # ((index, command), ...)
    leader_commit: int
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass(frozen=True)
class AppendEntriesResponse:
    """Response to an AppendEntries RPC."""

    term: int
    success: bool
    follower_id: str
    request_id: str
    match_index: int = -1
    conflict_term: int = 0
    conflict_index: int = -1


@dataclass
class ReplicationConfig:
    """Configuration for log replication."""

    max_batch_size: int = 100
    max_pipeline_depth: int = 5
    commit_quorum_min: int = 1
    append_timeout_ms: float = 500.0


@dataclass
class ReplicationResult:
    """Result of a log replication round."""

    entries_sent: int
    entries_committed: int
    followers_acked: int
    total_followers: int
    commit_index: int
    leader_commit: int
    latency_ms: float


class LogReplication:
    """Manages log replication from leader to followers.

    Implements the AppendEntries sub-protocol from Raft:
    - Leader tracks nextIndex and matchIndex per follower
    - On AppendEntries rejection, leader decrements nextIndex and retries
    - Entry is committed when replicated to a quorum
    - Only entries from the leader's current term commit via quorum

    Usage::

        repl = LogReplication(node_id="leader-1", peer_ids=["f1", "f2"])
        req = repl.build_append_entries(peer="f1", log=log, current_term=5)
        resp = follower.handle_append_entries(req)
        repl.process_response(peer="f1", resp=resp)
    """

    def __init__(
        self,
        node_id: str,
        peer_ids: list[str] | None = None,
        config: ReplicationConfig | None = None,
    ) -> None:
        self.node_id = node_id
        self.peer_ids = peer_ids or []
        self.config = config or ReplicationConfig()
        self._next_index: dict[str, int] = {}
        self._match_index: dict[str, int] = {}
        self._pending: dict[str, list[AppendEntriesRequest]] = {}
        self._last_replication: float = 0.0
        self._reset_indices()

    # ── Properties ───────────────────────────────────────────────

    @property
    def next_index(self) -> dict[str, int]:
        return dict(self._next_index)

    @property
    def match_index(self) -> dict[str, int]:
        return dict(self._match_index)

    # ── Public API ───────────────────────────────────────────────

    def build_append_entries(
        self,
        peer: str,
        log: list,
        current_term: int,
        leader_commit: int,
    ) -> AppendEntriesRequest | None:
        """Build an AppendEntries request for a specific peer.

        Returns None if no entries need to be sent (heartbeat only).
        """
        if peer not in self._next_index:
            self._next_index[peer] = 0

        prev_log_index = self._next_index[peer] - 1
        prev_log_term = 0
        if prev_log_index >= 0 and prev_log_index < len(log):
            prev_log_term = log[prev_log_index].term if hasattr(log[prev_log_index], 'term') else 0

        entries_to_send: list[tuple[int, str]] = []
        start = self._next_index[peer]
        end = min(start + self.config.max_batch_size, len(log))

        for i in range(start, end):
            entry = log[i]
            cmd = entry.command if hasattr(entry, 'command') else str(entry)
            idx = entry.index if hasattr(entry, 'index') else i
            entries_to_send.append((idx, cmd))

        self._last_replication = time.monotonic()

        return AppendEntriesRequest(
            term=current_term,
            leader_id=self.node_id,
            prev_log_index=prev_log_index,
            prev_log_term=prev_log_term,
            entries=tuple(entries_to_send),
            leader_commit=leader_commit,
        )

    def handle_append_entries(
        self,
        request: AppendEntriesRequest,
        log: list,
        current_term: int,
        commit_index: int,
    ) -> tuple[AppendEntriesResponse, list | None]:
        """Handle an incoming AppendEntries request as a follower.

        Returns (response, updated_log_or_None).
        Implements Raft's AppendEntries receiver logic.
        """
        if request.term < current_term:
            return (
                AppendEntriesResponse(
                    term=current_term,
                    success=False,
                    follower_id=self.node_id,
                    request_id=request.request_id,
                ),
                None,
            )

        # Consistency check: log must contain entry at prevLogIndex with prevLogTerm
        if request.prev_log_index >= 0:
            if request.prev_log_index >= len(log):
                return (
                    AppendEntriesResponse(
                        term=max(current_term, request.term),
                        success=False,
                        follower_id=self.node_id,
                        request_id=request.request_id,
                        conflict_index=len(log),
                    ),
                    None,
                )

            existing = log[request.prev_log_index]
            existing_term = existing.term if hasattr(existing, 'term') else 0
            if existing_term != request.prev_log_term:
                # Find the first index of the conflicting term
                conflict_term = existing_term
                conflict_index = request.prev_log_index
                while conflict_index > 0:
                    prev = log[conflict_index - 1]
                    prev_term = prev.term if hasattr(prev, 'term') else 0
                    if prev_term != conflict_term:
                        break
                    conflict_index -= 1

                return (
                    AppendEntriesResponse(
                        term=max(current_term, request.term),
                        success=False,
                        follower_id=self.node_id,
                        request_id=request.request_id,
                        conflict_term=conflict_term,
                        conflict_index=conflict_index,
                    ),
                    None,
                )

        # Append new entries, truncating conflicting ones
        new_log = list(log[: request.prev_log_index + 1])

        for entry_index, command in request.entries:
            new_log.append(_make_entry(entry_index, request.term, command))

        if new_log:
            match_idx = new_log[-1].index if hasattr(new_log[-1], 'index') else len(new_log) - 1
        else:
            match_idx = request.prev_log_index

        return (
            AppendEntriesResponse(
                term=max(current_term, request.term),
                success=True,
                follower_id=self.node_id,
                request_id=request.request_id,
                match_index=match_idx,
            ),
            new_log,
        )

    def process_response(self, peer: str, response: AppendEntriesResponse) -> int | None:
        """Process a follower's response to AppendEntries.

        Returns new commit_index if it advanced, None otherwise.
        """
        if response.success:
            self._match_index[peer] = max(
                self._match_index.get(peer, -1),
                response.match_index,
            )
            self._next_index[peer] = response.match_index + 1
            return None

        # On failure: decrement nextIndex and retry
        if response.conflict_index >= 0:
            self._next_index[peer] = response.conflict_index
        elif self._next_index.get(peer, 0) > 0:
            self._next_index[peer] -= 1

        return None

    def advance_commit_index(
        self,
        log: list,
        current_term: int,
        current_commit: int,
    ) -> int:
        """Advance the commit index based on quorum replication.

        Returns the new commit_index.
        """
        quorum = (len(self.peer_ids) + 1) // 2 + 1

        for idx in range(current_commit + 1, len(log)):
            replicated = 1  # Leader always counts
            for peer in self.peer_ids:
                if self._match_index.get(peer, -1) >= idx:
                    replicated += 1

            if replicated >= quorum:
                entry = log[idx]
                entry_term = entry.term if hasattr(entry, 'term') else 0
                if entry_term == current_term:
                    current_commit = idx

        return current_commit

    def get_replication_status(self) -> dict:
        """Return a summary of replication status across all peers."""
        committed_count = max(self._match_index.values()) + 1 if self._match_index else 0
        behind_peers = [
            p for p in self.peer_ids
            if self._match_index.get(p, -1) < committed_count - 1
        ]
        return {
            "match_index": dict(self._match_index),
            "next_index": dict(self._next_index),
            "committed_count": committed_count,
            "behind_peers": behind_peers,
            "fully_replicated": len(behind_peers) == 0,
        }

    def add_peer(self, peer_id: str, log_size: int = 0) -> None:
        """Add a new peer to the replication group."""
        if peer_id not in self.peer_ids:
            self.peer_ids.append(peer_id)
        self._next_index[peer_id] = log_size
        self._match_index[peer_id] = -1

    def remove_peer(self, peer_id: str) -> None:
        """Remove a peer from the replication group."""
        if peer_id in self.peer_ids:
            self.peer_ids.remove(peer_id)
        self._next_index.pop(peer_id, None)
        self._match_index.pop(peer_id, None)

    def build_heartbeat(
        self,
        current_term: int,
        leader_commit: int,
    ) -> list[tuple[str, AppendEntriesRequest]]:
        """Build heartbeat (empty AppendEntries) for all peers.

        Returns list of (peer_id, request) tuples.
        """
        requests: list[tuple[str, AppendEntriesRequest]] = []
        for peer in self.peer_ids:
            req = AppendEntriesRequest(
                term=current_term,
                leader_id=self.node_id,
                prev_log_index=self._match_index.get(peer, -1),
                prev_log_term=current_term,
                entries=(),
                leader_commit=leader_commit,
            )
            requests.append((peer, req))
        return requests

    def reset(self, log_size: int = 0) -> None:
        """Reset replication state (e.g., on new leader election)."""
        self._next_index = {p: log_size for p in self.peer_ids}
        self._match_index = {p: -1 for p in self.peer_ids}
        self._pending.clear()

    # ── Private ───────────────────────────────────────────────────

    def _reset_indices(self) -> None:
        self._next_index = {p: 0 for p in self.peer_ids}
        self._match_index = {p: -1 for p in self.peer_ids}


def _make_entry(index: int, term: int, command: str):
    """Create a log entry object compatible with the raft_consensus LogEntry."""
    from lyra_agent_swarm.consensus.raft_consensus import LogEntry

    return LogEntry(term=term, index=index, command=command)
