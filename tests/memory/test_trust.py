"""Tests for the Trust Scoring module.

Covers TrustScore and TrustWeightedBroadcast.
"""
from __future__ import annotations

import time

import pytest

from lyra.memory.trust import (
    TRUST_CONTRADICTION_DECREMENT,
    TRUST_DECAY_DAYS_THRESHOLD,
    TRUST_DECAY_PER_DAY,
    TRUST_DEFAULT,
    TRUST_SUCCESS_INCREMENT,
    TrustScore,
    TrustWeightedBroadcast,
)
from lyra.memory.population_broadcast import (
    SynthesizedMemory,
    MemoryTypeCategory,
)


# ===================================================================
# TrustScore tests
# ===================================================================


class TestTrustScore:
    """Tests for the TrustScore dataclass."""

    def test_default_creation(self) -> None:
        score = TrustScore()
        assert score.value == TRUST_DEFAULT
        assert score.evidence_count == 0
        assert score.last_updated > 0

    def test_custom_values(self) -> None:
        score = TrustScore(value=0.8, evidence_count=5, last_updated=1000.0)
        assert score.value == 0.8
        assert score.evidence_count == 5
        assert score.last_updated == 1000.0

    def test_record_success_increases_trust(self) -> None:
        score = TrustScore(value=0.5)
        new_score = score.record_success()
        assert new_score.value == 0.5 + TRUST_SUCCESS_INCREMENT
        assert new_score.evidence_count == 1
        assert new_score.last_updated >= score.last_updated

    def test_record_success_capped(self) -> None:
        score = TrustScore(value=0.95)
        new_score = score.record_success()
        assert new_score.value == 1.0  # Capped

    def test_record_contradiction_decreases_trust(self) -> None:
        score = TrustScore(value=0.7)
        new_score = score.record_contradiction()
        assert new_score.value == 0.7 - TRUST_CONTRADICTION_DECREMENT
        assert new_score.evidence_count == 1

    def test_record_contradiction_floor(self) -> None:
        score = TrustScore(value=0.1)
        new_score = score.record_contradiction()
        assert new_score.value == 0.0  # Floored

    def test_record_staleness_before_threshold(self) -> None:
        score = TrustScore(value=0.7)
        new_score = score.record_staleness(days=TRUST_DECAY_DAYS_THRESHOLD)
        assert new_score.value == 0.7  # No decay

    def test_record_staleness_after_threshold(self) -> None:
        score = TrustScore(value=0.8)
        days = TRUST_DECAY_DAYS_THRESHOLD + 10
        decay = TRUST_DECAY_PER_DAY * 10
        new_score = score.record_staleness(days=days)
        assert new_score.value == 0.8 - decay

    def test_record_staleness_floor(self) -> None:
        score = TrustScore(value=0.1)
        new_score = score.record_staleness(days=TRUST_DECAY_DAYS_THRESHOLD + 1000)
        assert new_score.value == 0.0

    def test_record_staleness_preserves_evidence_count(self) -> None:
        score = TrustScore(value=0.5, evidence_count=3)
        new_score = score.record_staleness(days=TRUST_DECAY_DAYS_THRESHOLD + 5)
        assert new_score.evidence_count == 3

    def test_confidence_level_high(self) -> None:
        assert TrustScore(value=0.9).confidence_level == "high"
        assert TrustScore(value=0.8).confidence_level == "high"

    def test_confidence_level_medium(self) -> None:
        assert TrustScore(value=0.7).confidence_level == "medium"
        assert TrustScore(value=0.6).confidence_level == "medium"

    def test_confidence_level_neutral(self) -> None:
        assert TrustScore(value=0.5).confidence_level == "neutral"
        assert TrustScore(value=0.4).confidence_level == "neutral"

    def test_confidence_level_low(self) -> None:
        assert TrustScore(value=0.3).confidence_level == "low"
        assert TrustScore(value=0.0).confidence_level == "low"

    def test_record_success_returns_new_object(self) -> None:
        score = TrustScore(value=0.5)
        new_score = score.record_success()
        assert new_score.value > score.value
        assert score.value == 0.5  # Original unchanged


# ===================================================================
# TrustWeightedBroadcast tests
# ===================================================================


class TestTrustWeightedBroadcast:
    """Tests for the TrustWeightedBroadcast class."""

    def test_creation_defaults(self) -> None:
        twb = TrustWeightedBroadcast()
        assert twb.agent_trust_scores == {}
        assert twb.min_broadcast_weight == 0.3

    def test_record_agent_success(self) -> None:
        twb = TrustWeightedBroadcast()
        twb.record_agent_success("agent-1")
        assert "agent-1" in twb.agent_trust_scores
        assert twb.agent_trust_scores["agent-1"].value > TRUST_DEFAULT

    def test_record_agent_contradiction(self) -> None:
        twb = TrustWeightedBroadcast()
        twb.record_agent_success("agent-1")  # First boost
        twb.record_agent_contradiction("agent-1")  # Then decrease
        # Value should be lower than after just one success
        score = twb.agent_trust_scores["agent-1"]
        assert score.evidence_count == 2

    def test_apply_staleness(self) -> None:
        twb = TrustWeightedBroadcast()
        twb.record_agent_success("agent-1")
        twb.apply_staleness("agent-1", days=TRUST_DECAY_DAYS_THRESHOLD + 10)
        score = twb.agent_trust_scores["agent-1"]
        # Should have decayed below the post-success value
        expected = min(1.0, TRUST_DEFAULT + TRUST_SUCCESS_INCREMENT) - TRUST_DECAY_PER_DAY * 10
        assert score.value <= expected + 0.01

    def test_get_trust_weight(self) -> None:
        twb = TrustWeightedBroadcast()
        # Unknown agent returns default trust (0.5), weight = 0.5 * 2.0 = 1.0
        weight = twb.get_trust_weight("unknown")
        assert weight == TRUST_DEFAULT * 2.0

    def test_get_trust_weight_maxed(self) -> None:
        twb = TrustWeightedBroadcast()
        twb.agent_trust_scores["agent-1"] = TrustScore(value=1.0)
        weight = twb.get_trust_weight("agent-1")
        assert weight == 2.0

    def test_is_broadcast_eligible_default(self) -> None:
        twb = TrustWeightedBroadcast(min_broadcast_weight=0.3)
        # Default trust 0.5 * 2 = 1.0 >= 0.3
        assert twb.is_broadcast_eligible("unknown") is True

    def test_is_broadcast_eligible_low_trust(self) -> None:
        twb = TrustWeightedBroadcast(min_broadcast_weight=1.0)
        twb.agent_trust_scores["bad-agent"] = TrustScore(value=0.2)
        # 0.2 * 2.0 = 0.4 < 1.0
        assert twb.is_broadcast_eligible("bad-agent") is False

    def test_is_broadcast_eligible_high_trust(self) -> None:
        twb = TrustWeightedBroadcast(min_broadcast_weight=0.5)
        twb.agent_trust_scores["good-agent"] = TrustScore(value=0.8)
        # 0.8 * 2.0 = 1.6 >= 0.5
        assert twb.is_broadcast_eligible("good-agent") is True

    def test_broadcast_weights_memories(self) -> None:
        twb = TrustWeightedBroadcast(min_broadcast_weight=0.0)
        # Set trust scores for some agents
        twb.agent_trust_scores["agent-high"] = TrustScore(value=0.9)
        twb.agent_trust_scores["agent-low"] = TrustScore(value=0.1)

        class MockMemory:
            def __init__(self, source_agent_id):
                self.source_agent_id = source_agent_id

        memories = [
            MockMemory("agent-high"),
            MockMemory("agent-low"),
        ]

        weighted = twb.broadcast(memories)
        # High trust memory should have higher weight
        assert len(weighted) == 2
        assert weighted[0][1] > weighted[1][1]

    def test_broadcast_filters_low_weight(self) -> None:
        twb = TrustWeightedBroadcast(min_broadcast_weight=1.0)
        twb.agent_trust_scores["agent-low"] = TrustScore(value=0.2)

        class MockMemory:
            def __init__(self, source_agent_id):
                self.source_agent_id = source_agent_id

        memories = [MockMemory("agent-low")]
        weighted = twb.broadcast(memories)
        assert weighted == []  # Filtered out

    def test_broadcast_with_external_scores(self) -> None:
        twb = TrustWeightedBroadcast(min_broadcast_weight=0.0)
        ext_scores = {"ext-agent": TrustScore(value=0.7)}

        class MockMemory:
            def __init__(self, source_agent_id):
                self.source_agent_id = source_agent_id

        memories = [MockMemory("ext-agent")]
        weighted = twb.broadcast(memories, agent_trust_scores=ext_scores)
        assert len(weighted) == 1
        assert weighted[0][1] == 0.7 * 2.0

    def test_broadcast_skips_memories_without_source(self) -> None:
        twb = TrustWeightedBroadcast(min_broadcast_weight=0.0)

        class NoSourceMemory:
            pass

        memories = [NoSourceMemory()]
        weighted = twb.broadcast(memories)
        assert weighted == []

    def test_get_statistics_empty(self) -> None:
        twb = TrustWeightedBroadcast()
        stats = twb.get_statistics()
        assert stats["agent_count"] == 0
        assert stats["avg_trust"] == 0.0

    def test_get_statistics_with_agents(self) -> None:
        twb = TrustWeightedBroadcast()
        twb.agent_trust_scores["a1"] = TrustScore(value=0.9)
        twb.agent_trust_scores["a2"] = TrustScore(value=0.3)
        stats = twb.get_statistics()
        assert stats["agent_count"] == 2
        assert stats["avg_trust"] == 0.6
        assert stats["high_trust_agents"] == 1
        assert stats["low_trust_agents"] == 1
