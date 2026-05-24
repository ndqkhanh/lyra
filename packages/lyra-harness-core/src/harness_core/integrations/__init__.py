"""harness_core.integrations — bridges to external graph + document substrates.

Per [docs/211-cross-project-power-up-plan-with-tradeoffs.md](../../../../../../research/harness-engineering/docs/211-cross-project-power-up-plan-with-tradeoffs.md)
§7 "Polaris back-port" — the harness_core multi_hop substrate is
Protocol-typed (Node/Edge/Graph/Document); any external graph-shaped object
that conforms to those Protocols can be used directly without forking.

When the external types don't quite match (different attribute names,
different method signatures), the adapters in this module wrap them so they
satisfy our Protocols. Polaris's ``ProgramGraph`` is the canonical case:
its ``GraphNode``/``GraphEdge`` already have ``id``/``title``/``src``/``dst``
attributes, so it should satisfy :class:`harness_core.multi_hop.Graph`
out-of-the-box. The adapters here exist for cases where it doesn't (e.g.,
Polaris evolves and breaks the duck-type match).
"""
from __future__ import annotations

from .external_graph import (
    AdaptedDocument,
    AdaptedEdge,
    AdaptedGraph,
    AdaptedNode,
    adapt_graph,
    verify_graph_protocol,
)

__all__ = [
    "AdaptedDocument",
    "AdaptedEdge",
    "AdaptedGraph",
    "AdaptedNode",
    "adapt_graph",
    "verify_graph_protocol",
]
