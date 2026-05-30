"""Gossip-based memory consensus protocol.

Peer-to-peer memory synchronization using vector clocks for causal
ordering and CRDT-style merge semantics for conflict resolution.
"""

from lyra_memory.gossip.consensus_protocol import (
    ConsensusConfig,
    GossipMessage,
    GossipNode,
    MemoryUpdate,
    MergeResult,
    UpdateOp,
    VectorClock,
)
from lyra_memory.gossip.fleet_merge import (
    FleetConfig,
    FleetCoordinator,
    FleetStats,
    MemoryFleet,
    SyncResult,
)
from lyra_memory.gossip.memory_vector_clock import (
    ClockDivergence,
    ClockHistory,
    ClockSnapshot,
    compact_clock,
    compute_causal_history,
    compute_divergence,
    detect_partition,
    is_causally_related,
    merge_multiple,
)

__all__ = [
    # consensus_protocol
    "ConsensusConfig",
    "GossipMessage",
    "GossipNode",
    "MemoryUpdate",
    "MergeResult",
    "UpdateOp",
    "VectorClock",
    # fleet_merge
    "FleetConfig",
    "FleetCoordinator",
    "FleetStats",
    "MemoryFleet",
    "SyncResult",
    # memory_vector_clock
    "ClockDivergence",
    "ClockHistory",
    "ClockSnapshot",
    "compact_clock",
    "compute_causal_history",
    "compute_divergence",
    "detect_partition",
    "is_causally_related",
    "merge_multiple",
]
