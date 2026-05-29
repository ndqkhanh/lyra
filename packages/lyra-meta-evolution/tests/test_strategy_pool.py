"""Tests for lyra_meta_evolution.strategy_pool module."""

import pytest
from lyra_meta_evolution.meta_evolution import AgentGenome
from lyra_meta_evolution.strategy_pool import (
    SimilarityMetrics,
    StrategyEncoding,
    StrategyNotFoundError,
    StrategyPool,
    StrategyRecord,
)

# ── Fixtures ────────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_genome():
    return AgentGenome(
        agent_id="agent_1",
        hyperparameters={"learning_rate": 0.01, "temperature": 0.7},
        strategy_weights={"greedy": 0.6, "exploration": 0.4},
        active_strategies=["greedy", "exploration"],
        objective_weights={"speed": 0.3, "quality": 0.3, "cost": 0.2, "reliability": 0.2},
    )


@pytest.fixture
def sample_encoding(sample_genome):
    return StrategyEncoding.from_genome(sample_genome)


@pytest.fixture
def strategy_pool():
    return StrategyPool(max_size=100)


# ── StrategyEncoding ────────────────────────────────────────────────────────────


class TestStrategyEncoding:
    def test_from_genome_creates_encoding(self, sample_genome):
        enc = StrategyEncoding.from_genome(sample_genome)
        assert enc.strategy_id == "agent_1"
        assert len(enc.signature) > 0
        assert len(enc.feature_vector) > 0

    def test_feature_vector_contains_all_params(self, sample_genome):
        enc = StrategyEncoding.from_genome(sample_genome)
        # Should include hps, strategy weights, objective weights
        expected_min = (
            len(sample_genome.hyperparameters)
            + len(sample_genome.strategy_weights)
            + len(sample_genome.objective_weights)
        )
        assert len(enc.feature_vector) >= expected_min

    def test_feature_vector_is_deterministic(self, sample_genome):
        enc1 = StrategyEncoding.from_genome(sample_genome)
        enc2 = StrategyEncoding.from_genome(sample_genome)
        assert enc1.signature == enc2.signature
        assert enc1.feature_vector == enc2.feature_vector


# ── SimilarityMetrics ───────────────────────────────────────────────────────────


class TestSimilarityMetrics:
    def test_cosine_identical_vectors(self):
        vec = [0.5, 0.3, 0.8]
        sim = SimilarityMetrics.cosine_similarity(vec, vec)
        assert abs(sim - 1.0) < 0.001

    def test_cosine_orthogonal_vectors(self):
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        sim = SimilarityMetrics.cosine_similarity(v1, v2)
        assert abs(sim - 0.0) < 0.001

    def test_cosine_empty_vectors(self):
        assert SimilarityMetrics.cosine_similarity([], []) == 0.0

    def test_euclidean_identical_vectors(self):
        vec = [0.5, 0.3]
        dist = SimilarityMetrics.euclidean_distance(vec, vec)
        assert abs(dist - 0.0) < 0.001

    def test_euclidean_different_vectors(self):
        v1 = [0.0, 0.0]
        v2 = [3.0, 4.0]
        dist = SimilarityMetrics.euclidean_distance(v1, v2)
        assert abs(dist - 5.0) < 0.001

    def test_euclidean_different_lengths(self):
        v1 = [1.0]
        v2 = [1.0, 2.0, 3.0]
        dist = SimilarityMetrics.euclidean_distance(v1, v2)
        assert dist > 0.0

    def test_jaccard_signature(self):
        sig1 = "abcdef1234567890"
        sig2 = "abcdef1234567890"
        sim = SimilarityMetrics.jaccard_signature(sig1, sig2)
        assert abs(sim - 1.0) < 0.001


# ── StrategyPool ────────────────────────────────────────────────────────────────


class TestStrategyPool:
    def test_add_strategy(self, strategy_pool, sample_encoding):
        record = strategy_pool.add_strategy(sample_encoding, fitness=0.75)
        assert isinstance(record, StrategyRecord)
        assert strategy_pool.size == 1

    def test_get_strategy(self, strategy_pool, sample_encoding):
        strategy_pool.add_strategy(sample_encoding)
        record = strategy_pool.get_strategy("agent_1")
        assert record.strategy_id == "agent_1"

    def test_get_nonexistent_raises(self, strategy_pool):
        with pytest.raises(StrategyNotFoundError):
            strategy_pool.get_strategy("nonexistent")

    def test_record_result_updates_stats(self, strategy_pool, sample_encoding):
        strategy_pool.add_strategy(sample_encoding)
        strategy_pool.record_result("agent_1", fitness=0.9, success=True)
        strategy_pool.record_result("agent_1", fitness=0.85, success=False)
        record = strategy_pool.get_strategy("agent_1")
        assert record.usage_count == 2
        assert record.success_count == 1
        assert abs(record.success_rate - 0.5) < 0.001

    def test_find_similar(self, strategy_pool, sample_genome):
        enc1 = StrategyEncoding.from_genome(sample_genome)
        pool.add_strategy(enc1)

        # Create a similar genome
        similar = sample_genome.clone("similar_1")
        enc2 = StrategyEncoding.from_genome(similar)
        pool.add_strategy(enc2)

        results = pool.find_similar(enc1, top_k=2, threshold=0.0)
        # Should find at least the similar genome (maybe not self)
        assert len(results) >= 1

    def test_find_similar_excludes_self(self, strategy_pool, sample_encoding):
        strategy_pool.add_strategy(sample_encoding)
        results = strategy_pool.find_similar(sample_encoding, threshold=0.0)
        # Should not match self
        ids = [r.strategy_id for r, _ in results]
        assert sample_encoding.strategy_id not in ids

    def test_compute_diversity_empty(self, strategy_pool):
        assert strategy_pool.compute_diversity() == 1.0

    def test_compute_diversity_with_one(self, strategy_pool, sample_encoding):
        strategy_pool.add_strategy(sample_encoding)
        assert strategy_pool.compute_diversity() == 1.0

    def test_compute_diversity_with_many(self, strategy_pool, sample_genome):
        for i in range(10):
            variant = sample_genome.clone(f"var_{i}")
            # Perturb hyperparameters for diversity
            for k in variant.hyperparameters:
                variant.hyperparameters[k] += i * 0.01
            enc = StrategyEncoding.from_genome(variant)
            strategy_pool.add_strategy(enc)
        diversity = strategy_pool.compute_diversity()
        assert 0.0 <= diversity <= 1.0

    def test_novelty_search(self, strategy_pool, sample_genome):
        # Fill pool with some strategies
        for i in range(5):
            variant = sample_genome.clone(f"exist_{i}")
            enc = StrategyEncoding.from_genome(variant)
            strategy_pool.add_strategy(enc)

        # Create population to search
        population = []
        for i in range(5):
            variant = sample_genome.clone(f"new_{i}")
            for k in variant.hyperparameters:
                variant.hyperparameters[k] += (i + 5) * 0.05
            enc = StrategyEncoding.from_genome(variant)
            population.append(enc)

        novel = strategy_pool.novelty_search(population, k=3)
        assert len(novel) <= 3
        assert len(novel) > 0

    def test_get_lineage(self, strategy_pool, sample_encoding, sample_genome):
        strategy_pool.add_strategy(sample_encoding, parent_ids=["grandparent"])

        # Child strategy
        child_genome = sample_genome.clone("child_1")
        enc_child = StrategyEncoding.from_genome(child_genome)
        strategy_pool.add_strategy(enc_child, parent_ids=["agent_1"])

        lineage = strategy_pool.get_lineage("child_1")
        assert "ancestors" in lineage
        assert "agent_1" in lineage["ancestors"]

    def test_get_top_strategies(self, strategy_pool):
        for i in range(10):
            g = AgentGenome(agent_id=f"strat_{i}")
            enc = StrategyEncoding.from_genome(g)
            strategy_pool.add_strategy(enc, fitness=0.5 + i * 0.05)
            strategy_pool.record_result(f"strat_{i}", fitness=0.5 + i * 0.05, success=True)

        top = strategy_pool.get_top_strategies(top_k=5, min_usage=1)
        assert len(top) <= 5
        # Top strategy should have highest fitness
        assert top[0].fitness >= top[-1].fitness

    def test_archive_and_unarchive(self, strategy_pool, sample_encoding):
        strategy_pool.add_strategy(sample_encoding)
        strategy_pool.archive_strategy("agent_1")
        assert strategy_pool.active_size == 0

        strategy_pool.unarchive_strategy("agent_1")
        assert strategy_pool.active_size == 1

    def test_by_tag(self, strategy_pool, sample_encoding):
        strategy_pool.add_strategy(sample_encoding, tags={"python", "optimization"})
        results = strategy_pool.by_tag("python")
        assert len(results) == 1
        assert results[0].strategy_id == "agent_1"

    def test_export_pool(self, strategy_pool, sample_encoding):
        strategy_pool.add_strategy(sample_encoding)
        exported = strategy_pool.export_pool()
        assert "strategies" in exported
        assert "stats" in exported
        assert exported["stats"]["current_size"] == 1

    def test_avg_fitness(self, strategy_pool):
        for i in range(5):
            g = AgentGenome(agent_id=f"fit_{i}")
            enc = StrategyEncoding.from_genome(g)
            strategy_pool.add_strategy(enc, fitness=0.5 + i * 0.1)
            strategy_pool.record_result(f"fit_{i}", fitness=0.5 + i * 0.1, success=True)

        avg = strategy_pool.avg_fitness
        assert 0.0 <= avg <= 1.0

    def test_prune_on_capacity(self, sample_genome):
        small_pool = StrategyPool(max_size=5)
        for i in range(10):
            g = sample_genome.clone(f"overflow_{i}")
            enc = StrategyEncoding.from_genome(g)
            small_pool.add_strategy(enc, fitness=0.1 + i * 0.05)
        # Should have pruned the lowest fitness entries
        assert small_pool.size <= 5

    def test_strategy_record_success_rate(self):
        record = StrategyRecord(
            strategy_id="test",
            encoding=StrategyEncoding(strategy_id="test", signature="abc", feature_vector=[0.5]),
        )
        assert record.success_rate == 0.0  # No usage
        record.record_result(0.8, success=True)
        record.record_result(0.6, success=False)
        assert record.success_rate == 0.5


# Create StrategyPool at module level for tests that use it as 'pool'
pool = StrategyPool(max_size=100)
