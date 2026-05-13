"""
Tests for the Research Skills Library (skills.py).
"""


import pytest
from datetime import datetime, timezone

from lyra_research.skills import (
    ResearchSkill,
    ResearchSkillStore,
    RefinementSuggestion,
    QueryRefinementSkill,
    StrategyAdaptationSkill,
    SkillEvolutionRecord,
    SkillEvolutionTracker,
)
from lyra_research.strategies import SearchStrategy


# ---------------------------------------------------------------------------
# ResearchSkill tests
# ---------------------------------------------------------------------------

def test_research_skill_average_performance_empty():
    skill = ResearchSkill(name="test", domain="ml")
    assert skill.average_performance() == 0.0


def test_research_skill_average_performance_with_scores():
    skill = ResearchSkill(name="test", domain="ml")
    skill.record_performance(0.8)
    skill.record_performance(0.6)
    assert abs(skill.average_performance() - 0.7) < 1e-9


def test_research_skill_record_performance_clamps_high():
    skill = ResearchSkill(name="test", domain="ml")
    skill.record_performance(1.5)
    assert skill.performance_history[-1] == 1.0


def test_research_skill_record_performance_clamps_low():
    skill = ResearchSkill(name="test", domain="ml")
    skill.record_performance(-0.5)
    assert skill.performance_history[-1] == 0.0


def test_research_skill_record_performance_within_range():
    skill = ResearchSkill(name="test", domain="ml")
    skill.record_performance(0.75)
    assert skill.performance_history[-1] == 0.75


def test_research_skill_has_id():
    skill = ResearchSkill(name="x", domain="ml")
    assert skill.id != ""


def test_research_skill_created_at_utc():
    skill = ResearchSkill(name="x", domain="ml")
    assert skill.created_at.tzinfo is not None


# ---------------------------------------------------------------------------
# ResearchSkillStore tests
# ---------------------------------------------------------------------------

def test_skill_store_builtins_loaded(tmp_path):
    store = ResearchSkillStore(store_path=tmp_path / "skills.json")
    names = {s.name for s in store.list_all()}
    assert "ml_paper_search" in names
    assert "nlp_paper_search" in names
    assert "systems_paper_search" in names
    assert "general_research" in names


def test_skill_store_get_for_domain(tmp_path):
    store = ResearchSkillStore(store_path=tmp_path / "skills.json")
    skill = store.get_for_domain("ml")
    assert skill is not None
    assert skill.domain == "ml"


def test_skill_store_get_for_domain_missing(tmp_path):
    store = ResearchSkillStore(store_path=tmp_path / "skills.json")
    skill = store.get_for_domain("nonexistent_domain_xyz")
    assert skill is None


def test_skill_store_get_by_name(tmp_path):
    store = ResearchSkillStore(store_path=tmp_path / "skills.json")
    skill = store.get_by_name("nlp_paper_search")
    assert skill is not None
    assert skill.name == "nlp_paper_search"


def test_skill_store_get_by_name_missing(tmp_path):
    store = ResearchSkillStore(store_path=tmp_path / "skills.json")
    skill = store.get_by_name("does_not_exist")
    assert skill is None


def test_skill_store_save_and_list(tmp_path):
    store = ResearchSkillStore(store_path=tmp_path / "skills.json")
    new_skill = ResearchSkill(name="custom_skill", domain="bio", description="Biology research")
    store.save_skill(new_skill)
    names = {s.name for s in store.list_all()}
    assert "custom_skill" in names


def test_skill_store_record_performance(tmp_path):
    store = ResearchSkillStore(store_path=tmp_path / "skills.json")
    store.record_performance("ml_paper_search", 0.9)
    skill = store.get_by_name("ml_paper_search")
    assert 0.9 in skill.performance_history


def test_skill_store_record_performance_unknown_name(tmp_path):
    store = ResearchSkillStore(store_path=tmp_path / "skills.json")
    # Should not raise
    store.record_performance("nonexistent_skill", 0.5)


def test_skill_store_persistence(tmp_path):
    path = tmp_path / "skills.json"
    store1 = ResearchSkillStore(store_path=path)
    new_skill = ResearchSkill(name="persist_skill", domain="cv", description="CV research")
    store1.save_skill(new_skill)

    store2 = ResearchSkillStore(store_path=path)
    skill = store2.get_by_name("persist_skill")
    assert skill is not None
    assert skill.domain == "cv"


def test_skill_store_get_for_domain_returns_best_performer(tmp_path):
    store = ResearchSkillStore(store_path=tmp_path / "skills.json")
    # Add two ml skills with different performance
    skill_a = ResearchSkill(name="ml_a", domain="ml_custom", performance_history=[0.9, 0.9])
    skill_b = ResearchSkill(name="ml_b", domain="ml_custom", performance_history=[0.3, 0.3])
    store.save_skill(skill_a)
    store.save_skill(skill_b)
    best = store.get_for_domain("ml_custom")
    assert best.name == "ml_a"


# ---------------------------------------------------------------------------
# QueryRefinementSkill tests
# ---------------------------------------------------------------------------

def test_query_refinement_too_broad():
    skill = QueryRefinementSkill()
    result = skill.refine("deep learning optimization", result_count=500, domain="ml")
    assert result.reason == "too_broad"
    assert "2024" in result.refined_query or "benchmark" in result.refined_query


def test_query_refinement_too_narrow():
    skill = QueryRefinementSkill()
    result = skill.refine("very specific obscure algorithm version 3.2.1", result_count=2, domain="ml")
    assert result.reason == "too_narrow"
    assert len(result.refined_query) < len(result.original_query) or result.refined_query == result.original_query


def test_query_refinement_add_recency():
    skill = QueryRefinementSkill()
    # Moderate result count, no year in query, ml domain
    result = skill.refine("attention mechanism", result_count=50, domain="ml")
    assert result.reason == "add_year"
    current_year = datetime.now(timezone.utc).year
    assert str(current_year) in result.refined_query or str(current_year - 1) in result.refined_query


def test_query_refinement_domain_suffix_ml():
    skill = QueryRefinementSkill()
    result = skill.refine("model training", result_count=50, domain="ml")
    # model is in BROAD_SIGNALS, should add domain suffix
    assert "model" in result.original_query.lower()


def test_query_refinement_returns_suggestion_dataclass():
    skill = QueryRefinementSkill()
    result = skill.refine("transformers", result_count=100, domain="nlp")
    assert isinstance(result, RefinementSuggestion)
    assert isinstance(result.confidence, float)
    assert 0.0 <= result.confidence <= 1.0


def test_query_refinement_is_too_broad_true():
    skill = QueryRefinementSkill()
    assert skill.is_too_broad("AI", 300) is True


def test_query_refinement_is_too_broad_false():
    skill = QueryRefinementSkill()
    assert skill.is_too_broad("sparse attention mechanism", 10) is False


def test_query_refinement_is_too_narrow_true():
    skill = QueryRefinementSkill()
    assert skill.is_too_narrow("some query", 1) is True


def test_query_refinement_is_too_narrow_false():
    skill = QueryRefinementSkill()
    assert skill.is_too_narrow("some query", 100) is False


def test_query_refinement_add_recency_appends_year():
    skill = QueryRefinementSkill()
    result = skill.add_recency("transformer models")
    current_year = datetime.now(timezone.utc).year
    assert str(current_year) in result


# ---------------------------------------------------------------------------
# StrategyAdaptationSkill tests
# ---------------------------------------------------------------------------

def test_strategy_adaptation_selects_breadth_first():
    skill = StrategyAdaptationSkill()
    strategy = skill.select_strategy("survey of transformer models")
    assert strategy == SearchStrategy.BREADTH_FIRST


def test_strategy_adaptation_selects_breadth_first_review():
    skill = StrategyAdaptationSkill()
    strategy = skill.select_strategy("literature review on diffusion models")
    assert strategy == SearchStrategy.BREADTH_FIRST


def test_strategy_adaptation_selects_depth_first():
    skill = StrategyAdaptationSkill()
    strategy = skill.select_strategy("mechanism of attention in transformers")
    assert strategy == SearchStrategy.DEPTH_FIRST


def test_strategy_adaptation_selects_snowball():
    skill = StrategyAdaptationSkill()
    strategy = skill.select_strategy("related work on RLHF")
    assert strategy == SearchStrategy.SNOWBALL


def test_strategy_adaptation_selects_systematic():
    skill = StrategyAdaptationSkill()
    strategy = skill.select_strategy("systematic review of LLM benchmarks")
    assert strategy == SearchStrategy.SYSTEMATIC


def test_strategy_adaptation_default_fallback():
    skill = StrategyAdaptationSkill()
    strategy = skill.select_strategy("gradient descent convergence")
    assert strategy == SearchStrategy.BREADTH_FIRST


def test_strategy_adaptation_should_switch_low_quality():
    skill = StrategyAdaptationSkill()
    result = skill.should_switch(
        current_strategy=SearchStrategy.BREADTH_FIRST,
        papers_found=60,
        repos_found=5,
        quality_scores=[0.2, 0.3, 0.25],
    )
    assert result == SearchStrategy.DEPTH_FIRST


def test_strategy_adaptation_no_switch_when_good():
    skill = StrategyAdaptationSkill()
    result = skill.should_switch(
        current_strategy=SearchStrategy.BREADTH_FIRST,
        papers_found=30,
        repos_found=5,
        quality_scores=[0.7, 0.8, 0.75],
    )
    assert result is None


def test_strategy_adaptation_depth_to_breadth_when_sparse():
    skill = StrategyAdaptationSkill()
    result = skill.should_switch(
        current_strategy=SearchStrategy.DEPTH_FIRST,
        papers_found=3,
        repos_found=0,
        quality_scores=[0.6],
    )
    assert result == SearchStrategy.BREADTH_FIRST


def test_strategy_adaptation_no_switch_depth_with_enough_papers():
    skill = StrategyAdaptationSkill()
    result = skill.should_switch(
        current_strategy=SearchStrategy.DEPTH_FIRST,
        papers_found=10,
        repos_found=2,
        quality_scores=[0.7],
    )
    assert result is None


# ---------------------------------------------------------------------------
# SkillEvolutionTracker tests
# ---------------------------------------------------------------------------

def test_skill_evolution_record(tmp_path):
    tracker = SkillEvolutionTracker(store_path=tmp_path / "evolution.json")
    tracker.record("ml_paper_search", "transformers", 0.8)
    trend = tracker.get_trend("ml_paper_search")
    assert 0.8 in trend


def test_skill_evolution_get_trend(tmp_path):
    tracker = SkillEvolutionTracker(store_path=tmp_path / "evolution.json")
    tracker.record("ml_paper_search", "topic1", 0.5)
    tracker.record("ml_paper_search", "topic2", 0.7)
    tracker.record("ml_paper_search", "topic3", 0.9)
    trend = tracker.get_trend("ml_paper_search")
    assert trend == [0.5, 0.7, 0.9]


def test_skill_evolution_get_trend_respects_last_n(tmp_path):
    tracker = SkillEvolutionTracker(store_path=tmp_path / "evolution.json")
    for i in range(10):
        tracker.record("ml_paper_search", f"topic{i}", i * 0.1)
    trend = tracker.get_trend("ml_paper_search", last_n=3)
    assert len(trend) == 3
    assert trend[-1] == pytest.approx(0.9)


def test_skill_evolution_is_improving(tmp_path):
    tracker = SkillEvolutionTracker(store_path=tmp_path / "evolution.json")
    tracker.record("ml_paper_search", "t1", 0.4)
    tracker.record("ml_paper_search", "t2", 0.6)
    tracker.record("ml_paper_search", "t3", 0.8)
    assert tracker.is_improving("ml_paper_search") is True


def test_skill_evolution_is_not_improving(tmp_path):
    tracker = SkillEvolutionTracker(store_path=tmp_path / "evolution.json")
    tracker.record("ml_paper_search", "t1", 0.8)
    tracker.record("ml_paper_search", "t2", 0.6)
    tracker.record("ml_paper_search", "t3", 0.4)
    assert tracker.is_improving("ml_paper_search") is False


def test_skill_evolution_is_improving_insufficient_data(tmp_path):
    tracker = SkillEvolutionTracker(store_path=tmp_path / "evolution.json")
    tracker.record("ml_paper_search", "t1", 0.5)
    assert tracker.is_improving("ml_paper_search") is False


def test_skill_evolution_propose_refinements(tmp_path):
    tracker = SkillEvolutionTracker(store_path=tmp_path / "evolution.json")
    tracker.record("ml_paper_search", "t1", 0.3)
    tracker.record("ml_paper_search", "t2", 0.3)
    tracker.record("ml_paper_search", "t3", 0.3)
    suggestions = tracker.propose_refinements("ml_paper_search")
    assert len(suggestions) > 0
    assert any(isinstance(s, str) for s in suggestions)


def test_skill_evolution_propose_refinements_insufficient_data(tmp_path):
    tracker = SkillEvolutionTracker(store_path=tmp_path / "evolution.json")
    tracker.record("ml_paper_search", "t1", 0.3)
    suggestions = tracker.propose_refinements("ml_paper_search")
    assert suggestions == []


def test_skill_evolution_persistence(tmp_path):
    path = tmp_path / "evolution.json"
    tracker1 = SkillEvolutionTracker(store_path=path)
    tracker1.record("nlp_paper_search", "LLM evaluation", 0.85, notes="good coverage")

    tracker2 = SkillEvolutionTracker(store_path=path)
    trend = tracker2.get_trend("nlp_paper_search")
    assert 0.85 in trend


def test_skill_evolution_record_clamps_score(tmp_path):
    tracker = SkillEvolutionTracker(store_path=tmp_path / "evolution.json")
    tracker.record("ml_paper_search", "t1", 1.5)
    trend = tracker.get_trend("ml_paper_search")
    assert trend[-1] == 1.0
