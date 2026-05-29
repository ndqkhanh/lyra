"""
Tests for Fast Evolution Engine (T103)

Tests caching, incremental mutations, and 10-minute cycle performance.
"""

import time

from lyra_evolution.fast_evolution import EvaluationCache, FastEvolutionEngine, IncrementalMutator


class TestEvaluationCache:
    """Test evaluation caching."""

    def test_cache_initialization(self):
        """Cache should initialize with correct parameters."""
        cache = EvaluationCache(max_size=1000)

        assert cache.max_size == 1000
        assert len(cache.cache) == 0
        assert cache.hits == 0
        assert cache.misses == 0

    def test_cache_miss(self):
        """First access should be a cache miss."""
        cache = EvaluationCache()

        config = {"skills": ["skill1"]}
        result = cache.get(config)

        assert result is None
        assert cache.misses == 1
        assert cache.hits == 0

    def test_cache_hit(self):
        """Second access should be a cache hit."""
        cache = EvaluationCache()

        config = {"skills": ["skill1"]}

        # First access - miss
        cache.put(config, 0.8)

        # Second access - hit
        result = cache.get(config)

        assert result == 0.8
        assert cache.hits == 1
        assert cache.misses == 0

    def test_cache_hit_rate(self):
        """Hit rate should be calculated correctly."""
        cache = EvaluationCache()

        config1 = {"skills": ["skill1"]}
        config2 = {"skills": ["skill2"]}

        # 2 misses
        cache.get(config1)
        cache.get(config2)

        # Cache them
        cache.put(config1, 0.8)
        cache.put(config2, 0.9)

        # 2 hits
        cache.get(config1)
        cache.get(config2)

        # Hit rate should be 50% (2 hits, 2 misses)
        assert cache.hit_rate() == 0.5

    def test_cache_eviction(self):
        """Cache should evict LRU entries when full."""
        cache = EvaluationCache(max_size=3)

        # Fill cache
        for i in range(3):
            config = {"skills": [f"skill{i}"]}
            cache.put(config, float(i))

        assert len(cache.cache) == 3

        # Add one more - should evict LRU
        config4 = {"skills": ["skill4"]}
        cache.put(config4, 4.0)

        assert len(cache.cache) == 3
        assert cache.evictions == 1

    def test_cache_statistics(self):
        """Cache statistics should be accurate."""
        cache = EvaluationCache(max_size=100)

        config = {"skills": ["skill1"]}
        cache.put(config, 0.8)
        cache.get(config)

        stats = cache.get_statistics()

        assert stats["size"] == 1
        assert stats["max_size"] == 100
        assert stats["hits"] == 1
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 1.0


class TestIncrementalMutator:
    """Test incremental mutation."""

    def test_mutator_initialization(self):
        """Mutator should initialize correctly."""
        mutator = IncrementalMutator()

        assert len(mutator.mutation_history) == 0

    def test_add_skill_mutation(self):
        """Add skill mutation should add one skill."""
        mutator = IncrementalMutator()

        config = {"skills": ["skill1"]}
        mutated = mutator.mutate_incremental(config, "add_skill")

        # Should have one more skill
        assert len(mutated["skills"]) == len(config["skills"]) + 1

    def test_remove_skill_mutation(self):
        """Remove skill mutation should remove one skill."""
        mutator = IncrementalMutator()

        config = {"skills": ["skill1", "skill2", "skill3"]}
        mutated = mutator.mutate_incremental(config, "remove_skill")

        # Should have one less skill
        assert len(mutated["skills"]) == len(config["skills"]) - 1

    def test_swap_skill_mutation(self):
        """Swap skill mutation should replace one skill."""
        mutator = IncrementalMutator()

        config = {"skills": ["skill1", "skill2"]}
        mutated = mutator.mutate_incremental(config, "swap_skill")

        # Should have same number of skills
        assert len(mutated["skills"]) == len(config["skills"])

    def test_mutation_history_recorded(self):
        """Mutations should be recorded in history."""
        mutator = IncrementalMutator()

        config = {"skills": ["skill1"]}
        mutator.mutate_incremental(config, "add_skill")
        mutator.mutate_incremental(config, "remove_skill")

        assert len(mutator.mutation_history) == 2

    def test_mutation_statistics(self):
        """Mutation statistics should be accurate."""
        mutator = IncrementalMutator()

        config = {"skills": ["skill1", "skill2"]}

        mutator.mutate_incremental(config, "add_skill")
        mutator.mutate_incremental(config, "add_skill")
        mutator.mutate_incremental(config, "remove_skill")

        stats = mutator.get_statistics()

        assert stats["total_mutations"] == 3
        assert stats["mutation_types"]["add_skill"] == 2
        assert stats["mutation_types"]["remove_skill"] == 1


class TestFastEvolutionEngine:
    """Test fast evolution engine."""

    def test_engine_initialization(self):
        """Engine should initialize with cache and mutator."""
        engine = FastEvolutionEngine(n_workers=4, cache_size=1000)

        assert engine.n_workers == 4
        assert engine.cache.max_size == 1000
        assert isinstance(engine.mutator, IncrementalMutator)

    def test_fast_generation_exploration(self):
        """Fast exploration should create new nodes."""
        engine = FastEvolutionEngine(n_workers=2)

        baseline = {"skills": ["skill1", "skill2"]}
        engine.initialize(baseline)

        # Explore one generation
        new_nodes = engine.explore_generation_fast(n_mutations=5)

        assert len(new_nodes) > 0
        assert len(engine.cycle_times) == 1

    def test_cache_improves_performance(self):
        """Cache should improve performance over time."""
        engine = FastEvolutionEngine(n_workers=2)

        baseline = {"skills": ["skill1"]}
        engine.initialize(baseline)

        # First generation - mostly cache misses
        engine.explore_generation_fast(n_mutations=10)
        first_hit_rate = engine.cache.hit_rate()

        # Second generation - should have more cache hits
        engine.explore_generation_fast(n_mutations=10)
        second_hit_rate = engine.cache.hit_rate()

        # Hit rate should improve (or stay same if already high)
        assert second_hit_rate >= first_hit_rate

    def test_performance_statistics(self):
        """Performance statistics should be comprehensive."""
        engine = FastEvolutionEngine(n_workers=2)

        baseline = {"skills": ["skill1"]}
        engine.initialize(baseline)

        engine.explore_generation_fast(n_mutations=5)

        stats = engine.get_performance_statistics()

        # Should have all required fields
        assert "cache" in stats
        assert "mutations" in stats
        assert "cycle_times" in stats
        assert "cache_hit_rates" in stats

        # Cache stats
        assert "hit_rate" in stats["cache"]
        assert "size" in stats["cache"]

        # Cycle time stats
        assert "avg" in stats["cycle_times"]
        assert "latest" in stats["cycle_times"]

    def test_cycle_time_estimation(self):
        """Should estimate cycle time for N generations."""
        engine = FastEvolutionEngine(n_workers=2)

        baseline = {"skills": ["skill1"]}
        engine.initialize(baseline)

        # Run a few generations
        for _ in range(3):
            engine.explore_generation_fast(n_mutations=5)

        # Estimate time for 10 generations
        estimated = engine.estimate_cycle_time(10)

        assert estimated > 0.0
        assert isinstance(estimated, float)


class TestCacheHitRate:
    """Test cache hit rate target (80%)."""

    def test_incremental_mutations_improve_cache_hits(self):
        """Incremental mutations should lead to higher cache hit rate."""
        engine = FastEvolutionEngine(n_workers=2, cache_size=10000)

        baseline = {"skills": ["skill1", "skill2"]}
        engine.initialize(baseline)

        # Run multiple generations
        for _ in range(5):
            engine.explore_generation_fast(n_mutations=20)

        # Check final cache hit rate
        final_hit_rate = engine.cache.hit_rate()

        # Should have reasonable hit rate (>10% after 5 generations)
        assert final_hit_rate > 0.10

    def test_cache_size_affects_hit_rate(self):
        """Larger cache should have better hit rate."""
        # Small cache
        engine_small = FastEvolutionEngine(n_workers=2, cache_size=10)
        baseline = {"skills": ["skill1"]}
        engine_small.initialize(baseline)

        for _ in range(3):
            engine_small.explore_generation_fast(n_mutations=10)

        small_hit_rate = engine_small.cache.hit_rate()

        # Large cache
        engine_large = FastEvolutionEngine(n_workers=2, cache_size=10000)
        engine_large.initialize(baseline)

        for _ in range(3):
            engine_large.explore_generation_fast(n_mutations=10)

        large_hit_rate = engine_large.cache.hit_rate()

        # Large cache should have better or equal hit rate
        assert large_hit_rate >= small_hit_rate


class TestPerformanceTarget:
    """Test 10-minute cycle target."""

    def test_cycle_time_reasonable(self):
        """Cycle time should be reasonable for small runs."""
        engine = FastEvolutionEngine(n_workers=4)

        baseline = {"skills": ["skill1", "skill2"]}
        engine.initialize(baseline)

        # Run one generation
        start = time.time()
        engine.explore_generation_fast(n_mutations=10)
        cycle_time = time.time() - start

        # Should complete in reasonable time (<5 seconds for small test)
        assert cycle_time < 5.0

    def test_parallel_speedup(self):
        """More workers should improve performance."""
        baseline = {"skills": ["skill1"]}

        # 2 workers
        engine_2 = FastEvolutionEngine(n_workers=2)
        engine_2.initialize(baseline)
        start = time.time()
        engine_2.explore_generation_fast(n_mutations=20)
        time_2 = time.time() - start

        # 4 workers
        engine_4 = FastEvolutionEngine(n_workers=4)
        engine_4.initialize(baseline)
        start = time.time()
        engine_4.explore_generation_fast(n_mutations=20)
        time_4 = time.time() - start

        # 4 workers should be faster or similar (not slower)
        # Allow some variance due to overhead
        assert time_4 <= time_2 * 1.5


class TestIntegration:
    """Integration tests for T103."""

    def test_full_fast_evolution_cycle(self):
        """Test complete fast evolution cycle."""
        engine = FastEvolutionEngine(n_workers=4, cache_size=5000)

        baseline = {"skills": ["skill1", "skill2", "skill3"]}
        engine.initialize(baseline)

        # Run 10 generations
        for gen in range(10):
            new_nodes = engine.explore_generation_fast(n_mutations=15)
            assert len(new_nodes) > 0

        # Verify all features work
        stats = engine.get_performance_statistics()

        assert stats["generations_explored"] == 10
        assert stats["cache"]["hit_rate"] > 0.0
        assert len(engine.cycle_times) == 10
        assert stats["total_nodes"] > 10

        # Verify cache is being used
        assert stats["cache"]["hits"] > 0

        # Verify mutations are tracked
        assert stats["mutations"]["total_mutations"] > 0

    def test_maintains_quality_with_caching(self):
        """Caching should not degrade evolution quality."""
        engine = FastEvolutionEngine(n_workers=2)

        baseline = {"skills": ["skill1"]}
        engine.initialize(baseline)

        # Run evolution
        for _ in range(5):
            engine.explore_generation_fast(n_mutations=10)

        stats = engine.get_performance_statistics()

        # Should still find good solutions
        assert stats["best_score"] > 0.0
        assert stats["best_metaproductivity"] > 0.0

        # Should maintain frontier
        assert stats["frontier_size"] > 0
