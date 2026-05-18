"""
Tests for Advanced Metaproductivity Tracking (T102)

Tests clade diversity, cross-time replay, and diversity preservation.
"""

import pytest
from lyra_evolution.parallel_exploration import ParallelExplorationEngine, AgentNode


class TestCladeDiversity:
    """Test clade diversity calculation."""

    def test_leaf_node_has_zero_diversity(self):
        """Leaf nodes should have zero diversity (no descendants)."""
        engine = ParallelExplorationEngine(n_workers=2)

        baseline = {"skills": ["skill1", "skill2"]}
        root_id = engine.initialize(baseline)

        # Explore one generation to create children
        engine.explore_generation(n_mutations=3)

        # Check leaf nodes have zero diversity
        for node in engine.nodes.values():
            if not node.children:
                assert node.clade_diversity == 0.0

    def test_diversity_increases_with_varied_descendants(self):
        """Nodes with varied descendants should have higher diversity."""
        engine = ParallelExplorationEngine(n_workers=2)

        baseline = {"skills": ["skill1"]}
        root_id = engine.initialize(baseline)

        # Explore multiple generations to build tree
        for _ in range(3):
            engine.explore_generation(n_mutations=5, mutation_rate=0.3)

        # Root should have non-zero diversity (has descendants)
        root = engine.nodes[root_id]
        assert root.clade_diversity > 0.0

    def test_diversity_calculation_with_similar_configs(self):
        """Similar configurations should result in lower diversity."""
        engine = ParallelExplorationEngine(n_workers=2)

        # Create nodes with similar configs
        configs = [
            {"skills": ["skill1", "skill2"]},
            {"skills": ["skill1", "skill2", "skill3"]},
            {"skills": ["skill1", "skill2"]}
        ]

        diversity = engine._calculate_config_diversity(configs)

        # Should have some diversity but not maximum
        assert 0.0 < diversity < 1.0

    def test_diversity_calculation_with_distinct_configs(self):
        """Distinct configurations should result in higher diversity."""
        engine = ParallelExplorationEngine(n_workers=2)

        # Create nodes with very different configs
        configs = [
            {"skills": ["skill1"]},
            {"skills": ["skill2"]},
            {"skills": ["skill3"]}
        ]

        diversity = engine._calculate_config_diversity(configs)

        # Should have high diversity
        assert diversity > 0.5


class TestCrossTimeReplay:
    """Test cross-time replay functionality."""

    def test_replay_history_recorded(self):
        """Generation snapshots should be recorded."""
        engine = ParallelExplorationEngine(n_workers=2)

        baseline = {"skills": ["skill1"]}
        engine.initialize(baseline)

        # Explore 3 generations
        for _ in range(3):
            engine.explore_generation(n_mutations=3)

        # Should have 3 snapshots (one per generation)
        assert len(engine.replay_history) == 3

    def test_replay_snapshot_contains_required_fields(self):
        """Snapshots should contain all required fields."""
        engine = ParallelExplorationEngine(n_workers=2)

        baseline = {"skills": ["skill1"]}
        engine.initialize(baseline)
        engine.explore_generation(n_mutations=3)

        snapshot = engine.replay_history[0]

        required_fields = [
            "generation", "timestamp", "frontier_size", "total_nodes",
            "best_score", "best_metaproductivity", "avg_diversity", "frontier_nodes"
        ]

        for field in required_fields:
            assert field in snapshot

    def test_replay_evolution_full_history(self):
        """Should replay full evolution history."""
        engine = ParallelExplorationEngine(n_workers=2)

        baseline = {"skills": ["skill1"]}
        engine.initialize(baseline)

        for _ in range(5):
            engine.explore_generation(n_mutations=2)

        # Replay full history
        history = engine.replay_evolution()

        assert len(history) == 5
        assert history[0]["generation"] == 0
        assert history[-1]["generation"] == 4

    def test_replay_evolution_partial_range(self):
        """Should replay specific generation range."""
        engine = ParallelExplorationEngine(n_workers=2)

        baseline = {"skills": ["skill1"]}
        engine.initialize(baseline)

        for _ in range(5):
            engine.explore_generation(n_mutations=2)

        # Replay generations 1-3
        history = engine.replay_evolution(start_gen=1, end_gen=3)

        assert len(history) == 3
        assert history[0]["generation"] == 1
        assert history[-1]["generation"] == 3


class TestMetaproductivityWithDiversity:
    """Test metaproductivity calculation with diversity component."""

    def test_metaproductivity_includes_diversity(self):
        """Metaproductivity should include diversity bonus."""
        node = AgentNode(
            id="test",
            config={"skills": []},
            generation=0,
            immediate_score=0.8,
            descendant_yield=0.6,
            clade_diversity=0.5
        )

        # With default diversity weight (0.1)
        meta = node.metaproductivity()

        # Should be: 0.3 * 0.8 + 0.6 * 0.6 + 0.1 * 0.5
        expected = 0.3 * 0.8 + 0.6 * 0.6 + 0.1 * 0.5
        assert abs(meta - expected) < 0.001

    def test_metaproductivity_custom_diversity_weight(self):
        """Should support custom diversity weight."""
        node = AgentNode(
            id="test",
            config={"skills": []},
            generation=0,
            immediate_score=0.8,
            descendant_yield=0.6,
            clade_diversity=0.5
        )

        # With custom diversity weight
        meta = node.metaproductivity(diversity_weight=0.2)

        # Should be: 0.3 * 0.8 + 0.6 * 0.6 + 0.2 * 0.5
        expected = 0.3 * 0.8 + 0.6 * 0.6 + 0.2 * 0.5
        assert abs(meta - expected) < 0.001

    def test_high_diversity_improves_metaproductivity(self):
        """Higher diversity should improve metaproductivity."""
        node_low_div = AgentNode(
            id="test1",
            config={"skills": []},
            generation=0,
            immediate_score=0.5,
            descendant_yield=0.5,
            clade_diversity=0.1
        )

        node_high_div = AgentNode(
            id="test2",
            config={"skills": []},
            generation=0,
            immediate_score=0.5,
            descendant_yield=0.5,
            clade_diversity=0.9
        )

        assert node_high_div.metaproductivity() > node_low_div.metaproductivity()


class TestDiversityPreservation:
    """Test that diversity is preserved in evolution."""

    def test_frontier_maintains_diverse_solutions(self):
        """Frontier should maintain diverse solutions, not just high-scoring."""
        engine = ParallelExplorationEngine(n_workers=2)

        baseline = {"skills": ["skill1"]}
        engine.initialize(baseline)

        # Explore multiple generations
        for _ in range(5):
            engine.explore_generation(n_mutations=10, mutation_rate=0.2)

        # Check frontier has multiple nodes (diversity preserved)
        assert len(engine.frontier) > 1

        # Check frontier nodes have varied metaproductivity
        frontier_nodes = [engine.nodes[nid] for nid in engine.frontier]
        meta_scores = [n.metaproductivity() for n in frontier_nodes]

        # Should have some variation (not all identical)
        assert max(meta_scores) - min(meta_scores) > 0.01

    def test_best_nodes_include_diverse_solutions(self):
        """Best nodes should include diverse solutions."""
        engine = ParallelExplorationEngine(n_workers=2)

        baseline = {"skills": ["skill1"]}
        engine.initialize(baseline)

        for _ in range(3):
            engine.explore_generation(n_mutations=10, mutation_rate=0.3)

        best_nodes = engine.get_best_nodes(n=5)

        # Should have multiple best nodes
        assert len(best_nodes) >= 3

        # Check they have varied configurations
        skill_sets = [set(n.config.get("skills", [])) for n in best_nodes]

        # At least some should be different
        unique_skill_sets = len(set(frozenset(s) for s in skill_sets))
        assert unique_skill_sets > 1


class TestIntegration:
    """Integration tests for all T102 features."""

    def test_full_evolution_with_tracking(self):
        """Test complete evolution with all tracking features."""
        engine = ParallelExplorationEngine(n_workers=4)

        baseline = {"skills": ["skill1", "skill2"]}
        root_id = engine.initialize(baseline)

        # Run evolution for 5 generations
        for gen in range(5):
            new_nodes = engine.explore_generation(n_mutations=8, mutation_rate=0.2)
            assert len(new_nodes) > 0

        # Verify all tracking features work
        assert len(engine.replay_history) == 5
        assert engine.nodes[root_id].clade_diversity > 0.0

        # Verify statistics
        stats = engine.get_statistics()
        assert stats["generations_explored"] == 5
        assert stats["total_nodes"] > 5
        assert stats["best_metaproductivity"] > 0.0

        # Verify replay works
        history = engine.replay_evolution()
        assert len(history) == 5

        # Verify diversity is tracked (may fluctuate, but should be non-zero)
        diversities = [h["avg_diversity"] for h in history]
        assert any(d > 0.0 for d in diversities)

    def test_avoids_high_score_low_descendant_trap(self):
        """Verify metaproductivity avoids the trap."""
        # Create two nodes: one high-score but no descendants,
        # one medium-score with good descendants

        high_score_node = AgentNode(
            id="high_score",
            config={"skills": []},
            generation=1,
            immediate_score=0.9,
            descendant_yield=0.1,  # Low descendants
            clade_diversity=0.0
        )

        balanced_node = AgentNode(
            id="balanced",
            config={"skills": []},
            generation=1,
            immediate_score=0.6,
            descendant_yield=0.7,  # Good descendants
            clade_diversity=0.5
        )

        # Balanced node should have better metaproductivity
        assert balanced_node.metaproductivity() > high_score_node.metaproductivity()
