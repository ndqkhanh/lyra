"""Graph navigation engine — not retrieval, but structural graph traversal.

Provides neighbor queries, shortest path, subgraph expansion,
tail/head entity access, and BFS/DFS traversal strategies.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TraversalStrategy(Enum):
    """Traversal algorithm for graph exploration."""
    BFS = "bfs"
    DFS = "dfs"


@dataclass(frozen=True)
class TraversalPath:
    """Result of a graph traversal or path search."""
    node_ids: tuple[str, ...]
    total_weight: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def length(self) -> int:
        return len(self.node_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_ids": list(self.node_ids),
            "length": self.length,
            "total_weight": self.total_weight,
            "metadata": dict(self.metadata),
        }


class NavigationEngine:
    """Navigate and explore a knowledge graph. Works with KnowledgeGraph objects.

    Provides structural query methods: neighbors, shortest paths,
    subgraph extraction, and traversal with configurable strategies.
    """

    def __init__(self, graph: Any) -> None:
        self._graph = graph

    # ── Neighbors ──────────────────────────────────────────────────────────

    def get_neighbors(self, node_id: str,
                      relation_types: set[str] | None = None) -> list[Any]:
        """Get neighbor nodes, optionally filtered by relation types."""
        if node_id not in self._graph.nodes:
            from .exceptions import NodeNotFoundError
            raise NodeNotFoundError(node_id)

        edges = self._graph.get_outgoing_edges(node_id)
        if relation_types:
            edges = [e for e in edges if e.relation.value in relation_types]

        neighbor_ids: set[str] = set()
        for e in edges:
            if e.target_id != node_id:
                neighbor_ids.add(e.target_id)

        incoming = self._graph.get_incoming_edges(node_id)
        if relation_types:
            incoming = [e for e in incoming if e.relation.value in relation_types]
        for e in incoming:
            if e.source_id != node_id:
                neighbor_ids.add(e.source_id)

        return [
            self._graph.nodes[nid] for nid in neighbor_ids
            if nid in self._graph.nodes
        ]

    def get_tail_relations(self, entity_id: str) -> list[Any]:
        """Get all outgoing edges (tail relations) from an entity."""
        if entity_id not in self._graph.nodes:
            from .exceptions import NodeNotFoundError
            raise NodeNotFoundError(entity_id)
        return self._graph.get_outgoing_edges(entity_id)

    def get_head_entities(self, entity_id: str) -> list[Any]:
        """Get all incoming edges (head entities) pointing to an entity."""
        if entity_id not in self._graph.nodes:
            from .exceptions import NodeNotFoundError
            raise NodeNotFoundError(entity_id)
        return self._graph.get_incoming_edges(entity_id)

    # ── Path Finding ───────────────────────────────────────────────────────

    def get_path(self, source_id: str, target_id: str) -> TraversalPath | None:
        """Find the shortest path (by edge count) between two nodes using BFS."""
        if source_id not in self._graph.nodes:
            from .exceptions import NodeNotFoundError
            raise NodeNotFoundError(source_id)
        if target_id not in self._graph.nodes:
            from .exceptions import NodeNotFoundError
            raise NodeNotFoundError(target_id)
        if source_id == target_id:
            return TraversalPath(node_ids=(source_id,))

        visited: set[str] = {source_id}
        parent: dict[str, str | None] = {source_id: None}
        queue: deque[str] = deque([source_id])

        while queue:
            current = queue.popleft()
            if current == target_id:
                return self._reconstruct_path(parent, target_id)
            try:
                neighbors = self._graph.get_neighbors(current)
            except Exception:
                continue
            for neighbor in neighbors:
                if neighbor.node_id not in visited:
                    visited.add(neighbor.node_id)
                    parent[neighbor.node_id] = current
                    queue.append(neighbor.node_id)

        return None

    def get_all_paths(self, source_id: str, target_id: str,
                      max_depth: int = 5) -> list[TraversalPath]:
        """Find all paths between two nodes up to max_depth using DFS."""
        if source_id not in self._graph.nodes:
            from .exceptions import NodeNotFoundError
            raise NodeNotFoundError(source_id)
        if target_id not in self._graph.nodes:
            from .exceptions import NodeNotFoundError
            raise NodeNotFoundError(target_id)

        paths: list[TraversalPath] = []

        def dfs(current: str, target: str, visited: set[str],
                path: list[str], depth: int) -> None:
            if depth > max_depth:
                return
            if current == target:
                paths.append(TraversalPath(node_ids=tuple(path)))
                return
            try:
                neighbors = self._graph.get_neighbors(current)
            except Exception:
                return
            for nbr in neighbors:
                if nbr.node_id not in visited:
                    visited.add(nbr.node_id)
                    path.append(nbr.node_id)
                    dfs(nbr.node_id, target, visited, path, depth + 1)
                    path.pop()
                    visited.remove(nbr.node_id)

        dfs(source_id, target_id, {source_id}, [source_id], 0)
        return paths

    # ── Subgraph ───────────────────────────────────────────────────────────

    def get_subgraph(self, node_ids: list[str],
                     depth: int = 1) -> dict[str, Any]:
        """Expand around given nodes, returning the subgraph structure."""
        if not node_ids:
            return {"nodes": {}, "edges": []}

        included: set[str] = set(node_ids)
        frontier: set[str] = set(node_ids)

        for _ in range(depth):
            next_frontier: set[str] = set()
            for nid in frontier:
                try:
                    neighbors = self._graph.get_neighbors(nid)
                except Exception:
                    continue
                for nbr in neighbors:
                    if nbr.node_id not in included:
                        included.add(nbr.node_id)
                        next_frontier.add(nbr.node_id)
            frontier = next_frontier

        sub_nodes: dict[str, Any] = {}
        for nid in included:
            if nid in self._graph.nodes:
                sub_nodes[nid] = self._graph.nodes[nid]

        sub_edges: list[Any] = []
        for edge in self._graph.edges:
            if edge.source_id in included and edge.target_id in included:
                sub_edges.append(edge)

        return {
            "nodes": sub_nodes,
            "edges": sub_edges,
        }

    # ── Traversal ──────────────────────────────────────────────────────────

    def traverse(self, start_id: str,
                 strategy: TraversalStrategy = TraversalStrategy.BFS,
                 max_depth: int = 5) -> TraversalPath:
        """Traverse the graph from a starting node using BFS or DFS.

        Returns the sequence of visited node IDs.
        """
        if start_id not in self._graph.nodes:
            from .exceptions import NodeNotFoundError
            raise NodeNotFoundError(start_id)

        if strategy == TraversalStrategy.BFS:
            return self._bfs_traverse(start_id, max_depth)
        return self._dfs_traverse(start_id, max_depth)

    # ── Graph Summary ──────────────────────────────────────────────────────

    def get_degree_centrality(self, node_id: str) -> float:
        """Compute degree centrality for a node (0.0 to 1.0)."""
        if node_id not in self._graph.nodes:
            from .exceptions import NodeNotFoundError
            raise NodeNotFoundError(node_id)
        total = self._graph.node_count
        if total <= 1:
            return 0.0
        degree = len(self._graph.get_neighbors(node_id))
        return degree / (total - 1)

    def get_node_connectivity(self, node_id: str) -> dict[str, int]:
        """Return incoming, outgoing, and total edge counts for a node."""
        if node_id not in self._graph.nodes:
            from .exceptions import NodeNotFoundError
            raise NodeNotFoundError(node_id)
        outgoing = len(self._graph.get_outgoing_edges(node_id))
        incoming = len(self._graph.get_incoming_edges(node_id))
        return {
            "outgoing": outgoing,
            "incoming": incoming,
            "total": outgoing + incoming,
        }

    # ── Internal ───────────────────────────────────────────────────────────

    def _reconstruct_path(self, parent: dict[str, str | None],
                          target: str) -> TraversalPath:
        """Reconstruct path from BFS parent dict."""
        path: list[str] = []
        current: str | None = target
        while current is not None:
            path.append(current)
            current = parent.get(current)
        path.reverse()
        return TraversalPath(node_ids=tuple(path))

    def _bfs_traverse(self, start: str, max_depth: int) -> TraversalPath:
        """BFS traversal returning visited node order."""
        visited: list[str] = [start]
        queue: deque[tuple[str, int]] = deque([(start, 0)])

        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
            try:
                neighbors = self._graph.get_neighbors(current)
            except Exception:
                continue
            for nbr in neighbors:
                if nbr.node_id not in visited:
                    visited.append(nbr.node_id)
                    queue.append((nbr.node_id, depth + 1))

        return TraversalPath(node_ids=tuple(visited))

    def _dfs_traverse(self, start: str, max_depth: int) -> TraversalPath:
        """DFS traversal returning visited node order."""
        visited: list[str] = [start]
        stack: list[tuple[str, int]] = [(start, 0)]

        while stack:
            current, depth = stack.pop()
            if depth >= max_depth:
                continue
            try:
                neighbors = self._graph.get_neighbors(current)
            except Exception:
                continue
            for nbr in reversed(neighbors):
                if nbr.node_id not in visited:
                    visited.append(nbr.node_id)
                    stack.append((nbr.node_id, depth + 1))

        return TraversalPath(node_ids=tuple(visited))
