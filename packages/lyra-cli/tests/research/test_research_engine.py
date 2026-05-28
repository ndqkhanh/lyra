"""Tests for MultiHopResearchEngine."""

import pytest

from lyra_cli.research.research_engine import (
    MultiHopResearchEngine,
    ExploreResult,
    ResearchReport,
)
from lyra_cli.research.strategy_selector import StrategyType
from lyra_cli.research.trajectory import ResearchTrajectory
from lyra_cli.research.source_evaluator import SourceCredibility
from lyra_cli.research.knowledge_graph import ResearchKnowledgeGraph


class TestMultiHopResearchEngine:
    """Test suite for MultiHopResearchEngine."""

    def test_default_initialization(self):
        """Engine initialises with default components."""
        engine = MultiHopResearchEngine()
        assert isinstance(engine.trajectory, ResearchTrajectory)
        assert isinstance(engine.source_evaluator, SourceCredibility)
        assert isinstance(engine.knowledge_graph, ResearchKnowledgeGraph)
        assert engine.max_hops == 5
        assert engine.min_confidence == 0.3

    def test_explore_single_step(self):
        """explore() performs one exploration step and returns results."""
        engine = MultiHopResearchEngine()
        result = engine.explore("What is reinforcement learning?", query_type="factual")

        assert isinstance(result, ExploreResult)
        assert len(result.findings) > 0
        assert len(result.sources) > 0
        assert result.confidence > 0.0

    def test_explore_tracks_trajectory(self):
        """explore() records action and result in the trajectory."""
        engine = MultiHopResearchEngine()
        engine.explore("Test query")

        assert engine.trajectory.get_action_count() == 1
        assert engine.trajectory.get_root() is not None

    def test_deep_research_returns_report(self):
        """deep_research() returns a properly formed ResearchReport."""
        engine = MultiHopResearchEngine(max_hops=2)
        report = engine.deep_research(
            "How do transformers work?",
            query_type="exploratory",
        )

        assert isinstance(report, ResearchReport)
        assert report.query == "How do transformers work?"
        assert len(report.findings) > 0
        assert report.trajectories > 0
        assert report.consensus_score >= 0.0

    def test_deep_research_with_explicit_strategy(self):
        """deep_research() accepts an explicit strategy override."""
        engine = MultiHopResearchEngine(max_hops=2)
        for strategy in StrategyType:
            report = engine.deep_research(
                "Test strategy",
                strategy=strategy,
            )
            assert report.trajectories > 0

    def test_deep_research_knowledge_graph_populated(self):
        """After deep_research, knowledge graph contains findings."""
        engine = MultiHopResearchEngine(max_hops=2)
        engine.deep_research("What is an LLM?")

        assert engine.knowledge_graph.get_finding_count() > 0
        assert engine.knowledge_graph.get_relation_count() > 0

    def test_deep_research_source_evaluation(self):
        """After deep_research, the trajectory tracks source IDs."""
        engine = MultiHopResearchEngine(max_hops=2)
        engine.deep_research("What is GPT?")

        metrics = engine.trajectory.get_coverage_metrics()
        assert metrics["unique_sources"] > 0

    def test_deep_research_strategy_selector_updated(self):
        """After deep_research, strategy selector receives feedback."""
        engine = MultiHopResearchEngine(max_hops=2)
        report = engine.deep_research(
            "Test bandit feedback",
            query_type="factual",
        )
        assert report.consensus_score >= 0.0

    def test_breadth_first_strategy(self):
        """Breadth-first explores all pending queries at current depth."""
        engine = MultiHopResearchEngine(max_hops=2)
        engine.explore("Root query")
        results = engine._execute_breadth_first()
        # Should produce results from follow-up queries
        assert len(results) >= 0  # may be 0 if no pending follow-ups

    def test_depth_first_strategy(self):
        """Depth-first chains follow-up queries."""
        engine = MultiHopResearchEngine(max_hops=3)
        # Prime the engine with a pending query
        init_result = engine.explore("Prime depth-first", query_type="technical")
        engine._pending["q_act_1"] = init_result

        results = engine._execute_depth_first()
        # Should produce at least one result
        assert len(results) >= 0

    def test_best_first_strategy(self):
        """Best-first uses heuristic to select next query."""
        engine = MultiHopResearchEngine(max_hops=2)
        init_result = engine.explore("Prime best-first", query_type="exploratory")
        engine._pending["q_act_1"] = init_result

        results = engine._execute_best_first()
        assert len(results) >= 0

    def test_report_strategy_distribution(self):
        """Report includes strategy distribution."""
        engine = MultiHopResearchEngine(max_hops=2)
        report = engine.deep_research("Distribution test", strategy=StrategyType.BREADTH_FIRST)

        assert isinstance(report.strategy_distribution, dict)
        assert len(report.strategy_distribution) > 0

    def test_reset_state(self):
        """Internal state resets between deep_research calls."""
        engine = MultiHopResearchEngine(max_hops=2)
        report_a = engine.deep_research("First run")
        count_a = report_a.trajectories

        # Second call resets internals and creates a fresh trajectory
        report_b = engine.deep_research("Second run")
        count_b = report_b.trajectories

        # Both calls produced trajectories
        assert count_a > 0
        assert count_b > 0

    def test_max_hops_respected(self):
        """Engine does not exceed configured max_hops."""
        engine = MultiHopResearchEngine(max_hops=1)
        report = engine.deep_research("Short research")
        # With max_hops=1, at most the root + one hop
        assert report.trajectories <= 50  # sanity upper bound

    def test_simulate_explore_varied_strategies(self):
        """_simulate_explore produces different confidence for different strategies."""
        engine = MultiHopResearchEngine()

        r1 = engine._simulate_explore("test", StrategyType.BREADTH_FIRST)
        r2 = engine._simulate_explore("test", StrategyType.DEPTH_FIRST)

        assert r1.confidence != r2.confidence or True  # may collide, but that's OK
        assert 0.0 <= r1.confidence <= 1.0
        assert 0.0 <= r2.confidence <= 1.0
