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
    VectorClock,
)

__all__ = [
    "ConsensusConfig",
    "GossipMessage",
    "GossipNode",
    "MemoryUpdate",
    "MergeResult",
    "VectorClock",
]
