"""Overnight batch enrichment — cross-linking entities, gap identification,
relation enrichment, and community consolidation.

The dream cycle runs asynchronously to enrich the knowledge graph
by discovering implicit connections, identifying unexplored areas,
inferring new relations, and consolidating similar communities.
"""

from __future__ import annotations

import itertools
from collections import defaultdict
from typing import Any


class DreamCycle:
    """Overnight batch enrichment for knowledge graphs.

    Runs a series of enrichment passes on a graph to discover
    implicit connections, gaps, and opportunities for expansion.
    """

    def __init__(self, graph: Any) -> None:
        self._graph = graph

    # ── Cross-Link Entities ────────────────────────────────────────────────

    def cross_link_entities(self,
                            similarity_threshold: float = 0.3) -> Any:
        """Find and link related entities across sessions.

        Links nodes that share common neighbors or have similar labels.
        Returns a new graph with added RELATES_TO edges.
        """
        result = self._graph
        nodes = list(result.nodes.values())

        # Group nodes by shared label words
        label_words: dict[str, set[str]] = defaultdict(set)
        for node in nodes:
            if node.node_type.value in {"concept", "entity", "insight"}:
                for word in node.label.lower().split():
                    if len(word) > 3:
                        label_words[word].add(node.node_id)

        # Find pairs sharing significant words
        linked: set[tuple[str, str]] = set()
        for _word, ids in label_words.items():
            if len(ids) < 2:
                continue
            for a, b in itertools.combinations(ids, 2):
                pair = (a, b) if a < b else (b, a)
                if pair not in linked:
                    linked.add(pair)

        from .graph_builder import EdgeRelation, KnowledgeEdge

        for a, b in linked:
            # Check if edge already exists
            existing = result.find_edges(source_id=a, target_id=b)
            if existing:
                continue
            existing = result.find_edges(source_id=b, target_id=a)
            if existing:
                continue

            conf = self._compute_cross_link_confidence(
                result, a, b, similarity_threshold
            )
            edge_id = f"dream:cross:{a}:{b}"
            if edge_id not in [e.edge_id for e in result.edges]:
                result = result.add_edge(KnowledgeEdge(
                    edge_id=edge_id,
                    source_id=a,
                    target_id=b,
                    relation=EdgeRelation.RELATES_TO,
                    weight=conf,
                    confidence=conf,
                    properties={"source": "dream_cycle_cross_link"},
                ))

        return result

    # ── Gap Identification ─────────────────────────────────────────────────

    def identify_gaps(self, min_neighbors: int = 1) -> list[dict[str, Any]]:
        """Find missing connections or unexplored areas.

        Returns a list of gap descriptions:
        - Isolated nodes (fewer than min_neighbors connections)
        - Potential connections between concept nodes that share properties
        """
        gaps: list[dict[str, Any]] = []

        # Find isolated nodes
        for nid, node in self._graph.nodes.items():
            try:
                neighbors = self._graph.get_neighbors(nid)
            except Exception:
                continue
            if len(neighbors) <= min_neighbors:
                gaps.append({
                    "type": "isolated_node",
                    "node_id": nid,
                    "label": node.label,
                    "node_type": node.node_type.value,
                    "neighbor_count": len(neighbors),
                    "suggestion": f"Node '{node.label}' has only "
                                  f"{len(neighbors)} connection(s)",
                })

        # Find potentially connectable concept pairs
        concept_ids = [
            nid for nid, node in self._graph.nodes.items()
            if node.node_type.value in {"concept", "entity"}
        ]
        concept_labels: dict[str, str] = {
            nid: self._graph.nodes[nid].label.lower()
            for nid in concept_ids
        }
        shared_word_pairs: set[tuple[str, str]] = set()
        for a, b in itertools.combinations(concept_ids, 2):
            if a == b:
                continue
            words_a = set(concept_labels[a].split())
            words_b = set(concept_labels[b].split())
            shared = words_a & words_b
            if len(shared) >= 2 and len(words_a) >= 3 and len(words_b) >= 3:
                pair = (a, b) if a < b else (b, a)
                if pair not in shared_word_pairs:
                    shared_word_pairs.add(pair)

        for a, b in shared_word_pairs:
            existing_a = self._graph.find_edges(source_id=a, target_id=b)
            existing_b = self._graph.find_edges(source_id=b, target_id=a)
            if not existing_a and not existing_b:
                gaps.append({
                    "type": "potential_connection",
                    "node_a": a,
                    "node_b": b,
                    "label_a": self._graph.nodes[a].label,
                    "label_b": self._graph.nodes[b].label,
                    "suggestion": f"Potential connection between "
                                  f"'{self._graph.nodes[a].label}' and "
                                  f"'{self._graph.nodes[b].label}'",
                })

        return gaps

    # ── Relation Enrichment ────────────────────────────────────────────────

    def enrich_relations(self) -> Any:
        """Add inferred relations based on structural patterns.

        Patterns:
        - If A extends B and B depends on C, infer A depends on C (transitive)
        - If A supports B and B supports C, infer A supports C
        """
        graph = self._graph
        result = graph
        from .graph_builder import EdgeRelation, KnowledgeEdge


        # Collect transitive edges for extends and depends_on
        transitive_pairs: list[tuple[str, str, str, float]] = []

        for edge in graph.edges:
            if edge.relation == EdgeRelation.DEPENDS_ON:
                # A depends_on B -> check B's outgoing depends_on
                b_outgoing = graph.get_outgoing_edges(edge.target_id)
                for out_edge in b_outgoing:
                    if out_edge.relation == EdgeRelation.DEPENDS_ON:
                        if out_edge.target_id != edge.source_id:
                            transitive_pairs.append((
                                edge.source_id,
                                out_edge.target_id,
                                "depends_on",
                                min(edge.confidence, out_edge.confidence) * 0.8,
                            ))
            elif edge.relation == EdgeRelation.SUPPORTS:
                # A supports B -> check B's outgoing supports
                b_outgoing = graph.get_outgoing_edges(edge.target_id)
                for out_edge in b_outgoing:
                    if out_edge.relation == EdgeRelation.SUPPORTS:
                        if out_edge.target_id != edge.source_id:
                            transitive_pairs.append((
                                edge.source_id,
                                out_edge.target_id,
                                "supports",
                                min(edge.confidence, out_edge.confidence) * 0.7,
                            ))

        existing_edge_ids = {e.edge_id for e in result.edges}
        for src, tgt, rel_type, conf in transitive_pairs:
            edge_id = f"dream:inferred:{src}:{tgt}:{rel_type}"
            if edge_id in existing_edge_ids:
                continue
            result = result.add_edge(KnowledgeEdge(
                edge_id=edge_id,
                source_id=src,
                target_id=tgt,
                relation=EdgeRelation(rel_type),
                weight=conf,
                confidence=conf,
                properties={"source": "dream_cycle_inferred"},
            ))
            existing_edge_ids.add(edge_id)

        return result

    # ── Community Consolidation ────────────────────────────────────────────

    def consolidate_communities(self,
                                communities: list[Any],
                                merge_threshold: float = 0.6) -> list[Any]:
        """Merge similar communities based on overlap and connectivity."""
        if len(communities) <= 1:
            return list(communities)

        # Compute pairwise Jaccard similarity for communities
        sim_matrix: dict[tuple[int, int], float] = {}
        for i in range(len(communities)):
            for j in range(i + 1, len(communities)):
                set_i = communities[i].node_ids
                set_j = communities[j].node_ids
                if not set_i or not set_j:
                    sim = 0.0
                else:
                    intersection = len(set_i & set_j)
                    union = len(set_i | set_j)
                    sim = intersection / union if union > 0 else 0.0
                sim_matrix[(i, j)] = sim

        # Merge communities above threshold
        remaining = set(range(len(communities)))
        new_communities: list[Any] = []

        for i in range(len(communities)):
            if i not in remaining:
                continue
            merge_group = {i}
            for j in range(i + 1, len(communities)):
                if j not in remaining:
                    continue
                if sim_matrix.get((i, j), 0.0) >= merge_threshold:
                    merge_group.add(j)
            remaining -= merge_group

            if len(merge_group) == 1:
                new_communities.append(communities[i])
            else:
                merged_ids: set[str] = set()
                merged_labels: list[str] = []
                for idx in merge_group:
                    merged_ids.update(communities[idx].node_ids)
                    merged_labels.append(communities[idx].label)
                from .community_detector import Community
                new_communities.append(
                    Community(
                        community_id=f"consolidated:{hash(frozenset(merge_group)) % 100000}",
                        node_ids=frozenset(merged_ids),
                        label=" | ".join(merged_labels[:3]),
                        level=0,
                    )
                )

        return new_communities

    # ── Full Enrichment Pipeline ──────────────────────────────────────────

    def run_full_cycle(self, communities: list[Any] | None = None) -> dict[str, Any]:
        """Run the complete dream cycle: cross-link, identify gaps, enrich, consolidate.

        Returns a report of all enrichment actions taken.
        """
        report: dict[str, Any] = {}

        # Phase 1: Cross-link
        linked_graph = self.cross_link_entities()
        report["cross_links_added"] = (
            linked_graph.edge_count - self._graph.edge_count
        )

        # Phase 2: Find gaps
        gaps = self.identify_gaps()
        report["gaps_found"] = len(gaps)
        report["gaps"] = gaps[:10]

        # Phase 3: Enrich relations on the linked graph
        enriched = DreamCycle(linked_graph)
        enriched_graph = enriched.enrich_relations()
        report["enriched_relations_added"] = (
            enriched_graph.edge_count - linked_graph.edge_count
        )

        # Phase 4: Consolidate communities
        if communities:
            consolidated = self.consolidate_communities(communities)
            report["communities_before"] = len(communities)
            report["communities_after"] = len(consolidated)
        else:
            report["communities_before"] = 0
            report["communities_after"] = 0

        return report

    # ── Internal ───────────────────────────────────────────────────────────

    def _compute_cross_link_confidence(self, graph: Any,
                                       node_a: str, node_b: str,
                                       threshold: float) -> float:
        """Compute confidence for a cross-link suggestion."""
        try:
            neighbors_a = {n.node_id for n in graph.get_neighbors(node_a)}
            neighbors_b = {n.node_id for n in graph.get_neighbors(node_b)}
        except Exception:
            return threshold

        shared = neighbors_a & neighbors_b
        all_nbrs = neighbors_a | neighbors_b
        if not all_nbrs:
            return 0.2
        jaccard = len(shared) / len(all_nbrs)
        return min(threshold + jaccard * 0.5, 1.0)


class KGDreamCycle:
    """Overnight KG enrichment — cross-links entities, fills gaps, merges similar nodes.

    Wraps DreamCycle to provide the specified dream() API for batch
    enrichment during idle periods.
    """

    def __init__(self, graph: Any) -> None:
        self._cycle = DreamCycle(graph)

    async def dream(self) -> dict[str, Any]:
        """Run a full enrichment cycle: cross-link, gap-fill, relation enrich.

        Returns a report of all enrichment actions.
        """
        return self._cycle.run_full_cycle()
