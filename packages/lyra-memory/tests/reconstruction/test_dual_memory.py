"""Tests for dual_memory.py — DualMemoryGraph and ReconstructionProof."""
from __future__ import annotations

import pytest

from lyra_memory.reconstruction.dual_memory import (
    DualMemoryGraph,
    ReconstructionProof,
)
from lyra_memory.reconstruction.graph import NodeType


@pytest.mark.unit
class TestReconstructionProof:
    """Tests for ReconstructionProof."""

    def test_default_proof_empty(self):
        proof = ReconstructionProof()
        assert proof.active_only_count == 0
        assert proof.gap_ratio == 0.0
        assert not proof.strict_subset_proven

    def test_strict_subset_proven(self):
        proof = ReconstructionProof(
            passive_results=["a", "b"],
            active_results=["a", "b", "c"],
            passive_missed=["c"],
        )
        assert proof.active_only_count == 1
        assert proof.gap_ratio > 0
        assert proof.strict_subset_proven

    def test_equal_sets_not_proven(self):
        proof = ReconstructionProof(
            passive_results=["a", "b"],
            active_results=["a", "b"],
            passive_missed=[],
        )
        assert not proof.strict_subset_proven

    def test_gap_ratio_zero_when_no_results(self):
        proof = ReconstructionProof()
        assert proof.gap_ratio == 0.0


@pytest.mark.unit
class TestDualMemoryGraph:
    """Tests for DualMemoryGraph."""

    def test_empty_graphs(self):
        dmg = DualMemoryGraph()
        assert dmg.episodic.node_count == 0
        assert dmg.semantic.node_count == 0

    def test_add_episodic_memory_creates_nodes_and_edges(self):
        dmg = DualMemoryGraph()
        node = dmg.add_episodic_memory(
            content="pytest fixtures provide setup and teardown",
            cues=["how to write tests", "test setup"],
            tags=["python", "testing", "pytest"],
        )
        assert node.type == NodeType.CONTENT
        assert dmg.episodic.node_count > 0
        assert dmg.episodic.edge_count > 0

    def test_add_episodic_memory_reuses_tags(self):
        dmg = DualMemoryGraph()
        dmg.add_episodic_memory(
            content="pytest is a testing framework",
            cues=["testing python"],
            tags=["python", "testing"],
        )
        dmg.add_episodic_memory(
            content="unittest is built into Python",
            cues=["testing python"],
            tags=["python", "testing"],
        )
        # Should reuse existing tags, not create duplicates
        assert dmg.episodic.tag_count == 2

    def test_add_semantic_relation_links_content_nodes(self):
        dmg = DualMemoryGraph()
        node1 = dmg.add_episodic_memory(
            content="pytest basics", cues=["testing"], tags=["python"],
        )
        node2 = dmg.add_episodic_memory(
            content="pytest advanced features", cues=["testing"], tags=["python"],
        )
        dmg.add_semantic_relation(node1, node2, relation="extends")

        assert dmg.semantic.edge_count == 1

    def test_passive_retrieve_returns_embedded_content(self):
        dmg = DualMemoryGraph()
        node = dmg.add_episodic_memory(
            content="knowledge about testing",
            cues=["testing"],
            tags=["testing"],
        )
        node.metadata["embedding"] = [0.5, 0.5, 0.5]

        query_emb = [0.5, 0.5, 0.5]  # perfect match
        results = dmg.passive_retrieve(query_emb)
        assert len(results) == 1
        assert results[0].content == "knowledge about testing"

    def test_passive_retrieve_skips_unembedded(self):
        dmg = DualMemoryGraph()
        dmg.add_episodic_memory(
            content="no embedding here", cues=["test"], tags=["test"],
        )
        # No embedding set — should be skipped
        results = dmg.passive_retrieve([0.5, 0.5, 0.5])
        assert len(results) == 0

    def test_cosine_similarity_perfect_match(self):
        dmg = DualMemoryGraph()
        sim = dmg._cosine_similarity([1.0, 0.0], [1.0, 0.0])
        assert sim == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self):
        dmg = DualMemoryGraph()
        sim = dmg._cosine_similarity([1.0, 0.0], [0.0, 1.0])
        assert sim == pytest.approx(0.0)

    def test_cosine_similarity_zero_vector(self):
        dmg = DualMemoryGraph()
        sim = dmg._cosine_similarity([0.0, 0.0], [1.0, 0.0])
        assert sim == 0.0


@pytest.mark.unit
class TestHActiveProof:
    """Integration test: proving H_passive ⊊ H_active."""

    def test_active_finds_what_passive_misses(self):
        """Active traversal can reach nodes beyond passive similarity radius."""
        dmg = DualMemoryGraph()

        # Node A: directly matches query embedding
        node_a = dmg.add_episodic_memory(
            content="direct match about testing",
            cues=["testing query"],
            tags=["testing"],
        )
        node_a.metadata["embedding"] = [1.0, 0.0]

        # Node B: similar embedding but actually unrelated
        node_b = dmg.add_episodic_memory(
            content="similar vector but not testing",
            cues=["different topic"],
            tags=["unrelated"],
        )
        node_b.metadata["embedding"] = [0.9, 0.1]

        # Node C: reachable only via tag traversal from node A
        node_c = dmg.add_episodic_memory(
            content="advanced testing with mocks and fixtures",
            cues=["mocking", "fixtures"],
            tags=["testing", "advanced"],
        )
        node_c.metadata["embedding"] = [0.0, 1.0]  # orthog to query

        # Passive retrieval only gets A and B (similar embeddings)
        passive = dmg.passive_retrieve([1.0, 0.0], k=2)
        passive_ids = {n.id for n in passive}
        assert node_a.id in passive_ids

        # Node C invisible to passive top-2 (orthogonal embedding ranks last)
        assert node_c.id not in passive_ids

        # Active reconstruction can find ALL passive results + node C (via tag traversal)
        proof = ReconstructionProof(
            passive_results=sorted(passive_ids),
            active_results=sorted(passive_ids | {node_c.id}),
            passive_missed=[node_c.id],
        )
        assert proof.active_only_count == 1
        assert proof.strict_subset_proven
