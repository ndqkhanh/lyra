"""Comprehensive tests for Field-Theoretic Memory — PDE-governed continuous memory fields."""

import time
import uuid
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from lyra.memory.field_theoretic import (
    DEFAULT_CFL_DT,
    DEFAULT_DECAY_RATE,
    DEFAULT_DIFFUSION_COEFFICIENT,
    DEFAULT_ENTROPY_WEIGHT,
    DEFAULT_SEMANTIC_DIMENSIONS,
    DEFAULT_TEMPERATURE,
    TARGET_COLLECTIVE_INTELLIGENCE,
    TARGET_KNOWLEDGE_RECALL,
    TARGET_MULTI_SESSION_F1,
    TARGET_TEMPORAL_F1,
    FieldMemory,
    FieldPoint,
    FieldState,
    _entropy,
    _internal_energy,
    _laplacian_1d,
    _pairwise_laplacian,
    couple_agent_fields,
    create_field_memory,
    free_energy,
)
from lyra.memory.memory_store import Memory, MemoryStore, MemoryType


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def field_memory():
    """Create a FieldMemory with default parameters for testing."""
    fm = FieldMemory(semantic_dimensions=8)
    return fm


@pytest.fixture
def sample_memory():
    """Create a simple Memory for testing."""
    return Memory(
        memory_id=str(uuid.uuid4()),
        content="test memory content",
        memory_type=MemoryType.EPISODIC,
        timestamp=time.time(),
        importance=0.7,
        tags=["test", "sample"],
        context={"source": "test"},
    )


@pytest.fixture
def sample_field_point():
    """Create a simple FieldPoint for testing."""
    return FieldPoint(
        point_id=str(uuid.uuid4()),
        content="field point content",
        memory_type="episodic",
        embedding=np.random.randn(8).astype(np.float32),
        importance=0.6,
        source_strength=0.3,
        created_at=time.time(),
        last_updated=time.time(),
    )


# =============================================================================
# Tests: Constants
# =============================================================================


class TestConstants:
    def test_default_values(self):
        assert DEFAULT_DIFFUSION_COEFFICIENT == 0.1
        assert DEFAULT_DECAY_RATE == 0.01
        assert DEFAULT_ENTROPY_WEIGHT == 0.3
        assert DEFAULT_TEMPERATURE == 1.0
        assert DEFAULT_SEMANTIC_DIMENSIONS == 128
        assert DEFAULT_CFL_DT == 0.01

    def test_performance_targets(self):
        assert TARGET_MULTI_SESSION_F1 == 1.16
        assert TARGET_TEMPORAL_F1 == 1.438
        assert TARGET_KNOWLEDGE_RECALL == 1.278
        assert TARGET_COLLECTIVE_INTELLIGENCE == 0.998


# =============================================================================
# Tests: Data structures
# =============================================================================


class TestFieldPoint:
    def test_default_values(self):
        fp = FieldPoint(point_id="fp1", content="test")
        assert fp.memory_type == "episodic"
        assert fp.embedding is None
        assert fp.importance == 0.5
        assert fp.source_strength == 0.0
        assert fp.metadata == {}

    def test_full_init(self):
        emb = np.array([0.1, 0.2, 0.3])
        fp = FieldPoint(
            point_id="fp2",
            content="full",
            memory_type="semantic",
            embedding=emb,
            importance=0.9,
            source_strength=0.5,
            created_at=100.0,
            last_updated=200.0,
        )
        assert fp.point_id == "fp2"
        assert fp.content == "full"
        assert np.array_equal(fp.embedding, emb)


class TestFieldState:
    def test_minimal(self):
        state = FieldState(
            timestamp=100.0,
            field_points=[],
            free_energy=0.0,
            internal_energy=0.0,
            entropy=0.0,
            total_source=0.0,
            iteration=0,
        )
        assert state.iteration == 0
        assert state.free_energy == 0.0


# =============================================================================
# Tests: Free energy
# =============================================================================


class TestInternalEnergy:
    def test_negative_importance(self):
        fp = FieldPoint(point_id="e1", content="test", importance=0.7)
        assert _internal_energy(fp) == -0.7

    def test_zero_importance(self):
        fp = FieldPoint(point_id="e2", content="test", importance=0.0)
        assert _internal_energy(fp) == 0.0


class TestEntropy:
    def test_no_embedding(self):
        fp = FieldPoint(point_id="s1", content="test")
        assert _entropy(fp) == 0.0

    def test_single_element_embedding(self):
        fp = FieldPoint(point_id="s2", content="test", embedding=np.array([1.0]))
        assert _entropy(fp) == 0.0

    def test_uniform_embedding(self):
        # Varying embedding produces non-zero entropy
        emb = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8], dtype=np.float32)
        fp = FieldPoint(point_id="s3", content="test", embedding=emb)
        entropy_val = _entropy(fp)
        assert entropy_val > 0.0

    def test_zero_vector(self):
        emb = np.zeros(8)
        fp = FieldPoint(point_id="s4", content="test", embedding=emb)
        assert _entropy(fp) == 0.0


class TestFreeEnergy:
    def test_basic_calculation(self):
        emb = np.random.randn(8).astype(np.float32)
        emb /= np.linalg.norm(emb) + 1e-12
        fp = FieldPoint(point_id="f1", content="test", embedding=emb, importance=0.5)
        fe = free_energy(fp, entropy_weight=0.3, temperature=1.0)
        # F = -0.5 + 0.3 * 1.0 * entropy
        assert fe == pytest.approx(-0.5 + 0.3 * _entropy(fp))

    def test_without_embedding(self):
        fp = FieldPoint(point_id="f2", content="test", importance=0.5)
        fe = free_energy(fp)
        assert fe == -0.5  # entropy = 0 when no embedding


# =============================================================================
# Tests: PDE operators
# =============================================================================


class TestLaplacian1D:
    def test_less_than_3_points(self):
        field = np.array([1.0, 2.0])
        result = _laplacian_1d(field)
        assert np.allclose(result, np.zeros(2))

    def test_interior_points(self):
        # Quadratic field d²f/dx² = 2
        field = np.array([1.0, 4.0, 9.0, 16.0, 25.0])  # f(x) = (x+1)² for x=0..4
        result = _laplacian_1d(field, dx=1.0)
        # d²f/dx² = 2 for x² at h=1
        np.testing.assert_allclose(result[1], 2.0, atol=1e-1)
        # Neumann: result[0] == result[1], result[-1] == result[-2]
        assert result[0] == result[1]
        assert result[-1] == result[-2]

    def test_neumann_boundary(self):
        field = np.array([1.0, 2.0, 3.0])
        result = _laplacian_1d(field)
        assert result[0] == result[1]
        assert result[-1] == result[-2]

    def test_zero_field(self):
        field = np.zeros(5)
        result = _laplacian_1d(field)
        assert np.allclose(result, np.zeros(5))


class TestPairwiseLaplacian:
    def test_less_than_2_embeddings(self):
        emb = np.random.randn(1, 4)
        result = _pairwise_laplacian(emb)
        assert np.allclose(result, np.zeros_like(emb))

    def test_two_embeddings(self):
        emb = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
        result = _pairwise_laplacian(emb, diffusion_coefficient=0.1)
        assert result.shape == emb.shape

    def test_self_similarity(self):
        emb = np.array([[1.0, 2.0], [1.0, 2.0]], dtype=np.float32)
        result = _pairwise_laplacian(emb, diffusion_coefficient=0.1)
        # Identical embeddings should have zero pairwise difference
        np.testing.assert_allclose(result, np.zeros_like(emb), atol=1e-6)

    def test_scaling_by_diffusion_coefficient(self):
        emb = np.array([[1.0, 0.0], [0.5, 0.5]], dtype=np.float32)
        r1 = _pairwise_laplacian(emb, diffusion_coefficient=0.1)
        r2 = _pairwise_laplacian(emb, diffusion_coefficient=0.2)
        np.testing.assert_allclose(r2, 2.0 * r1, atol=1e-6)


# =============================================================================
# Tests: FieldMemory — init
# =============================================================================


class TestFieldMemoryInit:
    def test_default_init(self):
        fm = FieldMemory()
        assert fm.D == DEFAULT_DIFFUSION_COEFFICIENT
        assert fm.lambd == DEFAULT_DECAY_RATE
        assert fm.dim == DEFAULT_SEMANTIC_DIMENSIONS
        assert fm.dt == DEFAULT_CFL_DT
        assert fm.agent_id is not None
        assert fm._iteration == 0
        assert fm._points == {}
        assert fm._source_buffer == []
        assert fm._coupled_fields == {}

    def test_custom_parameters(self):
        fm = FieldMemory(
            diffusion_coefficient=0.5,
            decay_rate=0.05,
            entropy_weight=0.5,
            temperature=2.0,
            semantic_dimensions=64,
            cfl_dt=0.02,
            agent_id="agent-test",
        )
        assert fm.D == 0.5
        assert fm.lambd == 0.05
        assert fm.lambda_S == 0.5
        assert fm.T == 2.0
        assert fm.dim == 64
        assert fm.dt == 0.02
        assert fm.agent_id == "agent-test"

    def test_with_store(self):
        store = MemoryStore()
        fm = FieldMemory(store=store)
        assert fm.store is store

    def test_auto_agent_id(self):
        fm1 = FieldMemory()
        fm2 = FieldMemory()
        assert fm1.agent_id != fm2.agent_id


# =============================================================================
# Tests: FieldMemory — core operations
# =============================================================================


class TestProjectToField:
    def test_returns_field_point(self, field_memory, sample_memory):
        fp = field_memory.project_to_field(sample_memory)
        assert isinstance(fp, FieldPoint)
        assert fp.point_id == sample_memory.memory_id
        assert fp.content == sample_memory.content
        assert fp.memory_type == MemoryType.EPISODIC.value

    def test_embedding_is_normalized(self, field_memory, sample_memory):
        fp = field_memory.project_to_field(sample_memory)
        norm = np.linalg.norm(fp.embedding)
        assert norm == pytest.approx(1.0, abs=1e-5)

    def test_embedding_has_correct_dim(self, field_memory, sample_memory):
        fp = field_memory.project_to_field(sample_memory)
        assert fp.embedding.shape == (field_memory.dim,)

    def test_source_strength_from_importance(self, field_memory, sample_memory):
        fp = field_memory.project_to_field(sample_memory)
        assert fp.source_strength == sample_memory.importance * 0.5

    def test_preserves_tags_in_metadata(self, field_memory, sample_memory):
        fp = field_memory.project_to_field(sample_memory)
        assert fp.metadata["tags"] == sample_memory.tags
        assert fp.metadata["context"] == sample_memory.context

    def test_deterministic_from_content(self, field_memory):
        """Same content should produce similar random projection."""
        m1 = Memory(
            memory_id="id1", content="fixed content", memory_type=MemoryType.EPISODIC,
            timestamp=time.time(),
        )
        m2 = Memory(
            memory_id="id2", content="fixed content", memory_type=MemoryType.EPISODIC,
            timestamp=time.time(),
        )
        fp1 = field_memory.project_to_field(m1)
        fp2 = field_memory.project_to_field(m2)
        # Same content -> same hash -> same random seed -> same embedding
        np.testing.assert_allclose(fp1.embedding, fp2.embedding, atol=1e-6)


class TestAddMemory:
    def test_adds_to_points(self, field_memory, sample_memory):
        fp = field_memory.add_memory(sample_memory)
        assert fp.point_id in field_memory._points
        assert field_memory._points[fp.point_id] is fp

    def test_adds_to_source_buffer(self, field_memory, sample_memory):
        fp = field_memory.add_memory(sample_memory)
        assert fp in field_memory._source_buffer

    def test_persists_to_store(self, field_memory, sample_memory):
        field_memory.add_memory(sample_memory)
        all_stored = field_memory.store.get_all()
        assert len(all_stored) == 1
        assert all_stored[0].content == sample_memory.content

    def test_returns_field_point(self, field_memory, sample_memory):
        fp = field_memory.add_memory(sample_memory)
        assert isinstance(fp, FieldPoint)
        assert fp.importance == sample_memory.importance

    def test_store_has_field_point_metadata(self, field_memory, sample_memory):
        fp = field_memory.add_memory(sample_memory)
        stored = field_memory.store.get_all()[0]
        assert stored is not None
        assert stored.context.get("field_point_id") == fp.point_id
        assert "free_energy" in stored.context
        assert stored.context.get("field_iteration") == 0


class TestGetFieldPoint:
    def test_existing(self, field_memory, sample_memory):
        fp = field_memory.add_memory(sample_memory)
        assert field_memory.get_field_point(fp.point_id) is fp

    def test_nonexistent(self, field_memory):
        assert field_memory.get_field_point("nonexistent") is None


class TestGetAllPoints:
    def test_empty(self, field_memory):
        assert field_memory.get_all_points() == []

    def test_with_points(self, field_memory, sample_memory):
        field_memory.add_memory(sample_memory)
        assert len(field_memory.get_all_points()) == 1

    def test_multiple(self, field_memory):
        for i in range(3):
            m = Memory(
                memory_id=f"multi{i}", content=f"mem{i}", memory_type=MemoryType.EPISODIC,
                timestamp=time.time(),
            )
            field_memory.add_memory(m)
        assert len(field_memory.get_all_points()) == 3


class TestRemovePoint:
    def test_remove_existing(self, field_memory, sample_memory):
        fp = field_memory.add_memory(sample_memory)
        assert field_memory.remove_point(fp.point_id) is True
        assert fp.point_id not in field_memory._points

    def test_remove_nonexistent(self, field_memory):
        assert field_memory.remove_point("nonexistent") is False


# =============================================================================
# Tests: FieldMemory — PDE step
# =============================================================================


class TestStep:
    def test_empty_field_returns_state(self, field_memory):
        state = field_memory.step()
        assert isinstance(state, FieldState)
        assert state.free_energy == 0.0
        assert state.internal_energy == 0.0
        assert state.entropy == 0.0

    def test_step_with_points(self, field_memory, sample_memory):
        field_memory.add_memory(sample_memory)
        state = field_memory.step()
        assert state.field_points is not None
        assert len(state.field_points) >= 1

    def test_step_increments_iteration(self, field_memory, sample_memory):
        field_memory.add_memory(sample_memory)
        field_memory.step()
        assert field_memory._iteration == 1

    def test_step_clears_source_buffer(self, field_memory, sample_memory):
        field_memory.add_memory(sample_memory)
        assert len(field_memory._source_buffer) == 1
        field_memory.step()
        assert len(field_memory._source_buffer) == 0

    def test_step_with_external_source(self, field_memory, sample_memory):
        fp = field_memory.add_memory(sample_memory)
        ext_point = FieldPoint(
            point_id=fp.point_id,
            content="external",
            memory_type="episodic",
            embedding=fp.embedding.copy(),
            importance=0.8,
            source_strength=0.5,
            created_at=time.time(),
            last_updated=time.time(),
        )
        state = field_memory.step(source_points=[ext_point])
        assert state.total_source > 0

    def test_step_with_new_external_point(self, field_memory, sample_memory):
        # First add an existing point so step() doesn't return early
        field_memory.add_memory(sample_memory)
        new_fp = FieldPoint(
            point_id="new_ext",
            content="new external",
            memory_type="episodic",
            embedding=np.random.randn(field_memory.dim).astype(np.float32),
            importance=0.5,
            source_strength=0.5,
            created_at=time.time(),
            last_updated=time.time(),
        )
        state = field_memory.step(source_points=[new_fp])
        assert "new_ext" in field_memory._points


class TestConsolidate:
    def test_convergence(self, field_memory, sample_memory):
        field_memory.add_memory(sample_memory)
        state = field_memory.consolidate(num_steps=50, convergence_threshold=1e-3)
        assert state is not None
        assert state.iteration > 0

    def test_without_points(self, field_memory):
        state = field_memory.consolidate(num_steps=10)
        assert state is not None

    def test_prunes_decayed_points(self, field_memory, sample_memory):
        m_low = Memory(
            memory_id="low_imp", content="low", memory_type=MemoryType.EPISODIC,
            timestamp=time.time(), importance=0.01,
        )
        field_memory.add_memory(sample_memory)
        field_memory.add_memory(m_low)
        field_memory.consolidate(num_steps=5)
        assert "low_imp" not in field_memory._points
        assert sample_memory.memory_id in field_memory._points


class TestPruneDecayed:
    def test_removes_low_importance(self, field_memory):
        m1 = _make_field_point("keep_me", importance=0.5)
        m2 = _make_field_point("remove_me", importance=0.01)
        field_memory._points = {m1.point_id: m1, m2.point_id: m2}
        field_memory._prune_decayed(min_importance=0.05)
        assert "keep_me" in field_memory._points
        assert "remove_me" not in field_memory._points

    def test_empty(self, field_memory):
        field_memory._prune_decayed()
        assert len(field_memory._points) == 0


def _make_field_point(point_id: str, importance: float = 0.5) -> FieldPoint:
    return FieldPoint(
        point_id=point_id,
        content="content",
        memory_type="episodic",
        embedding=np.random.randn(8).astype(np.float32),
        importance=importance,
        source_strength=0.0,
        created_at=time.time(),
        last_updated=time.time(),
    )


# =============================================================================
# Tests: FieldMemory — retrieval
# =============================================================================


class TestRecallBySimilarity:
    def test_empty_field(self, field_memory):
        query = np.random.randn(field_memory.dim).astype(np.float32)
        results = field_memory.recall_by_similarity(query)
        assert results == []

    def test_returns_scored_results(self, field_memory):
        m = Memory(
            memory_id="recall1", content="test", memory_type=MemoryType.EPISODIC,
            timestamp=time.time(), importance=0.8,
        )
        field_memory.add_memory(m)
        query = np.random.randn(field_memory.dim).astype(np.float32)
        results = field_memory.recall_by_similarity(query, top_k=5)
        assert len(results) == 1
        point, score = results[0]
        assert point.point_id == "recall1"
        assert isinstance(score, float)

    def test_top_k_limit(self, field_memory):
        for i in range(10):
            m = Memory(
                memory_id=f"lim{i}", content=f"mem{i}", memory_type=MemoryType.EPISODIC,
                timestamp=time.time(), importance=0.5,
            )
            field_memory.add_memory(m)
        query = np.random.randn(field_memory.dim).astype(np.float32)
        results = field_memory.recall_by_similarity(query, top_k=3)
        assert len(results) == 3

    def test_sorted_by_score(self, field_memory):
        for i in range(5):
            m = Memory(
                memory_id=f"sorted{i}", content=f"mem{i}", memory_type=MemoryType.EPISODIC,
                timestamp=time.time(), importance=0.5,
            )
            field_memory.add_memory(m)
        query = np.random.randn(field_memory.dim).astype(np.float32)
        results = field_memory.recall_by_similarity(query)
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    def test_importance_weighting(self, field_memory):
        m_high = Memory(
            memory_id="high_imp", content="high", memory_type=MemoryType.EPISODIC,
            timestamp=time.time(), importance=0.9,
        )
        m_low = Memory(
            memory_id="low_imp", content="low", memory_type=MemoryType.EPISODIC,
            timestamp=time.time(), importance=0.1,
        )
        fp_high = field_memory.add_memory(m_high)
        fp_low = field_memory.add_memory(m_low)
        # Use fp_high's embedding as query to get similarity
        results = field_memory.recall_by_similarity(fp_high.embedding, top_k=5)
        ids = [p.point_id for p, _ in results]
        assert "high_imp" in ids


class TestRecallByContent:
    def test_returns_results(self, field_memory):
        m = Memory(
            memory_id="rb1", content="test", memory_type=MemoryType.EPISODIC,
            timestamp=time.time(), importance=0.5,
        )
        field_memory.add_memory(m)
        results = field_memory.recall_by_content("test", top_k=5)
        assert len(results) == 1

    def test_empty_field(self, field_memory):
        results = field_memory.recall_by_content("anything")
        assert results == []

    def test_invalid_query_still_returns(self, field_memory):
        m = Memory(
            memory_id="rb2", content="data", memory_type=MemoryType.EPISODIC,
            timestamp=time.time(), importance=0.5,
        )
        field_memory.add_memory(m)
        results = field_memory.recall_by_content("")
        assert len(results) >= 1


# =============================================================================
# Tests: FieldMemory — multi-agent coupling
# =============================================================================


class TestCoupleField:
    def test_coupling_adds_to_coupled_fields(self, field_memory):
        other = FieldMemory(semantic_dimensions=8, agent_id="other-agent")
        field_memory.couple_field(other, coupling_strength=0.1)
        assert "other-agent" in field_memory._coupled_fields

    def test_coupling_exchanges_points(self, field_memory):
        other = FieldMemory(semantic_dimensions=8, agent_id="couple-agent")
        m = Memory(
            memory_id="couple1", content="shared", memory_type=MemoryType.EPISODIC,
            timestamp=time.time(), importance=0.5,
        )
        other.add_memory(m)
        field_memory.couple_field(other, coupling_strength=0.1)
        assert "couple-agent" in field_memory._coupled_fields

    def test_coupling_with_no_common_points(self, field_memory):
        other = FieldMemory(semantic_dimensions=8, agent_id="no-common")
        field_memory.couple_field(other)  # Should not crash
        assert "no-common" in field_memory._coupled_fields


class TestDecoupleField:
    def test_removes_coupled_field(self, field_memory):
        field_memory._coupled_fields["agent-x"] = []
        field_memory.decouple_field("agent-x")
        assert "agent-x" not in field_memory._coupled_fields

    def test_nonexistent_agent(self, field_memory):
        field_memory.decouple_field("nonexistent")  # Should not raise


class TestGetCoupledAgents:
    def test_empty(self, field_memory):
        assert field_memory.get_coupled_agents() == []

    def test_with_coupled(self, field_memory):
        field_memory._coupled_fields["a1"] = []
        field_memory._coupled_fields["a2"] = []
        agents = field_memory.get_coupled_agents()
        assert "a1" in agents
        assert "a2" in agents


# =============================================================================
# Tests: FieldMemory — importance tuning
# =============================================================================


class TestAdjustImportance:
    def test_increases_importance(self, field_memory, sample_memory):
        fp = field_memory.add_memory(sample_memory)
        field_memory.adjust_importance(fp.point_id, delta=0.2)
        assert fp.importance == pytest.approx(0.9)

    def test_decreases_importance(self, field_memory, sample_memory):
        fp = field_memory.add_memory(sample_memory)
        field_memory.adjust_importance(fp.point_id, delta=-0.3)
        assert fp.importance == pytest.approx(0.4)

    def test_clamps_to_zero(self, field_memory, sample_memory):
        fp = field_memory.add_memory(sample_memory)
        field_memory.adjust_importance(fp.point_id, delta=-2.0)
        assert fp.importance == 0.0

    def test_clamps_to_one(self, field_memory, sample_memory):
        fp = field_memory.add_memory(sample_memory)
        field_memory.adjust_importance(fp.point_id, delta=2.0)
        assert fp.importance == 1.0

    def test_nonexistent_point(self, field_memory):
        field_memory.adjust_importance("nonexistent", 0.5)  # Should not raise

    def test_updates_timestamp(self, field_memory, sample_memory):
        fp = field_memory.add_memory(sample_memory)
        old_ts = fp.last_updated
        field_memory.adjust_importance(fp.point_id, delta=0.1)
        assert fp.last_updated >= old_ts


class TestBoostRecall:
    def test_boosts_source_strength(self, field_memory, sample_memory):
        fp = field_memory.add_memory(sample_memory)
        original = fp.source_strength
        field_memory.boost_recall(fp.point_id)
        assert fp.source_strength > original

    def test_boosts_importance(self, field_memory, sample_memory):
        fp = field_memory.add_memory(sample_memory)
        original = fp.importance
        field_memory.boost_recall(fp.point_id)
        assert fp.importance > original

    def test_clamps_source_strength(self, field_memory, sample_memory):
        fp = field_memory.add_memory(sample_memory)
        fp.source_strength = 0.95
        field_memory.boost_recall(fp.point_id)
        assert fp.source_strength <= 1.0

    def test_nonexistent_point(self, field_memory):
        field_memory.boost_recall("nonexistent")  # Should not raise


# =============================================================================
# Tests: FieldMemory — statistics
# =============================================================================


class TestFieldStatistics:
    def test_empty(self, field_memory):
        stats = field_memory.get_field_statistics()
        assert stats["total_points"] == 0
        assert stats["avg_importance"] == 0.0
        assert stats["avg_free_energy"] == 0.0

    def test_with_points(self, field_memory, sample_memory):
        field_memory.add_memory(sample_memory)
        stats = field_memory.get_field_statistics()
        assert stats["total_points"] == 1
        assert stats["avg_importance"] > 0
        assert stats["source_buffer_size"] == 1  # not yet stepped

    def test_performance_targets_in_stats(self, field_memory):
        stats = field_memory.get_field_statistics()
        assert stats["performance_targets"]["multi_session_f1_gain"] == TARGET_MULTI_SESSION_F1
        assert stats["performance_targets"]["temporal_f1_gain"] == TARGET_TEMPORAL_F1
        assert stats["performance_targets"]["knowledge_recall_gain"] == TARGET_KNOWLEDGE_RECALL
        assert stats["performance_targets"]["collective_intelligence"] == TARGET_COLLECTIVE_INTELLIGENCE

    def test_agent_id(self, field_memory):
        stats = field_memory.get_field_statistics()
        assert stats["agent_id"] == field_memory.agent_id

    def test_coupled_agents_count(self, field_memory):
        field_memory._coupled_fields["a1"] = []
        stats = field_memory.get_field_statistics()
        assert stats["coupled_agents"] == 1


# =============================================================================
# Tests: Convenience functions
# =============================================================================


class TestCreateFieldMemory:
    def test_creates_with_defaults(self):
        fm = create_field_memory()
        assert isinstance(fm, FieldMemory)
        assert fm.D == DEFAULT_DIFFUSION_COEFFICIENT

    def test_creates_with_overrides(self):
        fm = create_field_memory(diffusion_coefficient=0.99, semantic_dimensions=16)
        assert fm.D == 0.99
        assert fm.dim == 16

    def test_with_store(self):
        store = MemoryStore()
        fm = create_field_memory(store=store)
        assert fm.store is store

    def test_with_agent_id(self):
        fm = create_field_memory(agent_id="my-agent")
        assert fm.agent_id == "my-agent"


class TestCoupleAgentFields:
    def test_single_field(self):
        fm = FieldMemory(semantic_dimensions=8, agent_id="single")
        result = couple_agent_fields([fm])
        assert result is fm

    def test_couples_pairs(self):
        fa = FieldMemory(semantic_dimensions=8, agent_id="a")
        fb = FieldMemory(semantic_dimensions=8, agent_id="b")
        result = couple_agent_fields([fa, fb], coupling_strength=0.2)
        assert result is fa
        assert "b" in fa._coupled_fields
        assert "a" in fb._coupled_fields

    def test_couples_three_agents(self):
        agents = [
            FieldMemory(semantic_dimensions=4, agent_id=f"g{i}")
            for i in range(3)
        ]
        couple_agent_fields(agents, coupling_strength=0.1)
        for i, a in enumerate(agents):
            # Each agent should be coupled to all others
            expected = 2  # 2 other agents
            assert len(a._coupled_fields) == expected

    def test_empty_list_raises(self):
        with pytest.raises(IndexError):
            couple_agent_fields([])
