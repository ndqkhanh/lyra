"""Tests for research strategies — query expansion, ranking, filtering, planning."""

from __future__ import annotations

from datetime import datetime, timedelta

from lyra_research.strategies import (
    QueryExpander,
    RankedResult,
    ResearchPlanner,
    ResultFilter,
    ResultRanker,
    SearchPlan,
    SearchStrategy,
    StoppingCriteria,
)

# ── SearchStrategy / SearchPlan ─────────────────────────────────────────


class TestSearchStrategy:
    def test_all_strategies(self):
        strategies = list(SearchStrategy)
        assert SearchStrategy.BREADTH_FIRST in strategies
        assert SearchStrategy.DEPTH_FIRST in strategies
        assert SearchStrategy.CITATION_FORWARD in strategies
        assert SearchStrategy.CITATION_BACKWARD in strategies
        assert SearchStrategy.SNOWBALL in strategies
        assert SearchStrategy.SYSTEMATIC in strategies


class TestSearchPlan:
    def test_search_plan_fields(self):
        plan = SearchPlan(
            query="transformer attention",
            strategy=SearchStrategy.DEPTH_FIRST,
            max_results=50,
            filters={"min_quality": 0.7},
            expansion_terms=["self-attention", "multi-head"],
        )
        assert plan.query == "transformer attention"
        assert plan.strategy == SearchStrategy.DEPTH_FIRST
        assert plan.max_results == 50
        assert len(plan.expansion_terms) == 2


# ── QueryExpander ───────────────────────────────────────────────────────


class TestQueryExpander:
    def test_expand_neural_network(self):
        qe = QueryExpander()
        expansions = qe.expand("neural network architecture")
        assert len(expansions) > 0

    def test_expand_machine_learning(self):
        qe = QueryExpander()
        expansions = qe.expand("machine learning for nlp")
        assert any("ML" in e or "statistical" in e for e in expansions)

    def test_expand_with_acronym(self):
        qe = QueryExpander()
        expansions = qe.expand("CNN for image recognition")
        assert any("convolutional neural network" in e for e in expansions)

    def test_expand_learning_adds_related(self):
        qe = QueryExpander()
        expansions = qe.expand("learning rate optimization")
        assert any("supervised" in e or "unsupervised" in e for e in expansions)

    def test_expand_model_adds_related(self):
        qe = QueryExpander()
        expansions = qe.expand("model compression techniques")
        assert any("architecture" in e or "framework" in e for e in expansions)

    def test_expand_data_adds_related(self):
        qe = QueryExpander()
        expansions = qe.expand("data augmentation strategies")
        assert any("dataset" in e or "corpus" in e for e in expansions)

    def test_expand_respects_max_expansions(self):
        qe = QueryExpander()
        expansions = qe.expand("machine learning model data processing", max_expansions=3)
        assert len(expansions) <= 3

    def test_expand_no_match_returns_empty(self):
        qe = QueryExpander()
        expansions = qe.expand("xyzzy foobar", max_expansions=10)
        assert expansions == []

    def test_expand_deduplicates(self):
        qe = QueryExpander()
        expansions = qe.expand("neural network", max_expansions=10)
        assert len(expansions) == len(set(expansions))


# ── ResultFilter ────────────────────────────────────────────────────────


class TestResultFilter:
    def test_filter_by_quality(self):
        rf = ResultFilter()
        results = [
            {"id": "1", "quality_score": 0.9},
            {"id": "2", "quality_score": 0.3},
            {"id": "3", "quality_score": 0.7},
        ]
        filtered = rf.filter_by_quality(results, min_quality=0.5)
        assert len(filtered) == 2
        assert all(r["quality_score"] >= 0.5 for r in filtered)

    def test_filter_by_quality_empty(self):
        rf = ResultFilter()
        assert rf.filter_by_quality([], min_quality=0.5) == []

    def test_filter_by_recency(self):
        rf = ResultFilter()
        recent = datetime.now() - timedelta(days=365)
        old = datetime.now() - timedelta(days=365 * 6)
        results = [
            {"id": "1", "published_date": recent},
            {"id": "2", "published_date": old},
            {"id": "3"},  # no date — included
        ]
        filtered = rf.filter_by_recency(results, max_age_years=5)
        assert len(filtered) == 2

    def test_filter_by_citations(self):
        rf = ResultFilter()
        results = [
            {"id": "1", "citations": 50},
            {"id": "2", "citations": 3},
            {"id": "3", "citations": 100},
        ]
        filtered = rf.filter_by_citations(results, min_citations=10)
        assert len(filtered) == 2

    def test_deduplicate_removes_duplicate_ids(self):
        rf = ResultFilter()
        results = [
            {"id": "a", "title": "Paper A"},
            {"id": "a", "title": "Paper A Dup"},
            {"id": "b", "title": "Paper B"},
        ]
        filtered = rf.deduplicate(results)
        assert len(filtered) == 2

    def test_deduplicate_removes_duplicate_titles(self):
        rf = ResultFilter()
        results = [
            {"id": "1", "title": "Same Title"},
            {"id": "2", "title": "Same Title"},
        ]
        filtered = rf.deduplicate(results)
        assert len(filtered) == 1

    def test_deduplicate_empty(self):
        rf = ResultFilter()
        assert rf.deduplicate([]) == []


# ── ResultRanker ────────────────────────────────────────────────────────


class TestResultRanker:
    def test_rank_sorts_by_overall_score(self):
        rr = ResultRanker()
        results = [
            {"id": "1", "title": "A", "relevance_score": 0.5, "quality_score": 0.5, "citations": 10},
            {"id": "2", "title": "B", "relevance_score": 0.9, "quality_score": 0.9, "citations": 200},
            {"id": "3", "title": "C", "relevance_score": 0.3, "quality_score": 0.3, "citations": 5000},
        ]
        ranked = rr.rank(results)
        assert len(ranked) == 3
        assert ranked[0].rank == 1
        assert ranked[0].overall_score >= ranked[-1].overall_score

    def test_rank_assigns_sequential_ranks(self):
        rr = ResultRanker()
        results = [
            {"id": f"{i}", "title": f"P{i}"} for i in range(5)
        ]
        ranked = rr.rank(results)
        ranks = [r.rank for r in ranked]
        assert ranks == [1, 2, 3, 4, 5]

    def test_rank_custom_weights(self):
        rr = ResultRanker()
        results = [
            {"id": "1", "title": "High Relevance", "relevance_score": 1.0, "quality_score": 0.1, "citations": 10},
            {"id": "2", "title": "High Quality", "relevance_score": 0.1, "quality_score": 1.0, "citations": 10},
        ]
        ranked = rr.rank(results, weights={"relevance": 0.9, "quality": 0.1, "novelty": 0.0, "recency": 0.0})
        assert ranked[0].title == "High Relevance"

    def test_rank_empty(self):
        rr = ResultRanker()
        assert rr.rank([]) == []

    def test_ranked_result_fields(self):
        r = RankedResult(
            source_id="s1", title="Test", relevance_score=0.8,
            quality_score=0.7, novelty_score=0.6, overall_score=0.75, rank=1,
        )
        assert r.source_id == "s1"
        assert r.overall_score == 0.75
        assert r.rank == 1

    def test_ranked_result_rank_default(self):
        r = RankedResult(
            source_id="s1", title="T", relevance_score=0.5,
            quality_score=0.5, novelty_score=0.5, overall_score=0.5,
        )
        assert r.rank == 0


# ── ResearchPlanner ─────────────────────────────────────────────────────


class TestResearchPlanner:
    def test_plan_survey_uses_breadth_first(self):
        rp = ResearchPlanner()
        plan = rp.plan("attention mechanisms", goal="survey")
        assert plan.strategy == SearchStrategy.BREADTH_FIRST
        assert plan.filters["min_quality"] == 0.6
        assert plan.filters["max_age_years"] == 10

    def test_plan_deep_dive_uses_depth_first(self):
        rp = ResearchPlanner()
        plan = rp.plan("transformer architecture", goal="deep_dive")
        assert plan.strategy == SearchStrategy.DEPTH_FIRST
        assert plan.filters["min_citations"] == 50

    def test_plan_comparison_uses_systematic(self):
        rp = ResearchPlanner()
        plan = rp.plan("CNN vs ViT", goal="comparison")
        assert plan.strategy == SearchStrategy.SYSTEMATIC

    def test_plan_trend_filters_recent(self):
        rp = ResearchPlanner()
        plan = rp.plan("latest in diffusion models", goal="trend")
        assert plan.filters["max_age_years"] == 2

    def test_plan_unknown_goal_defaults_to_breadth_first(self):
        rp = ResearchPlanner()
        plan = rp.plan("anything", goal="unknown_goal")
        assert plan.strategy == SearchStrategy.BREADTH_FIRST

    def test_plan_includes_expansion_terms(self):
        rp = ResearchPlanner()
        plan = rp.plan("neural network optimization", goal="survey")
        assert len(plan.expansion_terms) > 0

    def test_decompose_query_simple(self):
        rp = ResearchPlanner()
        parts = rp.decompose_query("attention mechanisms")
        assert len(parts) >= 1

    def test_decompose_query_with_and(self):
        rp = ResearchPlanner()
        parts = rp.decompose_query("transformers and attention and optimization")
        assert len(parts) >= 2

    def test_decompose_query_with_vs(self):
        rp = ResearchPlanner()
        parts = rp.decompose_query("CNN vs ViT for image classification")
        assert "CNN" in parts or "ViT" in parts

    def test_estimate_time_returns_all_phases(self):
        rp = ResearchPlanner()
        plan = rp.plan("test", goal="survey", max_results=20)
        estimates = rp.estimate_time(plan)
        assert "discovery" in estimates
        assert "analysis" in estimates
        assert "synthesis" in estimates
        assert "total" in estimates
        assert estimates["total"] > 0

    def test_estimate_time_systematic_is_slowest(self):
        rp = ResearchPlanner()
        plan_survey = rp.plan("test", goal="survey", max_results=10)
        plan_systematic = rp.plan("test", goal="comparison", max_results=10)
        assert rp.estimate_time(plan_systematic)["total"] > rp.estimate_time(plan_survey)["total"]


# ── StoppingCriteria ────────────────────────────────────────────────────


class TestStoppingCriteria:
    def test_should_stop_when_target_reached(self):
        sc = StoppingCriteria()
        assert sc.should_stop(100, 100, 0.5, 0.8, 1)

    def test_should_stop_when_quality_low_after_iterations(self):
        sc = StoppingCriteria()
        assert sc.should_stop(10, 100, 0.7, 0.3, 5)

    def test_should_stop_when_max_iterations_reached(self):
        sc = StoppingCriteria()
        assert sc.should_stop(10, 100, 0.5, 0.8, 10)

    def test_should_not_stop_early(self):
        sc = StoppingCriteria()
        assert not sc.should_stop(10, 100, 0.9, 0.8, 1)

    def test_should_not_stop_quality_low_early(self):
        sc = StoppingCriteria()
        assert not sc.should_stop(10, 100, 0.7, 0.3, 2)

    def test_calculate_saturation_empty_new(self):
        sc = StoppingCriteria()
        assert sc.calculate_saturation([], [{"id": "1"}]) == 1.0

    def test_calculate_saturation_no_duplicates(self):
        sc = StoppingCriteria()
        saturation = sc.calculate_saturation(
            [{"id": "2"}, {"id": "3"}],
            [{"id": "1"}],
        )
        assert saturation == 0.0

    def test_calculate_saturation_all_duplicates(self):
        sc = StoppingCriteria()
        saturation = sc.calculate_saturation(
            [{"id": "1"}, {"id": "2"}],
            [{"id": "1"}, {"id": "2"}],
        )
        assert saturation == 1.0

    def test_calculate_saturation_partial(self):
        sc = StoppingCriteria()
        saturation = sc.calculate_saturation(
            [{"id": "1"}, {"id": "3"}],
            [{"id": "1"}, {"id": "2"}],
        )
        assert 0.0 < saturation < 1.0
