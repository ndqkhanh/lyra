"""
Tests for research strategies.
"""

from datetime import datetime, timedelta
from lyra_research.strategies import (
    QueryExpander,
    ResearchPlanner,
    ResultFilter,
    ResultRanker,
    SearchStrategy,
    StoppingCriteria,
)


def test_query_expander():
    """Test query expansion."""
    expander = QueryExpander()

    query = "neural network for NLP"
    expansions = expander.expand(query, max_expansions=5)

    assert isinstance(expansions, list)
    assert len(expansions) <= 5
    # Should expand "neural network" and "NLP"


def test_query_expander_acronyms():
    """Test acronym expansion."""
    expander = QueryExpander()

    query = "CNN for image classification"
    expansions = expander.expand(query)

    # Should expand CNN to full form
    assert any('convolutional' in exp.lower() for exp in expansions)


def test_result_filter_quality():
    """Test quality filtering."""
    filter_engine = ResultFilter()

    results = [
        {'id': '1', 'quality_score': 0.8},
        {'id': '2', 'quality_score': 0.4},
        {'id': '3', 'quality_score': 0.6},
    ]

    filtered = filter_engine.filter_by_quality(results, min_quality=0.5)

    assert len(filtered) == 2
    assert all(r['quality_score'] >= 0.5 for r in filtered)


def test_result_filter_recency():
    """Test recency filtering."""
    filter_engine = ResultFilter()

    now = datetime.now()
    results = [
        {'id': '1', 'published_date': now - timedelta(days=365)},  # 1 year
        {'id': '2', 'published_date': now - timedelta(days=365*6)},  # 6 years
        {'id': '3', 'published_date': now - timedelta(days=365*3)},  # 3 years
    ]

    filtered = filter_engine.filter_by_recency(results, max_age_years=5)

    assert len(filtered) == 2
    # Should exclude 6-year-old paper


def test_result_filter_citations():
    """Test citation filtering."""
    filter_engine = ResultFilter()

    results = [
        {'id': '1', 'citations': 100},
        {'id': '2', 'citations': 5},
        {'id': '3', 'citations': 50},
    ]

    filtered = filter_engine.filter_by_citations(results, min_citations=10)

    assert len(filtered) == 2
    assert all(r['citations'] >= 10 for r in filtered)


def test_result_deduplication():
    """Test result deduplication."""
    filter_engine = ResultFilter()

    results = [
        {'id': '1', 'title': 'Deep Learning'},
        {'id': '1', 'title': 'Deep Learning'},  # Duplicate ID
        {'id': '2', 'title': 'Deep Learning'},  # Duplicate title
        {'id': '3', 'title': 'Neural Networks'},
    ]

    unique = filter_engine.deduplicate(results)

    assert len(unique) == 2
    # Should keep only unique IDs and titles


def test_result_ranker():
    """Test result ranking."""
    ranker = ResultRanker()

    results = [
        {
            'id': '1',
            'title': 'Paper 1',
            'relevance_score': 0.8,
            'quality_score': 0.7,
            'citations': 50,
        },
        {
            'id': '2',
            'title': 'Paper 2',
            'relevance_score': 0.6,
            'quality_score': 0.9,
            'citations': 200,
        },
    ]

    ranked = ranker.rank(results)

    assert len(ranked) == 2
    assert ranked[0].rank == 1
    assert ranked[1].rank == 2
    # Higher overall score should rank first


def test_research_planner_survey():
    """Test research planning for survey."""
    planner = ResearchPlanner()

    plan = planner.plan("machine learning", goal="survey", max_results=50)

    assert plan.query == "machine learning"
    assert plan.strategy == SearchStrategy.BREADTH_FIRST
    assert plan.max_results == 50
    assert 'min_quality' in plan.filters


def test_research_planner_deep_dive():
    """Test research planning for deep dive."""
    planner = ResearchPlanner()

    plan = planner.plan("transformer architecture", goal="deep_dive")

    assert plan.strategy == SearchStrategy.DEPTH_FIRST
    assert 'min_citations' in plan.filters


def test_query_decomposition():
    """Test query decomposition."""
    planner = ResearchPlanner()

    query = "transformers and attention mechanisms"
    sub_queries = planner.decompose_query(query)

    assert len(sub_queries) >= 2
    # Should split on "and"


def test_time_estimation():
    """Test time estimation."""
    planner = ResearchPlanner()

    plan = planner.plan("deep learning", goal="survey", max_results=100)
    estimates = planner.estimate_time(plan)

    assert 'discovery' in estimates
    assert 'analysis' in estimates
    assert 'synthesis' in estimates
    assert 'total' in estimates
    assert estimates['total'] > 0


def test_stopping_criteria():
    """Test stopping criteria."""
    criteria = StoppingCriteria()

    # Should stop when target reached
    assert criteria.should_stop(
        results_found=100,
        target_results=100,
        quality_threshold=0.5,
        current_quality=0.7,
        iterations=5,
    )

    # Should not stop when target not reached
    assert not criteria.should_stop(
        results_found=50,
        target_results=100,
        quality_threshold=0.5,
        current_quality=0.7,
        iterations=3,
    )

    # Should stop when max iterations reached
    assert criteria.should_stop(
        results_found=50,
        target_results=100,
        quality_threshold=0.5,
        current_quality=0.7,
        iterations=10,
        max_iterations=10,
    )


def test_saturation_calculation():
    """Test saturation calculation."""
    criteria = StoppingCriteria()

    existing = [
        {'id': '1', 'title': 'Paper 1'},
        {'id': '2', 'title': 'Paper 2'},
    ]

    # All new results
    new_results = [
        {'id': '3', 'title': 'Paper 3'},
        {'id': '4', 'title': 'Paper 4'},
    ]

    saturation = criteria.calculate_saturation(new_results, existing)
    assert saturation == 0.0  # No duplicates

    # All duplicates
    duplicate_results = [
        {'id': '1', 'title': 'Paper 1'},
        {'id': '2', 'title': 'Paper 2'},
    ]

    saturation = criteria.calculate_saturation(duplicate_results, existing)
    assert saturation == 1.0  # All duplicates
