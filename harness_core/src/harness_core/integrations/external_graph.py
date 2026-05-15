"""External-graph adapters for the multi_hop substrate.

The :mod:`harness_core.multi_hop.types` Protocols are runtime-checkable, so
any object that quacks (has ``id`` + ``title``, ``all_nodes()``, etc.) is
already a valid :class:`Graph`. These adapters exist for cases where the
external graph's attribute names don't match — they wrap nodes/edges/the
graph with thin adapter classes that expose the right names.

Use cases:
    - Polaris's ``ProgramGraph`` — already conforms; no adapter needed,
      but the verify helper confirms.
    - Any other in-tree graph (lyra symbol graph, helix biomed KG) — wrap
      via :func:`adapt_graph` if attribute names differ.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional


# Default attribute mappings for the most common cases.
_DEFAULT_NODE_ID_ATTR = "id"
_DEFAULT_NODE_TITLE_ATTR = "title"
_DEFAULT_EDGE_SRC_ATTR = "src"
_DEFAULT_EDGE_DST_ATTR = "dst"


@dataclass(frozen=True)
class AdaptedNode:
    """Thin adapter exposing a foreign node as :class:`harness_core.multi_hop.Node`."""

    id: str
    title: str = ""

    @classmethod
    def wrap(
        cls,
        external: Any,
        *,
        id_attr: str = _DEFAULT_NODE_ID_ATTR,
        title_attr: str = _DEFAULT_NODE_TITLE_ATTR,
    ) -> "AdaptedNode":
        node_id = getattr(external, id_attr, None)
        if node_id is None:
            raise AttributeError(
                f"external node has no {id_attr!r} attribute; "
                f"override id_attr= to a different name"
            )
        title = getattr(external, title_attr, "") or ""
        return cls(id=str(node_id), title=str(title))


@dataclass(frozen=True)
class AdaptedEdge:
    """Thin adapter exposing a foreign edge as :class:`harness_core.multi_hop.Edge`."""

    src: str
    dst: str

    @classmethod
    def wrap(
        cls,
        external: Any,
        *,
        src_attr: str = _DEFAULT_EDGE_SRC_ATTR,
        dst_attr: str = _DEFAULT_EDGE_DST_ATTR,
    ) -> "AdaptedEdge":
        src = getattr(external, src_attr, None)
        dst = getattr(external, dst_attr, None)
        if src is None or dst is None:
            raise AttributeError(
                f"external edge missing {src_attr!r} or {dst_attr!r}; "
                f"override src_attr/dst_attr to different names"
            )
        return cls(src=str(src), dst=str(dst))


@dataclass(frozen=True)
class AdaptedDocument:
    """Adapter exposing a foreign doc as :class:`harness_core.multi_hop.Document`."""

    doc_id: str
    text: str
    anchor_node_id: Optional[str] = None

    @classmethod
    def wrap(
        cls,
        external: Any,
        *,
        id_attr: str = "doc_id",
        text_attr: str = "text",
        anchor_attr: Optional[str] = "anchor_node_id",
    ) -> "AdaptedDocument":
        doc_id = getattr(external, id_attr, None) or getattr(external, "id", None)
        if doc_id is None:
            raise AttributeError(
                f"external document has no {id_attr!r} or 'id' attribute"
            )
        text = getattr(external, text_attr, "") or ""
        anchor = getattr(external, anchor_attr, None) if anchor_attr else None
        return cls(
            doc_id=str(doc_id),
            text=str(text),
            anchor_node_id=str(anchor) if anchor else None,
        )


@dataclass
class AdaptedGraph:
    """Wrap an external graph that has ``all_nodes()`` + ``all_edges()`` but
    different node/edge attribute names.

    For polaris's ``ProgramGraph``, no adapter is needed — it already conforms.
    For graphs whose nodes use ``name`` instead of ``id``, etc., this wraps.

    >>> class FakeNode:
    ...     def __init__(self, name): self.name, self.label = name, name.upper()
    >>> class FakeGraph:
    ...     def __init__(self):
    ...         self.nodes = [FakeNode("a"), FakeNode("b")]
    ...     def all_nodes(self): return self.nodes
    ...     def all_edges(self): return []
    ...     def __contains__(self, x): return any(n.name == x for n in self.nodes)
    >>> adapted = adapt_graph(FakeGraph(), node_id_attr="name", node_title_attr="label")
    >>> sorted(n.id for n in adapted.all_nodes())
    ['a', 'b']
    >>> sorted(n.title for n in adapted.all_nodes())
    ['A', 'B']
    """

    external: Any
    node_id_attr: str = _DEFAULT_NODE_ID_ATTR
    node_title_attr: str = _DEFAULT_NODE_TITLE_ATTR
    edge_src_attr: str = _DEFAULT_EDGE_SRC_ATTR
    edge_dst_attr: str = _DEFAULT_EDGE_DST_ATTR

    def all_nodes(self) -> Iterable[AdaptedNode]:
        for ext_node in self.external.all_nodes():
            yield AdaptedNode.wrap(
                ext_node,
                id_attr=self.node_id_attr,
                title_attr=self.node_title_attr,
            )

    def all_edges(self) -> Iterable[AdaptedEdge]:
        for ext_edge in self.external.all_edges():
            try:
                yield AdaptedEdge.wrap(
                    ext_edge,
                    src_attr=self.edge_src_attr,
                    dst_attr=self.edge_dst_attr,
                )
            except AttributeError:
                # Skip malformed edges rather than raising — common for
                # heterogeneous graphs with multiple edge types.
                continue

    def __contains__(self, node_id: object) -> bool:
        # Fall through to external __contains__ if available; otherwise
        # check by iterating nodes.
        if hasattr(self.external, "__contains__"):
            try:
                return self.external.__contains__(node_id)
            except (TypeError, KeyError):
                pass
        if not isinstance(node_id, str):
            return False
        return any(n.id == node_id for n in self.all_nodes())


def adapt_graph(
    external: Any,
    *,
    node_id_attr: str = _DEFAULT_NODE_ID_ATTR,
    node_title_attr: str = _DEFAULT_NODE_TITLE_ATTR,
    edge_src_attr: str = _DEFAULT_EDGE_SRC_ATTR,
    edge_dst_attr: str = _DEFAULT_EDGE_DST_ATTR,
) -> AdaptedGraph:
    """Wrap any graph-shaped object as an :class:`AdaptedGraph`.

    Falls through to no-op when the external graph already satisfies our
    Protocol (callers should prefer using the external directly in that case).
    """
    return AdaptedGraph(
        external=external,
        node_id_attr=node_id_attr,
        node_title_attr=node_title_attr,
        edge_src_attr=edge_src_attr,
        edge_dst_attr=edge_dst_attr,
    )


def verify_graph_protocol(graph: Any) -> tuple[bool, list[str]]:
    """Check whether ``graph`` satisfies :class:`harness_core.multi_hop.Graph`.

    Returns ``(satisfied, missing_methods_or_attrs)``. Useful for confirming
    that an external graph (e.g., polaris ProgramGraph) doesn't need wrapping.
    """
    missing: list[str] = []
    if not callable(getattr(graph, "all_nodes", None)):
        missing.append("all_nodes()")
    if not callable(getattr(graph, "all_edges", None)):
        missing.append("all_edges()")
    if not callable(getattr(graph, "__contains__", None)):
        missing.append("__contains__")
    if missing:
        return False, missing

    # Sample one node and one edge to check shape.
    try:
        nodes_iter = iter(graph.all_nodes())
        first_node = next(nodes_iter, None)
    except Exception as exc:
        return False, [f"all_nodes() raised: {exc.__class__.__name__}"]
    if first_node is not None:
        if not hasattr(first_node, "id"):
            missing.append("Node.id")
        if not hasattr(first_node, "title"):
            missing.append("Node.title")

    try:
        edges_iter = iter(graph.all_edges())
        first_edge = next(edges_iter, None)
    except Exception as exc:
        return False, [f"all_edges() raised: {exc.__class__.__name__}"]
    if first_edge is not None:
        if not hasattr(first_edge, "src"):
            missing.append("Edge.src")
        if not hasattr(first_edge, "dst"):
            missing.append("Edge.dst")

    return (len(missing) == 0), missing


__all__ = [
    "AdaptedDocument",
    "AdaptedEdge",
    "AdaptedGraph",
    "AdaptedNode",
    "adapt_graph",
    "verify_graph_protocol",
]
