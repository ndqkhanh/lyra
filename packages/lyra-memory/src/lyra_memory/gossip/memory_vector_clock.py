"""Extended vector clock operations for memory synchronization.

Provides advanced vector clock operations including:
  - Causal history tracking
  - Divergence detection
  - Clock compaction for long-running systems
  - Semantic versioning integration

Grounded in:
  - "Time, Clocks, and the Ordering of Events" (Lamport, 1978)
  - "Virtual Time and Global States" (Mattern, 1989)
  - Dynamo vector clocks (DeCandia et al., 2007)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from lyra_memory.gossip.consensus_protocol import VectorClock


@dataclass(frozen=True)
class ClockDivergence:
    """Measures divergence between two vector clocks."""

    manhattan_distance: int  # sum of absolute differences
    max_difference: int  # largest single difference
    divergent_nodes: tuple[str, ...]  # nodes with different counts
    ahead_nodes: tuple[str, ...]  # nodes where first clock is ahead
    behind_nodes: tuple[str, ...]  # nodes where first clock is behind


def compute_divergence(clock_a: VectorClock, clock_b: VectorClock) -> ClockDivergence:
    """Compute divergence metrics between two vector clocks.

    Args:
        clock_a: First vector clock
        clock_b: Second vector clock

    Returns:
        ClockDivergence with detailed metrics
    """
    a_dict = dict(clock_a.counters)
    b_dict = dict(clock_b.counters)
    all_nodes = set(a_dict) | set(b_dict)

    manhattan = 0
    max_diff = 0
    divergent: list[str] = []
    ahead: list[str] = []
    behind: list[str] = []

    for node in all_nodes:
        a_val = a_dict.get(node, 0)
        b_val = b_dict.get(node, 0)
        diff = abs(a_val - b_val)

        if diff > 0:
            divergent.append(node)
            manhattan += diff
            max_diff = max(max_diff, diff)

            if a_val > b_val:
                ahead.append(node)
            else:
                behind.append(node)

    return ClockDivergence(
        manhattan_distance=manhattan,
        max_difference=max_diff,
        divergent_nodes=tuple(sorted(divergent)),
        ahead_nodes=tuple(sorted(ahead)),
        behind_nodes=tuple(sorted(behind)),
    )


def is_causally_related(clock_a: VectorClock, clock_b: VectorClock) -> bool:
    """Check if two clocks are causally related (one happens-before the other).

    Returns:
        True if clock_a happens-before clock_b OR clock_b happens-before clock_a
    """
    return clock_a.happens_before(clock_b) or clock_b.happens_before(clock_a)


def compute_causal_history(clock: VectorClock) -> int:
    """Compute total causal history depth (sum of all counters).

    This represents the total number of events that causally precede
    the state represented by this clock.
    """
    return sum(count for _, count in clock.counters)


@dataclass(frozen=True)
class ClockSnapshot:
    """A timestamped snapshot of a vector clock for history tracking."""

    clock: VectorClock
    timestamp: float
    node_id: str
    metadata: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "clock": self.clock.to_dict(),
            "timestamp": self.timestamp,
            "node_id": self.node_id,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> ClockSnapshot:
        return ClockSnapshot(
            clock=VectorClock.from_dict(data["clock"]),
            timestamp=data["timestamp"],
            node_id=data["node_id"],
            metadata=tuple(sorted(data.get("metadata", {}).items())),
        )


class ClockHistory:
    """Tracks vector clock evolution over time for a node.

    Maintains a bounded history of clock snapshots to enable:
      - Rollback to previous states
      - Divergence analysis over time
      - Audit trail for debugging
    """

    def __init__(self, node_id: str, max_snapshots: int = 100) -> None:
        self.node_id = node_id
        self.max_snapshots = max_snapshots
        self._snapshots: list[ClockSnapshot] = []

    def record(
        self, clock: VectorClock, timestamp: float, metadata: dict[str, str] | None = None
    ) -> None:
        """Record a clock snapshot."""
        snapshot = ClockSnapshot(
            clock=clock,
            timestamp=timestamp,
            node_id=self.node_id,
            metadata=tuple(sorted((metadata or {}).items())),
        )
        self._snapshots.append(snapshot)

        # Prune old snapshots
        if len(self._snapshots) > self.max_snapshots:
            self._snapshots = self._snapshots[-self.max_snapshots :]

    def get_latest(self) -> ClockSnapshot | None:
        """Get the most recent snapshot."""
        return self._snapshots[-1] if self._snapshots else None

    def get_at_time(self, timestamp: float) -> ClockSnapshot | None:
        """Get the snapshot closest to (but not after) the given timestamp."""
        candidates = [s for s in self._snapshots if s.timestamp <= timestamp]
        return candidates[-1] if candidates else None

    def get_all(self) -> list[ClockSnapshot]:
        """Get all snapshots in chronological order."""
        return list(self._snapshots)

    def compute_growth_rate(self) -> float:
        """Compute average events per second over the history."""
        if len(self._snapshots) < 2:
            return 0.0

        first = self._snapshots[0]
        last = self._snapshots[-1]
        time_delta = last.timestamp - first.timestamp

        if time_delta <= 0:
            return 0.0

        first_depth = compute_causal_history(first.clock)
        last_depth = compute_causal_history(last.clock)
        event_delta = last_depth - first_depth

        return event_delta / time_delta

    def export_json(self) -> str:
        """Export history as JSON."""
        return json.dumps(
            {
                "node_id": self.node_id,
                "max_snapshots": self.max_snapshots,
                "snapshots": [s.to_dict() for s in self._snapshots],
            },
            indent=2,
        )

    @staticmethod
    def import_json(data: str) -> ClockHistory:
        """Import history from JSON."""
        d = json.loads(data)
        history = ClockHistory(
            node_id=d["node_id"],
            max_snapshots=d.get("max_snapshots", 100),
        )
        history._snapshots = [ClockSnapshot.from_dict(s) for s in d.get("snapshots", [])]
        return history


def compact_clock(clock: VectorClock, active_nodes: set[str]) -> VectorClock:
    """Compact a vector clock by removing entries for inactive nodes.

    Args:
        clock: Vector clock to compact
        active_nodes: Set of currently active node IDs

    Returns:
        Compacted vector clock with only active nodes
    """
    compacted = {node: count for node, count in clock.counters if node in active_nodes}
    return VectorClock(counters=tuple(sorted(compacted.items())))


def merge_multiple(clocks: list[VectorClock]) -> VectorClock:
    """Merge multiple vector clocks into a single clock.

    Takes the pointwise maximum across all clocks.

    Args:
        clocks: List of vector clocks to merge

    Returns:
        Merged vector clock
    """
    if not clocks:
        return VectorClock(counters=())

    if len(clocks) == 1:
        return clocks[0]

    result = clocks[0]
    for clock in clocks[1:]:
        result = result.merge(clock)

    return result


def detect_partition(
    node_clocks: dict[str, VectorClock], divergence_threshold: int = 10
) -> list[set[str]]:
    """Detect network partitions based on clock divergence.

    Nodes with high mutual divergence are likely in separate partitions.

    Args:
        node_clocks: Mapping of node_id to their current vector clock
        divergence_threshold: Maximum manhattan distance for same partition

    Returns:
        List of partition sets (each set contains node IDs in that partition)
    """
    if not node_clocks:
        return []

    nodes = list(node_clocks.keys())
    partitions: list[set[str]] = []

    # Build adjacency based on low divergence
    connected: dict[str, set[str]] = {node: {node} for node in nodes}

    for i, node_a in enumerate(nodes):
        for node_b in nodes[i + 1 :]:
            div = compute_divergence(node_clocks[node_a], node_clocks[node_b])
            if div.manhattan_distance <= divergence_threshold:
                connected[node_a].add(node_b)
                connected[node_b].add(node_a)

    # Find connected components
    visited: set[str] = set()
    for node in nodes:
        if node in visited:
            continue

        # BFS to find partition
        partition: set[str] = set()
        queue = [node]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            partition.add(current)
            for neighbor in connected[current]:
                if neighbor not in visited:
                    queue.append(neighbor)

        partitions.append(partition)

    return partitions


__all__ = [
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
