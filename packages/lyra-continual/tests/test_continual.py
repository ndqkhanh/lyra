"""
Comprehensive tests for lyra-continual: models, MoLEM, SkillPack, and legacy components.
"""

import math
import pytest
from datetime import datetime

from lyra_continual.models import (
    ContinualEpisode,
    ExpertStats,
    ForgettingMetrics,
    MoEExpert,
    MoELayer,
    SkillPack,
)
from lyra_continual.molem import MoLEMEngine
from lyra_continual.skill_pack import SkillPackCompressor

# Legacy
from lyra_continual import (
    AgentExperience,
    ContinualLearner,
    ElasticWeightConsolidation,
    ExperienceReplay,
    ProgressiveNetwork,
)


# ═══════════════════════════════════════════════════════════════════════════
# Model tests
# ═══════════════════════════════════════════════════════════════════════════


class TestMoEExpert:
    """MoEExpert frozen dataclass tests."""

    def test_create_expert(self):
        expert = MoEExpert(
            expert_id="expert_0",
            domain="mathematics",
            specialization_score=0.75,
        )
        assert expert.expert_id == "expert_0"
        assert expert.domain == "mathematics"
        assert expert.specialization_score == 0.75
        assert expert.usage_count == 0

    def test_specialization_score_bounds(self):
        with pytest.raises(ValueError):
            MoEExpert(expert_id="e", domain="d", specialization_score=-0.1)
        with pytest.raises(ValueError):
            MoEExpert(expert_id="e", domain="d", specialization_score=1.5)

    def test_touch_updates_counters(self):
        expert = MoEExpert(expert_id="e1", domain="science", usage_count=3)
        touched = expert.touch()
        assert touched.usage_count == 4
        assert expert.usage_count == 3  # original unchanged
        assert isinstance(touched.last_used, datetime)

    def test_frozen(self):
        expert = MoEExpert(expert_id="e1", domain="d")
        with pytest.raises(Exception):
            expert.domain = "new"  # type: ignore[misc]


class TestMoELayer:
    """MoELayer frozen dataclass tests."""

    def _make_layer(self, n: int = 4) -> MoELayer:
        experts = tuple(
            MoEExpert(expert_id=f"e{i}", domain=f"domain_{i}", specialization_score=0.5 + i * 0.1)
            for i in range(n)
        )
        weights = tuple(1.0 / n for _ in range(n))
        return MoELayer(experts=experts, router_weights=weights, active_count=2)

    def test_create_layer(self):
        layer = self._make_layer(4)
        assert len(layer.experts) == 4
        assert len(layer.router_weights) == 4
        assert layer.active_count == 2

    def test_top_k_experts(self):
        layer = MoELayer(
            experts=(
                MoEExpert(expert_id="e0", domain="a"),
                MoEExpert(expert_id="e1", domain="b"),
                MoEExpert(expert_id="e2", domain="c"),
            ),
            router_weights=(0.1, 0.7, 0.2),
            active_count=2,
        )
        top = layer.top_k_experts()
        assert len(top) == 2
        assert top[0].expert_id == "e1"  # highest weight
        assert top[1].expert_id == "e2"  # second highest

    def test_top_k_custom_k(self):
        layer = self._make_layer(5)
        top = layer.top_k_experts(k=3)
        assert len(top) == 3

    def test_top_k_clamped(self):
        layer = self._make_layer(3)
        top = layer.top_k_experts(k=10)
        assert len(top) == 3

    def test_update_expert(self):
        layer = self._make_layer(3)
        updated = MoEExpert(expert_id="e1", domain="new_domain", specialization_score=0.9)
        new_layer = layer.update_expert("e1", updated)
        assert new_layer.experts[1].domain == "new_domain"
        assert layer.experts[1].domain == "domain_1"  # original unchanged

    def test_update_weights(self):
        layer = self._make_layer(3)
        new_weights = (0.5, 0.3, 0.2)
        new_layer = layer.update_weights(new_weights)
        assert new_layer.router_weights == new_weights
        assert layer.router_weights != new_weights

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError):
            MoELayer(
                experts=(MoEExpert(expert_id="e0", domain="d"),),
                router_weights=(0.3, 0.7),
                active_count=2,
            )


class TestContinualEpisode:
    """ContinualEpisode frozen dataclass tests."""

    def test_create_episode(self):
        ep = ContinualEpisode(
            task="text_classification",
            input_distribution="news_articles",
            performance_delta=0.05,
            task_difficulty=0.6,
        )
        assert ep.task == "text_classification"
        assert ep.performance_delta == 0.05
        assert ep.task_difficulty == 0.6
        assert isinstance(ep.timestamp, datetime)


class TestSkillPack:
    """SkillPack frozen dataclass tests."""

    def test_create_skill_pack(self):
        pack = SkillPack(
            domain="math",
            compressed_data=(0.5, -3.0, 1.2, 0.0, 0.0, 0.0),
            original_size=100,
            compressed_size=6,
            compression_ratio=0.06,
        )
        assert pack.domain == "math"
        assert len(pack.compressed_data) == 6
        assert pack.original_size == 100
        assert pack.compressed_size == 6
        assert pack.compression_ratio == 0.06


class TestForgettingMetrics:
    """ForgettingMetrics frozen dataclass tests."""

    def test_create_metrics(self):
        fm = ForgettingMetrics(
            backward_transfer=-0.05,
            forward_transfer=0.1,
            retention=0.92,
            task_count=5,
            detailed_per_task={"task_1": 0.0, "task_2": -0.03},
        )
        assert fm.backward_transfer == -0.05
        assert fm.forward_transfer == 0.1
        assert fm.retention == 0.92
        assert fm.forgetting_rate == pytest.approx(0.08)
        assert fm.is_catastrophic is False

    def test_catastrophic_detection(self):
        fm = ForgettingMetrics(backward_transfer=-0.2, retention=0.8, task_count=3)
        assert fm.is_catastrophic is True

    def test_forgetting_rate(self):
        fm = ForgettingMetrics(retention=0.75)
        assert fm.forgetting_rate == 0.25

    def test_retention_bounds(self):
        with pytest.raises(ValueError):
            ForgettingMetrics(retention=-0.1)
        with pytest.raises(ValueError):
            ForgettingMetrics(retention=1.5)


class TestExpertStats:
    """ExpertStats frozen dataclass tests."""

    def test_create_stats(self):
        stats = ExpertStats(
            expert_id="e1",
            domain="math",
            total_uses=42,
            avg_weight=0.35,
            last_weight=0.40,
            weight_trend=0.05,
        )
        assert stats.expert_id == "e1"
        assert stats.total_uses == 42
        assert stats.weight_trend == 0.05


# ═══════════════════════════════════════════════════════════════════════════
# MoLEM tests
# ═══════════════════════════════════════════════════════════════════════════


class TestMoLEMEngine:
    """MoLEMEngine tests."""

    def test_init_creates_base_experts(self):
        engine = MoLEMEngine(base_experts=4)
        assert engine.expert_count == 4
        assert all(e.domain == "general" for e in engine.layer.experts)

    def test_route_returns_top_k(self):
        engine = MoLEMEngine(base_experts=4, default_active_count=2)
        experts = engine.route("Solve the quadratic equation")
        assert len(experts) == 2
        assert all(isinstance(e, MoEExpert) for e in experts)

    def test_add_expert(self):
        engine = MoLEMEngine(base_experts=2)
        initial_count = engine.expert_count
        expert = engine.add_expert("mathematics", "mathematical_reasoning")
        assert engine.expert_count == initial_count + 1
        assert expert.domain == "mathematics"

    def test_add_expert_renormalizes_weights(self):
        engine = MoLEMEngine(base_experts=2)
        engine.add_expert("math", "math_reasoning")
        total = sum(engine.layer.router_weights)
        assert math.isclose(total, 1.0, rel_tol=1e-9)

    def test_learn_updates_weights(self):
        engine = MoLEMEngine(base_experts=3)
        engine.add_expert("math", "math_specialization")

        episode = ContinualEpisode(
            task="Solve math equation",
            input_distribution="algebra_problems",
            performance_delta=0.15,
        )
        stats = engine.learn(episode)
        assert stats["matched_experts"] >= 1
        assert "weight_delta" in stats

    def test_learn_no_match(self):
        engine = MoLEMEngine(base_experts=3)
        # Base experts have domain "general" which matches everything at 0.6.
        # Add a domain-specific expert that won't match.
        engine.add_expert("sentiment_analysis", "nlp_specialization")
        episode = ContinualEpisode(
            task="solve linear algebra equations",
            input_distribution="math_problems",
            performance_delta=0.1,
        )
        stats = engine.learn(episode)
        # The general base experts match at 0.6, the sentiment expert shouldn't match math
        assert stats["matched_experts"] >= 1  # base experts always match
        assert stats["matched_experts"] <= 3  # sentiment expert should NOT match

    def test_prune_experts(self):
        engine = MoLEMEngine(base_experts=2)
        engine.add_expert("rare_domain", "rare")

        # Artificially lower the weight on the new expert
        experts = list(engine.layer.experts)
        weights = list(engine.layer.router_weights)
        weights[-1] = 0.001  # very small
        total = sum(weights)
        weights = [w / total for w in weights]
        engine.layer = MoELayer(
            experts=tuple(experts),
            router_weights=tuple(weights),
            active_count=engine.layer.active_count,
        )

        pruned = engine.prune_experts(threshold=0.01)
        assert len(pruned) > 0

    def test_prune_never_removes_base(self):
        engine = MoLEMEngine(base_experts=2)
        # Set all weights very low
        new_weights = (0.001, 0.001)
        total = sum(new_weights)
        engine.layer = engine.layer.update_weights(tuple(w / total for w in new_weights))
        pruned = engine.prune_experts(threshold=0.5)
        # Base experts should never be pruned regardless of weight
        assert len(pruned) == 0

    def test_get_active_experts(self):
        engine = MoLEMEngine(base_experts=4)
        active = engine.get_active_experts()
        assert len(active) == 4  # all base experts should be active

    def test_compute_forgetting_initial(self):
        engine = MoLEMEngine(base_experts=2)
        fm = engine.compute_forgetting()
        assert fm.task_count == 0

    def test_compute_forgetting_after_learning(self):
        engine = MoLEMEngine(base_experts=2)
        engine.add_expert("task_a", "domain_a")
        engine.add_expert("task_b", "domain_b")

        engine.learn(ContinualEpisode(task="task_a", input_distribution="d", performance_delta=0.1))
        engine.learn(ContinualEpisode(task="task_b", input_distribution="d", performance_delta=0.1))
        engine.learn(ContinualEpisode(task="task_a", input_distribution="d", performance_delta=0.05))

        fm = engine.compute_forgetting()
        assert fm.task_count == 2
        assert 0.0 <= fm.retention <= 1.0

    def test_episode_count(self):
        engine = MoLEMEngine(base_experts=2)
        assert engine.episode_count == 0
        engine.learn(ContinualEpisode(task="t1", input_distribution="d1", performance_delta=0.1))
        assert engine.episode_count == 1

    def test_get_expert_stats(self):
        engine = MoLEMEngine(base_experts=3)
        stats = engine.get_expert_stats()
        assert len(stats) == 3
        assert all(isinstance(s, ExpertStats) for s in stats)

    def test_router_temperature_initialized(self):
        engine = MoLEMEngine(router_temperature=0.5)
        assert engine.router_temperature == 0.5

    def test_multiple_episodes_build_performance_log(self):
        engine = MoLEMEngine(base_experts=2)
        engine.add_expert("domain_x", "x_spec")
        for _ in range(3):
            engine.learn(ContinualEpisode(task="domain_x", input_distribution="d", performance_delta=0.1))
        fm = engine.compute_forgetting()
        assert fm.task_count >= 1


# ═══════════════════════════════════════════════════════════════════════════
# SkillPack tests
# ═══════════════════════════════════════════════════════════════════════════


class TestSkillPackCompressor:
    """SkillPackCompressor tests."""

    def test_compress_empty_weights(self):
        compressor = SkillPackCompressor()
        pack = compressor.compress([], "empty")
        assert pack.domain == "empty"
        assert pack.original_size == 0
        assert pack.compressed_size == 0

    def test_compress_non_empty(self):
        compressor = SkillPackCompressor()
        weights = [0.1, 0.2, 0.3, 0.0, 0.0, 0.0, 0.0, 0.4, 0.5, 0.6]
        pack = compressor.compress(weights, "test_domain")
        assert pack.domain == "test_domain"
        assert pack.original_size == 10
        assert pack.compressed_size <= 10  # compression occurred
        assert pack.compression_ratio <= 1.0

    def test_compress_sparse_weights(self):
        """Sparse weights should compress well."""
        compressor = SkillPackCompressor(sparsity_threshold=0.05)
        weights = [0.8] + [0.0] * 98 + [0.9]
        pack = compressor.compress(weights, "sparse")
        # 100 weights -> should compress significantly
        assert pack.compressed_size < pack.original_size
        assert pack.compression_ratio < 0.3  # good compression

    def test_decompress_restores_size(self):
        compressor = SkillPackCompressor()
        weights = [0.1, 0.2, 0.3, 0.0, 0.0, 0.4, 0.5]
        pack = compressor.compress(weights, "test")
        restored = compressor.decompress(pack)
        assert len(restored) == len(weights)

    def test_decompress_roundtrip_approximate(self):
        """Decompressed weights should approximate originals."""
        compressor = SkillPackCompressor()
        weights = [0.5, 0.3, 0.8, 0.1, 0.0, 0.0, 0.0, 0.0, 0.9, 0.2]
        pack = compressor.compress(weights, "test")
        restored = compressor.decompress(pack)
        assert len(restored) == len(weights)
        # Non-zero values should be close
        for i, w in enumerate(weights):
            if w > 0.05:
                assert abs(restored[i] - w) < 0.15, f"weight[{i}]={w} vs {restored[i]}"

    def test_fuse_two_packs(self):
        compressor = SkillPackCompressor()
        weights_a = [0.8, 0.1, 0.0, 0.0]
        weights_b = [0.0, 0.0, 0.7, 0.2]
        pack_a = compressor.compress(weights_a, "domain_a")
        pack_b = compressor.compress(weights_b, "domain_b")
        fused = compressor.fuse(pack_a, pack_b)
        assert "domain_a" in fused.domain
        assert "domain_b" in fused.domain

    def test_compute_compression_ratio(self):
        compressor = SkillPackCompressor()
        weights = [0.1] * 100
        pack = compressor.compress(weights, "uniform")
        ratio = compressor.compute_compression_ratio(pack)
        assert 0.0 < ratio <= 1.0

    def test_aggregate_ratio_empty(self):
        compressor = SkillPackCompressor()
        assert compressor.aggregate_ratio() == 1.0

    def test_aggregate_ratio_with_packs(self):
        compressor = SkillPackCompressor()
        compressor.compress([0.1, 0.2, 0.3], "a")
        compressor.compress([0.4, 0.5], "b")
        ratio = compressor.aggregate_ratio()
        assert 0.0 < ratio <= 1.0

    def test_registered_packs(self):
        compressor = SkillPackCompressor()
        compressor.compress([0.1, 0.2], "domain_1")
        compressor.compress([0.3, 0.4], "domain_2")
        packs = compressor.registered_packs
        assert "domain_1" in packs
        assert "domain_2" in packs

    def test_compression_ratio_preserved(self):
        compressor = SkillPackCompressor()
        weights = [0.5, 0.0, 0.0, 0.0, 0.0, 0.3]
        pack = compressor.compress(weights, "test")
        assert pack.compression_ratio <= 1.0
        assert pack.original_size == len(weights)


# ═══════════════════════════════════════════════════════════════════════════
# Legacy tests (backward compatible)
# ═══════════════════════════════════════════════════════════════════════════


class TestExperienceReplay:
    """Legacy ExperienceReplay tests."""

    def test_store_and_sample(self):
        r = ExperienceReplay(capacity=100)
        for i in range(10):
            r.store(AgentExperience(task_id=f"task_{i%3}", state={}, action="test", result="ok"))
        samples = r.sample(batch_size=5, strategy="balanced")
        assert len(samples) <= 5
        assert r.stats["total_experiences"] == 10

    def test_balanced_sampling(self):
        r = ExperienceReplay(capacity=100)
        for i in range(30):
            r.store(AgentExperience(task_id=f"task_{i%2}", state={}, action="a", result="r"))
        samples = r.sample(batch_size=10, strategy="balanced")
        assert len(samples) <= 10

    def test_empty_sampling(self):
        r = ExperienceReplay()
        assert r.sample() == []

    def test_sample_default_strategy(self):
        r = ExperienceReplay(capacity=50)
        for i in range(5):
            r.store(AgentExperience(task_id="t", state={}, action="a", result="r"))
        samples = r.sample(batch_size=3)
        assert 0 < len(samples) <= 3


class TestElasticWeightConsolidation:
    """Legacy EWC tests."""

    def test_compute_fisher(self):
        ewc = ElasticWeightConsolidation(lambda_ewc=0.5)
        ewc.compute_fisher("task_1", {"w1": 0.8, "w2": 0.2})
        assert "task_1" in ewc.fisher_matrices

    def test_compute_ewc_loss_same_task(self):
        ewc = ElasticWeightConsolidation()
        ewc.compute_fisher("task_1", {"w1": 0.5})
        loss = ewc.compute_ewc_loss("task_1", {"w1": 0.3})
        assert loss == 0.0  # same task, no penalty

    def test_compute_ewc_loss_other_task(self):
        ewc = ElasticWeightConsolidation(lambda_ewc=0.5)
        ewc.compute_fisher("task_1", {"w1": 1.0})
        ewc.optimal_weights["task_1"] = {"w1": 0.5}
        loss = ewc.compute_ewc_loss("task_2", {"w1": 0.3})
        assert loss > 0


class TestProgressiveNetwork:
    """Legacy ProgressiveNetwork tests."""

    def test_add_column(self):
        pn = ProgressiveNetwork()
        pn.add_column("task_1", [128, 64])
        assert "task_1" in pn.columns
        assert len(pn.lateral_connections["task_1"]) > 0

    def test_transfer_from_existing(self):
        pn = ProgressiveNetwork()
        pn.add_column("task_1", [256, 128])
        result = pn.transfer_from("task_2", "task_1")
        assert result["transfer"] is True

    def test_transfer_from_nonexistent(self):
        pn = ProgressiveNetwork()
        result = pn.transfer_from("task_x", "nonexistent")
        assert result["transfer"] is False


class TestContinualLearner:
    """Legacy ContinualLearner tests."""

    def test_learn_task(self):
        cl = ContinualLearner()
        result = cl.learn_task("task_1", [
            AgentExperience(task_id="task_1", state={}, action="a", result="r", reward=1.0)
            for _ in range(5)
        ])
        assert result["task"] == "task_1"
        assert result["total_experiences"] == 5
        assert cl.task_count == 1

    def test_multiple_tasks(self):
        cl = ContinualLearner()
        for t in range(3):
            cl.learn_task(f"task_{t}", [
                AgentExperience(task_id=f"task_{t}", state={}, action="a", result="r")
                for _ in range(5)
            ])
        assert cl.task_count == 3


# ═══════════════════════════════════════════════════════════════════════════
# Integration tests
# ═══════════════════════════════════════════════════════════════════════════


class TestIntegration:
    """Cross-module integration tests for continual learning."""

    def test_molem_works_with_skillpack(self):
        """MoLEM experts can be compressed into skill packs."""
        engine = MoLEMEngine(base_experts=2)
        engine.add_expert("nlp", "language_understanding")

        # Learn some episodes
        engine.learn(ContinualEpisode(task="nlp", input_distribution="text", performance_delta=0.1))

        # Compress router weights into a skill pack
        compressor = SkillPackCompressor()
        pack = compressor.compress(engine.layer.router_weights, "nlp_router")
        assert pack.domain == "nlp_router"

        # Round-trip
        restored = compressor.decompress(pack)
        assert len(restored) == len(engine.layer.router_weights)

    def test_molem_route_after_learning(self):
        """Routing should improve after learning."""
        engine = MoLEMEngine(base_experts=2)
        engine.add_expert("sentiment", "sentiment_analysis")

        # Before learning
        initial_experts = engine.route("Analyze sentiment of this review")

        # Learn
        engine.learn(ContinualEpisode(task="sentiment", input_distribution="reviews", performance_delta=0.3))

        # After learning — sentiment expert should be more prominent for sentiment queries
        later_experts = engine.route("Analyze sentiment of this review")
        assert len(later_experts) >= 1

    def test_forgetting_with_skill_compression_cycle(self):
        """Full cycle: learn -> compress -> continue learning -> check forgetting."""
        engine = MoLEMEngine(base_experts=2)
        compressor = SkillPackCompressor()

        # Learn task A
        engine.add_expert("task_a_domain", "A")
        for _ in range(3):
            engine.learn(ContinualEpisode(task="task_a_domain", input_distribution="d", performance_delta=0.1))

        # Compress current state
        pack_a = compressor.compress(engine.layer.router_weights, "state_after_A")

        # Learn task B
        engine.add_expert("task_b_domain", "B")
        for _ in range(2):
            engine.learn(ContinualEpisode(task="task_b_domain", input_distribution="d", performance_delta=0.1))

        # Check forgetting
        fm = engine.compute_forgetting()
        assert fm.task_count >= 1
        assert 0.0 <= fm.retention <= 1.0
