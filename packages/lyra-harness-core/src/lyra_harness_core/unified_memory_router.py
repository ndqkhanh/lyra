"""Unified Memory Router — P2-B1 (CRITICAL, MED — BREAKTHROUGH).

Learned router that decides which memory store to use based on content type,
expected access pattern, and cost. Uses a multi-armed bandit over stores.

See: plan-phase2-memory.md §Breakthrough 1
Refs: Store Routing paper (UTRuEFJ57H), Thalamic Gateway (l9Ly41xxPb)
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Memory Store Tier
# ---------------------------------------------------------------------------


class MemoryTier(Enum):
    """Memory store tiers in order of latency/cost."""

    WORKING = "working"       # T0: KV-Cache managed, ~8K tokens, <1ms
    EPISODIC = "episodic"     # T1: Active reconstruction, ~100K tokens
    SEMANTIC = "semantic"     # T2: MAGMA 4-graph, ~1M tokens
    PROCEDURAL = "procedural"  # T3: Skills/workflows, unbounded


# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RawMemory:
    """A raw memory before routing."""

    id: str
    content: str
    content_type: str = "text"  # text, code, tool_output, conversation, etc.
    source: str = ""            # agent or session that produced this
    token_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MemoryFeatures:
    """Extracted features used for routing decisions."""

    content_length: int
    content_type_id: int  # hashed content_type → int bucket
    has_code: bool
    has_urls: bool
    entity_count: int
    token_count: int
    hour_of_day: int


@dataclass(frozen=True)
class StoreDecision:
    """Result of memory routing."""

    store: MemoryTier
    compression_level: float  # 0-1, 0 = no compression, 1 = max compression
    retention_policy: str     # "ephemeral", "session", "long_term", "permanent"
    confidence: float         # 0-1 bandit confidence
    reason: str = ""


# ---------------------------------------------------------------------------
# Multi-Armed Bandit (ε-greedy over store tiers)
# ---------------------------------------------------------------------------


@dataclass
class BanditArm:
    """Statistics for one store tier in the bandit."""

    tier: MemoryTier
    pulls: int = 0
    total_reward: float = 0.0
    sum_sq_reward: float = 0.0  # for UCB

    @property
    def mean(self) -> float:
        return self.total_reward / self.pulls if self.pulls > 0 else 0.5

    @property
    def ucb(self) -> float:
        """Upper Confidence Bound (UCB1)."""
        if self.pulls == 0:
            return float("inf")
        return self.mean + math.sqrt(2 * math.log(self.pulls + 1) / self.pulls)

    def update(self, reward: float) -> None:
        self.pulls += 1
        self.total_reward += reward
        self.sum_sq_reward += reward * reward


@dataclass
class MultiArmedBandit:
    """ε-greedy + UCB multi-armed bandit over memory store tiers."""

    arms: dict[MemoryTier, BanditArm] = field(default_factory=dict)
    epsilon: float = 0.1
    _total_pulls: int = 0

    def __post_init__(self) -> None:
        for tier in MemoryTier:
            if tier not in self.arms:
                self.arms[tier] = BanditArm(tier=tier)

    def select(self, features: MemoryFeatures) -> tuple[MemoryTier, float]:
        """Select best arm (store tier) for the given features.

        Returns (tier, confidence).
        """
        self._total_pulls += 1

        # ε-greedy exploration
        if random.random() < self.epsilon:
            tier = random.choice(list(MemoryTier))
            arm = self.arms[tier]
            return tier, max(0.0, min(1.0, arm.mean))

        # Greedy: pick highest UCB
        best_tier = MemoryTier.WORKING
        best_ucb = -1.0
        for tier, arm in self.arms.items():
            ucb = arm.ucb
            if ucb > best_ucb:
                best_ucb = ucb
                best_tier = tier

        arm = self.arms[best_tier]
        confidence = max(0.0, min(1.0, arm.mean))
        return best_tier, confidence

    def update(self, tier: MemoryTier, reward: float) -> None:
        """Feed back a reward signal for the chosen tier."""
        if tier in self.arms:
            self.arms[tier].update(reward)

    @property
    def stats(self) -> dict[str, dict[str, Any]]:
        return {
            t.value: {"pulls": a.pulls, "mean": round(a.mean, 4), "ucb": round(a.ucb, 4)}
            for t, a in self.arms.items()
        }


# ---------------------------------------------------------------------------
# Feature Extractor
# ---------------------------------------------------------------------------


@dataclass
class FeatureExtractor:
    """Extracts routing-relevant features from raw memory."""

    def extract(self, memory: RawMemory) -> MemoryFeatures:
        content = memory.content
        return MemoryFeatures(
            content_length=len(content),
            content_type_id=hash(memory.content_type) % 100,
            has_code="```" in content or "def " in content or "class " in content,
            has_urls="http://" in content or "https://" in content,
            entity_count=content.count("\n") + 1,  # rough: lines ≈ entities
            token_count=memory.token_count or max(1, len(content) // 4),
            hour_of_day=0,  # filled by router if time-aware
        )


# ---------------------------------------------------------------------------
# Compression & Retention Policies
# ---------------------------------------------------------------------------


@dataclass
class CompressionPolicy:
    """Determines compression level based on memory features."""

    min_compression: float = 0.0
    max_compression: float = 1.0

    def decide(self, features: MemoryFeatures, tier: MemoryTier) -> float:
        """Return compression level 0-1 for the given memory."""
        if tier == MemoryTier.WORKING:
            return 0.0  # working memory: no compression
        if tier == MemoryTier.EPISODIC:
            return 0.3  # light summarization
        if tier == MemoryTier.SEMANTIC:
            return 0.6  # extract entities + relations only
        # Procedural: compress heavily, keep only the pattern
        return 0.8


@dataclass
class RetentionPolicy:
    """Determines retention policy based on memory features."""

    def decide(self, features: MemoryFeatures, tier: MemoryTier) -> str:
        if tier == MemoryTier.WORKING:
            return "ephemeral"
        if tier == MemoryTier.EPISODIC:
            return "session"
        if tier == MemoryTier.SEMANTIC:
            return "long_term"
        return "permanent"


# ---------------------------------------------------------------------------
# Unified Memory Router
# ---------------------------------------------------------------------------


@dataclass
class UnifiedMemoryRouter:
    """Routes memories to optimal store based on content + access pattern + cost.

    Usage::

        router = UnifiedMemoryRouter()
        decision = router.route(RawMemory(id="m1", content="..."))
        store.write(memory, tier=decision.store)
        # Later, feed back reward:
        router.feedback("m1", reward=0.9)
    """

    extractor: FeatureExtractor = field(default_factory=FeatureExtractor)
    bandit: MultiArmedBandit = field(default_factory=MultiArmedBandit)
    compression_policy: CompressionPolicy = field(default_factory=CompressionPolicy)
    retention_policy: RetentionPolicy = field(default_factory=RetentionPolicy)
    _routing_history: dict[str, StoreDecision] = field(default_factory=dict)

    def route(self, memory: RawMemory) -> StoreDecision:
        """Route a raw memory to the optimal store tier."""
        features = self.extractor.extract(memory)
        tier, confidence = self.bandit.select(features)
        compression = self.compression_policy.decide(features, tier)
        retention = self.retention_policy.decide(features, tier)

        decision = StoreDecision(
            store=tier,
            compression_level=compression,
            retention_policy=retention,
            confidence=confidence,
            reason=f"bandit(ε={self.bandit.epsilon}, pulls={self.bandit._total_pulls})",
        )
        self._routing_history[memory.id] = decision
        return decision

    def feedback(self, memory_id: str, reward: float) -> None:
        """Feed back a reward for a previous routing decision.

        Reward should be 0-1, where 1 = perfect routing, 0 = wrong store.
        """
        decision = self._routing_history.get(memory_id)
        if decision is not None:
            self.bandit.update(decision.store, reward)

    def route_batch(self, memories: list[RawMemory]) -> list[StoreDecision]:
        """Route multiple memories at once."""
        return [self.route(m) for m in memories]

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_routes": len(self._routing_history),
            "bandit": self.bandit.stats,
        }


__all__ = [
    "BanditArm",
    "CompressionPolicy",
    "FeatureExtractor",
    "MemoryFeatures",
    "MemoryTier",
    "MultiArmedBandit",
    "RawMemory",
    "RetentionPolicy",
    "StoreDecision",
    "UnifiedMemoryRouter",
]
