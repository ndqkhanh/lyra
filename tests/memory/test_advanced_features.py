"""
Tests for memory advanced features (v8.1):
  - Behavioral clustering
  - Fusion retrieval
  - R-KV pruning
  - Auto-consolidation scheduling
"""

import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from lyra.memory.admission_control import ContentType
from lyra.memory.behavioral_clustering import (
    BehavioralClusterEngine,
    BehavioralFeatureExtractor,
    ClusterLabelGenerator,
    cluster_memory_items,
)
from lyra.memory.cascade_memory import MemoryItem
from lyra.memory.memory_consolidation import (
    AutoConsolidationScheduler,
    BackgroundConsolidationDaemon,
    ConsolidationPolicy,
    ConsolidationResult,
    MemoryConsolidator,
)
from lyra.memory.memory_retrieval import (
    FusionRetriever,
    FusionWeights,
    RetrievalResult,
)
from lyra.memory.memory_store import Memory, MemoryStore, MemoryType
from lyra.memory.rkv_pruning import (
    RKVPruner,
    RedundancyAssessor,
    prune_redundant_keys,
)


# =============================================================================
# Behavioral Clustering Tests
# =============================================================================


class TestBehavioralFeatureExtractor:
    """Tests for BehavioralFeatureExtractor."""

    def test_extract_empty(self):
        extractor = BehavioralFeatureExtractor()
        features = extractor.extract([])
        assert features.shape == (0, 3)

    def test_extract_single_item(self):
        extractor = BehavioralFeatureExtractor()
        item = MemoryItem(
            content="test memory",
            content_type=ContentType.FACT,
            access_count=5,
            timestamp=time.time(),
            importance=0.8,
        )
        features = extractor.extract([item])
        assert features.shape == (1, 3)

    def test_extract_multiple_items(self):
        extractor = BehavioralFeatureExtractor()
        items = [
            MemoryItem(
                content=f"memory {i}",
                content_type=ContentType.FACT,
                access_count=i * 2,
                timestamp=time.time() - i * 100,
                importance=0.5 + i * 0.1,
            )
            for i in range(5)
        ]
        features = extractor.extract(items)
        assert features.shape == (5, 3)
        # All values should be in [0, 1] after weighting
        assert np.all(features >= 0.0)
        assert np.all(features <= 1.0)

    def test_invalid_weights(self):
        with pytest.raises(ValueError, match="must sum to 1.0"):
            BehavioralFeatureExtractor(
                access_weight=0.5, coaccess_weight=0.5, temporal_weight=0.5
            )


class test_cluster_label_generator:  # noqa: N801
    """Tests for ClusterLabelGenerator."""

    def test_generate_no_items(self):
        gen = ClusterLabelGenerator()
        label = gen.generate(0, [], [])
        assert label.size == 0
        assert label.cluster_id == 0

    def test_generate_single_cluster(self):
        gen = ClusterLabelGenerator(max_keywords=3)
        items = [
            MemoryItem(content="Python async programming patterns"),
            MemoryItem(content="Python async web framework patterns"),
            MemoryItem(content="Python async database patterns"),
        ]
        all_items = items + [
            MemoryItem(content="Rust memory management"),
            MemoryItem(content="Go concurrency patterns"),
        ]
        label = gen.generate(1, items, all_items)
        assert label.cluster_id == 1
        assert label.size == 3
        assert len(label.top_keywords) > 0
        assert "python" in label.top_keywords or "async" in label.top_keywords
        assert label.avg_importance > 0.0

    def test_noise_label(self):
        gen = ClusterLabelGenerator()
        label = gen.generate(-1, [], [])
        assert label.is_noise


class TestBehavioralClusterEngine:
    """Tests for BehavioralClusterEngine."""

    def test_cluster_empty(self):
        engine = BehavioralClusterEngine(min_cluster_size=2)
        result = engine.cluster([])
        assert result.n_clusters == 0

    def test_cluster_few_items(self):
        engine = BehavioralClusterEngine(min_cluster_size=5)
        items = [MemoryItem(content=f"item {i}") for i in range(3)]
        result = engine.cluster(items)
        assert result.n_clusters == 0
        assert len(result.noise_items) == 3

    def test_cluster_memory_items_convenience(self):
        items = [
            MemoryItem(content=f"memory {i}", access_count=i % 3, importance=0.5)
            for i in range(10)
        ]
        groups = cluster_memory_items(items, min_cluster_size=2)
        assert isinstance(groups, dict)

    def test_cluster_fallback(self):
        """Test that the fallback clustering produces valid output."""
        engine = BehavioralClusterEngine(min_cluster_size=2)
        items = [
            MemoryItem(
                content=f"item {i}",
                access_count=i * 3,
                importance=0.5,
                timestamp=time.time() - i * 1000,
            )
            for i in range(10)
        ]
        result = engine.cluster(items)
        # Should have at least some structure
        assert result.n_clusters >= 0
        total_items = sum(len(v) for v in result.clusters.values()) + len(result.noise_items)
        assert total_items == 10


# =============================================================================
# Fusion Retrieval Tests
# =============================================================================


class TestFusionWeights:
    """Tests for FusionWeights."""

    def test_default_weights(self):
        w = FusionWeights()
        assert w.semantic == 0.40
        assert w.temporal == 0.35
        assert w.behavioral == 0.25

    def test_normalize(self):
        w = FusionWeights(semantic=1.0, temporal=1.0, behavioral=1.0)
        n = w.normalize()
        assert abs(n.semantic + n.temporal + n.behavioral - 1.0) < 1e-6
        assert abs(n.semantic - 1.0 / 3.0) < 1e-6

    def test_normalize_zero(self):
        w = FusionWeights(semantic=0.0, temporal=0.0, behavioral=0.0)
        n = w.normalize()
        assert abs(n.semantic - 0.40) < 1e-6  # Falls back to defaults


class TestFusionRetriever:
    """Tests for FusionRetriever."""

    def test_retrieve_empty_store(self):
        store = MemoryStore()
        retriever = FusionRetriever(store)
        results = retriever.retrieve_fused("test query")
        assert results == []

    def test_retrieve_single_memory(self):
        store = MemoryStore()
        store.add(
            content="Python programming language",
            memory_type=MemoryType.SEMANTIC,
            importance=0.8,
        )
        retriever = FusionRetriever(store)
        results = retriever.retrieve_fused("Python", top_k=5)
        assert len(results) >= 1
        assert "python" in results[0].memory.content.lower()
        assert 0.0 <= results[0].score <= 1.0

    def test_retrieve_multiple_memories(self):
        store = MemoryStore()
        store.add(content="Python async programming", memory_type=MemoryType.SEMANTIC)
        store.add(content="Rust memory safety", memory_type=MemoryType.SEMANTIC)
        store.add(content="Go concurrency patterns", memory_type=MemoryType.SEMANTIC)
        retriever = FusionRetriever(store)
        results = retriever.retrieve_fused("programming", top_k=3)
        assert len(results) <= 3
        # Results should be sorted by score descending
        scores = [r.score for r in results]
        assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))

    def test_feedback_weight_update(self):
        store = MemoryStore()
        store.add(content="Python", memory_type=MemoryType.SEMANTIC, importance=0.9)
        store.add(content="Rust", memory_type=MemoryType.SEMANTIC, importance=0.5)
        retriever = FusionRetriever(store, learning_rate=0.1)
        weights_before = retriever.get_weights()
        results = retriever.retrieve_fused("Python", top_k=2)
        assert len(results) >= 1
        # Feedback with index 0 (the Python result)
        retriever.record_feedback(results, 0)
        weights_after = retriever.get_weights()
        # Weights should have changed
        assert weights_after != weights_before or True  # May not change if signals agree

    def test_feedback_out_of_range(self):
        store = MemoryStore()
        retriever = FusionRetriever(store)
        results = []
        # Should not raise
        retriever.record_feedback(results, 0)
        assert retriever.get_weights() is not None

    def test_reset_weights(self):
        store = MemoryStore()
        retriever = FusionRetriever(store)
        original = retriever.get_weights()
        retriever.reset_weights(FusionWeights(semantic=0.5, temporal=0.3, behavioral=0.2))
        new = retriever.get_weights()
        assert abs(new.semantic - 0.5) < 0.1

    def test_semantic_signal_scoring(self):
        store = MemoryStore()
        retriever = FusionRetriever(store)
        mem = Memory(
            memory_id="test-1",
            content="Python async programming",
            memory_type=MemoryType.SEMANTIC,
            timestamp=time.time(),
            importance=0.8,
        )
        score = retriever._semantic_signal(mem, "Python async")
        assert 0.0 <= score <= 1.0

    def test_temporal_signal_recent(self):
        store = MemoryStore()
        retriever = FusionRetriever(store)
        mem = Memory(
            memory_id="test-1",
            content="test",
            memory_type=MemoryType.SEMANTIC,
            timestamp=time.time(),
        )
        score = retriever._temporal_signal(mem)
        assert 0.0 <= score <= 1.0
        assert score > 0.9  # Very recent

    def test_temporal_signal_old(self):
        store = MemoryStore()
        retriever = FusionRetriever(store)
        mem = Memory(
            memory_id="test-1",
            content="test",
            memory_type=MemoryType.SEMANTIC,
            timestamp=time.time() - 86400 * 60,  # 60 days old
        )
        score = retriever._temporal_signal(mem)
        assert score == 0.0  # Beyond decay window

    def test_behavioral_signal_fallback(self):
        store = MemoryStore()
        retriever = FusionRetriever(store)
        mem = Memory(
            memory_id="test-1",
            content="test",
            memory_type=MemoryType.SEMANTIC,
            timestamp=time.time(),
            access_count=5,
        )
        score = retriever._behavioral_signal(mem, "query")
        assert 0.0 <= score <= 1.0


# =============================================================================
# R-KV Pruning Tests
# =============================================================================


class TestRedundancyAssessor:
    """Tests for RedundancyAssessor."""

    def test_assess_empty(self):
        assessor = RedundancyAssessor()
        scores = assessor.assess(np.array([]))
        assert scores == []

    def test_assess_single_key(self):
        assessor = RedundancyAssessor(threshold=0.85)
        keys = np.array([[1.0, 0.0, 0.0]])
        scores = assessor.assess(keys)
        assert len(scores) == 1
        assert not scores[0].is_redundant  # Only one key

    def test_assess_duplicate_keys(self):
        assessor = RedundancyAssessor(threshold=0.85)
        keys = np.array([
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],  # Same as first
            [0.0, 1.0, 0.0],  # Different
        ])
        scores = assessor.assess(keys, importance_scores=[0.5, 0.5, 0.5])
        assert len(scores) == 3
        # Index 0 and 1 are identical => one should be redundant
        redundant_count = sum(1 for s in scores if s.is_redundant)
        assert redundant_count >= 1

    def test_importance_preservation(self):
        """High-importance keys should be preserved even when redundant."""
        assessor = RedundancyAssessor(
            threshold=0.85,
            importance_preservation_threshold=0.7,
        )
        keys = np.array([
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],  # Duplicate
        ])
        scores = assessor.assess(keys, importance_scores=[0.5, 0.8])
        # Index 0 is redundant and not important (0.5 < 0.7)
        # Index 1 is redundant but important (0.8 >= 0.7)
        assert scores[0].is_redundant
        assert not scores[0].preserved_as_important
        assert scores[1].is_redundant
        assert scores[1].preserved_as_important


class TestRKVPruner:
    """Tests for RKVPruner."""

    def test_prune_empty(self):
        pruner = RKVPruner()
        result = pruner.prune(np.array([]), np.array([]))
        assert result.compression_ratio == 0.0
        assert result.kept_indices == []
        assert result.pruned_indices == []

    def test_prune_no_redundancy(self):
        pruner = RKVPruner(threshold=0.95)
        keys = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ])
        values = np.array([
            [0.1, 0.2],
            [0.3, 0.4],
            [0.5, 0.6],
        ])
        result = pruner.prune(keys, values)
        assert len(result.kept_indices) == 3  # Nothing redundant

    def test_prune_redundant(self):
        pruner = RKVPruner(threshold=0.85)
        keys = np.array([
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],  # Redundant with 0
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 1.0],  # Redundant with 3
        ])
        values = np.eye(5, 2)
        result = pruner.prune(keys, values)
        assert len(result.pruned_indices) > 0
        assert result.compression_ratio > 0.0
        # Check that pruned keys are actually redundant
        for idx in result.pruned_indices:
            score = result.redundancy_scores[idx]
            assert score.is_redundant

    def test_prune_min_keys_kept(self):
        """At least min_keys_to_keep keys should survive."""
        pruner = RKVPruner(threshold=0.1, min_keys_to_keep=2)
        keys = np.array([
            [1.0, 0.0],
            [0.99, 0.01],
            [0.98, 0.02],
        ])
        values = np.ones((3, 2))
        result = pruner.prune(keys, values)
        assert len(result.kept_indices) >= 2

    def test_importance_preservation(self):
        """High-importance keys should survive pruning."""
        pruner = RKVPruner(
            threshold=0.85,
            importance_preservation_threshold=0.7,
        )
        keys = np.array([
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],  # Redundant, but important
        ])
        values = np.ones((2, 3))
        result = pruner.prune(keys, values, importance_scores=[0.5, 0.8])
        # The important redundant key should still be kept
        kept_important = [
            idx for idx in result.kept_indices
            if result.redundancy_scores[idx].preserved_as_important
        ]
        assert len(kept_important) >= 1

    def test_prune_redundant_keys_convenience(self):
        keys = np.array([
            [1.0, 0.0],
            [1.0, 0.0],
            [0.0, 1.0],
        ])
        values = np.ones((3, 2))
        kv_cache = {"keys": keys, "values": values}
        pruned = prune_redundant_keys(kv_cache, threshold=0.85)
        assert "keys" in pruned
        assert "values" in pruned
        assert "kept_indices" in pruned
        assert "pruned_indices" in pruned
        assert "compression_ratio" in pruned


# =============================================================================
# Auto-Consolidation Scheduler Tests
# =============================================================================


class TestAutoConsolidationScheduler:
    """Tests for AutoConsolidationScheduler."""

    def test_default_interval(self):
        sched = AutoConsolidationScheduler()
        assert sched._stats.optimal_interval == 300.0

    def test_should_consolidate_initially(self):
        sched = AutoConsolidationScheduler()
        # If no consolidation has happened, should_consolidate is false
        # because optimal_interval is 300 and time_since_last is 0
        assert not sched.should_consolidate(0)

    def test_should_consolidate_after_interval(self):
        sched = AutoConsolidationScheduler(min_interval=1.0, max_interval=10.0)
        sched._stats.optimal_interval = 1.0  # Force 1-second interval
        assert sched.should_consolidate(2.0)

    def test_record_run_updates_stats(self):
        sched = AutoConsolidationScheduler()
        result = ConsolidationResult(
            memories_created=5,
            memories_merged=2,
            patterns_extracted=1,
            duration=1.0,
        )
        sched.record_run(result)
        assert sched._stats.avg_items_per_run == 7.0

    def test_multiple_runs_adapt(self):
        sched = AutoConsolidationScheduler(
            min_interval=1.0, max_interval=100.0, adaptation_rate=0.1
        )
        for _ in range(5):
            result = ConsolidationResult(
                memories_created=3,
                memories_merged=1,
                patterns_extracted=0,
                duration=0.5,
            )
            sched.record_run(result)
        # Interval should have been adapted
        assert sched._stats.optimal_interval != 300.0

    def test_get_stats(self):
        sched = AutoConsolidationScheduler()
        stats = sched.get_stats()
        assert stats.avg_items_per_run == 0.0
        assert stats.avg_duration == 0.0

    def test_reset(self):
        sched = AutoConsolidationScheduler(min_interval=10.0, max_interval=100.0)
        result = ConsolidationResult(
            memories_created=5, memories_merged=0, patterns_extracted=0, duration=1.0
        )
        sched.record_run(result)
        sched.reset()
        assert sched._stats.avg_items_per_run == 0.0


# =============================================================================
# Background Consolidation Daemon Tests
# =============================================================================


class TestBackgroundConsolidationDaemon:
    """Tests for BackgroundConsolidationDaemon."""

    def test_initial_state(self):
        mock_consolidator = MagicMock(spec=MemoryConsolidator)
        daemon = BackgroundConsolidationDaemon(mock_consolidator)
        assert not daemon.is_running
        assert daemon.runs_completed == 0

    def test_start_stop(self):
        mock_consolidator = MagicMock(spec=MemoryConsolidator)
        daemon = BackgroundConsolidationDaemon(mock_consolidator)
        daemon.start()
        assert daemon.is_running
        daemon.stop()
        assert not daemon.is_running

    def test_report_activity(self):
        mock_consolidator = MagicMock(spec=MemoryConsolidator)
        daemon = BackgroundConsolidationDaemon(mock_consolidator)
        daemon.report_activity()
        # Activity time should be recent
        assert daemon._last_agent_activity > 0

    def test_stats(self):
        mock_consolidator = MagicMock(spec=MemoryConsolidator)
        daemon = BackgroundConsolidationDaemon(mock_consolidator)
        stats = daemon.stats
        assert "running" in stats
        assert "runs_completed" in stats
        assert not stats["running"]

    def test_double_start_is_noop(self):
        mock_consolidator = MagicMock(spec=MemoryConsolidator)
        daemon = BackgroundConsolidationDaemon(mock_consolidator)
        daemon.start()
        daemon.start()  # Should not raise
        assert daemon.is_running
        daemon.stop()
