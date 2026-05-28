"""Gossip Memory Protocol — peer-to-peer memory synchronization with CRDT merges.

Nodes exchange memory updates via anti-entropy gossip, using vector clocks
for causal ordering and last-writer-wins (LWW) conflict resolution. The
protocol guarantees eventual consistency across a decentralized agent swarm.

References:
  - "Epidemic Algorithms for Replicated Database Maintenance" (Demers et al.)
  - Dynamo-style gossip (Amazon)
  - Scuttlebutt / Secure Scuttlebutt (SSB) for offline-tolerant sync
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass
from enum import Enum


class UpdateOp(Enum):
    PUT = "put"
    DELETE = "delete"
    MERGE = "merge"


@dataclass(frozen=True)
class VectorClock:
    """Vector clock tracking causal ordering of updates across nodes."""

    counters: tuple[tuple[str, int], ...]

    @staticmethod
    def create(node_id: str) -> VectorClock:
        return VectorClock(counters=((node_id, 0),))

    def increment(self, node_id: str) -> VectorClock:
        counters = dict(self.counters)
        counters[node_id] = counters.get(node_id, 0) + 1
        return VectorClock(counters=tuple(sorted(counters.items())))

    def get(self, node_id: str) -> int:
        return dict(self.counters).get(node_id, 0)

    def happens_before(self, other: VectorClock) -> bool:
        """True if self strictly happens-before other."""
        self_d = dict(self.counters)
        other_d = dict(other.counters)
        all_nodes = set(self_d) | set(other_d)
        at_least_one_less = False
        for n in all_nodes:
            s = self_d.get(n, 0)
            o = other_d.get(n, 0)
            if s > o:
                return False
            if s < o:
                at_least_one_less = True
        return at_least_one_less

    def concurrent(self, other: VectorClock) -> bool:
        """True if neither clock happens-before the other."""
        return (
            not self.happens_before(other) and not other.happens_before(self)
        )

    def merge(self, other: VectorClock) -> VectorClock:
        """Pointwise max — the join in the vector clock lattice."""
        self_d = dict(self.counters)
        other_d = dict(other.counters)
        merged: dict[str, int] = {}
        for n in set(self_d) | set(other_d):
            merged[n] = max(self_d.get(n, 0), other_d.get(n, 0))
        return VectorClock(counters=tuple(sorted(merged.items())))

    def to_dict(self) -> dict[str, int]:
        return dict(self.counters)

    @staticmethod
    def from_dict(data: dict[str, int]) -> VectorClock:
        return VectorClock(counters=tuple(sorted(data.items())))


@dataclass(frozen=True)
class MemoryUpdate:
    """A single memory update propagated via gossip."""

    update_id: str
    key: str
    value: str
    op: UpdateOp
    node_id: str
    vector_clock: VectorClock
    timestamp: float
    content_hash: str
    parent_hash: str | None = None

    @staticmethod
    def create(
        key: str,
        value: str,
        op: UpdateOp,
        node_id: str,
        clock: VectorClock,
        parent_hash: str | None = None,
        update_id: str = "",
    ) -> MemoryUpdate:
        content = f"{key}:{value}:{op.value}:{node_id}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        return MemoryUpdate(
            update_id=update_id or str(uuid.uuid4()),
            key=key,
            value=value,
            op=op,
            node_id=node_id,
            vector_clock=clock,
            timestamp=time.time(),
            content_hash=content_hash,
            parent_hash=parent_hash,
        )


@dataclass(frozen=True)
class MergeResult:
    """Result of merging a batch of gossip messages."""

    accepted: tuple[MemoryUpdate, ...]
    rejected: tuple[MemoryUpdate, ...]
    conflicts: tuple[MemoryUpdate, ...]
    new_clock: VectorClock
    merge_count: int


@dataclass
class ConsensusConfig:
    """Gossip protocol configuration."""

    fanout: int = 3  # peers to gossip with per round
    sync_interval_sec: float = 5.0  # time between gossip rounds
    max_message_age_sec: float = 300.0  # TTL for gossip messages
    max_seen_messages: int = 10000  # dedup buffer size
    convergence_threshold: float = 0.99  # fraction of peers that must agree


@dataclass
class GossipMessage:
    """Envelope for a gossip message exchanged between nodes."""

    message_id: str
    updates: tuple[MemoryUpdate, ...]
    sender_id: str
    sender_clock: VectorClock
    sent_at: float
    ttl: int = 3  # remaining hop count

    @staticmethod
    def create(
        updates: tuple[MemoryUpdate, ...],
        sender_id: str,
        sender_clock: VectorClock,
        ttl: int = 3,
    ) -> GossipMessage:
        return GossipMessage(
            message_id=str(uuid.uuid4()),
            updates=updates,
            sender_id=sender_id,
            sender_clock=sender_clock,
            sent_at=time.time(),
            ttl=ttl,
        )


class GossipNode:
    """A node in the gossip network maintaining a local memory store.

    Each node tracks its own vector clock, a set of peer clocks, and a
    local key-value store of memory records. It periodically gossips with
    peers to propagate updates and achieve eventual consistency.
    """

    def __init__(
        self,
        node_id: str,
        config: ConsensusConfig | None = None,
    ) -> None:
        self.node_id = node_id
        self.config = config or ConsensusConfig()
        self._clock = VectorClock.create(node_id)
        self._store: dict[str, MemoryUpdate] = {}
        self._seen: set[str] = set()
        self._peer_clocks: dict[str, VectorClock] = {}
        self._peer_last_seen: dict[str, float] = {}
        self._msg_count: int = 0
        self._merge_count: int = 0

    # ── properties ────────────────────────────────────────────────────

    @property
    def clock(self) -> VectorClock:
        return self._clock

    @property
    def store_size(self) -> int:
        return len(self._store)

    @property
    def peer_count(self) -> int:
        return len(self._peer_clocks)

    @property
    def merge_count(self) -> int:
        return self._merge_count

    # ── local operations ──────────────────────────────────────────────

    def put(self, key: str, value: str) -> MemoryUpdate:
        """Write a value locally and advance the vector clock."""
        self._clock = self._clock.increment(self.node_id)
        update = MemoryUpdate.create(
            key=key,
            value=value,
            op=UpdateOp.PUT,
            node_id=self.node_id,
            clock=self._clock,
        )
        self._store[key] = update
        self._seen.add(update.content_hash)
        self._msg_count += 1
        return update

    def delete(self, key: str) -> MemoryUpdate | None:
        """Delete a key locally and advance the vector clock."""
        if key not in self._store:
            return None
        self._clock = self._clock.increment(self.node_id)
        update = MemoryUpdate.create(
            key=key,
            value="",
            op=UpdateOp.DELETE,
            node_id=self.node_id,
            clock=self._clock,
            parent_hash=self._store[key].content_hash,
        )
        self._store.pop(key, None)
        self._seen.add(update.content_hash)
        self._msg_count += 1
        return update

    def get(self, key: str) -> MemoryUpdate | None:
        return self._store.get(key)

    def local_keys(self) -> list[str]:
        return sorted(self._store)

    # ── gossip protocol ───────────────────────────────────────────────

    def prepare_gossip(self, peer_ids: list[str] | None = None) -> GossipMessage:
        """Prepare a gossip message with recent updates for peers."""
        targets = peer_ids or list(self._peer_clocks)
        recent: list[MemoryUpdate] = []

        for update in self._store.values():
            should_send = False
            for peer_id in targets:
                peer_clock = self._peer_clocks.get(peer_id)
                if peer_clock is None:
                    should_send = True
                    break
                if peer_clock.get(self.node_id) < update.vector_clock.get(
                    self.node_id
                ):
                    should_send = True
                    break
            if should_send:
                recent.append(update)

        return GossipMessage.create(
            updates=tuple(recent),
            sender_id=self.node_id,
            sender_clock=self._clock,
        )

    def receive_gossip(self, message: GossipMessage) -> MergeResult:
        """Process an incoming gossip message and merge updates."""
        if message.ttl <= 0:
            return MergeResult(
                accepted=(),
                rejected=(),
                conflicts=(),
                new_clock=self._clock,
                merge_count=0,
            )

        accepted: list[MemoryUpdate] = []
        rejected: list[MemoryUpdate] = []
        conflicts: list[MemoryUpdate] = []

        expire_cutoff = time.time() - self.config.max_message_age_sec
        self._peer_clocks[message.sender_id] = message.sender_clock
        self._peer_last_seen[message.sender_id] = time.time()

        for update in message.updates:
            if update.timestamp < expire_cutoff:
                rejected.append(update)
                continue

            if update.content_hash in self._seen:
                rejected.append(update)
                continue

            existing = self._store.get(update.key)
            if existing is not None:
                if update.vector_clock.concurrent(existing.vector_clock):
                    resolved = self._resolve_conflict(existing, update)
                    self._store[update.key] = resolved
                    conflicts.append(resolved)
                    self._seen.add(resolved.content_hash)
                elif existing.vector_clock.happens_before(update.vector_clock):
                    self._store[update.key] = update
                    accepted.append(update)
                    self._seen.add(update.content_hash)
                else:
                    rejected.append(update)
            else:
                self._store[update.key] = update
                accepted.append(update)
                self._seen.add(update.content_hash)

        self._clock = self._clock.merge(message.sender_clock)
        self._merge_count += 1

        # Prune seen set
        if len(self._seen) > self.config.max_seen_messages:
            self._seen = set(list(self._seen)[-self.config.max_seen_messages // 2 :])

        return MergeResult(
            accepted=tuple(accepted),
            rejected=tuple(rejected),
            conflicts=tuple(conflicts),
            new_clock=self._clock,
            merge_count=self._merge_count,
        )

    def should_sync(self) -> bool:
        """Check if enough time has elapsed for a new gossip round."""
        if not self._peer_last_seen:
            return True
        now = time.time()
        return any(
            now - ts > self.config.sync_interval_sec
            for ts in self._peer_last_seen.values()
        )

    # ── cluster membership ────────────────────────────────────────────

    def add_peer(self, peer_id: str) -> None:
        if peer_id not in self._peer_clocks:
            self._peer_clocks[peer_id] = VectorClock.create(peer_id)
            self._peer_last_seen[peer_id] = time.time()

    def remove_peer(self, peer_id: str) -> None:
        self._peer_clocks.pop(peer_id, None)
        self._peer_last_seen.pop(peer_id, None)

    def convergence_ratio(self) -> float:
        """Fraction of known peers whose clocks are within 1 tick of ours."""
        if not self._peer_clocks:
            return 1.0
        converged = 0
        for peer_clock in self._peer_clocks.values():
            diff = 0
            our_d = dict(self._clock.counters)
            peer_d = dict(peer_clock.counters)
            all_nodes = set(our_d) | set(peer_d)
            for n in all_nodes:
                diff += abs(our_d.get(n, 0) - peer_d.get(n, 0))
            if diff <= 1:
                converged += 1
        return converged / len(self._peer_clocks)

    def is_converged(self) -> bool:
        return self.convergence_ratio() >= self.config.convergence_threshold

    # ── internal ──────────────────────────────────────────────────────

    @staticmethod
    def _resolve_conflict(
        local: MemoryUpdate, remote: MemoryUpdate
    ) -> MemoryUpdate:
        """LWW conflict resolution: pick the update with the higher timestamp.

        Ties are broken by comparing node_id lexicographically.
        """
        if remote.timestamp > local.timestamp:
            return remote
        if remote.timestamp < local.timestamp:
            return local
        if remote.node_id > local.node_id:
            return remote
        return local


__all__ = [
    "ConsensusConfig",
    "GossipMessage",
    "GossipNode",
    "MemoryUpdate",
    "MergeResult",
    "UpdateOp",
    "VectorClock",
]
