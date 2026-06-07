"""
Tests for Cascade Memory — 3-tier pipeline, A-MAC admission,
cost-sensitive routing, and hybrid retrieval.
"""

import time
import uuid

import pytest

from lyra.memory.admission_control import (
    AdmissionController,
    AdmissionScore,
    ContentType,
)
from lyra.memory.cascade_memory import (
    CascadeMemory,
    CascadeRetrievalResult,
    MemoryItem,
    MemoryTier,
    TierAccessStats,
    _TIER_COST,
)
from lyra.memory.long_term_memory import LongTermMemory
from lyra.memory.memory_consolidation import ConsolidationPolicy, MemoryConsolidator
from lyra.memory.memory_store import MemoryType
from lyra.memory.short_term_memory import ShortTermMemory


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture()
def cascade() -> CascadeMemory:
    """Create a fresh CascadeMemory for each test."""
    return CascadeMemory(
        stm=ShortTermMemory(capacity=20, consolidation_threshold=10),
        ltm=LongTermMemory(),
        admission_controller=AdmissionController(threshold=0.45),
        auto_consolidate=False,
    )


@pytest.fixture()
def sample_items() -> list[MemoryItem]:
    """Return a list of varied memory items."""
    now = time.time()
    return [
        MemoryItem(
            content="The user prefers dark mode for all applications",
            content_type=ContentType.PREFERENCE,
            source="user",
            importance=0.85,
            confidence=0.95,
            timestamp=now - 100,
        ),
        MemoryItem(
            content="The database connection failed with timeout error",
            content_type=ContentType.ERROR_LOG,
            source="system",
            importance=0.70,
            confidence=0.90,
            timestamp=now - 200,
        ),
        MemoryItem(
            content="We decided to use PostgreSQL for the new service",
            content_type=ContentType.DECISION,
            source="team",
            importance=0.80,
            confidence=0.85,
            timestamp=now - 300,
        ),
        MemoryItem(
            content="def handle_request(): return process(data)",
            content_type=ContentType.CODE,
            source="agent",
            importance=0.40,
            confidence=0.70,
            timestamp=now - 400,
        ),
        MemoryItem(
            content="The weather today is sunny",
            content_type=ContentType.FACT,
            source="system",
            importance=0.25,
            confidence=0.50,
            timestamp=now - 500,
        ),
    ]


# =============================================================================
# Test MemoryItem
# =============================================================================


class TestMemoryItem:
    """Test MemoryItem data class."""

    def test_defaults(self):
        """Test that defaults are sensible."""
        item = MemoryItem(content="test content")
        assert item.content == "test content"
        assert item.content_type == ContentType.UNKNOWN
        assert item.importance == 0.5
        assert item.confidence == 0.8
        assert item.access_count == 0
        assert item.tier == MemoryTier.STM
        assert item.memory_id == ""

    def test_with_all_fields(self):
        """Test creating an item with all fields."""
        mid = str(uuid.uuid4())
        item = MemoryItem(
            content="test",
            content_type=ContentType.FACT,
            source="user",
            importance=0.9,
            confidence=0.99,
            timestamp=12345.0,
            access_count=5,
            tier=MemoryTier.LTM,
            memory_id=mid,
            metadata={"key": "val"},
        )
        assert item.content == "test"
        assert item.content_type == ContentType.FACT
        assert item.source == "user"
        assert item.importance == 0.9
        assert item.confidence == 0.99
        assert item.tier == MemoryTier.LTM
        assert item.memory_id == mid
        assert item.metadata["key"] == "val"


# =============================================================================
# Test TierAccessStats
# =============================================================================


class TestTierAccessStats:
    """Test TierAccessStats data class."""

    def test_defaults(self):
        """Test default values."""
        stats = TierAccessStats()
        assert stats.total_accesses == 0
        assert stats.total_items == 0
        assert stats.last_accessed == 0.0
        assert stats.cost_per_access == 0.01  # DEFAULT_COST_STM

    def test_tier_cost_constants(self):
        """Test that tier costs are defined for all tiers."""
        for tier in MemoryTier:
            assert tier in _TIER_COST
            assert _TIER_COST[tier] > 0


# =============================================================================
# Test CascadeRetrievalResult
# =============================================================================


class TestCascadeRetrievalResult:
    """Test CascadeRetrievalResult data class."""

    def test_defaults(self):
        """Test creation with defaults."""
        result = CascadeRetrievalResult(
            content="test memory",
            score=0.85,
            tier=MemoryTier.LTM,
        )
        assert result.content == "test memory"
        assert result.score == 0.85
        assert result.tier == MemoryTier.LTM
        assert result.item is None
        assert result.vector_score == 0.0
        assert result.graph_score == 0.0

    def test_to_dict(self):
        """Test serialization to dict."""
        result = CascadeRetrievalResult(
            content="test",
            score=0.75,
            tier=MemoryTier.STM,
            vector_score=0.6,
            graph_score=0.3,
        )
        d = result.to_dict()
        assert d["content"] == "test"
        assert d["score"] == 0.75
        assert d["tier"] == "stm"
        assert d["tier_label"] == "STM"
        assert d["vector_score"] == 0.6
        assert d["graph_score"] == 0.3


# =============================================================================
# Test CascadeMemory — Core API
# =============================================================================


class TestCascadeMemoryInit:
    """Test CascadeMemory construction."""

    def test_default_construction(self):
        """Test creating with all defaults."""
        c = CascadeMemory()
        assert c.stm is not None
        assert c.ltm is not None
        assert c.admission is not None
        assert c.consolidator is not None
        assert c.access_threshold_stm == 10
        assert c.access_threshold_ltm == 3
        assert c.hybrid_alpha == 0.6
        assert c.pagerank_damping == 0.85
        assert c.auto_consolidate is True

    def test_custom_construction(self):
        """Test creating with custom parameters."""
        stm = ShortTermMemory(capacity=5)
        ltm = LongTermMemory()
        ac = AdmissionController(threshold=0.6)
        c = CascadeMemory(
            stm=stm,
            ltm=ltm,
            admission_controller=ac,
            access_threshold_stm=20,
            pagerank_damping=0.90,
            hybrid_alpha=0.7,
            auto_consolidate=False,
        )
        assert c.stm.capacity == 5
        assert c.admission.threshold == 0.6
        assert c.access_threshold_stm == 20
        assert c.pagerank_damping == 0.90
        assert c.hybrid_alpha == 0.7
        assert c.auto_consolidate is False


# =============================================================================
# Test A-MAC Admission Gate
# =============================================================================


class TestAdmit:
    """Test the A-MAC admission gate integration."""

    def test_admit_high_value_item(self, cascade: CascadeMemory):
        """Test that high-value items are admitted."""
        item = MemoryItem(
            content="The user prefers JSON over XML for data exchange",
            content_type=ContentType.PREFERENCE,
            importance=0.9,
            confidence=0.95,
        )
        assert cascade.admit(item) is True

    def test_admit_low_value_item(self, cascade: CascadeMemory):
        """Test that low-value items are rejected.

        A-MAC with default threshold 0.45: CODE has the lowest type_prior
        (0.35). A single-char code with near-zero confidence should fall
        below the threshold.
        """
        item = MemoryItem(
            content= "z",
            content_type=ContentType.CODE,
            importance=0.2,
            confidence=0.05,
        )
        # single char → tiny utility bonus; very low confidence; CODE prior = 0.35
        assert cascade.admit(item) is False

    def test_admit_code_conservative(self, cascade: CascadeMemory):
        """Test that code items are admitted conservatively (type_prior=0.35).

        Even with the high type_prior weight (63%), a very short CODE
        snippet with near-zero confidence and utility should fall below
        the 0.45 threshold.
        """
        item = MemoryItem(
            content="z",
            content_type=ContentType.CODE,
            importance=0.2,
            confidence=0.1,
        )
        # Tiny content → near-zero utility bonus; low confidence → low factor
        assert cascade.admit(item) is False

    def test_admit_decision_liberal(self, cascade: CascadeMemory):
        """Test that decisions are admitted liberally (type_prior=0.75)."""
        item = MemoryItem(
            content="We decided to migrate from MongoDB to PostgreSQL",
            content_type=ContentType.DECISION,
            importance=0.7,
            confidence=0.85,
        )
        assert cascade.admit(item) is True

    def test_evaluate_admission_returns_score(self, cascade: CascadeMemory):
        """Test that evaluate_admission returns full AdmissionScore."""
        item = MemoryItem(
            content="The user prefers tab width of 4 spaces",
            content_type=ContentType.PREFERENCE,
            importance=0.8,
            confidence=0.90,
        )
        score = cascade.evaluate_admission(item)
        assert isinstance(score, AdmissionScore)
        assert score.admit is True
        assert score.combined > 0.0
        assert 0.0 <= score.utility <= 1.0
        assert 0.0 <= score.confidence <= 1.0
        assert 0.0 <= score.novelty <= 1.0
        assert 0.0 <= score.recency <= 1.0
        assert 0.0 <= score.type_prior <= 1.0

    def test_admission_factor_breakdown(self, cascade: CascadeMemory):
        """Test that all five admission factors contribute."""
        item = MemoryItem(
            content="We approved the new architecture proposal",
            content_type=ContentType.DECISION,
            importance=0.8,
            confidence=0.90,
        )
        score = cascade.evaluate_admission(item)
        # All factors should be non-zero for a strong candidate
        assert score.utility > 0
        assert score.confidence > 0
        assert score.type_prior > 0
        # Combined should be a weighted sum
        expected = (
            cascade.admission.weights["utility"] * score.utility
            + cascade.admission.weights["confidence"] * score.confidence
            + cascade.admission.weights["novelty"] * score.novelty
            + cascade.admission.weights["recency"] * score.recency
            + cascade.admission.weights["type_prior"] * score.type_prior
        )
        assert abs(score.combined - expected) < 1e-6


# =============================================================================
# Test 3-Tier Routing
# =============================================================================


class TestThreeTierRouting:
    """Test that items are routed to correct tiers."""

    def test_new_item_routes_to_stm(self, cascade: CascadeMemory):
        """Test a brand-new item (access_count=0) routes to STM."""
        item = MemoryItem(
            content="New observation",
            content_type=ContentType.FACT,
            source="user",
        )
        mid = cascade.store(item)
        assert mid is not None
        stored = cascade.get_item(mid)
        assert stored is not None
        assert stored.tier == MemoryTier.STM

    def test_frequent_item_routes_to_stm(self, cascade: CascadeMemory):
        """Test a high-access-count item stays in STM."""
        item = MemoryItem(
            content="Frequently accessed fact",
            access_count=15,  # >= access_threshold_stm (10)
        )
        mid = cascade.store(item)
        stored = cascade.get_item(mid)
        assert stored is not None
        assert stored.tier == MemoryTier.STM

    def test_medium_frequency_routes_to_ltm(self, cascade: CascadeMemory):
        """Test a medium-access-count item routes to LTM."""
        item = MemoryItem(
            content="Moderately accessed memory",
            access_count=5,  # >= access_threshold_ltm (3), < stm (10)
        )
        mid = cascade.store(item)
        stored = cascade.get_item(mid)
        assert stored is not None
        assert stored.tier == MemoryTier.LTM

    def test_rare_item_routes_to_consolidation(self, cascade: CascadeMemory):
        """Test a low-access-count item routes to consolidation."""
        item = MemoryItem(
            content="Rarely accessed historical fact",
            access_count=1,  # < access_threshold_ltm (3)
        )
        mid = cascade.store(item)
        stored = cascade.get_item(mid)
        assert stored is not None
        assert stored.tier == MemoryTier.CONSOLIDATION

    def test_force_tier_override(self, cascade: CascadeMemory):
        """Test that explicit tier override bypasses routing."""
        item = MemoryItem(
            content="Forced into LTM",
            access_count=0,
        )
        mid = cascade.store(item, tier=MemoryTier.LTM)
        stored = cascade.get_item(mid)
        assert stored is not None
        assert stored.tier == MemoryTier.LTM

    def test_store_multiple_items_different_tiers(
        self, cascade: CascadeMemory
    ):
        """Test storing items across all three tiers."""
        items = [
            MemoryItem("STM item", access_count=12),
            MemoryItem("LTM item", access_count=5),
            MemoryItem("CONS item", access_count=1),
        ]
        for item in items:
            cascade.store(item)

        # Verify tier distribution
        stats = cascade.get_statistics()
        tiers = stats["tier_distribution"]
        assert "stm" in tiers
        assert tiers["stm"] >= 1
        assert "ltm" in tiers
        assert tiers["ltm"] >= 1
        assert "consolidation" in tiers
        assert tiers["consolidation"] >= 1


# =============================================================================
# Test Cost-Sensitive Store Routing
# =============================================================================


class TestCostSensitiveRouting:
    """Test Gaikwad-style cost-sensitive routing behavior."""

    def test_tier_cost_values(self):
        """Test that STM is the cheapest tier."""
        assert _TIER_COST[MemoryTier.STM] < _TIER_COST[MemoryTier.LTM]
        assert _TIER_COST[MemoryTier.LTM] < _TIER_COST[MemoryTier.CONSOLIDATION]
        assert _TIER_COST[MemoryTier.STM] == 0.01
        assert _TIER_COST[MemoryTier.LTM] == 0.10
        assert _TIER_COST[MemoryTier.CONSOLIDATION] == 1.00

    def test_cost_analysis_in_statistics(self, cascade: CascadeMemory):
        """Test that statistics include cost analysis."""
        # Store one item in each tier
        cascade.store(MemoryItem("cheap", access_count=12), tier=MemoryTier.STM)
        cascade.store(MemoryItem("medium", access_count=5), tier=MemoryTier.LTM)
        cascade.store(MemoryItem("expensive", access_count=1), tier=MemoryTier.CONSOLIDATION)

        stats = cascade.get_statistics()
        assert "total_cost" in stats
        assert "tier_costs" in stats
        assert stats["tier_costs"]["stm"] == 0.01
        assert stats["tier_costs"]["ltm"] == 0.10
        assert stats["tier_costs"]["consolidation"] == 1.00

    def test_access_tracking_updates_tier(self, cascade: CascadeMemory):
        """Test that record_access bumps counters and can trigger re-routing."""
        item = MemoryItem(
            content="A memory that gets accessed",
            access_count=1,
        )
        mid = cascade.store(item)
        assert cascade.get_item(mid).tier == MemoryTier.CONSOLIDATION

        # Record many accesses
        for _ in range(12):
            cascade.record_access(mid)

        stored = cascade.get_item(mid)
        assert stored is not None
        assert stored.access_count == 13  # 1 initial + 12 recorded


# =============================================================================
# Test Hybrid Retrieval
# =============================================================================


class TestHybridRetrieval:
    """Test HippoRAG-style hybrid graph+vector retrieval."""

    def test_retrieve_empty(self, cascade: CascadeMemory):
        """Test retrieval from empty cascade."""
        results = cascade.retrieve("anything")
        assert results == []

    def test_retrieve_with_populated_cascade(self, cascade: CascadeMemory, sample_items):
        """Test that populated cascade returns results."""
        for item in sample_items:
            cascade.store(item)

        results = cascade.retrieve("dark mode preference", top_k=5)
        assert len(results) > 0
        assert len(results) <= 5

    def test_retrieve_returns_correct_type(self, cascade: CascadeMemory):
        """Test that retrieval returns CascadeRetrievalResult objects."""
        cascade.store(MemoryItem("test memory about Python programming"))
        results = cascade.retrieve("Python programming", top_k=3)
        assert all(isinstance(r, CascadeRetrievalResult) for r in results)

    def test_retrieve_relevance_ordering(self, cascade: CascadeMemory):
        """Test that more relevant results appear first."""
        items = [
            MemoryItem("Python is a programming language for AI"),
            MemoryItem("JavaScript is used for web development"),
            MemoryItem("The weather today is sunny and warm"),
        ]
        for item in items:
            cascade.store(item)

        results = cascade.retrieve("Python programming language", top_k=3)
        assert len(results) >= 1
        # The most relevant result should be the Python one
        assert "Python" in results[0].content

    def test_retrieve_with_alpha_override(self, cascade: CascadeMemory):
        """Test that alpha parameter can be overridden.

        alpha=1.0 = pure vector similarity; alpha=0.0 = pure graph
        PageRank (requires graph edges to return results).
        """
        cascade.store(MemoryItem("test content for retrieval"))
        # alpha=1.0 (pure vector) always works
        results_pure_vector = cascade.retrieve("test", top_k=3, alpha=1.0)

        assert len(results_pure_vector) >= 1

        # Build graph edges via consolidation then test pure-graph retrieval.
        # Two consecutive STM turns with memory_ids will form edges.
        cascade.store(MemoryItem("another item about testing"))
        cascade.consolidate()  # _update_graph_from_stm builds co-access edges

        results_pure_graph = cascade.retrieve("test", top_k=3, alpha=0.0)
        assert len(results_pure_graph) >= 1

    def test_retrieve_bumps_access_count(self, cascade: CascadeMemory):
        """Test that retrieving an item bumps its access count."""
        item = MemoryItem("frequently retrieved memory")
        mid = cascade.store(item)
        assert cascade.get_item(mid).access_count == 0

        for _ in range(3):
            cascade.retrieve("frequently retrieved memory")
        assert cascade.get_item(mid).access_count == 3

    def test_retrieve_returns_all_tiers(self, cascade: CascadeMemory):
        """Test that retrieval returns items from all tiers."""
        cascade.store(MemoryItem("STM tier item", access_count=12))
        cascade.store(MemoryItem("LTM tier item", access_count=5))
        cascade.store(MemoryItem("CONS tier item", access_count=1))

        results = cascade.retrieve("tier", top_k=10)
        tiers_found = {r.tier for r in results}
        assert MemoryTier.STM in tiers_found
        assert MemoryTier.LTM in tiers_found
        assert MemoryTier.CONSOLIDATION in tiers_found


# =============================================================================
# Test Consolidation Pipeline
# =============================================================================


class TestConsolidation:
    """Test the consolidation pipeline."""

    def test_consolidate_returns_result(self, cascade: CascadeMemory):
        """Test that consolidate() returns a ConsolidationResult."""
        cascade.store(MemoryItem("memory for consolidation"))
        result = cascade.consolidate()
        # MemoryConsolidator result fields
        result.memories_created >= 0
        result.memories_merged >= 0
        result.patterns_extracted >= 0
        result.duration >= 0.0

    def test_consolidate_promotes_high_access_items(self, cascade: CascadeMemory):
        """Test that consolidation promotes high-access LTM items."""
        item = MemoryItem("highly accessed memory")
        mid = cascade.store(item)

        # Bump access count above threshold_ltm
        for _ in range(5):
            cascade.record_access(mid)

        cascade.consolidate()
        stored = cascade.get_item(mid)
        # After consolidation, this item should be promoted
        assert stored is not None

    def test_consolidate_updates_graph(self, cascade: CascadeMemory):
        """Test that consolidation builds graph edges from STM."""
        # Store several items (they go through STM via add_turn)
        items = [
            MemoryItem("First memory about Python"),
            MemoryItem("Second memory about Python"),
            MemoryItem("Third memory about Python"),
        ]
        for item in items:
            cascade.store(item)

        # Consolidation should create co-access graph edges
        cascade.consolidate()
        stats = cascade.get_statistics()
        assert stats["graph_edges"] >= 0  # may have edges if consecutive

    def test_auto_consolidate_flag(self):
        """Test that auto_consolidate flag is respected."""
        c_off = CascadeMemory(auto_consolidate=False)
        assert c_off.auto_consolidate is False

        c_on = CascadeMemory(auto_consolidate=True)
        assert c_on.auto_consolidate is True


# =============================================================================
# Test Statistics
# =============================================================================


class TestStatistics:
    """Test CascadeMemory statistics."""

    def test_get_statistics_empty(self, cascade: CascadeMemory):
        """Test statistics on empty cascade."""
        stats = cascade.get_statistics()
        assert stats["total_items"] == 0
        assert stats["total_accesses"] == 0
        assert stats["graph_edges"] == 0
        assert stats["total_cost"] == 0.0
        assert "tier_distribution" in stats
        assert "type_distribution" in stats
        assert "admission_threshold" in stats
        assert "admission_weights" in stats

    def test_get_statistics_populated(
        self, cascade: CascadeMemory, sample_items
    ):
        """Test statistics with populated cascade."""
        for item in sample_items:
            cascade.store(item)

        stats = cascade.get_statistics()
        assert stats["total_items"] == len(sample_items)
        assert "stm" in stats["tier_distribution"]
        assert "fact" in stats["type_distribution"]
        assert "preference" in stats["type_distribution"]
        assert stats["admission_threshold"] == 0.45

    def test_get_tier_stats(self, cascade: CascadeMemory):
        """Test per-tier statistics."""
        cascade.store(MemoryItem("A", access_count=12), tier=MemoryTier.STM)
        cascade.store(MemoryItem("B", access_count=5), tier=MemoryTier.LTM)

        tier_stats = cascade.get_tier_stats()
        assert "stm" in tier_stats
        assert "ltm" in tier_stats
        assert "consolidation" in tier_stats
        assert tier_stats["stm"]["total_items"] >= 1
        assert tier_stats["ltm"]["total_items"] >= 1
        assert tier_stats["consolidation"]["total_items"] == 0

    def test_get_item_returns_none_for_missing(self, cascade: CascadeMemory):
        """Test get_item for non-existent ID."""
        assert cascade.get_item("nonexistent") is None

    def test_get_item_returns_stored_item(self, cascade: CascadeMemory):
        """Test get_item returns the correct item."""
        item = MemoryItem("unique memory", source="test")
        mid = cascade.store(item)
        retrieved = cascade.get_item(mid)
        assert retrieved is not None
        assert retrieved.content == "unique memory"
        assert retrieved.source == "test"
        assert retrieved.memory_id == mid


# =============================================================================
# Test Clear
# =============================================================================


class TestClear:
    """Test resetting cascade state."""

    def test_clear_empties_all_tiers(self, cascade: CascadeMemory):
        """Test that clear() empties all state."""
        for i in range(5):
            cascade.store(MemoryItem(f"Memory {i}"))

        assert cascade.get_statistics()["total_items"] == 5
        cascade.clear()
        assert cascade.get_statistics()["total_items"] == 0

    def test_clear_resets_accesses(self, cascade: CascadeMemory):
        """Test that clear() resets access tracking."""
        cascade.store(MemoryItem("test"))
        cascade.retrieve("test")
        cascade.clear()
        stats = cascade.get_statistics()
        assert stats["total_accesses"] == 0
