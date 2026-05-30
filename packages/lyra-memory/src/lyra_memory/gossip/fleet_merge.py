"""Fleet-wide memory convergence and synchronization.

Orchestrates gossip-based memory synchronization across a fleet of agents,
providing:
  - Async peer-to-peer gossip rounds
  - Fleet-wide convergence detection
  - Partition tolerance and healing
  - Performance monitoring (<5s for 100-memory sync)

Grounded in:
  - Epidemic algorithms (Demers et al., 1987)
  - Dynamo eventual consistency (DeCandia et al., 2007)
  - SWIM membership protocol (Das et al., 2002)
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from lyra_memory.gossip.consensus_protocol import (
    ConsensusConfig,
    GossipMessage,
    GossipNode,
    MemoryUpdate,
    VectorClock,
)
from lyra_memory.gossip.memory_vector_clock import (
    ClockHistory,
    compute_divergence,
    detect_partition,
    merge_multiple,
)


@dataclass
class FleetConfig:
    """Configuration for fleet-wide memory synchronization."""

    gossip_interval_sec: float = 0.5  # time between gossip rounds (reduced for faster sync)
    convergence_check_interval_sec: float = 1.0  # time between convergence checks
    max_gossip_rounds: int = 100  # max rounds before declaring failure
    convergence_threshold: float = 0.95  # fraction of nodes that must converge
    partition_detection_enabled: bool = True
    partition_heal_interval_sec: float = 10.0
    performance_target_sec: float = 5.0  # target time for 100-memory sync


@dataclass
class FleetStats:
    """Statistics for fleet synchronization performance."""

    total_nodes: int
    converged_nodes: int
    total_messages: int
    total_merges: int
    total_conflicts: int
    elapsed_time_sec: float
    gossip_rounds: int
    convergence_ratio: float
    partitions_detected: int
    avg_divergence: float

    def meets_performance_target(self, target_sec: float) -> bool:
        """Check if sync completed within performance target."""
        return self.elapsed_time_sec <= target_sec


@dataclass
class SyncResult:
    """Result of a fleet-wide synchronization operation."""

    success: bool
    stats: FleetStats
    final_clocks: dict[str, VectorClock]
    partitions: list[set[str]]
    error_message: str | None = None


class FleetCoordinator:
    """Coordinates gossip-based memory synchronization across a fleet of nodes.

    Manages:
      - Periodic gossip rounds between peers
      - Convergence detection and monitoring
      - Partition detection and healing
      - Performance tracking
    """

    def __init__(
        self,
        nodes: dict[str, GossipNode],
        config: FleetConfig | None = None,
    ) -> None:
        self.nodes = nodes
        self.config = config or FleetConfig()
        self._histories: dict[str, ClockHistory] = {
            node_id: ClockHistory(node_id) for node_id in nodes
        }
        self._total_messages = 0
        self._total_merges = 0
        self._total_conflicts = 0
        self._gossip_rounds = 0
        self._start_time: float | None = None

    # ── Fleet operations ──────────────────────────────────────────────

    async def sync_fleet(self, max_rounds: int | None = None) -> SyncResult:
        """Synchronize memory across the entire fleet.

        Runs gossip rounds until convergence or max_rounds is reached.

        Args:
            max_rounds: Maximum gossip rounds (uses config default if None)

        Returns:
            SyncResult with convergence status and statistics
        """
        self._start_time = time.time()
        self._gossip_rounds = 0
        max_rounds = max_rounds or self.config.max_gossip_rounds

        # Ensure all nodes know about each other
        self._bootstrap_peers()

        while self._gossip_rounds < max_rounds:
            await self._run_gossip_round()
            self._gossip_rounds += 1

            # Check convergence
            if self._check_convergence():
                elapsed = time.time() - self._start_time
                stats = self._compute_stats(elapsed)
                final_clocks = {node_id: node.clock for node_id, node in self.nodes.items()}
                partitions = self._detect_partitions()

                return SyncResult(
                    success=True,
                    stats=stats,
                    final_clocks=final_clocks,
                    partitions=partitions,
                )

            # Periodic convergence check delay
            if self._gossip_rounds % 3 == 0:
                await asyncio.sleep(self.config.convergence_check_interval_sec)

        # Max rounds reached without convergence
        elapsed = time.time() - self._start_time
        stats = self._compute_stats(elapsed)
        final_clocks = {node_id: node.clock for node_id, node in self.nodes.items()}
        partitions = self._detect_partitions()

        return SyncResult(
            success=False,
            stats=stats,
            final_clocks=final_clocks,
            partitions=partitions,
            error_message=f"Failed to converge after {max_rounds} rounds",
        )

    async def _run_gossip_round(self) -> None:
        """Execute one round of gossip across all nodes."""
        tasks = []
        for node_id, node in self.nodes.items():
            task = self._gossip_from_node(node_id, node)
            tasks.append(task)

        await asyncio.gather(*tasks)

        # Record clock snapshots
        now = time.time()
        for node_id, node in self.nodes.items():
            self._histories[node_id].record(
                node.clock,
                now,
                {"round": str(self._gossip_rounds)},
            )

    async def _gossip_from_node(self, node_id: str, node: GossipNode) -> None:
        """Execute gossip from a single node to its peers."""
        # Select random peers (fanout)
        import random

        peer_ids = [pid for pid in self.nodes if pid != node_id]
        if not peer_ids:
            return

        fanout = min(node.config.fanout, len(peer_ids))
        selected_peers = random.sample(peer_ids, fanout)

        # Prepare and send gossip message
        message = node.prepare_gossip(selected_peers)
        self._total_messages += 1

        # Simulate async message delivery
        for peer_id in selected_peers:
            peer = self.nodes[peer_id]
            result = peer.receive_gossip(message)

            self._total_merges += result.merge_count
            self._total_conflicts += len(result.conflicts)

        # Small delay to simulate network latency
        await asyncio.sleep(0.01)

    def _bootstrap_peers(self) -> None:
        """Ensure all nodes know about all other nodes."""
        all_node_ids = list(self.nodes.keys())
        for node_id, node in self.nodes.items():
            for peer_id in all_node_ids:
                if peer_id != node_id:
                    node.add_peer(peer_id)

    def _check_convergence(self) -> bool:
        """Check if the fleet has converged.

        Convergence requires individual nodes to report clock convergence
        (peer clocks within 1 tick). Once all clocks are within tolerance,
        eventual data consistency is guaranteed by the gossip protocol.
        """
        if not self.nodes:
            return True

        converged_count = sum(1 for node in self.nodes.values() if node.is_converged())
        ratio = converged_count / len(self.nodes)
        return ratio >= self.config.convergence_threshold

    def _detect_partitions(self) -> list[set[str]]:
        """Detect network partitions based on clock divergence."""
        if not self.config.partition_detection_enabled:
            return []

        node_clocks = {node_id: node.clock for node_id, node in self.nodes.items()}
        return detect_partition(node_clocks, divergence_threshold=10)

    def _compute_stats(self, elapsed_time: float) -> FleetStats:
        """Compute fleet synchronization statistics."""
        converged_count = sum(1 for node in self.nodes.values() if node.is_converged())
        convergence_ratio = converged_count / len(self.nodes) if self.nodes else 0.0

        # Compute average divergence
        node_clocks = list(node.clock for node in self.nodes.values())
        if len(node_clocks) >= 2:
            divergences = []
            for i, clock_a in enumerate(node_clocks):
                for clock_b in node_clocks[i + 1 :]:
                    div = compute_divergence(clock_a, clock_b)
                    divergences.append(div.manhattan_distance)
            avg_divergence = sum(divergences) / len(divergences) if divergences else 0.0
        else:
            avg_divergence = 0.0

        partitions = self._detect_partitions()

        return FleetStats(
            total_nodes=len(self.nodes),
            converged_nodes=converged_count,
            total_messages=self._total_messages,
            total_merges=self._total_merges,
            total_conflicts=self._total_conflicts,
            elapsed_time_sec=elapsed_time,
            gossip_rounds=self._gossip_rounds,
            convergence_ratio=convergence_ratio,
            partitions_detected=len(partitions),
            avg_divergence=avg_divergence,
        )

    # ── Fleet queries ─────────────────────────────────────────────────

    def get_fleet_state(self) -> dict[str, Any]:
        """Get current state of the entire fleet."""
        return {
            "total_nodes": len(self.nodes),
            "node_states": {
                node_id: {
                    "clock": node.clock.to_dict(),
                    "store_size": node.store_size,
                    "peer_count": node.peer_count,
                    "merge_count": node.merge_count,
                    "converged": node.is_converged(),
                }
                for node_id, node in self.nodes.items()
            },
            "gossip_rounds": self._gossip_rounds,
            "total_messages": self._total_messages,
        }

    def get_node_history(self, node_id: str) -> ClockHistory | None:
        """Get clock history for a specific node."""
        return self._histories.get(node_id)

    def export_histories(self) -> dict[str, str]:
        """Export all node histories as JSON."""
        return {node_id: history.export_json() for node_id, history in self._histories.items()}


class MemoryFleet:
    """High-level interface for fleet-wide memory operations.

    Provides simplified API for:
      - Adding/removing nodes
      - Writing memories to specific nodes
      - Fleet-wide synchronization
      - Querying fleet state
    """

    def __init__(self, config: FleetConfig | None = None) -> None:
        self.config = config or FleetConfig()
        self._nodes: dict[str, GossipNode] = {}
        self._coordinator: FleetCoordinator | None = None

    def add_node(self, node_id: str, consensus_config: ConsensusConfig | None = None) -> None:
        """Add a new node to the fleet."""
        if node_id in self._nodes:
            raise ValueError(f"Node {node_id} already exists")

        node = GossipNode(node_id, consensus_config)
        self._nodes[node_id] = node

        # Rebuild coordinator
        self._coordinator = FleetCoordinator(self._nodes, self.config)

    def remove_node(self, node_id: str) -> None:
        """Remove a node from the fleet."""
        if node_id not in self._nodes:
            raise ValueError(f"Node {node_id} not found")

        self._nodes.pop(node_id)

        # Rebuild coordinator
        self._coordinator = FleetCoordinator(self._nodes, self.config)

    def write_memory(self, node_id: str, key: str, value: str) -> MemoryUpdate:
        """Write a memory to a specific node."""
        if node_id not in self._nodes:
            raise ValueError(f"Node {node_id} not found")

        return self._nodes[node_id].put(key, value)

    def read_memory(self, node_id: str, key: str) -> MemoryUpdate | None:
        """Read a memory from a specific node."""
        if node_id not in self._nodes:
            raise ValueError(f"Node {node_id} not found")

        return self._nodes[node_id].get(key)

    async def sync(self, max_rounds: int | None = None) -> SyncResult:
        """Synchronize all nodes in the fleet."""
        if not self._coordinator:
            self._coordinator = FleetCoordinator(self._nodes, self.config)

        return await self._coordinator.sync_fleet(max_rounds)

    def get_node(self, node_id: str) -> GossipNode | None:
        """Get a specific node."""
        return self._nodes.get(node_id)

    def get_all_nodes(self) -> dict[str, GossipNode]:
        """Get all nodes in the fleet."""
        return dict(self._nodes)

    def get_fleet_state(self) -> dict[str, Any]:
        """Get current state of the fleet."""
        if not self._coordinator:
            return {"total_nodes": len(self._nodes), "node_states": {}}

        return self._coordinator.get_fleet_state()

    @property
    def node_count(self) -> int:
        """Get total number of nodes in the fleet."""
        return len(self._nodes)


__all__ = [
    "FleetConfig",
    "FleetCoordinator",
    "FleetStats",
    "MemoryFleet",
    "SyncResult",
]
