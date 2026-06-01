"""Tests for MultiHopResearchEngine — explore, deep_research, strategies, reports."""

from __future__ import annotations

from lyra_cli.research.knowledge_graph import ResearchKnowledgeGraph
from lyra_cli.research.research_engine import (
    ExploreResult,
    MultiHopResearchEngine,
    ResearchReport,
)
from lyra_cli.research.source_evaluator import SourceCredibility
from lyra_cli.research.strategy_selector import StrategySelector, StrategyType
from lyra_cli.research.trajectory import ResearchTrajectory


def _engine(**kwargs) -> MultiHopResearchEngine:
    return MultiHopResearchEngine(**kwargs)


# ── Explore ─────────────────────────────────────────────────────────────


class TestExplore:
    def test_explore_returns_result(self):
        eng = _engine()
        result = eng.explore("transformer attention")
        assert isinstance(result, ExploreResult)
        assert result.sub_query == "transformer attention"
        assert len(result.findings) > 0
        assert len(result.sources) > 0

    def test_explore_registers_action_and_result(self):
        eng = _engine()
        eng.explore("test query")
        assert eng.trajectory.get_action_count() == 1

    def test_explore_ingests_into_knowledge_graph(self):
        eng = _engine()
        eng.explore("test query")
        assert eng.knowledge_graph.get_finding_count() > 0

    def test_explore_with_explicit_strategy(self):
        eng = _engine()
        result = eng.explore("test", strategy=StrategyType.DEPTH_FIRST)
        assert isinstance(result, ExploreResult)


# ── Deep Research ───────────────────────────────────────────────────────


class TestDeepResearch:
    def test_deep_research_returns_report(self):
        eng = _engine(max_hops=3)
        report = eng.deep_research("transformer attention mechanisms")
        assert isinstance(report, ResearchReport)
        assert report.query == "transformer attention mechanisms"
        assert len(report.findings) > 0

    def test_deep_research_with_explicit_strategy(self):
        eng = _engine(max_hops=2)
        report = eng.deep_research("Rust async runtime", strategy=StrategyType.BREADTH_FIRST)
        assert isinstance(report, ResearchReport)

    def test_deep_research_respects_max_hops(self):
        eng = _engine(max_hops=1)
        report = eng.deep_research("test")
        assert report.trajectories <= 5

    def test_deep_research_clears_state_between_runs(self):
        eng = _engine(max_hops=2)
        eng.deep_research("topic A")
        count_a = eng.knowledge_graph.get_finding_count()
        eng.deep_research("topic B")
        count_b = eng.knowledge_graph.get_finding_count()
        assert count_b < count_a * 2


class TestDeepResearchReportFields:
    def test_report_includes_consensus_score(self):
        eng = _engine(max_hops=2)
        report = eng.deep_research("test")
        assert 0.0 <= report.consensus_score <= 1.0

    def test_report_includes_strategy_distribution(self):
        eng = _engine(max_hops=3)
        report = eng.deep_research("test", strategy=StrategyType.BREADTH_FIRST)
        assert isinstance(report.strategy_distribution, dict)


# ── Strategy execution ──────────────────────────────────────────────────


class TestStrategyExecution:
    def test_breadth_first_explores_all_pending(self):
        eng = _engine(max_hops=3)
        report = eng.deep_research("broad topic", strategy=StrategyType.BREADTH_FIRST)
        assert isinstance(report, ResearchReport)

    def test_depth_first_follows_best_path(self):
        eng = _engine(max_hops=3)
        report = eng.deep_research("specific topic", strategy=StrategyType.DEPTH_FIRST)
        assert isinstance(report, ResearchReport)

    def test_best_first_scores_globally(self):
        eng = _engine(max_hops=3)
        report = eng.deep_research("any topic", strategy=StrategyType.BEST_FIRST)
        assert isinstance(report, ResearchReport)

    def test_auto_strategy_selection(self):
        eng = _engine(max_hops=3)
        report = eng.deep_research("exploratory research question", query_type="exploratory")
        assert isinstance(report, ResearchReport)


# ── Edge cases ──────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_query_still_completes(self):
        eng = _engine(max_hops=1)
        report = eng.deep_research("")
        assert isinstance(report, ResearchReport)

    def test_single_hop_with_no_follow_ups(self):
        eng = _engine(max_hops=1)
        report = eng.deep_research("test")
        assert report.trajectories >= 1

    def test_reset_clears_internal_state(self):
        eng = _engine()
        eng.explore("query 1")
        eng.explore("query 2")
        eng._reset()
        assert eng._action_counter == 0
        assert eng._result_counter == 0
        assert eng._finding_counter == 0
        assert len(eng._pending) == 0
        assert len(eng._completed) == 0

    def test_highest_confidence_pending_empty(self):
        eng = _engine()
        assert eng._highest_confidence_pending() is None


# ── Custom dependencies ─────────────────────────────────────────────────


class TestCustomDependencies:
    def test_custom_knowledge_graph(self):
        kg = ResearchKnowledgeGraph()
        eng = _engine(knowledge_graph=kg, max_hops=1)
        eng.deep_research("test")
        assert kg.get_finding_count() > 0

    def test_custom_trajectory(self):
        traj = ResearchTrajectory()
        eng = _engine(trajectory=traj, max_hops=1)
        eng.deep_research("test")
        assert traj.get_action_count() > 0

    def test_custom_source_evaluator(self):
        se = SourceCredibility()
        eng = _engine(source_evaluator=se, max_hops=1)
        report = eng.deep_research("test")
        assert isinstance(report, ResearchReport)

    def test_custom_strategy_selector(self):
        ss = StrategySelector()
        eng = _engine(strategy_selector=ss, max_hops=1)
        report = eng.deep_research("test", query_type="factual")
        assert isinstance(report, ResearchReport)

    def test_min_confidence_threshold(self):
        eng = _engine(min_confidence=0.9, max_hops=2)
        report = eng.deep_research("test")
        assert isinstance(report, ResearchReport)


# ── Dataclass contracts ─────────────────────────────────────────────────


class TestExploreResult:
    def test_immutable_defaults(self):
        r = ExploreResult(sub_query="q")
        assert r.findings == ()
        assert r.sources == ()
        assert r.confidence == 1.0


class TestResearchReport:
    def test_immutable_defaults(self):
        r = ResearchReport(query="q")
        assert r.findings == ()
        assert r.sources == ()
        assert r.consensus_score == 0.0
        assert r.contradictions == 0
        assert r.knowledge_gaps == 0
        assert r.strategy_distribution == {}
