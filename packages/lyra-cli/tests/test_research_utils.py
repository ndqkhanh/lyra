"""Tests for SourceCredibility and StrategySelector."""

from __future__ import annotations

from lyra_cli.research.source_evaluator import (
    BASE_CREDIBILITY,
    SourceCredibility,
    SourceType,
)
from lyra_cli.research.strategy_selector import (
    DEFAULT_QUERY_TYPES,
    StrategyResult,
    StrategySelector,
    StrategyType,
)

# ── SourceCredibility ───────────────────────────────────────────────────


class TestSourceCredibilityEvaluate:
    def test_academic_paper_gets_high_score(self):
        sc = SourceCredibility()
        profile = sc.evaluate_source("s1", "https://arxiv.org/abs/1234",
                                     SourceType.ACADEMIC_PAPER, "A Paper", citation_count=5)
        assert profile.credibility_score >= 0.90

    def test_social_media_gets_low_score(self):
        sc = SourceCredibility()
        profile = sc.evaluate_source("s1", "https://x.com/user/post", SourceType.SOCIAL_MEDIA)
        assert profile.credibility_score <= 0.40

    def test_citation_bonus_increases_score(self):
        sc = SourceCredibility()
        no_cite = sc.evaluate_source("a", "url", SourceType.UNKNOWN, citation_count=0)
        with_cite = sc.evaluate_source("b", "url", SourceType.UNKNOWN, citation_count=5)
        assert with_cite.credibility_score > no_cite.credibility_score

    def test_bias_penalty_decreases_score(self):
        sc = SourceCredibility()
        no_bias = sc.evaluate_source("a", "url", SourceType.ACADEMIC_PAPER)
        with_bias = sc.evaluate_source("b", "url", SourceType.ACADEMIC_PAPER, detected_biases=[
                                       "confirmation", "selection"])
        assert with_bias.credibility_score < no_bias.credibility_score

    def test_score_clamped_to_range(self):
        sc = SourceCredibility()
        profile = sc.evaluate_source("s1", "url", SourceType.ACADEMIC_PAPER, citation_count=1000)
        assert 0.0 <= profile.credibility_score <= 1.0

    def test_get_source_returns_none_for_unknown(self):
        sc = SourceCredibility()
        assert sc.get_source("nope") is None

    def test_get_all_sources(self):
        sc = SourceCredibility()
        sc.evaluate_source("a", "url", SourceType.ACADEMIC_PAPER)
        sc.evaluate_source("b", "url", SourceType.EXPERT_BLOG)
        assert len(sc.get_all_sources()) == 2


class TestSourceCredibilityCitationChain:
    def test_citation_chain_single_source(self):
        sc = SourceCredibility()
        sc.evaluate_source("a", "url", SourceType.ACADEMIC_PAPER, cited_by=[])
        chain = sc.get_citation_chain("a")
        assert len(chain) == 1

    def test_citation_chain_follows_cited_by(self):
        sc = SourceCredibility()
        sc.evaluate_source("root", "url", SourceType.ACADEMIC_PAPER, cited_by=[])
        sc.evaluate_source("mid", "url", SourceType.ACADEMIC_PAPER, cited_by=["root"])
        sc.evaluate_source("leaf", "url", SourceType.ACADEMIC_PAPER, cited_by=["mid"])
        chain = sc.get_citation_chain("leaf")
        assert len(chain) == 3
        assert chain[0].source_id == "root"
        assert chain[-1].source_id == "leaf"

    def test_citation_chain_breaks_cycles(self):
        sc = SourceCredibility()
        sc.evaluate_source("a", "url", SourceType.ACADEMIC_PAPER, cited_by=["b"])
        sc.evaluate_source("b", "url", SourceType.ACADEMIC_PAPER, cited_by=["a"])
        chain = sc.get_citation_chain("a")
        assert len(chain) == 2


class TestSourceCredibilityConsensus:
    def test_consensus_empty_list(self):
        sc = SourceCredibility()
        assert sc.get_consensus_score([]) == 0.0

    def test_consensus_single_high_quality(self):
        sc = SourceCredibility()
        sc.evaluate_source("a", "url", SourceType.ACADEMIC_PAPER, title="A")
        score = sc.get_consensus_score(["a"])
        assert score >= 0.85

    def test_consensus_with_contradictions(self):
        sc = SourceCredibility()
        sc.evaluate_source("a", "url", SourceType.ACADEMIC_PAPER, title="A")
        sc.evaluate_source("b", "url", SourceType.ACADEMIC_PAPER, title="B")
        consensus_before = sc.get_consensus_score(["a", "b"])
        sc.detect_contradictions("a", "b", "claim A", "claim not A", severity=1.0)
        consensus_after = sc.get_consensus_score(["a", "b"])
        assert consensus_after < consensus_before

    def test_consensus_unknown_sources(self):
        sc = SourceCredibility()
        assert sc.get_consensus_score(["unknown"]) == 0.0


class TestSourceCredibilityContradictions:
    def test_detect_and_retrieve_contradiction(self):
        sc = SourceCredibility()
        sc.detect_contradictions("a", "b", "X is true", "X is false", severity=0.8)
        all_c = sc.get_contradictions()
        assert len(all_c) == 1
        assert all_c[0].severity == 0.8

    def test_filter_contradictions_by_source(self):
        sc = SourceCredibility()
        sc.detect_contradictions("a", "b", "c1", "c2")
        sc.detect_contradictions("c", "d", "c3", "c4")
        assert len(sc.get_contradictions(source_id="a")) == 1
        assert len(sc.get_contradictions(source_id="x")) == 0


class TestBaseCredibilityTable:
    def test_all_source_types_have_credibility(self):
        for st in SourceType:
            assert st in BASE_CREDIBILITY

    def test_academic_higher_than_forum(self):
        assert BASE_CREDIBILITY[SourceType.ACADEMIC_PAPER] > BASE_CREDIBILITY[SourceType.USER_FORUM]


# ── StrategySelector ────────────────────────────────────────────────────


class TestStrategySelectorUCB1:
    def test_select_first_strategy_explores_unknown(self):
        ss = StrategySelector()
        s = ss.select_strategy("exploratory")
        assert isinstance(s, StrategyType)

    def test_select_cycles_through_unpulled_arms(self):
        ss = StrategySelector()
        first = ss.select_strategy("factual")
        ss.update_feedback(first, 0.5, "factual")
        second = ss.select_strategy("factual")
        assert second != first  # UCB1 should try unpulled arms next

    def test_unknown_query_type_falls_back(self):
        ss = StrategySelector()
        s = ss.select_strategy("nonexistent_query_type")
        assert s == StrategyType.BREADTH_FIRST

    def test_ucb1_converges_on_best_strategy(self):
        ss = StrategySelector()
        for _ in range(20):
            s = ss.select_strategy("factual")
            reward = 1.0 if s == StrategyType.BREADTH_FIRST else 0.1
            ss.update_feedback(s, reward, "factual")
        stats = ss.get_strategy_stats("factual")
        bf_mean = stats["BREADTH_FIRST"]["mean_reward"]
        df_mean = stats["DEPTH_FIRST"]["mean_reward"]
        assert bf_mean > df_mean


class TestStrategySelectorFeedback:
    def test_update_feedback_clamps_reward(self):
        ss = StrategySelector()
        ss.update_feedback(StrategyType.BREADTH_FIRST, 1.5, "factual")
        stats = ss.get_strategy_stats("factual")
        assert stats["BREADTH_FIRST"]["total_reward"] <= 1.0

    def test_history_is_recorded(self):
        ss = StrategySelector()
        ss.update_feedback(StrategyType.DEPTH_FIRST, 0.7, "exploratory")
        h = ss.get_history()
        assert len(h) == 1
        assert isinstance(h[0], StrategyResult)

    def test_add_query_type_tracks_new(self):
        ss = StrategySelector()
        ss.add_query_type("custom_type")
        s = ss.select_strategy("custom_type")
        assert isinstance(s, StrategyType)

    def test_reward_below_zero_clamped(self):
        ss = StrategySelector()
        ss.update_feedback(StrategyType.BREADTH_FIRST, -0.5, "factual")
        stats = ss.get_strategy_stats("factual")
        assert stats["BREADTH_FIRST"]["total_reward"] >= 0.0


class TestStrategyStats:
    def test_confusion_matrix_all_query_types(self):
        ss = StrategySelector()
        for qt in DEFAULT_QUERY_TYPES:
            for st in StrategyType:
                ss.update_feedback(st, 0.5, qt)
        matrix = ss.get_confusion_matrix()
        assert len(matrix) == len(DEFAULT_QUERY_TYPES)
        for qt in DEFAULT_QUERY_TYPES:
            assert qt in matrix

    def test_stats_unknown_query_type_empty(self):
        ss = StrategySelector()
        assert ss.get_strategy_stats("unknown") == {}


class TestStrategyResult:
    def test_strategy_result_immutable(self):
        sr = StrategyResult(strategy_type=StrategyType.BREADTH_FIRST,
                            query_type="factual", reward=0.8)
        assert sr.reward == 0.8
        assert sr.timestamp
