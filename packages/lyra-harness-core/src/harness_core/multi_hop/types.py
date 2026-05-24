"""Abstracted Node/Edge/Graph/Document protocols + simple dataclass impls.

The Polaris-side ``ppr_fusion.py`` was tightly coupled to ``ProgramGraph`` and
``Claim`` from ``polaris_core.memory``. To promote the algorithm to shared
``harness_core``, we abstract those into Protocols and provide zero-dependency
default implementations any project can use.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, Protocol, runtime_checkable


@runtime_checkable
class Node(Protocol):
    """A graph node — minimum surface needed by HippoRAG."""

    id: str
    title: str  # used by entity extractors for token-matching


@runtime_checkable
class Edge(Protocol):
    """A directed edge."""

    src: str
    dst: str


@runtime_checkable
class Graph(Protocol):
    """The graph substrate HippoRAG walks."""

    def all_nodes(self) -> Iterable[Node]: ...
    def all_edges(self) -> Iterable[Edge]: ...
    def __contains__(self, node_id: object) -> bool: ...


@runtime_checkable
class Document(Protocol):
    """A retrievable document (Polaris's ``Claim`` is one specialisation).

    Required: ``doc_id`` (str) + ``text`` (str). Optional: ``anchor_node_id``
    pre-resolved to a graph node (skip entity extraction for this doc when set).
    """

    doc_id: str
    text: str
    anchor_node_id: Optional[str]


# --- Simple dataclass implementations (zero-dep defaults) -----------------


@dataclass(frozen=True)
class SimpleNode:
    id: str
    title: str = ""


@dataclass(frozen=True)
class SimpleEdge:
    src: str
    dst: str


@dataclass
class SimpleGraph:
    """In-memory graph keyed by node id. Suitable for tests + small corpora."""

    nodes: dict[str, SimpleNode] = field(default_factory=dict)
    edges: list[SimpleEdge] = field(default_factory=list)

    def add_node(self, node: SimpleNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: SimpleEdge) -> None:
        # Don't reject orphan edges; downstream code is robust to them.
        self.edges.append(edge)

    def all_nodes(self) -> Iterable[SimpleNode]:
        return list(self.nodes.values())

    def all_edges(self) -> Iterable[SimpleEdge]:
        return list(self.edges)

    def __contains__(self, node_id: object) -> bool:
        return isinstance(node_id, str) and node_id in self.nodes

    @classmethod
    def from_pairs(cls, edges: Iterable[tuple[str, str]], *, titles: Optional[dict[str, str]] = None) -> "SimpleGraph":
        """Build a graph from ``(src, dst)`` edge pairs.

        Auto-creates nodes for any id seen on either end of an edge. Optional
        ``titles`` overrides the default title (= node id).
        """
        titles = titles or {}
        g = cls()
        seen: set[str] = set()
        for src, dst in edges:
            for nid in (src, dst):
                if nid not in seen:
                    g.add_node(SimpleNode(id=nid, title=titles.get(nid, nid)))
                    seen.add(nid)
            g.add_edge(SimpleEdge(src=src, dst=dst))
        return g


@dataclass
class SimpleDocument:
    doc_id: str
    text: str
    anchor_node_id: Optional[str] = None
