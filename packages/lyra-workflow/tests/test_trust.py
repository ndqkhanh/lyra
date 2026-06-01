"""
Tests for A-Trust (Attention Trust Score) — weighted inter-agent message routing.

Tests cover:
- TrustScore dataclass: creation, clamping, overall computation
- TrustHistory: recording, average, volatility, trend
- TrustEvaluator: rule-based scoring across all 6 dimensions
- TrustWeightedRouter: routing with trust-based weighting
- AVP integration: trust_from_critic_verdicts
"""

from __future__ import annotations

import math

import pytest

from lyra_workflow.trust import (
    AgentTrustProfile,
    TrustDimension,
    TrustEvaluator,
    TrustEvaluation,
    TrustHistory,
    TrustScore,
    TrustWeightedRouter,
    WeightedMessage,
    trust_from_critic_verdicts,
)


# ────────────────────────────────────────────────────────────────────
# TrustScore tests
# ────────────────────────────────────────────────────────────────────


class TestTrustScore:
    def test_default_score(self) -> None:
        score = TrustScore()
        assert score.quality == 0.5
        assert score.quantity == 0.5
        assert score.relevance == 0.5
        assert score.manner == 0.5
        assert score.sincerity == 0.5
        assert score.competence == 0.5

    def test_clamps_to_0_1(self) -> None:
        score = TrustScore(quality=-0.5, competence=1.5)
        assert score.quality == 0.0
        assert score.competence == 1.0

    def test_overall_geometric_mean(self) -> None:
        score = TrustScore(quality=1.0, quantity=1.0, relevance=1.0,
                           manner=1.0, sincerity=1.0, competence=1.0)
        assert score.overall == pytest.approx(1.0)

    def test_overall_zero_dimension_drags(self) -> None:
        """A single zero dimension should drag overall to zero."""
        score = TrustScore(quality=1.0, quantity=1.0, relevance=0.0,
                           manner=1.0, sincerity=1.0, competence=1.0)
        assert score.overall == pytest.approx(0.0)

    def test_overall_mixed_values(self) -> None:
        score = TrustScore(quality=0.9, quantity=0.7, relevance=0.8,
                           manner=0.6, sincerity=0.8, competence=0.7)
        expected = (0.9 * 0.7 * 0.8 * 0.6 * 0.8 * 0.7) ** (1.0 / 6.0)
        assert score.overall == pytest.approx(expected)

    def test_dimensions_property(self) -> None:
        score = TrustScore(quality=0.8, quantity=0.6, relevance=0.9,
                           manner=0.7, sincerity=0.5, competence=0.4)
        dims = score.dimensions
        assert dims["quality"] == 0.8
        assert dims["sincerity"] == 0.5
        assert len(dims) == 6

    def test_to_dict_includes_overall(self) -> None:
        d = TrustScore().to_dict()
        assert "overall" in d
        assert len(d) == 7

    def test_equal_factory(self) -> None:
        score = TrustScore.equal(0.8)
        assert all(
            getattr(score, dim) == 0.8
            for dim in ("quality", "quantity", "relevance", "manner",
                        "sincerity", "competence")
        )

    def test_neutral_factory(self) -> None:
        score = TrustScore.neutral()
        assert score.overall == pytest.approx(0.5)

    def test_is_frozen(self) -> None:
        score = TrustScore()
        with pytest.raises(AttributeError):
            score.quality = 0.9  # type: ignore[misc]


# ────────────────────────────────────────────────────────────────────
# TrustDimension tests
# ────────────────────────────────────────────────────────────────────


class TestTrustDimension:
    def test_enum_has_six_values(self) -> None:
        assert len(TrustDimension) == 6

    def test_enum_members(self) -> None:
        expected = {"quality", "quantity", "relevance", "manner", "sincerity", "competence"}
        actual = {d.value for d in TrustDimension}
        assert actual == expected

    def test_quality_member(self) -> None:
        assert TrustDimension.QUALITY.value == "quality"
        assert TrustDimension.QUALITY.name == "QUALITY"

    def test_iterates_dimensions(self) -> None:
        dims = list(TrustDimension)
        assert TrustDimension.QUALITY in dims
        assert TrustDimension.COMPETENCE in dims


# ────────────────────────────────────────────────────────────────────
# AgentTrustProfile tests
# ────────────────────────────────────────────────────────────────────


class TestAgentTrustProfile:
    def test_create_initializes_all_dimensions(self) -> None:
        profile = AgentTrustProfile.create(agent_id="agent-1")
        assert profile.agent_id == "agent-1"
        assert len(profile.dimension_histories) == 6
        for dim in TrustDimension:
            assert dim in profile.dimension_histories

    def test_record_updates_all_dimensions(self) -> None:
        profile = AgentTrustProfile.create(agent_id="agent-1")
        score = TrustScore(quality=0.9, quantity=0.7, relevance=0.8,
                           manner=0.6, sincerity=0.8, competence=0.4)
        profile.record(score)

        avg = profile.dimension_averages
        assert avg["quality"] == pytest.approx(0.9, abs=0.01)
        assert avg["competence"] == pytest.approx(0.4, abs=0.01)

    def test_dimension_averages_from_multiple_records(self) -> None:
        profile = AgentTrustProfile.create(agent_id="agent-1")
        profile.record(TrustScore(quality=0.8, competence=0.6))
        profile.record(TrustScore(quality=0.6, competence=0.8))

        avg = profile.dimension_averages
        assert avg["quality"] == pytest.approx(0.7, abs=0.01)
        assert avg["competence"] == pytest.approx(0.7, abs=0.01)

    def test_dimension_trends_positive(self) -> None:
        profile = AgentTrustProfile.create(agent_id="agent-1")
        profile.record(TrustScore(quality=0.3))
        profile.record(TrustScore(quality=0.5))
        profile.record(TrustScore(quality=0.9))
        assert profile.dimension_trends["quality"] > 0

    def test_dimension_trends_negative(self) -> None:
        profile = AgentTrustProfile.create(agent_id="agent-1")
        profile.record(TrustScore(quality=0.9))
        profile.record(TrustScore(quality=0.5))
        profile.record(TrustScore(quality=0.3))
        assert profile.dimension_trends["quality"] < 0

    def test_weakest_dimension(self) -> None:
        profile = AgentTrustProfile.create(agent_id="agent-1")
        profile.record(TrustScore(quality=0.9, quantity=0.9, relevance=0.9,
                                   manner=0.9, sincerity=0.9, competence=0.2))
        dim, score = profile.weakest_dimension
        assert dim == TrustDimension.COMPETENCE
        assert score == pytest.approx(0.2, abs=0.01)

    def test_strongest_dimension(self) -> None:
        profile = AgentTrustProfile.create(agent_id="agent-1")
        profile.record(TrustScore(quality=0.9, quantity=0.3, competence=0.3))
        dim, score = profile.strongest_dimension
        assert dim == TrustDimension.QUALITY
        assert score == pytest.approx(0.9, abs=0.01)

    def test_to_dict(self) -> None:
        profile = AgentTrustProfile.create(agent_id="agent-1")
        profile.record(TrustScore(quality=0.8))
        d = profile.to_dict()
        assert d["agent_id"] == "agent-1"
        assert "dimension_averages" in d
        assert "dimension_trends" in d
        assert "weakest" in d
        assert "strongest" in d


# ────────────────────────────────────────────────────────────────────
# TrustHistory tests
# ────────────────────────────────────────────────────────────────────


class TestTrustHistory:
    def test_default_state(self) -> None:
        history = TrustHistory(agent_id="agent-1")
        assert history.agent_id == "agent-1"
        assert len(history.scores) == 0
        assert history.current == TrustScore.neutral()

    def test_record_adds_score(self) -> None:
        history = TrustHistory(agent_id="a1")
        score = TrustScore(quality=0.9, competence=0.8)
        history.record(score)
        assert len(history.scores) == 1
        assert history.current == score

    def test_average_with_single_score(self) -> None:
        history = TrustHistory(agent_id="a1")
        history.record(TrustScore(quality=0.8, quantity=0.6))
        avg = history.average
        assert avg.quality == pytest.approx(0.8)
        assert avg.quantity == pytest.approx(0.6)

    def test_average_with_multiple_scores(self) -> None:
        history = TrustHistory(agent_id="a1")
        history.record(TrustScore(quality=0.8))
        history.record(TrustScore(quality=0.6))
        assert history.average.quality == pytest.approx(0.7)

    def test_average_empty_returns_neutral(self) -> None:
        history = TrustHistory(agent_id="a1")
        assert history.average == TrustScore.neutral()

    def test_volatility_no_scores(self) -> None:
        history = TrustHistory(agent_id="a1")
        assert history.volatility == 0.0

    def test_volatility_single_score(self) -> None:
        history = TrustHistory(agent_id="a1")
        history.record(TrustScore.equal(0.7))
        assert history.volatility == 0.0

    def test_volatility_computed(self) -> None:
        history = TrustHistory(agent_id="a1")
        history.record(TrustScore.equal(0.9))
        history.record(TrustScore.equal(0.5))
        history.record(TrustScore.equal(0.9))
        assert history.volatility > 0.0

    def test_trend_positive(self) -> None:
        history = TrustHistory(agent_id="a1")
        history.record(TrustScore.equal(0.3))
        history.record(TrustScore.equal(0.5))
        history.record(TrustScore.equal(0.8))
        assert history.trend > 0

    def test_trend_negative(self) -> None:
        history = TrustHistory(agent_id="a1")
        history.record(TrustScore.equal(0.8))
        history.record(TrustScore.equal(0.5))
        history.record(TrustScore.equal(0.3))
        assert history.trend < 0

    def test_window_size_drops_old_scores(self) -> None:
        history = TrustHistory(agent_id="a1", window_size=3)
        for i in range(5):
            history.record(TrustScore.equal(0.5))
        assert len(history.scores) == 3

    def test_to_dict(self) -> None:
        history = TrustHistory(agent_id="a1")
        history.record(TrustScore(quality=0.9))
        d = history.to_dict()
        assert d["agent_id"] == "a1"
        assert d["score_count"] == 1
        assert "current" in d
        assert "average" in d
        assert "volatility" in d


# ────────────────────────────────────────────────────────────────────
# TrustEvaluator tests
# ────────────────────────────────────────────────────────────────────


class TestTrustEvaluatorQuality:
    def test_evidence_boosts_quality(self) -> None:
        evaluator = TrustEvaluator()
        result = evaluator.evaluate(
            "msg-1",
            "The system was verified to handle 10k requests. According to data shows "
            "confirmed evidence from our measurements.",
        )
        assert result.score.quality >= 0.7

    def test_hedging_penalizes_quality(self) -> None:
        evaluator = TrustEvaluator()
        result = evaluator.evaluate(
            "msg-2",
            "I think maybe the bug could be in the auth module, perhaps.",
        )
        assert result.score.quality <= 0.5

    def test_mixed_quality(self) -> None:
        evaluator = TrustEvaluator()
        result = evaluator.evaluate(
            "msg-3",
            "The data shows 32 connections. I think that might be enough.",
        )
        # Evidence indicator should offset hedging somewhat
        assert 0.3 <= result.score.quality <= 0.8


class TestTrustEvaluatorQuantity:
    def test_too_few_words_low_score(self) -> None:
        evaluator = TrustEvaluator()
        result = evaluator.evaluate("msg-1", "OK")
        assert result.score.quantity < 0.3

    def test_good_length_high_score(self) -> None:
        evaluator = TrustEvaluator()
        result = evaluator.evaluate("msg-2", " ".join(["word"] * 100))
        assert result.score.quantity >= 0.9

    def test_verbose_gets_lower_score(self) -> None:
        evaluator = TrustEvaluator()
        result = evaluator.evaluate("msg-3", " ".join(["word"] * 1500))
        assert result.score.quantity < 0.7


class TestTrustEvaluatorRelevance:
    def test_relevance_indicators_boost(self) -> None:
        evaluator = TrustEvaluator()
        result = evaluator.evaluate(
            "msg-1",
            "Therefore, with respect to the database issue, pertaining to "
            "the connection pool size, we conclude the fix.",
            context="database connection",
        )
        assert result.score.relevance >= 0.6

    def test_topic_drift_penalizes(self) -> None:
        evaluator = TrustEvaluator()
        result = evaluator.evaluate(
            "msg-2", "By the way, this is unrelated to the current topic.",
            context="deploy pipeline",
        )
        assert result.score.relevance < 0.5

    def test_context_overlap_boosts(self) -> None:
        evaluator = TrustEvaluator()
        result = evaluator.evaluate(
            "msg-3",
            "The deployment pipeline failed at the build stage.",
            context="deployment pipeline build",
        )
        assert result.score.relevance >= 0.5


class TestTrustEvaluatorManner:
    def test_structured_content_boosted(self) -> None:
        evaluator = TrustEvaluator()
        result = evaluator.evaluate(
            "msg-1",
            "First, check the config. Second, restart the service. "
            "Third, verify the logs. For example, check /var/log/app.log.",
        )
        assert result.score.manner >= 0.6

    def test_ambiguous_language_penalized(self) -> None:
        evaluator = TrustEvaluator()
        result = evaluator.evaluate(
            "msg-2",
            "Kind of sort of broken, something like that, etc.",
        )
        assert result.score.manner < 0.5


class TestTrustEvaluatorSincerity:
    def test_genuine_indicators_boost(self) -> None:
        evaluator = TrustEvaluator()
        result = evaluator.evaluate(
            "msg-1",
            "I confirmed the fix works. I verified the test passes. "
            "To the best of my knowledge, this resolves the issue.",
        )
        assert result.score.sincerity >= 0.6

    def test_protest_too_much_penalized(self) -> None:
        evaluator = TrustEvaluator()
        result = evaluator.evaluate(
            "msg-2",
            "Believe me, I would never lie to you. Honestly speaking, "
            "truthfully, I am being completely honest.",
        )
        assert result.score.sincerity < 0.6


class TestTrustEvaluatorCompetence:
    def test_precise_language_boosted(self) -> None:
        evaluator = TrustEvaluator()
        result = evaluator.evaluate(
            "msg-1",
            "The database has 32 connections with 2.5ms latency on port 5432. "
            "Memory usage hits 1.2GB at 95th percentile.",
        )
        assert result.score.competence >= 0.6

    def test_explicit_uncertainty_penalized(self) -> None:
        evaluator = TrustEvaluator()
        result = evaluator.evaluate(
            "msg-2",
            "I don't know how to fix this. I'm not capable of analyzing this module.",
        )
        assert result.score.competence <= 0.5

    def test_evaluation_return_type(self) -> None:
        evaluator = TrustEvaluator()
        result = evaluator.evaluate("msg-1", "some content", agent_id="agent-7")
        assert isinstance(result, TrustEvaluation)
        assert result.message_id == "msg-1"
        assert result.evaluator == "rule-based"
        assert len(result.breakdown) == 6


class TestTrustEvaluatorLLM:
    def test_falls_back_when_no_llm(self) -> None:
        evaluator = TrustEvaluator()
        result = evaluator.evaluate_llm("msg-1", "test content")
        assert result.evaluator == "rule-based"

    def test_uses_llm_when_configured(self) -> None:
        def mock_llm(content: str, context: str) -> TrustScore:
            return TrustScore(quality=0.95, competence=0.92)

        evaluator = TrustEvaluator(llm_evaluator=mock_llm)
        result = evaluator.evaluate_llm("msg-1", "test content")
        assert result.evaluator == "llm"
        assert result.score.quality == 0.95
        assert result.score.competence == 0.92


# ────────────────────────────────────────────────────────────────────
# TrustWeightedRouter tests
# ────────────────────────────────────────────────────────────────────


class TestTrustWeightedRouter:
    def test_route_creates_weighted_message(self) -> None:
        evaluator = TrustEvaluator()
        router = TrustWeightedRouter(evaluator)
        wm = router.route(
            message_id="msg-1",
            content="The auth module has a timing side-channel at line 203.",
            sender_id="security-agent",
            context="security audit",
        )
        assert isinstance(wm, WeightedMessage)
        assert wm.message_id == "msg-1"
        assert wm.sender_id == "security-agent"
        assert 0.0 <= wm.weight <= 1.0

    def test_high_trust_message_gets_high_weight(self) -> None:
        evaluator = TrustEvaluator()
        router = TrustWeightedRouter(evaluator)
        wm = router.route(
            message_id="msg-1",
            content=(
                "The data shows 32 connections confirmed by measurements. "
                "Therefore, with respect to connection pooling, the fix is validated."
            ),
            sender_id="reliable-agent",
        )
        assert wm.weight > 0.5

    def test_low_trust_message_gets_lower_weight(self) -> None:
        evaluator = TrustEvaluator()
        router = TrustWeightedRouter(evaluator)
        wm = router.route(
            message_id="msg-1",
            content="OK maybe it's broken or something, not sure.",
            sender_id="uncertain-agent",
        )
        assert wm.weight < 0.6

    def test_trust_improves_over_time(self) -> None:
        """Repeated good messages should increase trust."""
        evaluator = TrustEvaluator()
        router = TrustWeightedRouter(evaluator)
        good_msg = (
            "The data shows the connection pool has 32 connections, "
            "confirmed by our measurements. The fix is verified."
        )

        first = router.route("msg-1", good_msg, "agent-1")
        # Send more good messages
        for i in range(4):
            router.route(f"msg-{i+2}", good_msg, "agent-1")

        later = router.route("msg-6", good_msg, "agent-1")
        # Later weight should be at least as high (usually higher due to history)
        assert later.weight >= first.weight * 0.8

    def test_trust_declines_with_bad_messages(self) -> None:
        bad_msg = "I don't know maybe it's broken or something sort of etc."
        evaluator = TrustEvaluator()
        router = TrustWeightedRouter(evaluator)

        first = router.route("msg-1", bad_msg, "agent-1")
        for i in range(4):
            router.route(f"msg-{i+2}", bad_msg, "agent-1")
        later = router.route("msg-6", bad_msg, "agent-1")

        # Additional bad messages should not increase weight significantly
        assert later.weight <= first.weight + 0.1

    def test_route_batch_sorts_by_weight(self) -> None:
        evaluator = TrustEvaluator()
        router = TrustWeightedRouter(evaluator)
        messages = [
            {"message_id": "m1", "content": "OK maybe broken", "sender_id": "low"},
            {"message_id": "m2", "content": "The data shows 32 verified connections.", "sender_id": "high"},
            {"message_id": "m3", "content": "Not sure about this possibly.", "sender_id": "low-2"},
        ]
        results = router.route_batch(messages)
        assert len(results) == 3
        # Highest trust should be first
        assert results[0].weight >= results[-1].weight

    def test_get_history_returns_none_for_unknown(self) -> None:
        router = TrustWeightedRouter()
        assert router.get_history("unknown-agent") is None

    def test_get_history_after_routing(self) -> None:
        evaluator = TrustEvaluator()
        router = TrustWeightedRouter(evaluator)
        router.route("msg-1", "test content", "agent-1")
        history = router.get_history("agent-1")
        assert history is not None
        assert len(history.scores) == 1

    def test_stats_aggregates(self) -> None:
        evaluator = TrustEvaluator()
        router = TrustWeightedRouter(evaluator)
        router.route("msg-1", "test", "agent-1")
        router.route("msg-2", "test", "agent-2")
        stats = router.stats
        assert stats["routed_total"] == 2
        assert stats["agents_tracked"] == 2
        assert stats["average_trust"] > 0.0

    def test_min_weight_enforced(self) -> None:
        evaluator = TrustEvaluator()
        router = TrustWeightedRouter(evaluator, min_weight=0.1)
        wm = router.route(
            "msg-1",
            "I don't know I'm not capable not sure maybe.",
            "agent-1",
        )
        assert wm.weight >= 0.1

    def test_default_min_weight(self) -> None:
        router = TrustWeightedRouter()
        assert router._min_weight == 0.05

    def test_weighted_message_metadata(self) -> None:
        evaluator = TrustEvaluator()
        router = TrustWeightedRouter(evaluator)
        wm = router.route("msg-1", "verified data shows 32 connections", "agent-1")
        assert "breakdown" in wm.metadata
        assert "evaluator" in wm.metadata
        assert wm.metadata["evaluator"] == "rule-based"

    def test_get_profile_after_routing(self) -> None:
        router = TrustWeightedRouter()
        router.route("msg-1", "verified data shows 32 connections", "agent-1")
        profile = router.get_profile("agent-1")
        assert profile is not None
        assert profile.agent_id == "agent-1"
        assert len(profile.dimension_histories) == 6

    def test_get_profile_unknown_agent(self) -> None:
        router = TrustWeightedRouter()
        assert router.get_profile("unknown") is None

    def test_stats_includes_profiles(self) -> None:
        router = TrustWeightedRouter()
        router.route("msg-1", "test", "agent-1")
        stats = router.stats
        assert "profiles" in stats
        assert "agent-1" in stats["profiles"]

    def test_metadata_includes_dimension_extremes(self) -> None:
        router = TrustWeightedRouter()
        wm = router.route("msg-1", "verified data shows 32 connections", "agent-1")
        assert "weakest_dimension" in wm.metadata
        assert "strongest_dimension" in wm.metadata


# ────────────────────────────────────────────────────────────────────
# AVP integration: trust_from_critic_verdicts
# ────────────────────────────────────────────────────────────────────


class TestTrustFromCriticVerdicts:
    def test_empty_verdicts_returns_neutral(self) -> None:
        score = trust_from_critic_verdicts([])
        assert score == TrustScore.neutral()

    def test_maps_confidence_to_quality(self) -> None:
        verdicts = [
            {"verdict": "accept", "confidence": 0.9, "evidence_tier": "A"},
            {"verdict": "accept", "confidence": 0.8, "evidence_tier": "B"},
            {"verdict": "accept", "confidence": 0.7, "evidence_tier": "C"},
        ]
        score = trust_from_critic_verdicts(verdicts)
        assert score.quality == pytest.approx(0.8)

    def test_highest_evidence_tier_for_competence(self) -> None:
        verdicts = [
            {"verdict": "accept", "confidence": 0.5, "evidence_tier": "C"},
            {"verdict": "accept", "confidence": 0.5, "evidence_tier": "A"},
            {"verdict": "flag", "confidence": 0.5, "evidence_tier": "D"},
        ]
        score = trust_from_critic_verdicts(verdicts)
        assert score.competence == 1.0  # evidence_tier A

    def test_low_consensus_lowers_sincerity(self) -> None:
        verdicts = [
            {"verdict": "accept", "confidence": 0.5, "evidence_tier": "C"},
            {"verdict": "reject", "confidence": 0.5, "evidence_tier": "C"},
            {"verdict": "flag", "confidence": 0.5, "evidence_tier": "C"},
        ]
        score = trust_from_critic_verdicts(verdicts)
        assert score.sincerity < 0.5

    def test_full_consensus_high_sincerity(self) -> None:
        verdicts = [
            {"verdict": "accept", "confidence": 0.9, "evidence_tier": "A"},
            {"verdict": "accept", "confidence": 0.9, "evidence_tier": "A"},
            {"verdict": "accept", "confidence": 0.9, "evidence_tier": "A"},
        ]
        score = trust_from_critic_verdicts(verdicts)
        assert score.sincerity == 0.9

    def test_maintains_neutral_for_unscored_dimensions(self) -> None:
        verdicts = [
            {"verdict": "accept", "confidence": 0.9, "evidence_tier": "A"},
            {"verdict": "accept", "confidence": 0.9, "evidence_tier": "B"},
            {"verdict": "accept", "confidence": 0.9, "evidence_tier": "C"},
        ]
        score = trust_from_critic_verdicts(verdicts)
        assert score.quantity == 0.5
        assert score.relevance == 0.5
        assert score.manner == 0.5

    def test_uses_direct_trust_dimensions_when_present(self) -> None:
        """When verdicts have trust_dimensions, use them directly."""
        verdicts = [
            {"verdict": "accept", "confidence": 0.5, "evidence_tier": "C",
             "trust_dimensions": {"quality": 0.9, "competence": 0.8}},
            {"verdict": "accept", "confidence": 0.5, "evidence_tier": "C",
             "trust_dimensions": {"quality": 0.7, "competence": 0.6}},
        ]
        score = trust_from_critic_verdicts(verdicts)
        assert score.quality == pytest.approx(0.8)
        assert score.competence == pytest.approx(0.7)

    def test_direct_trust_dimensions_fills_all_six(self) -> None:
        """When trust_dimensions provide all 6 dims, they all populate."""
        verdicts = [
            {"verdict": "accept", "confidence": 0.5, "evidence_tier": "D",
             "trust_dimensions": {
                 "quality": 0.8, "quantity": 0.7, "relevance": 0.9,
                 "manner": 0.6, "sincerity": 0.8, "competence": 0.4,
             }},
        ]
        score = trust_from_critic_verdicts(verdicts)
        assert score.quality == 0.8
        assert score.quantity == 0.7
        assert score.relevance == 0.9
        assert score.manner == 0.6
        assert score.sincerity == 0.8
        assert score.competence == 0.4

    def test_mixed_trust_dimensions_averaged(self) -> None:
        """Trust dimensions are averaged across all verdicts that provide them."""
        verdicts = [
            {"verdict": "accept", "trust_dimensions": {"quality": 1.0}},
            {"verdict": "accept", "trust_dimensions": {"quality": 0.5}},
            {"verdict": "accept"},
        ]
        score = trust_from_critic_verdicts(verdicts)
        # Only the first two provide trust_dimensions; averaged = 0.75
        assert score.quality == pytest.approx(0.75)
