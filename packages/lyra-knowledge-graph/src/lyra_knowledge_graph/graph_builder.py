"""Dynamic knowledge graph construction during research.

Provides the core KnowledgeGraph class with typed nodes and edges,
graph mutation, querying, serialization, and merging.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .exceptions import NodeNotFoundError, EdgeNotFoundError


class NodeType(Enum):
    """Types of nodes in the knowledge graph."""
    CONCEPT = "concept"
    SOURCE = "source"
    INSIGHT = "insight"
    CLAIM = "claim"
    ENTITY = "entity"
    QUESTION = "question"


class EdgeRelation(Enum):
    """Types of relations (edge labels) in the knowledge graph."""
    SUPPORTS = "supports"
    REFUTES = "refutes"
    CITES = "cites"
    DEPENDS_ON = "depends_on"
    RELATES_TO = "relates_to"
    EXTENDS = "extends"


@dataclass(frozen=True)
class KnowledgeNode:
    """An immutable node in the knowledge graph."""
    node_id: str
    node_type: NodeType
    label: str
    properties: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    community_id: str | None = None
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "label": self.label,
            "properties": dict(self.properties),
            "metadata": dict(self.metadata),
            "community_id": self.community_id,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KnowledgeNode:
        return cls(
            node_id=data["node_id"],
            node_type=NodeType(data["node_type"]),
            label=data["label"],
            properties=data.get("properties", {}),
            metadata=data.get("metadata", {}),
            community_id=data.get("community_id"),
            confidence=data.get("confidence", 1.0),
        )


@dataclass(frozen=True)
class KnowledgeEdge:
    """An immutable directed edge in the knowledge graph."""
    edge_id: str
    source_id: str
    target_id: str
    relation: EdgeRelation
    weight: float = 1.0
    label: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation.value,
            "weight": self.weight,
            "label": self.label,
            "properties": dict(self.properties),
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KnowledgeEdge:
        return cls(
            edge_id=data["edge_id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            relation=EdgeRelation(data["relation"]),
            weight=data.get("weight", 1.0),
            label=data.get("label"),
            properties=data.get("properties", {}),
            confidence=data.get("confidence", 1.0),
        )


class KnowledgeGraph:
    """A mutable knowledge graph with typed nodes and edges.

    Provides add_node, add_edge, query, merge, and JSON serialization.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, KnowledgeNode] = {}
        self._edges: list[KnowledgeEdge] = []
        self._incoming: dict[str, list[KnowledgeEdge]] = defaultdict(list)
        self._outgoing: dict[str, list[KnowledgeEdge]] = defaultdict(list)

    # ── Properties ──────────────────────────────────────────────────────────

    @property
    def nodes(self) -> dict[str, KnowledgeNode]:
        return dict(self._nodes)

    @property
    def edges(self) -> list[KnowledgeEdge]:
        return list(self._edges)

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    # ── Mutators ────────────────────────────────────────────────────────────

    def add_node(self, node: KnowledgeNode) -> KnowledgeGraph:
        """Add a node to the graph. Returns self for chaining."""
        new_nodes = dict(self._nodes)
        new_nodes[node.node_id] = node
        result = KnowledgeGraph.__new__(KnowledgeGraph)
        result._nodes = new_nodes
        result._edges = list(self._edges)
        result._incoming = defaultdict(list, {k: list(v) for k, v in self._incoming.items()})
        result._outgoing = defaultdict(list, {k: list(v) for k, v in self._outgoing.items()})
        return result

    def add_edge(self, edge: KnowledgeEdge) -> KnowledgeGraph:
        """Add an edge to the graph. Returns self for chaining."""
        if edge.source_id not in self._nodes:
            raise NodeNotFoundError(edge.source_id)
        if edge.target_id not in self._nodes:
            raise NodeNotFoundError(edge.target_id)
        new_edges = list(self._edges) + [edge]
        new_incoming = defaultdict(list, {k: list(v) for k, v in self._incoming.items()})
        new_outgoing = defaultdict(list, {k: list(v) for k, v in self._outgoing.items()})
        new_incoming[edge.target_id].append(edge)
        new_outgoing[edge.source_id].append(edge)
        result = KnowledgeGraph.__new__(KnowledgeGraph)
        result._nodes = dict(self._nodes)
        result._edges = new_edges
        result._incoming = new_incoming
        result._outgoing = new_outgoing
        return result

    def remove_node(self, node_id: str) -> KnowledgeGraph:
        """Remove a node and all its edges. Returns updated graph."""
        if node_id not in self._nodes:
            raise NodeNotFoundError(node_id)
        new_nodes = {k: v for k, v in self._nodes.items() if k != node_id}
        new_edges = [
            e for e in self._edges
            if e.source_id != node_id and e.target_id != node_id
        ]
        new_outgoing = defaultdict(list)
        new_incoming = defaultdict(list)
        for e in new_edges:
            new_outgoing[e.source_id].append(e)
            new_incoming[e.target_id].append(e)
        result = KnowledgeGraph.__new__(KnowledgeGraph)
        result._nodes = new_nodes
        result._edges = new_edges
        result._incoming = new_incoming
        result._outgoing = new_outgoing
        return result

    def remove_edge(self, edge_id: str) -> KnowledgeGraph:
        """Remove an edge by ID. Returns updated graph."""
        new_edges = [e for e in self._edges if e.edge_id != edge_id]
        if len(new_edges) == len(self._edges):
            raise EdgeNotFoundError(edge_id)
        new_outgoing = defaultdict(list)
        new_incoming = defaultdict(list)
        for e in new_edges:
            new_outgoing[e.source_id].append(e)
            new_incoming[e.target_id].append(e)
        result = KnowledgeGraph.__new__(KnowledgeGraph)
        result._nodes = dict(self._nodes)
        result._edges = new_edges
        result._incoming = new_incoming
        result._outgoing = new_outgoing
        return result

    def update_node(self, node_id: str, **kwargs: Any) -> KnowledgeGraph:
        """Return a new graph with the node's properties updated."""
        if node_id not in self._nodes:
            raise NodeNotFoundError(node_id)
        old = self._nodes[node_id]
        new_props = {**old.properties, **kwargs.get("properties", {})}
        new_meta = {**old.metadata, **kwargs.get("metadata", {})}
        updated = KnowledgeNode(
            node_id=old.node_id,
            node_type=kwargs.get("node_type", old.node_type),
            label=kwargs.get("label", old.label),
            properties=new_props,
            metadata=new_meta,
            community_id=kwargs.get("community_id", old.community_id),
            confidence=kwargs.get("confidence", old.confidence),
        )
        return self.add_node(updated)

    # ── Query ───────────────────────────────────────────────────────────────

    def get_node(self, node_id: str) -> KnowledgeNode:
        """Get a node by ID. Raises NodeNotFoundError if missing."""
        if node_id not in self._nodes:
            raise NodeNotFoundError(node_id)
        return self._nodes[node_id]

    def get_edge(self, edge_id: str) -> KnowledgeEdge:
        """Get an edge by ID. Raises EdgeNotFoundError if missing."""
        for e in self._edges:
            if e.edge_id == edge_id:
                return e
        raise EdgeNotFoundError(edge_id)

    def query(self, node_type: NodeType | None = None,
              label_contains: str | None = None,
              min_confidence: float = 0.0) -> list[KnowledgeNode]:
        """Query nodes by optional type, label substring, and confidence."""
        results: list[KnowledgeNode] = []
        for node in self._nodes.values():
            if node_type is not None and node.node_type != node_type:
                continue
            if label_contains is not None and label_contains.lower() not in node.label.lower():
                continue
            if node.confidence < min_confidence:
                continue
            results.append(node)
        return results

    def find_edges(self, source_id: str | None = None,
                   target_id: str | None = None,
                   relation: EdgeRelation | None = None) -> list[KnowledgeEdge]:
        """Find edges matching optional filters."""
        results: list[KnowledgeEdge] = []
        for e in self._edges:
            if source_id is not None and e.source_id != source_id:
                continue
            if target_id is not None and e.target_id != target_id:
                continue
            if relation is not None and e.relation != relation:
                continue
            results.append(e)
        return results

    # ── Merge ───────────────────────────────────────────────────────────────

    def merge_graphs(self, other: KnowledgeGraph) -> KnowledgeGraph:
        """Merge another graph into this one, combining nodes and edges."""
        result = self
        for node in other._nodes.values():
            if node.node_id not in result._nodes:
                result = result.add_node(node)
        for edge in other._edges:
            try:
                result = result.add_edge(edge)
            except (NodeNotFoundError, KeyError):
                continue
        return result

    # ── Serialization ───────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": {nid: n.to_dict() for nid, n in self._nodes.items()},
            "edges": [e.to_dict() for e in self._edges],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KnowledgeGraph:
        g = cls()
        for node_data in data.get("nodes", {}).values():
            g = g.add_node(KnowledgeNode.from_dict(node_data))
        for edge_data in data.get("edges", []):
            try:
                g = g.add_edge(KnowledgeEdge.from_dict(edge_data))
            except (NodeNotFoundError, KeyError):
                continue
        return g

    @classmethod
    def from_json(cls, json_str: str) -> KnowledgeGraph:
        return cls.from_dict(json.loads(json_str))

    # ── Derived Queries ─────────────────────────────────────────────────────

    def get_outgoing_edges(self, node_id: str) -> list[KnowledgeEdge]:
        """Get all outgoing edges from a node."""
        if node_id not in self._nodes:
            raise NodeNotFoundError(node_id)
        return list(self._outgoing.get(node_id, []))

    def get_incoming_edges(self, node_id: str) -> list[KnowledgeEdge]:
        """Get all incoming edges to a node."""
        if node_id not in self._nodes:
            raise NodeNotFoundError(node_id)
        return list(self._incoming.get(node_id, []))

    def get_neighbors(self, node_id: str) -> list[KnowledgeNode]:
        """Get all nodes directly connected to a given node."""
        if node_id not in self._nodes:
            raise NodeNotFoundError(node_id)
        neighbor_ids: set[str] = set()
        for e in self._outgoing.get(node_id, []):
            neighbor_ids.add(e.target_id)
        for e in self._incoming.get(node_id, []):
            neighbor_ids.add(e.source_id)
        return [self._nodes[nid] for nid in neighbor_ids if nid in self._nodes]

    def summary(self) -> dict[str, Any]:
        """Return a summary of the graph's contents."""
        type_counts: dict[str, int] = defaultdict(int)
        relation_counts: dict[str, int] = defaultdict(int)
        for n in self._nodes.values():
            type_counts[n.node_type.value] += 1
        for e in self._edges:
            relation_counts[e.relation.value] += 1
        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "nodes_by_type": dict(type_counts),
            "edges_by_relation": dict(relation_counts),
        }


class GraphBuilder:
    """Dynamic knowledge graph construction during research.

    Wraps KnowledgeGraph with a simplified async builder API for node/edge
    management, graph merging, and text-based graph construction.
    Nodes have: node_id, label, node_type, properties, confidence.
    Edges have: source_id, target_id, relation, confidence.
    """

    def __init__(self) -> None:
        self._graph = KnowledgeGraph()

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def nodes(self) -> dict[str, KnowledgeNode]:
        return dict(self._graph.nodes)

    @property
    def edges(self) -> list[KnowledgeEdge]:
        return list(self._graph.edges)

    @property
    def node_count(self) -> int:
        return self._graph.node_count

    @property
    def edge_count(self) -> int:
        return self._graph.edge_count

    # ── Mutators ──────────────────────────────────────────────────────────────

    async def add_node(
        self,
        node_id: str,
        label: str,
        node_type: NodeType = NodeType.CONCEPT,
        properties: dict[str, Any] | None = None,
        confidence: float = 1.0,
    ) -> GraphBuilder:
        """Add a node to the graph. Returns self for chaining."""
        node = KnowledgeNode(
            node_id=node_id,
            node_type=node_type,
            label=label,
            properties=properties or {},
            confidence=confidence,
        )
        self._graph = self._graph.add_node(node)
        return self

    async def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation: EdgeRelation = EdgeRelation.RELATES_TO,
        confidence: float = 1.0,
    ) -> GraphBuilder:
        """Add an edge to the graph. Returns self for chaining."""
        edge_id = f"{source_id}->{target_id}"
        edge = KnowledgeEdge(
            edge_id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            confidence=confidence,
        )
        self._graph = self._graph.add_edge(edge)
        return self

    # ── Query ─────────────────────────────────────────────────────────────────

    async def query_nodes(
        self,
        node_type: NodeType | None = None,
        label: str | None = None,
        min_confidence: float = 0.0,
    ) -> list[KnowledgeNode]:
        """Query nodes by optional type, label substring, and confidence."""
        return self._graph.query(
            node_type=node_type, label_contains=label, min_confidence=min_confidence
        )

    async def get_neighbors(self, node_id: str) -> list[KnowledgeNode]:
        """Get all nodes directly connected to a given node."""
        return self._graph.get_neighbors(node_id)

    # ── Merge ─────────────────────────────────────────────────────────────────

    async def merge_graphs(self, other: GraphBuilder) -> GraphBuilder:
        """Merge another GraphBuilder's graph into this one."""
        result = GraphBuilder()
        result._graph = self._graph.merge_graphs(other._graph)
        return result

    # ── Text-Based Construction ────────────────────────────────────────────────

    async def build_from_text(self, text: str) -> GraphBuilder:
        """Extract entities and relations from text and add them as nodes/edges.

        Uses regex-based extraction for file paths, function names, class names,
        URLs, and common noun phrases.
        """
        if not text.strip():
            return self

        ent_id = 0

        for match in re.finditer(
            r'\b[\w./\\]+\.(?:py|ts|js|rs|go|java|cpp|h)\b', text
        ):
            path = match.group(0)
            ent_id += 1
            node = KnowledgeNode(
                node_id=f"file:{ent_id}",
                node_type=NodeType.SOURCE,
                label=path.split("/")[-1],
                properties={"path": path},
            )
            self._graph = self._graph.add_node(node)

        for match in re.finditer(r'\b([a-zA-Z_]\w*)\s*\(', text):
            name = match.group(1)
            if name.lower() in {
                "if", "for", "while", "def", "class", "return", "import",
                "from", "with", "as", "in", "not", "and", "or", "is",
                "async", "await", "yield", "raise", "try", "except",
                "finally", "else", "elif", "pass", "break", "continue",
            }:
                continue
            ent_id += 1
            node = KnowledgeNode(
                node_id=f"func:{ent_id}",
                node_type=NodeType.CONCEPT,
                label=name,
                properties={"kind": "function"},
            )
            self._graph = self._graph.add_node(node)

        for match in re.finditer(
            r'\b[A-Z][a-zA-Z0-9]*(?:Error|Exception|Manager|Builder'
            r'|Factory|Service|Controller|Handler)\b',
            text,
        ):
            name = match.group(0)
            ent_id += 1
            ntype = NodeType.CONCEPT
            if "Error" in name or "Exception" in name:
                ntype = NodeType.CLAIM
            node = KnowledgeNode(
                node_id=f"class:{ent_id}",
                node_type=ntype,
                label=name,
                properties={"kind": "class"},
            )
            self._graph = self._graph.add_node(node)

        for match in re.finditer(r'https?://[^\s,)]+', text):
            url = match.group(0)
            ent_id += 1
            node = KnowledgeNode(
                node_id=f"url:{ent_id}",
                node_type=NodeType.SOURCE,
                label=url,
                properties={"url": url},
            )
            self._graph = self._graph.add_node(node)

        return self
