"""Graph querier — structured query API for the knowledge graph.

Provides path queries, subgraph extraction, pattern matching, and ranked
node/edge search on top of KnowledgeGraph.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .exceptions import NodeNotFoundError
from .graph_builder import EdgeRelation, KnowledgeEdge, KnowledgeGraph, KnowledgeNode, NodeType


class QueryStrategy(StrEnum):
    BFS = "bfs"
    DFS = "dfs"
    DIJKSTRA = "dijkstra"


class SortOrder(StrEnum):
    CONFIDENCE = "confidence"
    DEGREE = "degree"
    PAGE_RANK = "page_rank"


@dataclass(frozen=True)
class PathResult:
    path: list[str]
    length: int
    total_weight: float

    @property
    def node_count(self) -> int:
        return len(self.path)


@dataclass(frozen=True)
class SubgraphResult:
    nodes: list[KnowledgeNode]
    edges: list[KnowledgeEdge]
    root_id: str

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)


@dataclass(frozen=True)
class QueryResult:
    nodes: list[KnowledgeNode]
    total_matches: int
    query_time_ms: float


class GraphQuerier:
    """Structured query interface for KnowledgeGraph.

    Provides path finding, subgraph extraction, pattern matching,
    and ranked search beyond the graph's built-in query methods.
    """

    def __init__(self, graph: KnowledgeGraph) -> None:
        self._graph = graph

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
        strategy: QueryStrategy = QueryStrategy.BFS,
    ) -> list[PathResult]:
        if source_id not in self._graph.nodes:
            raise NodeNotFoundError(source_id)
        if target_id not in self._graph.nodes:
            raise NodeNotFoundError(target_id)

        if strategy == QueryStrategy.BFS:
            return self._bfs_paths(source_id, target_id, max_depth)
        return self._dfs_paths(source_id, target_id, max_depth)

    def _bfs_paths(self, source: str, target: str, max_depth: int) -> list[PathResult]:
        results: list[PathResult] = []
        queue: list[tuple[str, list[str], float]] = [(source, [source], 0.0)]

        while queue:
            current, path, weight = queue.pop(0)
            if len(path) > max_depth + 1:
                continue
            if current == target and len(path) > 1:
                results.append(
                    PathResult(path=list(path), length=len(path) - 1, total_weight=round(weight, 4))
                )
                continue
            for edge in self._graph.get_outgoing_edges(current):
                if edge.target_id not in path:
                    queue.append((edge.target_id, path + [edge.target_id], weight + edge.weight))

        return sorted(results, key=lambda r: r.length)

    def _dfs_paths(self, source: str, target: str, max_depth: int) -> list[PathResult]:
        results: list[PathResult] = []

        def _dfs(current: str, path: list[str], weight: float) -> None:
            if len(path) > max_depth + 1:
                return
            if current == target and len(path) > 1:
                results.append(
                    PathResult(path=list(path), length=len(path) - 1, total_weight=round(weight, 4))
                )
                return
            for edge in self._graph.get_outgoing_edges(current):
                if edge.target_id not in path:
                    _dfs(edge.target_id, path + [edge.target_id], weight + edge.weight)

        _dfs(source, [source], 0.0)
        return sorted(results, key=lambda r: r.length)

    def extract_subgraph(
        self, root_id: str, depth: int = 2, node_types: list[NodeType] | None = None
    ) -> SubgraphResult:
        if root_id not in self._graph.nodes:
            raise NodeNotFoundError(root_id)

        visited: set[str] = set()
        nodes: list[KnowledgeNode] = []
        edges: list[KnowledgeEdge] = []
        current_layer = {root_id}
        allowed_types = set(node_types) if node_types else None

        for _ in range(depth + 1):
            next_layer: set[str] = set()
            for nid in current_layer:
                if nid in visited:
                    continue
                visited.add(nid)
                node = self._graph.nodes[nid]
                if allowed_types and node.node_type not in allowed_types:
                    continue
                nodes.append(node)
                for edge in self._graph.get_outgoing_edges(nid):
                    edges.append(edge)
                    next_layer.add(edge.target_id)
                for edge in self._graph.get_incoming_edges(nid):
                    if edge.source_id not in visited:
                        edges.append(edge)
                        next_layer.add(edge.source_id)
            current_layer = next_layer

        return SubgraphResult(nodes=nodes, edges=edges, root_id=root_id)

    def find_by_pattern(
        self,
        node_type: NodeType | None = None,
        relation: EdgeRelation | None = None,
        min_confidence: float = 0.0,
        label_regex: str | None = None,
    ) -> list[KnowledgeNode]:
        import re

        results: list[KnowledgeNode] = []
        for node in self._graph.nodes.values():
            if node_type is not None and node.node_type != node_type:
                continue
            if node.confidence < min_confidence:
                continue
            if label_regex is not None and not re.search(label_regex, node.label):
                continue
            if relation is not None:
                has_relation = any(
                    e.relation == relation for e in self._graph.get_outgoing_edges(node.node_id)
                ) or any(
                    e.relation == relation for e in self._graph.get_incoming_edges(node.node_id)
                )
                if not has_relation:
                    continue
            results.append(node)
        return results

    def ranked_search(
        self,
        query: str,
        sort_by: SortOrder = SortOrder.CONFIDENCE,
        limit: int = 20,
    ) -> QueryResult:
        import time

        start = time.time()

        query_lower = query.lower()
        matches: list[tuple[KnowledgeNode, float]] = []

        for node in self._graph.nodes.values():
            score = 0.0
            if query_lower in node.label.lower():
                score += 3.0
            for val in node.properties.values():
                if isinstance(val, str) and query_lower in val.lower():
                    score += 1.0
            if score > 0:
                if sort_by == SortOrder.DEGREE:
                    degree = len(self._graph.get_outgoing_edges(node.node_id)) + len(
                        self._graph.get_incoming_edges(node.node_id)
                    )
                    score = float(degree)
                elif sort_by == SortOrder.PAGE_RANK:
                    score = self._approx_pagerank(node.node_id)
                elif sort_by == SortOrder.CONFIDENCE:
                    score = node.confidence * score
                matches.append((node, score))

        matches.sort(key=lambda x: x[1], reverse=True)
        top = matches[:limit]

        return QueryResult(
            nodes=[m[0] for m in top],
            total_matches=len(matches),
            query_time_ms=round((time.time() - start) * 1000, 2),
        )

    def _approx_pagerank(self, node_id: str, damping: float = 0.85, iterations: int = 20) -> float:
        node_ids = list(self._graph.nodes.keys())
        if not node_ids:
            return 0.0

        n = len(node_ids)
        ranks: dict[str, float] = dict.fromkeys(node_ids, 1.0 / n)

        for _ in range(iterations):
            new_ranks: dict[str, float] = {}
            for nid in node_ids:
                incoming = self._graph.get_incoming_edges(nid)
                rank_sum = 0.0
                for edge in incoming:
                    out_degree = max(len(self._graph.get_outgoing_edges(edge.source_id)), 1)
                    rank_sum += ranks[edge.source_id] / out_degree
                new_ranks[nid] = (1 - damping) / n + damping * rank_sum
            ranks = new_ranks

        return round(ranks.get(node_id, 0.0), 6)

    def stats(self) -> dict:
        return {
            "graph_nodes": self._graph.node_count,
            "graph_edges": self._graph.edge_count,
        }
