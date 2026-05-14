"""Codebase knowledge graph for Lyra self-modification safety analysis.

Implements a LightRAG-style entity-relationship graph (arXiv:2305.16291) over
the Lyra codebase, as specified in Doc 322 of the Lyra 322–326 evolution plan.
Nodes represent structural units (functions, classes, modules, tests, skills);
edges represent typed relationships between them.  The primary use-case is
impact analysis: before Lyra rewrites any artifact it queries ``find_impact``
to enumerate every downstream node that could be affected, enabling the
self-modification safety gate described in the AER cockpit design.

No external dependencies are required — the graph is stored in plain Python
dicts and lists so that this module is importable in any environment.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

__all__ = [
    "NodeKind",
    "EdgeKind",
    "GraphNode",
    "GraphEdge",
    "CodebaseGraph",
]


class NodeKind(str, Enum):
    function = "function"
    class_ = "class"
    module = "module"
    test = "test"
    skill = "skill"


class EdgeKind(str, Enum):
    calls = "calls"
    imports = "imports"
    tests = "tests"
    depends_on = "depends_on"
    defines = "defines"


@dataclass
class GraphNode:
    id: str
    kind: NodeKind
    label: str
    file_path: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class GraphEdge:
    source_id: str
    target_id: str
    kind: EdgeKind


class CodebaseGraph:
    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._out: dict[str, list[GraphEdge]] = {}
        self._in: dict[str, list[GraphEdge]] = {}

    def add_node(self, node: GraphNode) -> None:
        self._nodes[node.id] = node
        self._out.setdefault(node.id, [])
        self._in.setdefault(node.id, [])

    def add_edge(self, edge: GraphEdge) -> None:
        if edge.source_id not in self._nodes:
            raise KeyError(f"source node '{edge.source_id}' not in graph")
        if edge.target_id not in self._nodes:
            raise KeyError(f"target node '{edge.target_id}' not in graph")
        self._out[edge.source_id].append(edge)
        self._in[edge.target_id].append(edge)

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        return self._nodes.get(node_id)

    def successors(self, node_id: str) -> list[GraphEdge]:
        return list(self._out.get(node_id, []))

    def predecessors(self, node_id: str) -> list[GraphEdge]:
        return list(self._in.get(node_id, []))

    def nodes_by_kind(self, kind: NodeKind) -> list[GraphNode]:
        return [n for n in self._nodes.values() if n.kind == kind]

    def find_impact(self, node_id: str, max_depth: int = 5) -> set[str]:
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])
        while queue:
            current, depth = queue.popleft()
            if current in visited or depth > max_depth:
                continue
            visited.add(current)
            for edge in self._out.get(current, []):
                if edge.target_id not in visited:
                    queue.append((edge.target_id, depth + 1))
        visited.discard(node_id)
        return visited

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return sum(len(edges) for edges in self._out.values())
