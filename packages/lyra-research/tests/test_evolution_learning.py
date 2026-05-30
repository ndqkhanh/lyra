"""
Unit tests for evolution and learning system (US-028).

Tests strategy adaptation, performance improvement, and cross-run learning.
"""

import pytest
from lyra_research.skills import (
    QueryRefinementSkill,
    ResearchSkill,
    SkillEvolutionTracker,
    StrategyAdaptationSkill,
)


class TestSkillEvolutionTracker:
    """Test skill evolution tracking system."""

    def test_create_tracker(self):
        """Test creating skill evolution tracker."""
        tracker = SkillEvolutionTracker()

        assert tracker is not None
        assert hasattr(tracker, "record")
        assert hasattr(tracker, "get_trend")

    def test_track_single_performance(self):
        """Test tracking single performance metric."""
        tracker = SkillEvolutionTracker()

        tracker.record(
            skill_name="query_refinement",
            topic="machine learning",
            score=0.85,
            notes="Good performance",
        )

        trend = tracker.get_trend("query_refinement", last_n=1)
        assert len(trend) == 1
        assert trend[0] == 0.85

    def test_track_multiple_performances(self):
        """Test tracking multiple performance metrics."""
        tracker = SkillEvolutionTracker()

        for i in range(5):
            tracker.record(
                skill_name="query_refinement",
                topic=f"topic_{i}",
                score=0.7 + i * 0.05,
                notes=f"Session {i}",
            )

        trend = tracker.get_trend("query_refinement", last_n=5)
        assert len(trend) == 5
        # Should show improvement over time
        assert trend[-1] > trend[0]

    def test_track_multiple_skills(self):
        """Test tracking multiple skills independently."""
        tracker = SkillEvolutionTracker()

        tracker.record("skill_a", "topic_a", 0.8, "Test A")
        tracker.record("skill_b", "topic_b", 0.9, "Test B")

        trend_a = tracker.get_trend("skill_a", last_n=1)
        trend_b = tracker.get_trend("skill_b", last_n=1)

        assert len(trend_a) == 1
        assert len(trend_b) == 1
        assert trend_a[0] == 0.8
        assert trend_b[0] == 0.9

    def test_calculate_improvement_rate(self):
        """Test calculating improvement rate over time."""
        tracker = SkillEvolutionTracker()

        # Simulate improving performance
        for i in range(10):
            tracker.record(
                skill_name="query_refinement",
                topic=f"topic_{i}",
                score=0.5 + i * 0.05,
                notes=f"Session {i}",
            )

        # Check if improving
        is_improving = tracker.is_improving("query_refinement", window=5)
        assert is_improving is True


class TestQueryRefinementSkill:
    """Test query refinement skill."""

    def test_create_query_refinement_skill(self):
        """Test creating query refinement skill."""
        skill = QueryRefinementSkill()

        assert skill is not None
        assert hasattr(skill, "refine")

    def test_refine_simple_query(self):
        """Test refining a simple query."""
        skill = QueryRefinementSkill()

        original = "machine learning"
        result_count = 500  # Too broad
        refined_suggestion = skill.refine(original, result_count, domain="ml")

        assert refined_suggestion.refined_query != original
        assert len(refined_suggestion.refined_query) > len(original)
        assert refined_suggestion.reason == "too_broad"

    def test_refine_with_context(self):
        """Test refining query with domain context."""
        skill = QueryRefinementSkill()

        original = "transformers"
        result_count = 500  # Too broad
        refined_suggestion = skill.refine(original, result_count, domain="nlp")

        # Should incorporate NLP domain context
        assert "language model" in refined_suggestion.refined_query.lower() or "transformer" in refined_suggestion.refined_query.lower()

    def test_refine_narrow_query(self):
        """Test refining too-narrow query."""
        skill = QueryRefinementSkill()

        query = "very specific narrow query with many terms"
        result_count = 2  # Too narrow
        refined_suggestion = skill.refine(query, result_count, domain="ml")

        # Should broaden by removing terms
        assert refined_suggestion.reason == "too_narrow"
        assert len(refined_suggestion.refined_query) < len(query)

    def test_add_recency(self):
        """Test adding recency to query."""
        skill = QueryRefinementSkill()

        query = "deep learning"
        result_count = 50  # Normal range
        refined_suggestion = skill.refine(query, result_count, domain="ml")

        # Should add year for ML domain
        assert any(str(year) in refined_suggestion.refined_query for year in range(2024, 2027))


class TestStrategyAdaptationSkill:
    """Test strategy adaptation skill."""

    def test_create_strategy_adaptation_skill(self):
        """Test creating strategy adaptation skill."""
        skill = StrategyAdaptationSkill()

        assert skill is not None
        assert hasattr(skill, "select_strategy")
        assert hasattr(skill, "should_switch")

    def test_select_initial_strategy(self):
        """Test selecting initial strategy."""
        skill = StrategyAdaptationSkill()

        # Test breadth-first for survey
        strategy = skill.select_strategy("survey of machine learning", domain="ml")
        assert strategy is not None

        # Test depth-first for mechanism
        strategy = skill.select_strategy("how does attention mechanism work", domain="ml")
        assert strategy is not None

    def test_should_switch_strategy(self):
        """Test deciding when to switch strategy."""
        from lyra_research.strategies import SearchStrategy

        skill = StrategyAdaptationSkill()

        # Should switch from breadth to depth when too many low-quality papers
        new_strategy = skill.should_switch(
            current_strategy=SearchStrategy.BREADTH_FIRST,
            papers_found=60,
            repos_found=10,
            quality_scores=[0.3, 0.35, 0.32],
        )
        assert new_strategy == SearchStrategy.DEPTH_FIRST

        # Should switch from depth to breadth when too few papers
        new_strategy = skill.should_switch(
            current_strategy=SearchStrategy.DEPTH_FIRST,
            papers_found=3,
            repos_found=1,
            quality_scores=[0.8],
        )
        assert new_strategy == SearchStrategy.BREADTH_FIRST

        # Should not switch when performance is good
        new_strategy = skill.should_switch(
            current_strategy=SearchStrategy.BREADTH_FIRST,
            papers_found=30,
            repos_found=10,
            quality_scores=[0.7, 0.75, 0.8],
        )
        assert new_strategy is None

    def test_strategy_selection_keywords(self):
        """Test strategy selection based on keywords."""
        from lyra_research.strategies import SearchStrategy

        skill = StrategyAdaptationSkill()

        # Survey should use breadth-first
        assert skill.select_strategy("survey of NLP", "nlp") == SearchStrategy.BREADTH_FIRST

        # Mechanism should use depth-first
        assert skill.select_strategy("mechanism of attention", "ml") == SearchStrategy.DEPTH_FIRST

        # Related work should use snowball
        assert skill.select_strategy("related work on transformers", "nlp") == SearchStrategy.SNOWBALL


class TestCrossRunLearning:
    """Test cross-run learning and improvement."""

    def test_learn_from_previous_session(self):
        """Test learning from previous research session."""
        tracker = SkillEvolutionTracker()

        # Session 1: Initial performance
        tracker.record("query_refinement", "topic_1", 0.6, "Initial")

        # Session 2: Improved performance
        tracker.record("query_refinement", "topic_2", 0.75, "Improved")

        # Session 3: Further improvement
        tracker.record("query_refinement", "topic_3", 0.85, "Better")

        is_improving = tracker.is_improving("query_refinement", window=3)
        assert is_improving is True

    def test_transfer_learning_across_skills(self):
        """Test transferring learning across related skills."""
        tracker = SkillEvolutionTracker()

        # Learn from query refinement
        tracker.record("query_refinement", "ml_topic", 0.8, "Good")

        # Apply to strategy adaptation
        query_skill = QueryRefinementSkill()
        strategy_skill = StrategyAdaptationSkill()

        # Strategy should work independently
        strategy = strategy_skill.select_strategy("transformers", "nlp")
        assert strategy is not None

    def test_skill_synthesis_from_lessons(self):
        """Test synthesizing new skills from learned lessons."""
        tracker = SkillEvolutionTracker()

        # Track multiple successful patterns
        for i in range(10):
            tracker.record(
                skill_name="query_refinement",
                topic=f"topic_{i}",
                score=0.7 + i * 0.02,
                notes=f"Session {i}",
            )

        # Should be able to get refinement suggestions
        suggestions = tracker.propose_refinements("query_refinement")
        assert len(suggestions) > 0


class TestResearchSkillDataStructure:
    """Test research skill data structure."""

    def test_create_research_skill(self):
        """Test creating research skill with proper fields."""
        skill = ResearchSkill(
            name="test_skill",
            domain="ml",
            description="Test skill for machine learning",
            preferred_sources=["arxiv", "semantic_scholar"],
            preferred_venues=["NeurIPS", "ICML"],
            query_expansions=["deep learning", "neural network"],
            max_results_per_source=30,
            recency_bias=0.5,
            min_papers=5,
            min_repos=3,
            min_quality_score=0.5,
        )

        assert skill.name == "test_skill"
        assert skill.domain == "ml"
        assert len(skill.preferred_sources) == 2
        assert skill.min_papers == 5

    def test_skill_performance_tracking(self):
        """Test skill performance tracking."""
        skill = ResearchSkill(
            name="test_skill",
            domain="general",
            description="Test",
        )

        # Record performance
        skill.record_performance(0.8)
        skill.record_performance(0.85)
        skill.record_performance(0.9)

        # Check average
        avg = skill.average_performance()
        assert avg > 0.8
        assert len(skill.performance_history) == 3

    def test_skill_serialization(self):
        """Test skill serialization for persistence."""
        from lyra_research.skills import _skill_to_dict, _dict_to_skill

        skill = ResearchSkill(
            name="test_skill",
            domain="ml",
            description="Test skill",
            preferred_sources=["arxiv"],
            min_papers=5,
        )

        # Serialize
        serialized = _skill_to_dict(skill)
        assert serialized["name"] == "test_skill"
        assert serialized["domain"] == "ml"

        # Deserialize
        deserialized = _dict_to_skill(serialized)
        assert deserialized.name == skill.name
        assert deserialized.domain == skill.domain


class TestPerformanceImprovement:
    """Test performance improvement over time."""

    def test_measure_baseline_performance(self):
        """Test measuring baseline performance."""
        tracker = SkillEvolutionTracker()

        tracker.record("query_refinement", "baseline_topic", 0.6, "Baseline precision")
        tracker.record("query_refinement", "baseline_topic", 0.5, "Baseline recall")

        trend = tracker.get_trend("query_refinement", last_n=2)
        assert len(trend) == 2
        assert trend[0] == 0.6

    def test_measure_improvement_over_baseline(self):
        """Test measuring improvement over baseline."""
        tracker = SkillEvolutionTracker()

        # Baseline
        tracker.record("query_refinement", "topic_0", 0.6, "Baseline")

        # Improved sessions
        tracker.record("query_refinement", "topic_1", 0.7, "Improved")
        tracker.record("query_refinement", "topic_2", 0.8, "Better")

        trend = tracker.get_trend("query_refinement", last_n=3)
        improvement = trend[-1] - trend[0]
        assert improvement > 0.15  # 25% improvement

    def test_detect_performance_plateau(self):
        """Test detecting performance plateau."""
        tracker = SkillEvolutionTracker()

        # Simulate plateau
        for i in range(10):
            value = 0.85 if i < 5 else 0.86  # Plateau after 5 sessions
            tracker.record("query_refinement", f"topic_{i}", value, f"Session {i}")

        # Check if improving in recent window
        is_improving = tracker.is_improving("query_refinement", window=3)
        # With values 0.86, 0.86, 0.86, last > first is False
        assert is_improving is False

    def test_recommend_next_improvement(self, tmp_path):
        """Test recommending next improvement action."""
        tracker = SkillEvolutionTracker(store_path=tmp_path / "skill_evolution.json")

        # Track performance with low scores
        tracker.record("query_refinement", "topic_1", 0.4, "Low performance")
        tracker.record("query_refinement", "topic_2", 0.45, "Still low")
        tracker.record("query_refinement", "topic_3", 0.42, "Not improving")

        recommendations = tracker.propose_refinements("query_refinement")
        assert len(recommendations) > 0
        # Should suggest improvements for low performance
        assert any("benchmark" in rec.lower() or "increase" in rec.lower() for rec in recommendations)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
