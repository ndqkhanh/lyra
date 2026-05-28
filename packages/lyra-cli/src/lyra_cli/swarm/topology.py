"""
Swarm Topology for defining agent connection patterns.

Implements:
- Connection patterns: mesh, star, ring, DAG
- Routing tables for message forwarding
- Neighbor discovery and management
- Topology validation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple


class TopologyType(Enum):
    """Supported swarm topology patterns."""

    MESH = auto()
    STAR = auto()
    RING = auto()
    DAG = auto()


@dataclass(frozen=True)
class TopologyNode:
    """A node in the swarm topology."""

    node_id: str
    node_type: str = "agent"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingEntry:
    """A routing table entry for message forwarding."""

    target_id: str
    next_hop: str
    hop_count: int = 1
    is_direct: bool = True
    cost: float = 1.0


@dataclass
class TopologyConfig:
    """Configuration for the swarm topology."""

    topology_type: TopologyType = TopologyType.MESH
    heartbeat_interval: float = 5.0
    max_hops: int = 10
    enable_route_optimization: bool = True
    dag_dependency_graph: Dict[str, List[str]] = field(default_factory=dict)


class SwarmTopology:
    """
    Manages agent connection patterns and routing within the swarm.

    Features:
    - Multiple topology patterns: mesh, star, ring, DAG
    - Routing table generation for message forwarding
    - Neighbor discovery and management
    - Topology validation and health checks
    """

    def __init__(self, config: Optional[TopologyConfig] = None) -> None:
        self.config = config or TopologyConfig()
        self.nodes: Dict[str, TopologyNode] = {}
        self._connections: Dict[str, Set[str]] = {}
        self._routing_table: Dict[str, List[RoutingEntry]] = {}
        self._center_node: Optional[str] = None

    def add_node(self, node: TopologyNode) -> None:
        """
        Add a node to the topology.

        Args:
            node: The node to add
        """
        self.nodes[node.node_id] = node
        if node.node_id not in self._connections:
            self._connections[node.node_id] = set()

        if self.config.topology_type == TopologyType.STAR and self._center_node is None:
            self._center_node = node.node_id

        self._rebuild_routing_table()

    def remove_node(self, node_id: str) -> None:
        """
        Remove a node from the topology.

        Args:
            node_id: The node to remove
        """
        self.nodes.pop(node_id, None)
        self._connections.pop(node_id, None)
        for conns in self._connections.values():
            conns.discard(node_id)

        if self._center_node == node_id:
            self._center_node = next(iter(self.nodes)) if self.nodes else None

        self._rebuild_routing_table()

    def connect(self, node_a: str, node_b: str) -> bool:
        """
        Connect two nodes in the topology.

        Args:
            node_a: First node ID
            node_b: Second node ID

        Returns:
            True if connected, False if nodes don't exist
        """
        if node_a not in self.nodes or node_b not in self.nodes:
            return False

        if self.config.topology_type == TopologyType.STAR:
            if node_a == self._center_node or node_b == self._center_node:
                self._connections[node_a].add(node_b)
                self._connections[node_b].add(node_a)
                self._rebuild_routing_table()
                return True
            return False

        self._connections[node_a].add(node_b)
        self._connections[node_b].add(node_a)
        self._rebuild_routing_table()
        return True

    def disconnect(self, node_a: str, node_b: str) -> bool:
        """Disconnect two nodes."""
        if node_a not in self._connections or node_b not in self._connections:
            return False
        self._connections[node_a].discard(node_b)
        self._connections[node_b].discard(node_a)
        self._rebuild_routing_table()
        return True

    def get_neighbors(self, node_id: str) -> List[str]:
        """
        Get all neighbors of a node.

        Args:
            node_id: The node to query

        Returns:
            List of neighbor node IDs
        """
        if self.config.topology_type == TopologyType.STAR:
            if node_id == self._center_node:
                return [n for n in self.nodes if n != self._center_node]
            return [self._center_node] if self._center_node else []

        dag_deps = self.config.dag_dependency_graph.get(node_id, [])
        conns = list(self._connections.get(node_id, set()))
        return list(set(conns + dag_deps))

    def get_routing_table(self, node_id: str) -> List[RoutingEntry]:
        """
        Get the routing table for a specific node.

        Args:
            node_id: The node to get the routing table for

        Returns:
            List of routing entries
        """
        if node_id in self._routing_table:
            return self._routing_table[node_id]
        return self._compute_routes(node_id)

    def discover_route(self, source: str, target: str) -> List[str]:
        """
        Find a path between two nodes using BFS.

        Args:
            source: Source node ID
            target: Target node ID

        Returns:
            List of node IDs forming the path, empty if unreachable
        """
        if source not in self.nodes or target not in self.nodes:
            return []
        if source == target:
            return [source]

        visited: Set[str] = set()
        queue: List[Tuple[str, List[str]]] = [(source, [source])]
        visited.add(source)

        while queue:
            current, path = queue.pop(0)
            for neighbor in self._connections.get(current, set()):
                if neighbor not in visited:
                    if neighbor == target:
                        return path + [neighbor]
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return []

    def validate_topology(self) -> List[str]:
        """
        Validate the topology for correctness.

        Returns:
            List of validation error messages, empty if valid
        """
        errors: List[str] = []

        if self.config.topology_type == TopologyType.STAR:
            if self._center_node is None and len(self.nodes) > 0:
                errors.append("Star topology requires a center node")
            elif self._center_node is not None and self._center_node not in self.nodes:
                errors.append("Center node not found in nodes")

        if self.config.topology_type == TopologyType.RING:
            if len(self.nodes) == 1:
                pass
            elif len(self.nodes) > 1:
                for nid in self.nodes:
                    if len(self._connections.get(nid, set())) != 2:
                        errors.append(f"Ring requires degree 2 for node {nid}")
                        break

        if self.config.topology_type == TopologyType.DAG:
            if self._detect_cycle():
                errors.append("DAG topology contains a cycle")

        return errors

    def build_initial_connections(self) -> None:
        """Build initial connections based on the configured topology type."""
        node_ids = list(self.nodes.keys())

        if self.config.topology_type == TopologyType.MESH:
            for i in range(len(node_ids)):
                for j in range(i + 1, len(node_ids)):
                    self._connections[node_ids[i]].add(node_ids[j])
                    self._connections[node_ids[j]].add(node_ids[i])

        elif self.config.topology_type == TopologyType.STAR:
            if node_ids:
                self._center_node = node_ids[0]
                for nid in node_ids[1:]:
                    self._connections[self._center_node].add(nid)
                    self._connections[nid].add(self._center_node)

        elif self.config.topology_type == TopologyType.RING:
            for i in range(len(node_ids)):
                next_i = (i + 1) % len(node_ids)
                self._connections[node_ids[i]].add(node_ids[next_i])
                self._connections[node_ids[next_i]].add(node_ids[i])

        elif self.config.topology_type == TopologyType.DAG:
            deps = self.config.dag_dependency_graph
            for node_id, dependencies in deps.items():
                if node_id in self._connections:
                    for dep in dependencies:
                        if dep in self._connections:
                            self._connections[dep].add(node_id)

        self._rebuild_routing_table()

    def _rebuild_routing_table(self) -> None:
        """Rebuild routing tables for all nodes."""
        self._routing_table.clear()
        for node_id in self.nodes:
            self._routing_table[node_id] = self._compute_routes(node_id)

    def _compute_routes(self, node_id: str) -> List[RoutingEntry]:
        """Compute routing entries for a node to all reachable targets."""
        routes: List[RoutingEntry] = []
        for target_id in self.nodes:
            if target_id == node_id:
                continue
            path = self.discover_route(node_id, target_id)
            if path:
                routes.append(
                    RoutingEntry(
                        target_id=target_id,
                        next_hop=path[1],
                        hop_count=len(path) - 1,
                        is_direct=len(path) == 2,
                    )
                )
        return routes

    def _detect_cycle(self) -> bool:
        """Detect if the DAG topology contains a cycle using DFS."""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in self._connections.get(node, set()):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.discard(node)
            return False

        for node_id in self.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        return False

    def get_topology_summary(self) -> Dict[str, Any]:
        """Get a summary of the current topology."""
        return {
            "type": self.config.topology_type.name,
            "node_count": len(self.nodes),
            "connection_count": sum(len(c) for c in self._connections.values()) // 2,
            "center_node": self._center_node,
            "nodes": list(self.nodes.keys()),
        }
