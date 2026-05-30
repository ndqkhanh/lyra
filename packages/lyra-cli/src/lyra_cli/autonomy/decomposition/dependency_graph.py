"""Dependency Graph — manages dependencies between sub-goals in decomposition.

Part of the intelligent goal decomposer (Step 5.1).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum


class NodeStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    label: str
    status: NodeStatus = NodeStatus.PENDING
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class GraphEdge:
    from_node: str
    to_node: str
    label: str = ""


@dataclass(frozen=True)
class DependencyGraph:
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    @property
    def ready_nodes(self) -> tuple[GraphNode, ...]:
        return tuple(n for n in self.nodes if n.status == NodeStatus.READY)


class DependencyGraphBuilder:
    """Builds and manages dependency graphs for goal decomposition.

    Tracks sub-goal dependencies, computes execution order via topological
    sort, and identifies ready/blocked nodes for scheduling.

    Usage::

        builder = DependencyGraphBuilder()
        builder.add_node("g1", "Design API")
        builder.add_node("g2", "Implement API")
        builder.add_edge("g1", "g2", "blocks")
        builder.mark_completed("g1")
        ready = builder.get_ready_nodes()  # ["g2"]
    """

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._dependents: dict[str, set[str]] = defaultdict(set)  # node → nodes that depend on it
        self._dependencies: dict[str, set[str]] = defaultdict(set)  # node → nodes it depends on

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    def add_node(self, node_id: str, label: str = "", metadata: dict[str, str] | None = None) -> GraphNode:
        if node_id in self._nodes:
            raise ValueError(f"Node '{node_id}' already exists")
        node = GraphNode(node_id=node_id, label=label or node_id, metadata=metadata or {})
        self._nodes[node_id] = node
        self._update_status(node_id)
        return node

    def add_edge(self, from_node: str, to_node: str, label: str = "") -> GraphEdge:
        if from_node not in self._nodes:
            raise ValueError(f"Source node '{from_node}' not found")
        if to_node not in self._nodes:
            raise ValueError(f"Target node '{to_node}' not found")
        edge = GraphEdge(from_node=from_node, to_node=to_node, label=label)
        self._edges.append(edge)
        self._dependents[from_node].add(to_node)
        self._dependencies[to_node].add(from_node)
        self._update_status(to_node)
        return edge

    def mark_completed(self, node_id: str) -> GraphNode:
        node = self._get_node(node_id)
        new_node = GraphNode(
            node_id=node.node_id,
            label=node.label,
            status=NodeStatus.COMPLETED,
            metadata=node.metadata,
        )
        self._nodes[node_id] = new_node
        # Unblock dependents
        for dep_id in self._dependents.get(node_id, set()):
            self._update_status(dep_id)
        return new_node

    def mark_failed(self, node_id: str) -> GraphNode:
        node = self._get_node(node_id)
        new_node = GraphNode(
            node_id=node.node_id,
            label=node.label,
            status=NodeStatus.FAILED,
            metadata=node.metadata,
        )
        self._nodes[node_id] = new_node
        # Block dependents
        for dep_id in self._dependents.get(node_id, set()):
            dep = self._nodes[dep_id]
            if dep.status != NodeStatus.COMPLETED:
                self._nodes[dep_id] = GraphNode(
                    node_id=dep.node_id,
                    label=dep.label,
                    status=NodeStatus.BLOCKED,
                    metadata=dep.metadata,
                )
        return new_node

    def get_ready_nodes(self) -> list[str]:
        return [
            nid for nid, node in self._nodes.items()
            if node.status == NodeStatus.READY
        ]

    def get_blocked_nodes(self) -> list[str]:
        return [
            nid for nid, node in self._nodes.items()
            if node.status == NodeStatus.BLOCKED
        ]

    def get_execution_order(self) -> list[str]:
        """Topological sort — returns nodes in valid execution order."""
        in_degree: dict[str, int] = {nid: 0 for nid in self._nodes}
        for edge in self._edges:
            in_degree[edge.to_node] = in_degree.get(edge.to_node, 0) + 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result: list[str] = []

        while queue:
            node_id = queue.pop(0)
            result.append(node_id)
            for dep_id in self._dependents.get(node_id, set()):
                in_degree[dep_id] -= 1
                if in_degree[dep_id] == 0:
                    queue.append(dep_id)

        return result if len(result) == len(self._nodes) else list(self._nodes.keys())

    def get_dependencies(self, node_id: str) -> list[str]:
        return sorted(self._dependencies.get(node_id, set()))

    def get_dependents(self, node_id: str) -> list[str]:
        return sorted(self._dependents.get(node_id, set()))

    def build(self) -> DependencyGraph:
        return DependencyGraph(
            nodes=tuple(self._nodes.values()),
            edges=tuple(self._edges),
        )

    def _get_node(self, node_id: str) -> GraphNode:
        node = self._nodes.get(node_id)
        if node is None:
            raise ValueError(f"Node '{node_id}' not found")
        return node

    def _update_status(self, node_id: str) -> None:
        node = self._nodes.get(node_id)
        if node is None or node.status in (NodeStatus.COMPLETED, NodeStatus.FAILED):
            return

        deps = self._dependencies.get(node_id, set())
        all_deps_done = all(
            self._nodes[d].status == NodeStatus.COMPLETED
            for d in deps
        )
        any_dep_failed = any(
            self._nodes[d].status == NodeStatus.FAILED
            for d in deps
        )

        if any_dep_failed:
            new_status = NodeStatus.BLOCKED
        elif not deps or all_deps_done:
            new_status = NodeStatus.READY
        else:
            new_status = NodeStatus.BLOCKED

        if node.status != new_status:
            self._nodes[node_id] = GraphNode(
                node_id=node.node_id,
                label=node.label,
                status=new_status,
                metadata=node.metadata,
            )
