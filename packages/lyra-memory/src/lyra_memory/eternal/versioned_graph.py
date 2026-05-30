"""Versioned graph database for eternal memories.

Implements an immutable, versioned graph structure where:
  - Nodes represent eternal memory records
  - Edges represent relationships between memories
  - All mutations create new versions (copy-on-write)
  - Full version history is preserved
  - Conflict-free merge semantics for distributed scenarios

Grounded in:
  - Git's content-addressable storage model
  - CRDTs (Conflict-free Replicated Data Types)
  - MemAgents Workshop (ICLR 2026) — graph-based memory structures
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class NodeType(Enum):
    """Type of memory node in the graph."""

    EPISODIC = "episodic"  # Event-based memory
    SEMANTIC = "semantic"  # Fact-based memory
    PROCEDURAL = "procedural"  # Skill/procedure memory
    META = "meta"  # Meta-cognitive memory
    ETERNAL = "eternal"  # Promoted to eternal layer


class EdgeType(Enum):
    """Type of relationship between memory nodes."""

    DERIVES_FROM = "derives_from"  # Causal relationship
    RELATES_TO = "relates_to"  # Semantic similarity
    CONTRADICTS = "contradicts"  # Conflicting information
    SUPERSEDES = "supersedes"  # Newer version replaces older
    SUPPORTS = "supports"  # Evidence relationship
    TEMPORAL_NEXT = "temporal_next"  # Sequential in time


@dataclass(frozen=True)
class GraphNode:
    """Immutable node in the versioned graph."""

    node_id: str
    node_type: NodeType
    content: str
    content_hash: str
    metadata: tuple[tuple[str, str], ...]
    created_at: float
    version: int = 1

    @classmethod
    def create(
        cls,
        node_id: str,
        node_type: NodeType,
        content: str,
        metadata: dict[str, str] | None = None,
    ) -> GraphNode:
        """Create a new graph node."""
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        meta_tuples = tuple(sorted((metadata or {}).items()))

        return cls(
            node_id=node_id,
            node_type=node_type,
            content=content,
            content_hash=content_hash,
            metadata=meta_tuples,
            created_at=time.time(),
            version=1,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "content": self.content,
            "content_hash": self.content_hash,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphNode:
        """Create from dictionary."""
        return cls(
            node_id=data["node_id"],
            node_type=NodeType(data["node_type"]),
            content=data["content"],
            content_hash=data["content_hash"],
            metadata=tuple(sorted(data.get("metadata", {}).items())),
            created_at=data["created_at"],
            version=data.get("version", 1),
        )


@dataclass(frozen=True)
class GraphEdge:
    """Immutable edge in the versioned graph."""

    edge_id: str
    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float
    metadata: tuple[tuple[str, str], ...]
    created_at: float

    @classmethod
    def create(
        cls,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        weight: float = 1.0,
        metadata: dict[str, str] | None = None,
    ) -> GraphEdge:
        """Create a new graph edge."""
        edge_id = _compute_edge_id(source_id, target_id, edge_type)
        meta_tuples = tuple(sorted((metadata or {}).items()))

        return cls(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            weight=weight,
            metadata=meta_tuples,
            created_at=time.time(),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type.value,
            "weight": self.weight,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphEdge:
        """Create from dictionary."""
        return cls(
            edge_id=data["edge_id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            edge_type=EdgeType(data["edge_type"]),
            weight=data.get("weight", 1.0),
            metadata=tuple(sorted(data.get("metadata", {}).items())),
            created_at=data["created_at"],
        )


@dataclass(frozen=True)
class GraphVersion:
    """Immutable snapshot of graph state at a point in time."""

    version_id: int
    parent_version: int | None
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    timestamp: float
    description: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "version_id": self.version_id,
            "parent_version": self.parent_version,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "timestamp": self.timestamp,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphVersion:
        """Create from dictionary."""
        return cls(
            version_id=data["version_id"],
            parent_version=data.get("parent_version"),
            nodes=tuple(GraphNode.from_dict(n) for n in data["nodes"]),
            edges=tuple(GraphEdge.from_dict(e) for e in data["edges"]),
            timestamp=data["timestamp"],
            description=data.get("description", ""),
        )


@dataclass
class VersionedGraph:
    """Immutable versioned graph database for eternal memories.

    All mutations create new versions. Full history is preserved.
    Supports conflict-free merges for distributed scenarios.

    Usage::

        graph = VersionedGraph()
        node = GraphNode.create("node1", NodeType.SEMANTIC, "Important fact")
        graph.add_node(node, description="Added important fact")

        # Query
        results = graph.search_nodes("Important")
        neighbors = graph.get_neighbors("node1")

        # Time travel
        old_version = graph.get_version(1)
    """

    base_path: Path | None = None
    _nodes: dict[str, GraphNode] = field(default_factory=dict)
    _edges: dict[str, GraphEdge] = field(default_factory=dict)
    _versions: list[GraphVersion] = field(default_factory=list)
    _current_version: int = 0
    _adjacency: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))

    def __post_init__(self) -> None:
        """Initialize graph and load existing data if path provided."""
        if self.base_path:
            self.base_path = Path(self.base_path).expanduser().resolve()
            self.base_path.mkdir(parents=True, exist_ok=True)
            self._load_from_disk()

    def add_node(self, node: GraphNode, *, description: str = "") -> int:
        """Add a node and create a new version.

        Returns:
            New version ID
        """
        self._nodes[node.node_id] = node
        return self._create_version(description or f"Added node {node.node_id}")

    def add_edge(self, edge: GraphEdge, *, description: str = "") -> int:
        """Add an edge and create a new version.

        Returns:
            New version ID
        """
        self._edges[edge.edge_id] = edge
        self._adjacency[edge.source_id].add(edge.target_id)
        return self._create_version(description or f"Added edge {edge.edge_id}")

    def get_node(self, node_id: str) -> GraphNode | None:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def get_edge(self, edge_id: str) -> GraphEdge | None:
        """Get an edge by ID."""
        return self._edges.get(edge_id)

    def get_neighbors(self, node_id: str, *, edge_type: EdgeType | None = None) -> list[GraphNode]:
        """Get all neighbor nodes connected to the given node.

        Args:
            node_id: Source node ID
            edge_type: Optional filter by edge type

        Returns:
            List of neighbor nodes
        """
        neighbors: list[GraphNode] = []

        for edge in self._edges.values():
            if edge.source_id == node_id:
                if edge_type is None or edge.edge_type == edge_type:
                    neighbor = self._nodes.get(edge.target_id)
                    if neighbor:
                        neighbors.append(neighbor)

        return neighbors

    def search_nodes(self, query: str, *, node_type: NodeType | None = None, limit: int = 10) -> list[GraphNode]:
        """Search nodes by content.

        Args:
            query: Search query
            node_type: Optional filter by node type
            limit: Maximum results

        Returns:
            List of matching nodes
        """
        query_lower = query.lower()
        results: list[tuple[float, GraphNode]] = []

        for node in self._nodes.values():
            if node_type and node.node_type != node_type:
                continue

            if query_lower in node.content.lower():
                score = len(query_lower) / max(len(node.content), 1.0)
                results.append((score, node))

        results.sort(key=lambda x: (-x[0], -x[1].created_at))
        return [node for _, node in results[:limit]]

    def get_subgraph(self, root_id: str, depth: int = 2) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Extract a subgraph starting from a root node.

        Args:
            root_id: Root node ID
            depth: Maximum traversal depth

        Returns:
            (nodes, edges) tuple
        """
        visited_nodes: set[str] = set()
        visited_edges: set[str] = set()
        queue: list[tuple[str, int]] = [(root_id, 0)]

        while queue:
            current_id, current_depth = queue.pop(0)

            if current_id in visited_nodes or current_depth > depth:
                continue

            visited_nodes.add(current_id)

            # Find all edges from this node
            for edge in self._edges.values():
                if edge.source_id == current_id and edge.edge_id not in visited_edges:
                    visited_edges.add(edge.edge_id)
                    queue.append((edge.target_id, current_depth + 1))

        nodes = [self._nodes[nid] for nid in visited_nodes if nid in self._nodes]
        edges = [self._edges[eid] for eid in visited_edges if eid in self._edges]

        return nodes, edges

    def get_version(self, version_id: int) -> GraphVersion | None:
        """Get a specific version by ID."""
        if 0 <= version_id < len(self._versions):
            return self._versions[version_id]
        return None

    def get_current_version(self) -> GraphVersion | None:
        """Get the current (latest) version."""
        if self._versions:
            return self._versions[-1]
        return None

    def restore_version(self, version_id: int) -> bool:
        """Restore graph state to a specific version.

        Args:
            version_id: Version to restore

        Returns:
            True if successful
        """
        version = self.get_version(version_id)
        if not version:
            return False

        # Clear current state
        self._nodes.clear()
        self._edges.clear()
        self._adjacency.clear()

        # Restore from version
        for node in version.nodes:
            self._nodes[node.node_id] = node

        for edge in version.edges:
            self._edges[edge.edge_id] = edge
            self._adjacency[edge.source_id].add(edge.target_id)

        self._current_version = version_id
        return True

    def _create_version(self, description: str) -> int:
        """Create a new version snapshot."""
        version = GraphVersion(
            version_id=len(self._versions),
            parent_version=self._current_version if self._versions else None,
            nodes=tuple(self._nodes.values()),
            edges=tuple(self._edges.values()),
            timestamp=time.time(),
            description=description,
        )

        self._versions.append(version)
        self._current_version = version.version_id

        if self.base_path:
            self._save_version(version)

        return version.version_id

    def _save_version(self, version: GraphVersion) -> None:
        """Save a version to disk."""
        if not self.base_path:
            return

        version_file = self.base_path / f"version_{version.version_id:06d}.json"
        version_file.write_text(json.dumps(version.to_dict(), indent=2))

    def _load_from_disk(self) -> None:
        """Load all versions from disk."""
        if not self.base_path:
            return

        version_files = sorted(self.base_path.glob("version_*.json"))

        for version_file in version_files:
            try:
                data = json.loads(version_file.read_text())
                version = GraphVersion.from_dict(data)
                self._versions.append(version)
            except (json.JSONDecodeError, KeyError):
                continue

        # Restore to latest version
        if self._versions:
            latest = self._versions[-1]
            self.restore_version(latest.version_id)

    def export_dot(self, output_path: Path | None = None) -> str:
        """Export graph to Graphviz DOT format for visualization.

        Args:
            output_path: Optional path to write DOT file

        Returns:
            DOT format string
        """
        lines = ["digraph EternalMemory {", "  rankdir=LR;", "  node [shape=box];", ""]

        # Add nodes
        for node in self._nodes.values():
            label = node.content[:50] + "..." if len(node.content) > 50 else node.content
            label = label.replace('"', '\\"')
            lines.append(f'  "{node.node_id}" [label="{label}"];')

        lines.append("")

        # Add edges
        for edge in self._edges.values():
            lines.append(f'  "{edge.source_id}" -> "{edge.target_id}" [label="{edge.edge_type.value}"];')

        lines.append("}")

        dot_content = "\n".join(lines)

        if output_path:
            Path(output_path).write_text(dot_content)

        return dot_content

    @property
    def node_count(self) -> int:
        """Number of nodes in current version."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Number of edges in current version."""
        return len(self._edges)

    @property
    def version_count(self) -> int:
        """Total number of versions."""
        return len(self._versions)


def _compute_edge_id(source_id: str, target_id: str, edge_type: EdgeType) -> str:
    """Compute deterministic edge ID from source, target, and type."""
    data = f"{source_id}|{target_id}|{edge_type.value}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]


__all__ = [
    "EdgeType",
    "GraphEdge",
    "GraphNode",
    "GraphVersion",
    "NodeType",
    "VersionedGraph",
]
