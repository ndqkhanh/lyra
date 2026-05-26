"""Tests for the Phase 2.3 Latent-Space Collaboration Bridge."""
from __future__ import annotations

import time

from lyra_core.orchestration.latent_bridge import (
    BridgeMetrics,
    ConsensusMethod,
    ConsensusSynthesizer,
    KnowledgeExchangeBus,
    LatentStateType,
    SharedLatentState,
)


class TestSharedLatentState:
    def test_publish_returns_vector(self):
        state = SharedLatentState()
        vec = state.publish(
            LatentStateType.TASK_EMBEDDING,
            (0.9, 0.1, 0.8),
            "sonnet",
        )
        assert vec.vector_id.startswith("lv-")
        assert vec.model_source == "sonnet"
        assert vec.version == 1

    def test_version_increments_on_same_type_source(self):
        state = SharedLatentState()
        v1 = state.publish(LatentStateType.TASK_EMBEDDING, (0.9,), "sonnet")
        v2 = state.publish(LatentStateType.TASK_EMBEDDING, (0.8,), "sonnet")
        assert v1.version == 1
        assert v2.version == 2

    def test_different_sources_independent_versions(self):
        state = SharedLatentState()
        v1 = state.publish(LatentStateType.TASK_EMBEDDING, (0.9,), "sonnet")
        v2 = state.publish(LatentStateType.TASK_EMBEDDING, (0.9,), "opus")
        assert v1.version == 1
        assert v2.version == 1

    def test_retrieve_filters_by_type(self):
        state = SharedLatentState()
        state.publish(LatentStateType.TASK_EMBEDDING, (0.9, 0.1), "sonnet")
        state.publish(LatentStateType.CONTEXT_EMBEDDING, (0.5, 0.5), "sonnet")
        results = state.retrieve(state_type=LatentStateType.TASK_EMBEDDING)
        assert len(results) == 1
        assert results[0].state_type == LatentStateType.TASK_EMBEDDING

    def test_retrieve_filters_by_source(self):
        state = SharedLatentState()
        state.publish(LatentStateType.TASK_EMBEDDING, (0.9,), "sonnet")
        state.publish(LatentStateType.TASK_EMBEDDING, (0.9,), "opus")
        results = state.retrieve(model_source="sonnet")
        assert len(results) == 1
        assert results[0].model_source == "sonnet"

    def test_retrieve_with_similarity(self):
        state = SharedLatentState()
        state.publish(LatentStateType.TASK_EMBEDDING, (1.0, 0.0), "sonnet")
        state.publish(LatentStateType.TASK_EMBEDDING, (-1.0, 0.0), "opus")
        results = state.retrieve(
            state_type=LatentStateType.TASK_EMBEDDING,
            query_vector=(1.0, 0.0),
            min_similarity=0.5,
        )
        assert len(results) >= 1
        assert results[0].model_source == "sonnet"

    def test_get_latest_returns_highest_version(self):
        state = SharedLatentState()
        state.publish(LatentStateType.TASK_EMBEDDING, (0.1,), "sonnet")
        state.publish(LatentStateType.TASK_EMBEDDING, (0.2,), "sonnet")
        state.publish(LatentStateType.TASK_EMBEDDING, (0.3,), "sonnet")
        latest = state.get_latest(LatentStateType.TASK_EMBEDDING, "sonnet")
        assert latest is not None
        assert latest.version == 3

    def test_get_latest_nonexistent(self):
        state = SharedLatentState()
        assert state.get_latest(LatentStateType.TASK_EMBEDDING, "unknown") is None

    def test_size_tracks_vectors(self):
        state = SharedLatentState()
        assert state.size == 0
        state.publish(LatentStateType.TASK_EMBEDDING, (1.0,), "sonnet")
        assert state.size == 1

    def test_clear_removes_all(self):
        state = SharedLatentState()
        state.publish(LatentStateType.TASK_EMBEDDING, (1.0,), "sonnet")
        state.clear()
        assert state.size == 0

    def test_max_vectors_enforced(self):
        state = SharedLatentState(max_vectors=5)
        for i in range(10):
            state.publish(LatentStateType.TASK_EMBEDDING, (float(i),), f"model-{i}")
        assert state.size <= 5


class TestConsensusSynthesizer:
    def test_synthesize_empty_state(self):
        state = SharedLatentState()
        synth = ConsensusSynthesizer()
        result = synth.synthesize(state, LatentStateType.TASK_EMBEDDING)
        assert result.confidence == 0.0
        assert len(result.source_vectors) == 0

    def test_synthesize_single_model(self):
        state = SharedLatentState()
        state.publish(LatentStateType.TASK_EMBEDDING, (0.9, 0.1, 0.8), "sonnet")
        synth = ConsensusSynthesizer()
        result = synth.synthesize(state, LatentStateType.TASK_EMBEDDING)
        assert result.confidence >= 1.0
        assert len(result.participating_models) == 1

    def test_synthesize_multiple_models(self):
        state = SharedLatentState()
        state.publish(LatentStateType.TASK_EMBEDDING, (0.9, 0.1, 0.8), "sonnet")
        state.publish(LatentStateType.TASK_EMBEDDING, (0.85, 0.15, 0.75), "opus")
        synth = ConsensusSynthesizer()
        result = synth.synthesize(state, LatentStateType.TASK_EMBEDDING)
        assert len(result.participating_models) == 2
        assert len(result.fused_vector) == 3
        assert result.confidence > 0

    def test_disagreement_score_increases_with_divergence(self):
        state = SharedLatentState()
        state.publish(LatentStateType.TASK_EMBEDDING, (1.0, 0.0, 0.0), "model-a")
        state.publish(LatentStateType.TASK_EMBEDDING, (0.0, 1.0, 0.0), "model-b")
        synth = ConsensusSynthesizer()
        result = synth.synthesize(state, LatentStateType.TASK_EMBEDDING)
        assert result.disagreement_score > 0.5

    def test_consensus_id_is_unique(self):
        state = SharedLatentState()
        state.publish(LatentStateType.TASK_EMBEDDING, (0.5,), "sonnet")
        synth = ConsensusSynthesizer()
        r1 = synth.synthesize(state, LatentStateType.TASK_EMBEDDING)
        r2 = synth.synthesize(state, LatentStateType.TASK_EMBEDDING)
        assert r1.consensus_id != r2.consensus_id

    def test_weighted_method_works(self):
        state = SharedLatentState()
        state.publish(LatentStateType.TASK_EMBEDDING, (0.9, 0.2), "sonnet")
        state.publish(LatentStateType.TASK_EMBEDDING, (0.1, 0.8), "opus")
        synth = ConsensusSynthesizer()
        result = synth.synthesize(
            state,
            LatentStateType.TASK_EMBEDDING,
            method=ConsensusMethod.WEIGHTED_AVERAGE,
            model_weights={"sonnet": 3.0, "opus": 1.0},
        )
        assert result.fused_vector  # sonnet-weighted
        assert result.fused_vector[0] > result.fused_vector[1]

    def test_summary_includes_models(self):
        state = SharedLatentState()
        state.publish(LatentStateType.TASK_EMBEDDING, (0.9,), "sonnet")
        synth = ConsensusSynthesizer()
        result = synth.synthesize(state, LatentStateType.TASK_EMBEDDING)
        assert "sonnet" in result.summary


class TestKnowledgeExchangeBus:
    def test_publish_returns_fragment(self):
        bus = KnowledgeExchangeBus()
        frag = bus.publish("sonnet", "This code uses O(n) complexity.")
        assert frag.fragment_id.startswith("kf-")
        assert frag.source_model == "sonnet"

    def test_deduplication_by_content(self):
        bus = KnowledgeExchangeBus()
        f1 = bus.publish("sonnet", "identical content")
        f2 = bus.publish("opus", "identical content")
        assert f1.fragment_id == f2.fragment_id
        assert bus.metrics.cache_hits == 1

    def test_subscribe_all_broadcast(self):
        bus = KnowledgeExchangeBus()
        bus.publish("sonnet", "broadcast message")
        results = bus.subscribe("opus")
        assert len(results) == 1

    def test_subscribe_targeted_only(self):
        bus = KnowledgeExchangeBus()
        bus.publish("sonnet", "secret", target_models=("haiku",))
        results = bus.subscribe("opus")
        assert len(results) == 0

    def test_subscribe_target_match(self):
        bus = KnowledgeExchangeBus()
        bus.publish("sonnet", "for haiku", target_models=("haiku",))
        results = bus.subscribe("haiku")
        assert len(results) == 1

    def test_subscribe_min_priority_filter(self):
        bus = KnowledgeExchangeBus()
        bus.publish("sonnet", "low priority", priority=0.1)
        bus.publish("sonnet", "high priority", priority=0.9)
        results = bus.subscribe("opus", min_priority=0.5)
        assert len(results) == 1
        assert results[0].priority == 0.9

    def test_metrics_track_exchanges(self):
        bus = KnowledgeExchangeBus()
        bus.publish("sonnet", "message 1")
        bus.publish("sonnet", "message 2")
        assert bus.metrics.total_exchanges == 2

    def test_get_model_fragments(self):
        bus = KnowledgeExchangeBus()
        bus.publish("sonnet", "msg1")
        bus.publish("sonnet", "msg2")
        bus.publish("opus", "msg3")
        frags = bus.get_model_fragments("sonnet")
        assert len(frags) == 2

    def test_expired_fragments_excluded(self):
        bus = KnowledgeExchangeBus()
        bus.publish("sonnet", "expires fast", ttl_seconds=0.001)
        time.sleep(0.01)
        results = bus.subscribe("opus")
        assert len(results) == 0

    def test_clear_resets_everything(self):
        bus = KnowledgeExchangeBus()
        bus.publish("sonnet", "msg")
        bus.clear()
        assert bus.fragment_count == 0
        assert bus.metrics.total_exchanges == 0

    def test_max_fragments_enforced(self):
        bus = KnowledgeExchangeBus(max_fragments=5)
        for i in range(10):
            bus.publish("sonnet", f"message {i}")
        assert bus.fragment_count <= 5


class TestBridgeMetrics:
    def test_initial_savings_rate_zero(self):
        m = BridgeMetrics()
        assert m.savings_rate == 0.0

    def test_savings_rate_with_hits(self):
        m = BridgeMetrics()
        m.cache_hits = 7
        m.cache_misses = 3
        assert m.savings_rate == 0.7

    def test_estimated_token_reduction(self):
        m = BridgeMetrics()
        m.total_tokens_saved = 5000
        m.total_exchanges = 10
        assert m.estimated_token_reduction_pct > 0
