"""
Cue-Tag-Content associative graph for active memory reconstruction.

The graph has three node types:
  CUE     — A retrieval key or query fragment that triggers recall
  TAG     — A semantic label bridging cues to content
  CONTENT — The actual memory payload

Traversal flows: CUE → TAG → CONTENT → CUE → ... (iterative, bidirectional)

Source: MRAgent (YPoHy6lgKP), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4


class NodeType(str, Enum):
    CUE = "cue"
    TAG = "tag"
    CONTENT = "content"


@dataclass
class GraphNode:
    """A node in the Cue-Tag-Content associative graph."""

    id: str = field(default_factory=lambda: uuid4().hex)
    type: NodeType = NodeType.CONTENT
    content: str = ""
    metadata: dict = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass
class GraphEdge:
    """A directed edge in the associative graph."""

    source_id: str
    target_id: str
    weight: float = 1.0
    relation: str = ""


@dataclass
class CueTagContentGraph:
    """Associative memory graph with Cue → Tag → Content → Cue topology.

    Supports forward traversal (CUE → TAG → CONTENT), reverse traversal
    (CONTENT → CUE), and tag-based content lookup.

    The graph stores separate indices for each node type to enable
    efficient beam search during active reconstruction.
    """

    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: dict[str, list[GraphEdge]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._cue_nodes: dict[str, GraphNode] = {}
        self._tag_nodes: dict[str, GraphNode] = {}
        self._content_nodes: dict[str, GraphNode] = {}
        # Rebuild indices if nodes were passed during construction
        for node in self.nodes.values():
            self._index_node(node)

    def add_node(self, node: GraphNode) -> None:
        self.nodes[node.id] = node
        self._index_node(node)

    def add_edge(self, source_id: str, target_id: str,
                 weight: float = 1.0, relation: str = "") -> None:
        if source_id not in self.nodes or target_id not in self.nodes:
            return
        edge = GraphEdge(source_id=source_id, target_id=target_id,
                        weight=weight, relation=relation)
        self.edges.setdefault(source_id, []).append(edge)

    def get_tags(self, cue_node: GraphNode) -> list[GraphNode]:
        """Forward: CUE → TAG. Returns all tag nodes linked from this cue."""
        if cue_node.type != NodeType.CUE:
            return []
        return self._follow(cue_node.id, NodeType.TAG)

    def get_content(self, tag_node: GraphNode) -> list[GraphNode]:
        """Forward: TAG → CONTENT. Returns all content nodes for this tag."""
        if tag_node.type != NodeType.TAG:
            return []
        return self._follow(tag_node.id, NodeType.CONTENT)

    def get_related_cues(self, content_node: GraphNode) -> list[GraphNode]:
        """Reverse: CONTENT → CUE. Returns cues associated with this content.

        This enables the iterative reconstruction: after finding content,
        the engine follows reverse edges to discover new cues for further
        exploration.
        """
        if content_node.type != NodeType.CONTENT:
            return []
        return self._follow(content_node.id, NodeType.CUE)

    def get_cues(self) -> list[GraphNode]:
        return list(self._cue_nodes.values())

    def get_all_tags(self) -> list[GraphNode]:
        return list(self._tag_nodes.values())

    def get_all_content(self) -> list[GraphNode]:
        return list(self._content_nodes.values())

    def search_by_tag(self, tag_name: str) -> list[GraphNode]:
        """Find content nodes by fuzzy tag name match."""
        results = []
        tag_lower = tag_name.lower()
        for tag in self._tag_nodes.values():
            if tag_lower in tag.content.lower():
                results.extend(self._follow(tag.id, NodeType.CONTENT))
        return results

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return sum(len(e) for e in self.edges.values())

    @property
    def cue_count(self) -> int:
        return len(self._cue_nodes)

    @property
    def tag_count(self) -> int:
        return len(self._tag_nodes)

    @property
    def content_count(self) -> int:
        return len(self._content_nodes)

    def _follow(self, source_id: str, target_type: NodeType) -> list[GraphNode]:
        """Follow outgoing edges from source, returning targets matching type."""
        outgoing = self.edges.get(source_id, [])
        results = []
        for edge in outgoing:
            target = self.nodes.get(edge.target_id)
            if target and target.type == target_type:
                results.append(target)
        return results

    def _index_node(self, node: GraphNode) -> None:
        if node.type == NodeType.CUE:
            self._cue_nodes[node.id] = node
        elif node.type == NodeType.TAG:
            self._tag_nodes[node.id] = node
        elif node.type == NodeType.CONTENT:
            self._content_nodes[node.id] = node
