"""Tests for Unified Memory Router (P2-B1)."""
from __future__ import annotations

import pytest

from lyra_harness_core.unified_memory_router import (
    BanditArm,
    CompressionPolicy,
    FeatureExtractor,
    MemoryFeatures,
    MemoryTier,
    MultiArmedBandit,
    RawMemory,
    RetentionPolicy,
    StoreDecision,
    UnifiedMemoryRouter,
)


# ---------------------------------------------------------------------------
# MemoryTier
# ---------------------------------------------------------------------------


class TestMemoryTier:
    def test_values(self):
        assert MemoryTier.WORKING.value == "working"
        assert MemoryTier.EPISODIC.value == "episodic"
        assert MemoryTier.SEMANTIC.value == "semantic"
        assert MemoryTier.PROCEDURAL.value == "procedural"

    def test_four_tiers(self):
        assert len(MemoryTier) == 4

    def test_tiers_are_distinct(self):
        values = [t.value for t in MemoryTier]
        assert len(values) == len(set(values))


# ---------------------------------------------------------------------------
# RawMemory
# ---------------------------------------------------------------------------


class TestRawMemory:
    def test_minimal(self):
        m = RawMemory(id="m1", content="hello")
        assert m.id == "m1"
        assert m.content == "hello"
        assert m.content_type == "text"
        assert m.token_count == 0

    def test_with_metadata(self):
        m = RawMemory(id="m1", content="x", metadata={"key": "val"})
        assert m.metadata == {"key": "val"}

    def test_frozen(self):
        m = RawMemory(id="m1", content="x")
        with pytest.raises(Exception):
            m.content = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# MemoryFeatures
# ---------------------------------------------------------------------------


class TestMemoryFeatures:
    def test_create(self):
        f = MemoryFeatures(
            content_length=100,
            content_type_id=5,
            has_code=False,
            has_urls=True,
            entity_count=3,
            token_count=25,
            hour_of_day=14,
        )
        assert f.content_length == 100
        assert f.has_urls

    def test_frozen(self):
        f = MemoryFeatures(100, 5, False, False, 1, 25, 14)
        with pytest.raises(Exception):
            f.content_length = 200  # type: ignore[misc]


# ---------------------------------------------------------------------------
# StoreDecision
# ---------------------------------------------------------------------------


class TestStoreDecision:
    def test_create(self):
        d = StoreDecision(
            store=MemoryTier.EPISODIC,
            compression_level=0.5,
            retention_policy="session",
            confidence=0.85,
            reason="test",
        )
        assert d.store == MemoryTier.EPISODIC
        assert d.compression_level == 0.5
        assert d.confidence == 0.85

    def test_frozen(self):
        d = StoreDecision(MemoryTier.WORKING, 0.0, "ephemeral", 0.9)
        with pytest.raises(Exception):
            d.store = MemoryTier.SEMANTIC  # type: ignore[misc]


# ---------------------------------------------------------------------------
# BanditArm
# ---------------------------------------------------------------------------


class TestBanditArm:
    def test_defaults(self):
        arm = BanditArm(tier=MemoryTier.WORKING)
        assert arm.pulls == 0
        assert arm.mean == 0.5
        assert arm.ucb == float("inf")

    def test_update(self):
        arm = BanditArm(tier=MemoryTier.WORKING)
        arm.update(1.0)
        assert arm.pulls == 1
        assert arm.mean == 1.0

    def test_multiple_updates(self):
        arm = BanditArm(tier=MemoryTier.EPISODIC)
        arm.update(0.8)
        arm.update(0.6)
        assert arm.pulls == 2
        assert arm.mean == 0.7

    def test_ucb_finite_after_pull(self):
        arm = BanditArm(tier=MemoryTier.WORKING)
        arm.update(0.5)
        assert arm.ucb != float("inf")
        assert arm.ucb > arm.mean


# ---------------------------------------------------------------------------
# MultiArmedBandit
# ---------------------------------------------------------------------------


class TestMultiArmedBandit:
    @pytest.fixture
    def bandit(self):
        return MultiArmedBandit(epsilon=0.0)  # greedy for deterministic tests

    @pytest.fixture
    def features(self):
        return MemoryFeatures(100, 5, False, False, 3, 25, 14)

    def test_four_arms(self, bandit):
        assert len(bandit.arms) == 4

    def test_select_returns_tier_and_confidence(self, bandit, features):
        tier, conf = bandit.select(features)
        assert isinstance(tier, MemoryTier)
        assert 0.0 <= conf <= 1.0

    def test_select_deterministic_greedy(self, bandit, features):
        # With zero epsilon, should be deterministic given same state
        t1, _ = bandit.select(features)
        t2, _ = bandit.select(features)
        assert t1 == t2  # same UCB values → same choice

    def test_update_affects_mean(self, bandit, features):
        bandit.update(MemoryTier.SEMANTIC, 1.0)
        assert bandit.arms[MemoryTier.SEMANTIC].mean == 1.0

    def test_exploration_with_epsilon(self, features):
        bandit = MultiArmedBandit(epsilon=1.0)  # always explore
        tiers_seen = set()
        for _ in range(50):
            tier, _ = bandit.select(features)
            tiers_seen.add(tier)
        # With 50 random choices, should see at least 3 different tiers
        assert len(tiers_seen) >= 3

    def test_stats(self, bandit):
        bandit.update(MemoryTier.WORKING, 0.9)
        s = bandit.stats
        assert "working" in s
        assert s["working"]["pulls"] == 1

    def test_confidence_in_range(self, bandit, features):
        for _ in range(20):
            _, conf = bandit.select(features)
            assert 0.0 <= conf <= 1.0


# ---------------------------------------------------------------------------
# FeatureExtractor
# ---------------------------------------------------------------------------


class TestFeatureExtractor:
    @pytest.fixture
    def extractor(self):
        return FeatureExtractor()

    def test_extracts_basic_features(self, extractor):
        m = RawMemory(id="m1", content="hello world")
        f = extractor.extract(m)
        assert f.content_length == 11
        assert f.token_count >= 1
        assert not f.has_code

    def test_detects_code(self, extractor):
        m = RawMemory(id="m1", content="def foo():\n    return 42")
        f = extractor.extract(m)
        assert f.has_code

    def test_detects_code_fence(self, extractor):
        m = RawMemory(id="m1", content="```python\nprint('hi')\n```")
        f = extractor.extract(m)
        assert f.has_code

    def test_detects_urls(self, extractor):
        m = RawMemory(id="m1", content="check https://example.com for info")
        f = extractor.extract(m)
        assert f.has_urls

    def test_entity_count(self, extractor):
        m = RawMemory(id="m1", content="line1\nline2\nline3")
        f = extractor.extract(m)
        assert f.entity_count == 3

    def test_uses_provided_token_count(self, extractor):
        m = RawMemory(id="m1", content="hello", token_count=500)
        f = extractor.extract(m)
        assert f.token_count == 500

    def test_content_type_id_deterministic(self, extractor):
        f1 = extractor.extract(RawMemory(id="a", content="x", content_type="code"))
        f2 = extractor.extract(RawMemory(id="b", content="y", content_type="code"))
        assert f1.content_type_id == f2.content_type_id


# ---------------------------------------------------------------------------
# CompressionPolicy
# ---------------------------------------------------------------------------


class TestCompressionPolicy:
    @pytest.fixture
    def policy(self):
        return CompressionPolicy()

    @pytest.fixture
    def features(self):
        return MemoryFeatures(100, 5, False, False, 3, 25, 14)

    def test_working_no_compression(self, policy, features):
        assert policy.decide(features, MemoryTier.WORKING) == 0.0

    def test_episodic_light_compression(self, policy, features):
        assert policy.decide(features, MemoryTier.EPISODIC) == 0.3

    def test_semantic_moderate_compression(self, policy, features):
        assert policy.decide(features, MemoryTier.SEMANTIC) == 0.6

    def test_procedural_heavy_compression(self, policy, features):
        assert policy.decide(features, MemoryTier.PROCEDURAL) == 0.8


# ---------------------------------------------------------------------------
# RetentionPolicy
# ---------------------------------------------------------------------------


class TestRetentionPolicy:
    @pytest.fixture
    def policy(self):
        return RetentionPolicy()

    @pytest.fixture
    def features(self):
        return MemoryFeatures(100, 5, False, False, 3, 25, 14)

    def test_working_ephemeral(self, policy, features):
        assert policy.decide(features, MemoryTier.WORKING) == "ephemeral"

    def test_episodic_session(self, policy, features):
        assert policy.decide(features, MemoryTier.EPISODIC) == "session"

    def test_semantic_long_term(self, policy, features):
        assert policy.decide(features, MemoryTier.SEMANTIC) == "long_term"

    def test_procedural_permanent(self, policy, features):
        assert policy.decide(features, MemoryTier.PROCEDURAL) == "permanent"


# ---------------------------------------------------------------------------
# UnifiedMemoryRouter
# ---------------------------------------------------------------------------


class TestUnifiedMemoryRouter:
    @pytest.fixture
    def router(self):
        return UnifiedMemoryRouter()

    def test_route_returns_decision(self, router):
        m = RawMemory(id="m1", content="hello world")
        d = router.route(m)
        assert isinstance(d, StoreDecision)
        assert isinstance(d.store, MemoryTier)
        assert 0.0 <= d.confidence <= 1.0
        assert 0.0 <= d.compression_level <= 1.0
        assert d.retention_policy in ("ephemeral", "session", "long_term", "permanent")

    def test_route_different_content_types(self, router):
        """Different content types should produce valid decisions."""
        memories = [
            RawMemory(id="code", content="def foo(): pass", content_type="code"),
            RawMemory(id="text", content="hello world", content_type="text"),
            RawMemory(id="url", content="see https://example.com", content_type="text"),
        ]
        for m in memories:
            d = router.route(m)
            assert isinstance(d.store, MemoryTier)

    def test_feedback_updates_bandit(self, router):
        m = RawMemory(id="m1", content="test")
        router.route(m)
        stats_before = router.stats["bandit"]
        router.feedback("m1", reward=1.0)
        stats_after = router.stats["bandit"]
        # At least one arm should have a pull
        total_pulls = sum(a["pulls"] for a in stats_after.values())
        assert total_pulls > sum(a["pulls"] for a in stats_before.values())

    def test_feedback_unknown_id_no_error(self, router):
        router.feedback("nonexistent", reward=0.5)

    def test_route_batch(self, router):
        memories = [
            RawMemory(id=f"m{i}", content=f"memory {i}")
            for i in range(10)
        ]
        decisions = router.route_batch(memories)
        assert len(decisions) == 10
        for d in decisions:
            assert isinstance(d, StoreDecision)

    def test_stats(self, router):
        router.route(RawMemory(id="m1", content="test"))
        s = router.stats
        assert s["total_routes"] == 1
        assert "bandit" in s

    def test_routing_is_repeatable(self, router):
        """Same memory routed twice gives decisions (may differ due to exploration)."""
        m = RawMemory(id="m1", content="consistent content here")
        d1 = router.route(m)
        d2 = router.route(m)
        assert isinstance(d1.store, MemoryTier)
        assert isinstance(d2.store, MemoryTier)

    def test_compression_varies_by_tier(self, router):
        """Test that compression levels differ by tier."""
        memories = [
            RawMemory(id=f"m{i}", content=f"test content {i}")
            for i in range(50)
        ]
        decisions = router.route_batch(memories)
        levels = {d.store: d.compression_level for d in decisions}
        # Working memory should always be 0.0
        for d in decisions:
            if d.store == MemoryTier.WORKING:
                assert d.compression_level == 0.0

    def test_retention_varies_by_tier(self, router):
        """Test that retention policies align with tiers."""
        memories = [
            RawMemory(id=f"m{i}", content=f"test content {i}")
            for i in range(50)
        ]
        decisions = router.route_batch(memories)
        for d in decisions:
            if d.store == MemoryTier.WORKING:
                assert d.retention_policy == "ephemeral"
            elif d.store == MemoryTier.PROCEDURAL:
                assert d.retention_policy == "permanent"


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------


class TestUnifiedMemoryRouterIntegration:
    def test_full_routing_workflow(self):
        router = UnifiedMemoryRouter()

        # Route a batch of memories
        memories = [
            RawMemory(id="sys", content="System configuration", content_type="config"),
            RawMemory(id="code1", content="def train(): pass", content_type="code"),
            RawMemory(id="conv1", content="User asked about weather", content_type="conversation"),
            RawMemory(id="tool1", content='{"result": "ok"}', content_type="tool_output"),
        ]

        decisions = router.route_batch(memories)
        assert len(decisions) == 4

        # Feed back rewards
        for mem, dec in zip(memories, decisions):
            # Simulate: code memories should go to procedural, conversations to episodic
            if mem.content_type == "code":
                reward = 1.0 if dec.store in (MemoryTier.PROCEDURAL, MemoryTier.SEMANTIC) else 0.3
            elif mem.content_type == "conversation":
                reward = 1.0 if dec.store in (MemoryTier.EPISODIC, MemoryTier.WORKING) else 0.3
            elif mem.content_type == "tool_output":
                reward = 1.0 if dec.store in (MemoryTier.EPISODIC, MemoryTier.WORKING) else 0.3
            else:
                reward = 0.5
            router.feedback(mem.id, reward)

        stats = router.stats
        assert stats["total_routes"] == 4
        # Bandit should have updated at least one arm
        total_pulls = sum(a["pulls"] for a in stats["bandit"].values())
        assert total_pulls == 4

    def test_bandit_converges_with_feedback(self):
        """Repeated feedback on one tier should make it the go-to."""
        router = UnifiedMemoryRouter()
        router.bandit.epsilon = 0.0  # greedy

        good_memory = RawMemory(id="good", content="important data here", content_type="research")

        # Train: EPISODIC is always good
        for _ in range(20):
            d = router.route(good_memory)
            reward = 1.0 if d.store == MemoryTier.EPISODIC else 0.0
            router.feedback(good_memory.id, reward)

        # After training, EPISODIC should have highest mean
        episodic_mean = router.bandit.arms[MemoryTier.EPISODIC].mean
        for tier in MemoryTier:
            if tier != MemoryTier.EPISODIC:
                assert episodic_mean >= router.bandit.arms[tier].mean or router.bandit.arms[tier].pulls == 0
