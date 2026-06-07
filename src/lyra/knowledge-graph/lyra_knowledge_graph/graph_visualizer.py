"""Graph visualizer — exports knowledge graphs to visualization formats.

Supports DOT (Graphviz), Mermaid, JSON tree, and ASCII art output
for rendering knowledge graphs in various contexts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum

from .graph_builder import EdgeRelation, KnowledgeGraph


class ExportFormat(StrEnum):
    DOT = "dot"
    MERMAID = "mermaid"
    JSON_TREE = "json_tree"
    ASCII = "ascii"


@dataclass(frozen=True)
class VisualStyle:
    node_colors: dict[str, str]
    edge_styles: dict[str, str]
    font_size: int
    direction: str


DEFAULT_STYLE = VisualStyle(
    node_colors={
        "concept": "#4A90D9",
        "source": "#7ED321",
        "insight": "#F5A623",
        "claim": "#D0021B",
        "entity": "#9B59B6",
        "question": "#50E3C2",
    },
    edge_styles={
        "supports": "solid",
        "refutes": "dashed",
        "cites": "dotted",
        "depends_on": "bold",
        "relates_to": "solid",
        "extends": "bold",
    },
    font_size=11,
    direction="LR",
)


class GraphVisualizer:
    """Exports KnowledgeGraph to various visualization formats.

    Produces DOT, Mermaid, JSON tree, and ASCII representations
    suitable for rendering in documentation, CLI, and web UIs.
    """

    def __init__(self, graph: KnowledgeGraph, style: VisualStyle | None = None) -> None:
        self._graph = graph
        self._style = style or DEFAULT_STYLE

    def export(self, fmt: ExportFormat) -> str:
        if fmt == ExportFormat.DOT:
            return self._to_dot()
        if fmt == ExportFormat.MERMAID:
            return self._to_mermaid()
        if fmt == ExportFormat.JSON_TREE:
            return self._to_json_tree()
        return self._to_ascii()

    def _to_dot(self) -> str:
        lines = ["digraph KnowledgeGraph {"]
        lines.append(f"  rankdir={self._style.direction};")
        lines.append(f"  fontsize={self._style.font_size};")
        lines.append("")

        for node in self._graph.nodes.values():
            color = self._style.node_colors.get(node.node_type.value, "#CCCCCC")
            label = node.label.replace('"', '\\"')
            lines.append(
                f'  "{node.node_id}" [label="{label}", '
                f'fillcolor="{color}", style=filled, '
                f'tooltip="{node.node_type.value}"];'
            )

        lines.append("")
        for edge in self._graph.edges:
            style = self._style.edge_styles.get(edge.relation.value, "solid")
            label = edge.label or edge.relation.value
            lines.append(
                f'  "{edge.source_id}" -> "{edge.target_id}" '
                f'[label="{label}", style={style}, weight={edge.weight}];'
            )

        lines.append("}")
        return "\n".join(lines)

    def _to_mermaid(self) -> str:
        lines = ["graph TD"]
        for node in self._graph.nodes.values():
            safe_label = node.label.replace('"', "#quot;").replace("(", "#40;").replace(")", "#41;")
            lines.append(f"  {node.node_id}[{safe_label}]")

        for edge in self._graph.edges:
            label = edge.label or edge.relation.value
            arrow = "-->"
            if edge.relation == EdgeRelation.REFUTES:
                arrow = "-.->"
            elif edge.relation == EdgeRelation.CITES:
                arrow = "-.->"
            lines.append(f"  {edge.source_id} {arrow}|{label}| {edge.target_id}")

        return "\n".join(lines)

    def _to_json_tree(self) -> str:
        roots = self._find_roots()
        tree = {
            "graph_summary": self._graph.summary(),
            "roots": [self._build_tree(nid) for nid in roots],
            "orphans": [
                {"id": n.node_id, "label": n.label, "type": n.node_type.value}
                for n in self._graph.nodes.values()
                if not self._graph.get_incoming_edges(n.node_id)
                and not self._graph.get_outgoing_edges(n.node_id)
            ],
        }
        return json.dumps(tree, indent=2)

    def _build_tree(self, node_id: str, depth: int = 0, max_depth: int = 4) -> dict:
        node = self._graph.nodes.get(node_id)
        if node is None:
            return {"id": node_id, "error": "not found"}

        children = []
        if depth < max_depth:
            for edge in self._graph.get_outgoing_edges(node_id):
                children.append(
                    {
                        "relation": edge.relation.value,
                        "weight": edge.weight,
                        "node": self._build_tree(edge.target_id, depth + 1, max_depth),
                    }
                )

        return {
            "id": node.node_id,
            "label": node.label,
            "type": node.node_type.value,
            "confidence": node.confidence,
            "children": children,
        }

    def _to_ascii(self) -> str:
        lines = [
            f"Knowledge Graph ({self._graph.node_count} nodes, {self._graph.edge_count} edges)"
        ]
        lines.append("=" * 60)

        roots = self._find_roots()
        for root_id in roots:
            self._ascii_subtree(root_id, lines, "", True)

        return "\n".join(lines)

    def _ascii_subtree(self, node_id: str, lines: list[str], prefix: str, is_last: bool) -> None:
        node = self._graph.nodes.get(node_id)
        if node is None:
            return

        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{node.label} [{node.node_type.value}]")

        children = self._graph.get_outgoing_edges(node_id)
        child_prefix = prefix + ("    " if is_last else "│   ")

        for i, edge in enumerate(children):
            child_node = self._graph.nodes.get(edge.target_id)
            if child_node:
                label = f"({edge.relation.value})"
                lines.append(f"{child_prefix}│")
                lines.append(f"{child_prefix}├── {label}")
                self._ascii_subtree(edge.target_id, lines, child_prefix, i == len(children) - 1)

    def _find_roots(self) -> list[str]:
        roots = []
        for nid in self._graph.nodes:
            if not self._graph.get_incoming_edges(nid):
                roots.append(nid)
        if not roots and self._graph.nodes:
            roots.append(next(iter(self._graph.nodes)))
        return roots

    def stats(self) -> dict:
        return {
            "format_count": len(ExportFormat),
            "nodes_visualizable": self._graph.node_count,
            "edges_visualizable": self._graph.edge_count,
        }
