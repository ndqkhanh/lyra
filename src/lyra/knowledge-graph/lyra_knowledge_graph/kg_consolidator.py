"""KG consolidator — merges multiple knowledge graphs with conflict resolution.

Handles duplicate detection, entity resolution, confidence-weighted merging,
and graph compaction across multiple KnowledgeGraph instances.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum

from .graph_builder import KnowledgeGraph, KnowledgeNode


class MergeStrategy(StrEnum):
    KEEP_HIGHEST_CONFIDENCE = "keep_highest_confidence"
    KEEP_FIRST = "keep_first"
    KEEP_LAST = "keep_last"
    AVERAGE_CONFIDENCE = "average_confidence"


class ConflictResolution(StrEnum):
    OVERWRITE = "overwrite"
    MERGE_PROPS = "merge_props"
    KEEP_BOTH = "keep_both"


@dataclass(frozen=True)
class ConsolidationReport:
    graphs_merged: int
    nodes_before: int
    nodes_after: int
    edges_before: int
    edges_after: int
    duplicates_resolved: int
    conflicts_found: int
    duration_ms: float
    merged_graph: KnowledgeGraph

    @property
    def node_reduction_pct(self) -> float:
        if self.nodes_before == 0:
            return 0.0
        return round((1 - self.nodes_after / self.nodes_before) * 100, 1)

    @property
    def edge_reduction_pct(self) -> float:
        if self.edges_before == 0:
            return 0.0
        return round((1 - self.edges_after / self.edges_before) * 100, 1)


class KGConsolidator:
    """Merges and consolidates multiple KnowledgeGraph instances.

    Detects duplicate nodes via label + type matching, resolves conflicts
    using configurable strategies, and produces a compact merged graph.
    """

    def __init__(
        self,
        merge_strategy: MergeStrategy = MergeStrategy.KEEP_HIGHEST_CONFIDENCE,
        conflict_resolution: ConflictResolution = ConflictResolution.MERGE_PROPS,
        similarity_threshold: float = 0.85,
    ) -> None:
        self._merge_strategy = merge_strategy
        self._conflict_resolution = conflict_resolution
        self._similarity_threshold = similarity_threshold
        self._reports: list[ConsolidationReport] = []

    def consolidate(self, graphs: list[KnowledgeGraph]) -> ConsolidationReport:
        start = time.time()

        if not graphs:
            empty = KnowledgeGraph()
            return ConsolidationReport(
                graphs_merged=0, nodes_before=0, nodes_after=0,
                edges_before=0, edges_after=0, duplicates_resolved=0,
                conflicts_found=0, duration_ms=0.0, merged_graph=empty,
            )

        total_nodes_before = sum(g.node_count for g in graphs)
        total_edges_before = sum(g.edge_count for g in graphs)
        duplicates = 0
        conflicts = 0

        merged = KnowledgeGraph()
        node_index: dict[str, list[KnowledgeNode]] = defaultdict(list)

        for graph in graphs:
            for node in graph.nodes.values():
                key = self._node_key(node)
                existing = node_index.get(key, [])

                if existing:
                    resolved, had_conflict = self._resolve_duplicate(node, existing)
                    if had_conflict:
                        conflicts += 1
                    duplicates += 1
                    merged = merged.add_node(resolved)
                    node_index[key].append(resolved)
                else:
                    merged = merged.add_node(node)
                    node_index[key].append(node)

            for edge in graph.edges:
                if edge.source_id in merged.nodes and edge.target_id in merged.nodes:
                    try:
                        merged = merged.add_edge(edge)
                    except Exception:
                        pass

        report = ConsolidationReport(
            graphs_merged=len(graphs),
            nodes_before=total_nodes_before,
            nodes_after=merged.node_count,
            edges_before=total_edges_before,
            edges_after=merged.edge_count,
            duplicates_resolved=duplicates,
            conflicts_found=conflicts,
            duration_ms=round((time.time() - start) * 1000, 2),
            merged_graph=merged,
        )
        self._reports.append(report)
        return report

    def _node_key(self, node: KnowledgeNode) -> str:
        label_norm = node.label.lower().strip()
        return f"{label_norm}:{node.node_type.value}"

    def _resolve_duplicate(
        self, new_node: KnowledgeNode, existing_nodes: list[KnowledgeNode]
    ) -> tuple[KnowledgeNode, bool]:
        existing = existing_nodes[0]
        has_conflict = False

        if self._merge_strategy == MergeStrategy.KEEP_FIRST:
            return existing, False
        if self._merge_strategy == MergeStrategy.KEEP_LAST:
            return new_node, False
        if self._merge_strategy == MergeStrategy.AVERAGE_CONFIDENCE:
            avg_confidence = round((new_node.confidence + existing.confidence) / 2, 4)
            return KnowledgeNode(
                node_id=existing.node_id,
                node_type=existing.node_type,
                label=existing.label,
                properties=existing.properties,
                metadata=existing.metadata,
                community_id=existing.community_id,
                confidence=avg_confidence,
            ), False

        if new_node.confidence > existing.confidence:
            return new_node, new_node.label != existing.label

        if self._conflict_resolution == ConflictResolution.MERGE_PROPS:
            merged_props = {**existing.properties, **new_node.properties}
            merged_meta = {**existing.metadata, **new_node.metadata}
            if merged_props != existing.properties:
                has_conflict = True
            return KnowledgeNode(
                node_id=existing.node_id,
                node_type=existing.node_type,
                label=existing.label,
                properties=merged_props,
                metadata=merged_meta,
                community_id=new_node.community_id or existing.community_id,
                confidence=max(existing.confidence, new_node.confidence),
            ), has_conflict

        return existing, False

    def merge_edges(
        self, graph: KnowledgeGraph, deduplicate: bool = True
    ) -> KnowledgeGraph:
        if not deduplicate:
            return graph

        seen: set[tuple[str, str, str]] = set()
        result = KnowledgeGraph()

        for node in graph.nodes.values():
            result = result.add_node(node)

        for edge in graph.edges:
            sig = (edge.source_id, edge.target_id, edge.relation.value)
            if sig not in seen:
                seen.add(sig)
                result = result.add_edge(edge)

        return result

    def compact(self, graph: KnowledgeGraph, min_confidence: float = 0.1) -> KnowledgeGraph:
        result = KnowledgeGraph()
        for node in graph.nodes.values():
            if node.confidence >= min_confidence:
                result = result.add_node(node)

        for edge in graph.edges:
            if (
                edge.source_id in result.nodes
                and edge.target_id in result.nodes
                and edge.confidence >= min_confidence
            ):
                try:
                    result = result.add_edge(edge)
                except Exception:
                    pass

        return result

    def get_reports(self) -> list[ConsolidationReport]:
        return list(self._reports)

    def stats(self) -> dict:
        return {
            "total_consolidations": len(self._reports),
            "merge_strategy": self._merge_strategy.value,
            "conflict_resolution": self._conflict_resolution.value,
            "total_duplicates_resolved": sum(r.duplicates_resolved for r in self._reports),
        }
