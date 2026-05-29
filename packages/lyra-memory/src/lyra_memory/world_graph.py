"""
WorldDB-style Graph-of-Worlds Memory Engine.

Implements a hierarchical graph memory inspired by WorldDB (96.4% on LongMemEval-S):

World Graph
├── World 1: "Project A"
│   ├── Entities: files, functions, classes, concepts
│   ├── Relations: depends_on, implements, calls, imports
│   └── Temporal snapshots (versioned states)
├── World 2: "Research Topic B"
│   └── ...
└── Cross-World Edges: analogy, pattern_reuse, dependency
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class WorldRelationType(str, Enum):
    """Types of relationships in the world graph."""

    DEPENDS_ON = "depends_on"
    IMPLEMENTS = "implements"
    CALLS = "calls"
    IMPORTS = "imports"
    CONTAINS = "contains"
    REFERENCES = "references"
    EXTENDS = "extends"
    ANALOGY = "analogy"
    PATTERN_REUSE = "pattern_reuse"
    DEPENDENCY = "dependency"
    PRECEDES = "precedes"


class WorldNodeType(str, Enum):
    """Types of nodes in a world graph."""

    FILE = "file"
    FUNCTION = "function"
    CLASS = "class"
    CONCEPT = "concept"
    MODULE = "module"
    VARIABLE = "variable"
    INTERFACE = "interface"
    ENTITY = "entity"
    ARTIFACT = "artifact"


@dataclass(frozen=True)
class WorldNode:
    """
    A node in the world graph representing an entity.

    Attributes:
        id: Unique identifier (UUID)
        label: Human-readable label
        node_type: Type of node (file, function, class, concept, etc.)
        properties: Arbitrary metadata key-value pairs
        embedding: Optional vector embedding for semantic search
        created_at: Timestamp when the node was created
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    label: str = ""
    node_type: WorldNodeType = WorldNodeType.ENTITY
    properties: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class WorldRelation:
    """
    A typed directed edge between two nodes in the world graph.

    Attributes:
        id: Unique identifier (UUID)
        source_id: Source node ID
        target_id: Target node ID
        relation_type: Type of relationship
        weight: Edge weight (0.0-1.0)
        metadata: Additional edge data
        created_at: Timestamp when the relation was created
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    source_id: str = ""
    target_id: str = ""
    relation_type: WorldRelationType = WorldRelationType.REFERENCES
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"Weight must be 0.0-1.0, got {self.weight}")


@dataclass(frozen=True)
class WorldSnapshot:
    """
    A temporal snapshot capturing the state of a world at a point in time.

    Attributes:
        timestamp: When the snapshot was taken
        world_id: The world this snapshot belongs to
        node_ids: IDs of nodes present at this time
        relation_ids: IDs of relations present at this time
        metadata: Additional snapshot metadata
    """

    timestamp: datetime = field(default_factory=datetime.now)
    world_id: str = ""
    node_ids: list[str] = field(default_factory=list)
    relation_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class World:
    """
    A named subgraph representing a domain of knowledge.

    Attributes:
        id: Unique identifier (UUID)
        name: Human-readable name
        description: What this world represents
        created_at: When the world was created
        metadata: Additional world metadata
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CrossWorldEdge:
    """
    An edge connecting nodes across different worlds.

    Attributes:
        id: Unique identifier (UUID)
        source_world_id: Source world ID
        source_node_id: Source node ID
        target_world_id: Target world ID
        target_node_id: Target node ID
        relation_type: Type of cross-world relationship
        weight: Edge weight (0.0-1.0)
        metadata: Additional edge data
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    source_world_id: str = ""
    source_node_id: str = ""
    target_world_id: str = ""
    target_node_id: str = ""
    relation_type: WorldRelationType = WorldRelationType.ANALOGY
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"Weight must be 0.0-1.0, got {self.weight}")


class WorldGraph:
    """
    Top-level graph managing multiple worlds and cross-world edges.

    Maintains the registry of worlds, their internal node/relation graphs,
    and cross-world connections. Supports temporal snapshotting for versioned
    state history.
    """

    def __init__(self) -> None:
        self._worlds: dict[str, World] = {}
        self._nodes: dict[str, dict[str, WorldNode]] = defaultdict(dict)
        self._relations: dict[str, dict[str, WorldRelation]] = defaultdict(dict)
        self._cross_world_edges: dict[str, CrossWorldEdge] = {}
        self._snapshots: dict[str, list[WorldSnapshot]] = defaultdict(list)

    def add_world(self, world: World) -> str:
        """
        Register a new world in the graph.

        Args:
            world: The World to add

        Returns:
            The world ID
        """
        self._worlds[world.id] = world
        logger.info("Added world: %s (%s)", world.name, world.id)
        return world.id

    def get_world(self, world_id: str) -> World | None:
        """Get a world by ID."""
        return self._worlds.get(world_id)

    def list_worlds(self) -> list[World]:
        """List all registered worlds."""
        return list(self._worlds.values())

    def remove_world(self, world_id: str) -> bool:
        """
        Remove a world and all its contained nodes, relations, and snapshots.

        Args:
            world_id: The world to remove

        Returns:
            True if removed, False if not found
        """
        if world_id not in self._worlds:
            return False
        del self._worlds[world_id]
        self._nodes.pop(world_id, None)
        self._relations.pop(world_id, None)
        self._snapshots.pop(world_id, None)
        self._cross_world_edges = {
            kid: edge
            for kid, edge in self._cross_world_edges.items()
            if edge.source_world_id != world_id and edge.target_world_id != world_id
        }
        logger.info("Removed world: %s", world_id)
        return True

    def add_node(self, world_id: str, node: WorldNode) -> str:
        """
        Add a node to a specific world.

        Args:
            world_id: Target world ID
            node: The WorldNode to add

        Returns:
            The node ID

        Raises:
            ValueError: If world_id does not exist
        """
        if world_id not in self._worlds:
            raise ValueError(f"World {world_id} not found")
        self._nodes[world_id][node.id] = node
        logger.debug("Added node '%s' to world %s", node.label, world_id)
        return node.id

    def get_node(self, world_id: str, node_id: str) -> WorldNode | None:
        """Get a node from a world."""
        return self._nodes.get(world_id, {}).get(node_id)

    def list_nodes(self, world_id: str, node_type: WorldNodeType | None = None) -> list[WorldNode]:
        """
        List nodes in a world, optionally filtered by type.

        Args:
            world_id: Target world ID
            node_type: Optional type filter

        Returns:
            List of matching WorldNode objects
        """
        nodes = list(self._nodes.get(world_id, {}).values())
        if node_type is not None:
            nodes = [n for n in nodes if n.node_type == node_type]
        return nodes

    def remove_node(self, world_id: str, node_id: str) -> bool:
        """
        Remove a node and its associated relations from a world.

        Args:
            world_id: Target world ID
            node_id: Node to remove

        Returns:
            True if removed, False if not found
        """
        if node_id not in self._nodes.get(world_id, {}):
            return False
        del self._nodes[world_id][node_id]
        self._relations[world_id] = {
            rid: rel
            for rid, rel in self._relations.get(world_id, {}).items()
            if rel.source_id != node_id and rel.target_id != node_id
        }
        return True

    def add_relation(self, world_id: str, relation: WorldRelation) -> str:
        """
        Add a typed relation between nodes in a world.

        Args:
            world_id: Target world ID
            relation: The WorldRelation to add

        Returns:
            The relation ID

        Raises:
            ValueError: If world_id does not exist, or if either node does not exist
        """
        if world_id not in self._worlds:
            raise ValueError(f"World {world_id} not found")
        if relation.source_id not in self._nodes.get(world_id, {}):
            raise ValueError(f"Source node {relation.source_id} not found in world {world_id}")
        if relation.target_id not in self._nodes.get(world_id, {}):
            raise ValueError(f"Target node {relation.target_id} not found in world {world_id}")
        self._relations[world_id][relation.id] = relation
        logger.debug(
            "Added relation %s -> %s [%s] in world %s",
            relation.source_id,
            relation.target_id,
            relation.relation_type.value,
            world_id,
        )
        return relation.id

    def get_relation(self, world_id: str, relation_id: str) -> WorldRelation | None:
        """Get a relation by ID."""
        return self._relations.get(world_id, {}).get(relation_id)

    def list_relations(
        self,
        world_id: str,
        relation_type: WorldRelationType | None = None,
    ) -> list[WorldRelation]:
        """
        List relations in a world, optionally filtered by type.

        Args:
            world_id: Target world ID
            relation_type: Optional relation type filter

        Returns:
            List of matching WorldRelation objects
        """
        relations = list(self._relations.get(world_id, {}).values())
        if relation_type is not None:
            relations = [r for r in relations if r.relation_type == relation_type]
        return relations

    def remove_relation(self, world_id: str, relation_id: str) -> bool:
        """
        Remove a relation from a world.

        Args:
            world_id: Target world ID
            relation_id: Relation to remove

        Returns:
            True if removed, False if not found
        """
        if relation_id not in self._relations.get(world_id, {}):
            return False
        del self._relations[world_id][relation_id]
        return True

    def get_neighbors(
        self,
        world_id: str,
        node_id: str,
        direction: str = "both",
        relation_type: WorldRelationType | None = None,
    ) -> list[tuple[WorldNode, WorldRelation]]:
        """
        Get neighboring nodes and their connecting relations.

        Args:
            world_id: Target world ID
            node_id: Source node ID
            direction: "outbound", "inbound", or "both"
            relation_type: Optional relation type filter

        Returns:
            List of (neighbor_node, connecting_relation) tuples
        """
        neighbors: list[tuple[WorldNode, WorldRelation]] = []
        nodes = self._nodes.get(world_id, {})

        for rel in self._relations.get(world_id, {}).values():
            if relation_type is not None and rel.relation_type != relation_type:
                continue
            if direction in ("outbound", "both") and rel.source_id == node_id:
                target = nodes.get(rel.target_id)
                if target:
                    neighbors.append((target, rel))
            if direction in ("inbound", "both") and rel.target_id == node_id:
                source = nodes.get(rel.source_id)
                if source:
                    neighbors.append((source, rel))

        return neighbors

    def add_cross_world_edge(self, edge: CrossWorldEdge) -> str:
        """
        Add an edge connecting nodes across different worlds.

        Args:
            edge: The CrossWorldEdge to add

        Returns:
            The edge ID

        Raises:
            ValueError: If source or target worlds do not exist
        """
        if edge.source_world_id not in self._worlds:
            raise ValueError(f"Source world {edge.source_world_id} not found")
        if edge.target_world_id not in self._worlds:
            raise ValueError(f"Target world {edge.target_world_id} not found")
        self._cross_world_edges[edge.id] = edge
        logger.debug(
            "Added cross-world edge: %s:%s -> %s:%s [%s]",
            edge.source_world_id,
            edge.source_node_id,
            edge.target_world_id,
            edge.target_node_id,
            edge.relation_type.value,
        )
        return edge.id

    def list_cross_world_edges(
        self,
        relation_type: WorldRelationType | None = None,
    ) -> list[CrossWorldEdge]:
        """
        List cross-world edges, optionally filtered by type.

        Args:
            relation_type: Optional relation type filter

        Returns:
            List of matching CrossWorldEdge objects
        """
        edges = list(self._cross_world_edges.values())
        if relation_type is not None:
            edges = [e for e in edges if e.relation_type == relation_type]
        return edges

    def snapshot(self, world_id: str, metadata: dict[str, Any] | None = None) -> WorldSnapshot:
        """
        Create a temporal snapshot of a world's current state.

        Args:
            world_id: Target world ID
            metadata: Optional snapshot metadata

        Returns:
            The created WorldSnapshot

        Raises:
            ValueError: If world_id does not exist
        """
        if world_id not in self._worlds:
            raise ValueError(f"World {world_id} not found")
        snapshot = WorldSnapshot(
            world_id=world_id,
            node_ids=list(self._nodes.get(world_id, {}).keys()),
            relation_ids=list(self._relations.get(world_id, {}).keys()),
            metadata=metadata or {},
        )
        self._snapshots[world_id].append(snapshot)
        logger.info("Created snapshot for world %s at %s", world_id, snapshot.timestamp.isoformat())
        return snapshot

    def get_snapshots(self, world_id: str) -> list[WorldSnapshot]:
        """Get all snapshots for a world, ordered by timestamp."""
        return sorted(self._snapshots.get(world_id, []), key=lambda s: s.timestamp)

    def get_snapshot_at(self, world_id: str, timestamp: datetime) -> WorldSnapshot | None:
        """
        Get the latest snapshot at or before the given timestamp.

        Args:
            world_id: Target world ID
            timestamp: The timestamp to query

        Returns:
            The closest snapshot, or None if no snapshots exist
        """
        snapshots = self.get_snapshots(world_id)
        if not snapshots:
            return None
        for snapshot in reversed(snapshots):
            if snapshot.timestamp <= timestamp:
                return snapshot
        return None

    @property
    def stats(self) -> dict[str, int]:
        """Get aggregate statistics for the world graph."""
        total_nodes = sum(len(n) for n in self._nodes.values())
        total_relations = sum(len(r) for r in self._relations.values())
        return {
            "worlds": len(self._worlds),
            "nodes": total_nodes,
            "relations": total_relations,
            "cross_world_edges": len(self._cross_world_edges),
            "snapshots": sum(len(s) for s in self._snapshots.values()),
        }

    def export_graph(self) -> dict[str, Any]:
        """
        Export the entire world graph as a NetworkX-compatible dict.

        Returns:
            Dict with nodes, edges, and world metadata
        """
        all_nodes: list[dict[str, Any]] = []
        all_edges: list[dict[str, Any]] = []

        for world_id, nodes in self._nodes.items():
            for node in nodes.values():
                node_dict = {
                    "id": node.id,
                    "label": node.label,
                    "node_type": node.node_type.value,
                    "world_id": world_id,
                    "properties": node.properties,
                    "created_at": node.created_at.isoformat(),
                }
                if node.embedding:
                    node_dict["embedding"] = node.embedding
                all_nodes.append(node_dict)

        for world_id, relations in self._relations.items():
            for rel in relations.values():
                all_edges.append(
                    {
                        "id": rel.id,
                        "source_id": rel.source_id,
                        "target_id": rel.target_id,
                        "relation_type": rel.relation_type.value,
                        "weight": rel.weight,
                        "world_id": world_id,
                        "metadata": rel.metadata,
                    }
                )

        for edge in self._cross_world_edges.values():
            all_edges.append(
                {
                    "id": edge.id,
                    "source_id": edge.source_node_id,
                    "target_id": edge.target_node_id,
                    "relation_type": edge.relation_type.value,
                    "weight": edge.weight,
                    "source_world_id": edge.source_world_id,
                    "target_world_id": edge.target_world_id,
                    "cross_world": True,
                    "metadata": edge.metadata,
                }
            )

        return {
            "nodes": all_nodes,
            "edges": all_edges,
            "worlds": [
                {
                    "id": w.id,
                    "name": w.name,
                    "description": w.description,
                    "created_at": w.created_at.isoformat(),
                    "metadata": w.metadata,
                }
                for w in self._worlds.values()
            ],
        }


class WorldGraphMemory:
    """
    Main engine for the Graph-of-Worlds memory system.

    Provides high-level operations for managing worlds, entities,
    semantic search, temporal snapshots, and world merging.

    Inspired by WorldDB (96.4% on LongMemEval-S).
    """

    def __init__(self, embedder: Any | None = None) -> None:
        """
        Initialize the WorldGraphMemory engine.

        Args:
            embedder: Optional embedding model for semantic search.
                      Should provide an ``encode(text) -> list[float]`` interface.
        """
        self.graph = WorldGraph()
        self._embedder = embedder
        self._merge_conflicts: dict[str, list[str]] = defaultdict(list)

    def add_world(
        self, name: str, description: str = "", metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Create a new world in the graph.

        Args:
            name: Human-readable world name
            description: What this world represents
            metadata: Optional world metadata

        Returns:
            The new world ID
        """
        world = World(name=name, description=description, metadata=metadata or {})
        return self.graph.add_world(world)

    def add_entity(
        self,
        world_id: str,
        label: str,
        node_type: WorldNodeType = WorldNodeType.ENTITY,
        properties: dict[str, Any] | None = None,
        content: str | None = None,
    ) -> str:
        """
        Add an entity node to a world.

        Args:
            world_id: Target world ID
            label: Entity label
            node_type: Type of entity
            properties: Additional entity properties
            content: Optional text content for embedding generation

        Returns:
            The new node ID
        """
        embedding: list[float] | None = None
        if content and self._embedder:
            try:
                embedding = list(self._embedder.encode(content))
            except Exception:
                logger.warning("Failed to generate embedding for entity '%s'", label)

        node = WorldNode(
            label=label,
            node_type=node_type,
            properties=properties or {},
            embedding=embedding,
        )
        return self.graph.add_node(world_id, node)

    def add_relation(
        self,
        world_id: str,
        source_id: str,
        target_id: str,
        rel_type: WorldRelationType,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Add a typed relation between entities in a world.

        Args:
            world_id: Target world ID
            source_id: Source node ID
            target_id: Target node ID
            rel_type: Type of relationship
            weight: Edge weight (0.0-1.0)
            metadata: Optional edge metadata

        Returns:
            The new relation ID
        """
        relation = WorldRelation(
            source_id=source_id,
            target_id=target_id,
            relation_type=rel_type,
            weight=weight,
            metadata=metadata or {},
        )
        return self.graph.add_relation(world_id, relation)

    def query_world(
        self,
        world_id: str,
        query: str,
        top_k: int = 10,
        node_type: WorldNodeType | None = None,
    ) -> list[tuple[WorldNode, float]]:
        """
        Semantic search within a world using embedding similarity.

        Falls back to label substring matching if no embedder is configured.

        Args:
            world_id: Target world ID
            query: Search query string
            top_k: Maximum results
            node_type: Optional node type filter

        Returns:
            List of (node, score) tuples sorted by relevance
        """
        nodes = self.graph.list_nodes(world_id, node_type=node_type)
        if not nodes:
            return []

        if self._embedder:
            return self._semantic_search(nodes, query, top_k)
        else:
            return self._substring_search(nodes, query, top_k)

    def cross_world_search(
        self,
        query: str,
        top_k: int = 10,
        node_type: WorldNodeType | None = None,
    ) -> list[tuple[WorldNode, str, float]]:
        """
        Search across all worlds for entities matching the query.

        Args:
            query: Search query string
            top_k: Maximum results
            node_type: Optional node type filter

        Returns:
            List of (node, world_name, score) tuples sorted by relevance
        """
        all_nodes: list[tuple[WorldNode, str]] = []
        for world in self.graph.list_worlds():
            nodes = self.graph.list_nodes(world.id, node_type=node_type)
            for node in nodes:
                all_nodes.append((node, world.name))

        if not all_nodes:
            return []

        if self._embedder:
            nodes_only = [n for n, _ in all_nodes]
            ranked = self._semantic_search(nodes_only, query, top_k)
            node_to_world = {n.id: wname for n, wname in all_nodes}
            return [(node, node_to_world[node.id], score) for node, score in ranked]
        else:
            nodes_only = [n for n, _ in all_nodes]
            ranked = self._substring_search(nodes_only, query, top_k)
            node_to_world = {n.id: wname for n, wname in all_nodes}
            return [(node, node_to_world[node.id], score) for node, score in ranked]

    def get_temporal_snapshot(
        self,
        world_id: str,
        timestamp: datetime | None = None,
    ) -> WorldSnapshot | None:
        """
        Get the state of a world at a specific point in time.

        Args:
            world_id: Target world ID
            timestamp: When to query (default: now)

        Returns:
            The closest WorldSnapshot, or None
        """
        ts = timestamp or datetime.now()
        return self.graph.get_snapshot_at(world_id, ts)

    def create_snapshot(
        self, world_id: str, metadata: dict[str, Any] | None = None
    ) -> WorldSnapshot:
        """
        Create a new temporal snapshot of the current world state.

        Args:
            world_id: Target world ID
            metadata: Optional snapshot metadata

        Returns:
            The created WorldSnapshot
        """
        return self.graph.snapshot(world_id, metadata=metadata)

    def merge_worlds(
        self,
        world_a_id: str,
        world_b_id: str,
        new_name: str | None = None,
    ) -> str:
        """
        Merge two worlds into one, detecting and recording conflicts.

        Entities with identical labels in both worlds are flagged as conflicts.
        All unique entities and relations from both worlds are copied to the
        merged world. The original worlds are preserved.

        Args:
            world_a_id: First world to merge
            world_b_id: Second world to merge
            new_name: Optional name for the merged world

        Returns:
            The new merged world ID

        Raises:
            ValueError: If either world does not exist
        """
        world_a = self.graph.get_world(world_a_id)
        world_b = self.graph.get_world(world_b_id)
        if world_a is None:
            raise ValueError(f"World {world_a_id} not found")
        if world_b is None:
            raise ValueError(f"World {world_b_id} not found")

        merged_name = new_name or f"{world_a.name} + {world_b.name}"
        merged_world = World(
            name=merged_name,
            description=f"Merged from '{world_a.name}' and '{world_b.name}'",
        )
        merged_id = self.graph.add_world(merged_world)
        self._merge_conflicts.pop(merged_id, None)

        id_mapping: dict[str, str] = {}

        for world_id in (world_a_id, world_b_id):
            for node in self.graph.list_nodes(world_id):
                existing = [
                    n
                    for n in self.graph.list_nodes(merged_id)
                    if n.label == node.label and n.node_type == node.node_type
                ]
                if existing:
                    conflict_msg = (
                        f"Conflict: entity '{node.label}' [{node.node_type.value}] "
                        f"exists in both worlds. Keeping existing (id={existing[0].id})."
                    )
                    self._merge_conflicts[merged_id].append(conflict_msg)
                    logger.warning(conflict_msg)
                    id_mapping[node.id] = existing[0].id
                else:
                    new_node = WorldNode(
                        label=node.label,
                        node_type=node.node_type,
                        properties={**node.properties, "origin_world_id": world_id},
                        embedding=node.embedding,
                    )
                    self.graph.add_node(merged_id, new_node)
                    id_mapping[node.id] = new_node.id

        for world_id in (world_a_id, world_b_id):
            for rel in self.graph.list_relations(world_id):
                mapped_source = id_mapping.get(rel.source_id, rel.source_id)
                mapped_target = id_mapping.get(rel.target_id, rel.target_id)
                new_relation = WorldRelation(
                    source_id=mapped_source,
                    target_id=mapped_target,
                    relation_type=rel.relation_type,
                    weight=rel.weight,
                    metadata={**rel.metadata, "origin_world_id": world_id},
                )
                try:
                    self.graph.add_relation(merged_id, new_relation)
                except ValueError:
                    logger.debug(
                        "Skipping relation %s -> %s: mapped nodes not found",
                        rel.source_id,
                        rel.target_id,
                    )

        logger.info(
            "Merged worlds '%s' and '%s' into '%s' (id=%s)",
            world_a.name,
            world_b.name,
            merged_name,
            merged_id,
        )
        return merged_id

    def get_merge_conflicts(self, world_id: str) -> list[str]:
        """Get conflict messages from the last merge operation for a world."""
        return self._merge_conflicts.get(world_id, [])

    def export_graph(self) -> dict[str, Any]:
        """Export the entire graph as a NetworkX-compatible dict."""
        return self.graph.export_graph()

    @property
    def stats(self) -> dict[str, int]:
        """Get aggregate statistics."""
        return self.graph.stats

    @property
    def world_count(self) -> int:
        """Number of worlds in the graph."""
        return len(self.graph.list_worlds())

    def _semantic_search(
        self,
        nodes: list[WorldNode],
        query: str,
        top_k: int,
    ) -> list[tuple[WorldNode, float]]:
        """Rank nodes by embedding cosine similarity to query."""
        try:
            import numpy as np

            query_embedding = np.array(self._embedder.encode(query))
            query_norm = np.linalg.norm(query_embedding)
            if query_norm == 0:
                return [(node, 0.0) for node in nodes[:top_k]]

            scored: list[tuple[WorldNode, float]] = []
            for node in nodes:
                if node.embedding:
                    node_emb = np.array(node.embedding)
                    node_norm = np.linalg.norm(node_emb)
                    if node_norm > 0:
                        score = float(np.dot(query_embedding, node_emb) / (query_norm * node_norm))
                    else:
                        score = 0.0
                else:
                    score = 0.0
                scored.append((node, score))

            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:top_k]
        except Exception:
            logger.exception("Semantic search failed, falling back to substring match")
            return self._substring_search(nodes, query, top_k)

    @staticmethod
    def _substring_search(
        nodes: list[WorldNode],
        query: str,
        top_k: int,
    ) -> list[tuple[WorldNode, float]]:
        """Rank nodes by exact substring match in label."""
        query_lower = query.lower()
        scored: list[tuple[WorldNode, float]] = []
        for node in nodes:
            score = 1.0 if query_lower in node.label.lower() else 0.0
            scored.append((node, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


__all__ = [
    "WorldRelationType",
    "WorldNodeType",
    "WorldNode",
    "WorldRelation",
    "WorldSnapshot",
    "World",
    "CrossWorldEdge",
    "WorldGraph",
    "WorldGraphMemory",
]
