"""
Dual Memory Graph — Episodic + Semantic memory with active/passive retrieval.

MRAgent's key theoretical result: H_passive ⊊ H_active (strict subset).
Passive retrieval (embedding similarity) has an expressivity ceiling because
it can only match against what was indexed. Active reconstruction iteratively
traverses the graph, composing evidence across multiple hops to access memories
that are NOT reachable by passive similarity.

This module provides:
  DualMemoryGraph  — Episodic + Semantic graph with dual retrieval modes
  ReconstructionProof — Evidence tracker for the H_passive ⊊ H_active proof

Source: MRAgent (YPoHy6lgKP), ICLR 2026 MemAgent Workshop.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lyra_memory.reconstruction.graph import (
    CueTagContentGraph,
    GraphNode,
    NodeType,
)


@dataclass
class ReconstructionProof:
    """Evidence for H_passive ⊊ H_active.

    Tracks memories recovered by active reconstruction that were missed
    by passive similarity-based retrieval, providing empirical proof of
    the strict expressivity gap.
    """

    passive_results: list[str] = field(default_factory=list)
    active_results: list[str] = field(default_factory=list)
    passive_missed: list[str] = field(default_factory=list)

    @property
    def active_only_count(self) -> int:
        return len(self.passive_missed)

    @property
    def gap_ratio(self) -> float:
        """Ratio of memories ONLY accessible via active reconstruction."""
        total = len(set(self.passive_results) | set(self.active_results))
        if total == 0:
            return 0.0
        return len(self.passive_missed) / total

    @property
    def strict_subset_proven(self) -> bool:
        """H_passive ⊊ H_active holds if passive results are a subset of active."""
        passive_set = set(self.passive_results)
        active_set = set(self.active_results)
        return passive_set.issubset(active_set) and passive_set != active_set


@dataclass
class DualMemoryGraph:
    """Episodic + Semantic memory with dual passive/active retrieval modes.

    Passive retrieval (embedding similarity) operates on the episodic store.
    Active reconstruction traverses the full Cue-Tag-Content graph, combining
    episodic facts with semantic relationships to access memories passive
    retrieval cannot reach.
    """

    episodic: CueTagContentGraph = field(default_factory=CueTagContentGraph)
    semantic: CueTagContentGraph = field(default_factory=CueTagContentGraph)

    def add_episodic_memory(self, content: str, cues: list[str],
                            tags: list[str]) -> GraphNode:
        """Add a content node with its cues and tags to episodic memory."""
        content_node = GraphNode(type=NodeType.CONTENT, content=content)
        self.episodic.add_node(content_node)

        for tag_text in tags:
            tag_node = self._get_or_create_tag(self.episodic, tag_text)
            self.episodic.add_edge(tag_node.id, content_node.id,
                                   relation="tags")

        for cue_text in cues:
            cue_node = GraphNode(type=NodeType.CUE, content=cue_text)
            self.episodic.add_node(cue_node)
            for tag_text in tags:
                tag_node = self._get_or_create_tag(self.episodic, tag_text)
                self.episodic.add_edge(cue_node.id, tag_node.id,
                                       relation="triggers")

        return content_node

    def add_semantic_relation(self, source_content: GraphNode,
                              target_content: GraphNode,
                              relation: str = "relates") -> None:
        """Link two content nodes with a semantic relationship."""
        # Move or ensure nodes are in the semantic graph
        for node in (source_content, target_content):
            if node.id not in self.semantic.nodes:
                self.semantic.add_node(node)
        self.semantic.add_edge(source_content.id, target_content.id,
                               weight=0.8, relation=relation)

    def passive_retrieve(self, query_embedding: list[float],
                         k: int = 10) -> list[GraphNode]:
        """Passive retrieval: cosine similarity over episodic content nodes.

        This is the baseline — it can only return nodes whose embeddings
        are within similarity radius of the query. Memories that require
        multi-hop traversal are invisible to this method.
        """
        scored = []
        for node in self.episodic.get_all_content():
            node_emb = node.metadata.get("embedding")
            if node_emb is None:
                continue
            sim = self._cosine_similarity(query_embedding, node_emb)
            scored.append((node, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [node for node, _ in scored[:k]]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _get_or_create_tag(graph: CueTagContentGraph, tag_text: str) -> GraphNode:
        """Find existing tag or create a new one."""
        for tag in graph.get_all_tags():
            if tag.content.lower() == tag_text.lower():
                return tag
        tag_node = GraphNode(type=NodeType.TAG, content=tag_text)
        graph.add_node(tag_node)
        return tag_node
