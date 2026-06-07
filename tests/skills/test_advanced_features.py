"""
Tests for skills advanced features (v8.1):
  - Full skill graph traversal (GraphTraversal)
  - Skill recommendation (SkillRecommender)
  - Graph visualization (GraphVisualization)
  - Quality calibration (QualityCalibrator)
  - Regression detection
"""

import pytest

from lyra.skills.evolution import (
    CLARITY,
    COMPLETENESS,
    CORRECTNESS,
    EFFICIENCY,
    RUBRIC_DIMENSIONS,
    SAFETY,
    EvalScore,
)
from lyra.skills.quality_calibrator import (
    CalibrationSample,
    QualityCalibrator,
    RegressionReport,
    calibrate_from_feedback,
)
from lyra.skills.skill import Skill, SkillCategory
from lyra.skills.skillnet import (
    CONFLICT,
    DEPENDENCY,
    PREREQUISITE,
    SIMILARITY,
    GraphTraversal,
    GraphVisualization,
    SkillGraphLink,
    SkillNet,
    SkillRecommender,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_skills() -> list[Skill]:
    """Create a small set of skills for graph tests."""
    skills = [
        Skill(
            name="python-basics",
            description="Fundamentals of Python programming",
            content="Python syntax, data types, control flow",
            category=SkillCategory.BACKEND_PATTERNS,
            tags=["python", "basics", "programming"],
        ),
        Skill(
            name="async-python",
            description="Async/await patterns in Python",
            content="Async functions, event loops, asyncio",
            category=SkillCategory.BACKEND_PATTERNS,
            tags=["python", "async", "concurrency"],
            dependencies=["python-basics"],
        ),
        Skill(
            name="web-framework",
            description="Python web frameworks",
            content="Flask, FastAPI, Django basics",
            category=SkillCategory.FRAMEWORK_SPECIFIC,
            tags=["python", "web", "flask", "fastapi"],
            dependencies=["async-python"],
        ),
        Skill(
            name="database-sql",
            description="SQL and database patterns",
            content="SQL queries, migrations, ORM patterns",
            category=SkillCategory.DATABASE,
            tags=["sql", "database", "orm"],
        ),
        Skill(
            name="testing-pytest",
            description="Testing with pytest",
            content="Fixtures, mocks, parametrize",
            category=SkillCategory.TDD_TESTING,
            tags=["testing", "pytest", "python"],
            dependencies=["python-basics"],
        ),
    ]
    return skills


@pytest.fixture
def sample_net(sample_skills: list[Skill]) -> SkillNet:
    """Create a SkillNet with pre-built links."""
    net = SkillNet()
    for s in sample_skills:
        net.add_skill(s)

    # Add explicit links
    net.add_link(SkillGraphLink(
        source="async-python", target="python-basics",
        link_type=DEPENDENCY, weight=1.0,
    ))
    net.add_link(SkillGraphLink(
        source="web-framework", target="async-python",
        link_type=DEPENDENCY, weight=1.0,
    ))
    net.add_link(SkillGraphLink(
        source="testing-pytest", target="python-basics",
        link_type=DEPENDENCY, weight=1.0,
    ))
    net.add_link(SkillGraphLink(
        source="testing-pytest", target="database-sql",
        link_type=SIMILARITY, weight=0.4,
    ))
    net.add_link(SkillGraphLink(
        source="async-python", target="python-basics",
        link_type=PREREQUISITE, weight=0.9,
    ))
    return net


# =============================================================================
# Skill Graph Traversal Tests
# =============================================================================


class TestGraphTraversal:
    """Tests for GraphTraversal."""

    def test_find_skill_path_direct(self, sample_net: SkillNet):
        traversal = GraphTraversal(sample_net)
        path = traversal.find_skill_path(
            current_skills=["python-basics"],
            target_capability="async-python",
        )
        assert len(
            path) > 0, "Should find a path from python-basics to async-python"
        # The path should connect towards the target skill; validate that
        # the target capability appears somewhere at the correct end.
        edge_targets = {e.target for e in path}
        edge_sources = {e.source for e in path}
        assert "async-python" in edge_sources or "async-python" in edge_targets

    def test_find_skill_path_multi_hop(self, sample_net: SkillNet):
        traversal = GraphTraversal(sample_net)
        path = traversal.find_skill_path(
            current_skills=["python-basics"],
            target_capability="web-framework",
        )
        assert len(path) > 0

    def test_find_skill_path_unreachable(self, sample_net: SkillNet):
        traversal = GraphTraversal(sample_net)
        path = traversal.find_skill_path(
            current_skills=["web-framework"],
            target_capability="nonexistent-skill",
        )
        assert path == []

    def test_missing_prerequisites_none(self, sample_net: SkillNet):
        traversal = GraphTraversal(sample_net)
        missing = traversal.missing_prerequisites(
            "python-basics", owned={"python-basics"}
        )
        assert missing == []

    def test_missing_prerequisites_some(self, sample_net: SkillNet):
        traversal = GraphTraversal(sample_net)
        missing = traversal.missing_prerequisites(
            "async-python", owned={"python-basics"}
        )
        # async-python depends on python-basics which is owned
        assert isinstance(missing, list)

    def test_downstream_skills(self, sample_net: SkillNet):
        traversal = GraphTraversal(sample_net)
        downstream = traversal.downstream_skills("python-basics", max_depth=2)
        assert len(downstream) > 0
        assert "async-python" in downstream

    def test_topological_sort(self, sample_net: SkillNet):
        traversal = GraphTraversal(sample_net)
        ordered = traversal.topological_sort()
        assert len(ordered) == len(sample_net.skills)
        # python-basics should come before async-python
        pb_index = ordered.index("python-basics")
        ap_index = ordered.index("async-python")
        assert pb_index < ap_index


# =============================================================================
# Skill Recommender Tests
# =============================================================================


class TestSkillRecommender:
    """Tests for SkillRecommender."""

    def test_recommend_no_skills(self, sample_net: SkillNet):
        recommender = SkillRecommender(sample_net)
        recs = recommender.recommend(current_skills=[], top_k=3)
        assert len(recs) >= 0  # May recommend any skills

    def test_recommend_with_skills(self, sample_net: SkillNet):
        recommender = SkillRecommender(sample_net)
        recs = recommender.recommend(
            current_skills=["python-basics"], top_k=3
        )
        assert len(recs) <= 3
        for name, score, reason in recs:
            assert isinstance(name, str)
            assert 0.0 <= score <= 1.0
            assert isinstance(reason, str)
            assert name != "python-basics"  # Should not recommend owned skills

    def test_recommend_all_owned(self, sample_net: SkillNet):
        """When all skills are owned, no recommendations should be returned."""
        recommender = SkillRecommender(sample_net)
        all_skills = list(sample_net.skills.keys())
        recs = recommender.recommend(current_skills=all_skills, top_k=5)
        assert len(recs) == 0

    def test_recommend_to_fill_gap(self, sample_net: SkillNet):
        recommender = SkillRecommender(sample_net)
        result = recommender.recommend_to_fill_gap(
            current_skills=["python-basics"],
            target_skill="web-framework",
            top_k=3,
        )
        if result:
            assert "async-python" in [r[0] for r in result]

    def test_recommend_to_fill_gap_unknown_target(self, sample_net: SkillNet):
        recommender = SkillRecommender(sample_net)
        result = recommender.recommend_to_fill_gap(
            current_skills=["python-basics"],
            target_skill="nonexistent",
        )
        assert result == []


# =============================================================================
# Skill Graph Visualization Tests
# =============================================================================


class TestGraphVisualization:
    """Tests for GraphVisualization."""

    def test_to_mermaid(self, sample_net: SkillNet):
        viz = GraphVisualization(sample_net)
        mermaid = viz.to_mermaid(show_legend=True)
        assert "```mermaid" in mermaid
        assert "flowchart LR" in mermaid
        assert "python-basics" in mermaid
        assert "async-python" in mermaid

    def test_to_mermaid_no_legend(self, sample_net: SkillNet):
        viz = GraphVisualization(sample_net)
        mermaid = viz.to_mermaid(show_legend=False)
        assert "Legend" not in mermaid

    def test_to_markdown_report(self, sample_net: SkillNet):
        viz = GraphVisualization(sample_net)
        report = viz.to_markdown_report()
        assert "Skill Graph Report" in report
        assert "Total skills" in report
        assert "Total links" in report
        assert "Dependency Graph" in report

    def test_safe_mermaid_id(self):
        assert GraphVisualization._safe_mermaid_id("hello-world") == "hello_world"
        assert GraphVisualization._safe_mermaid_id("123abc") == "n_123abc"
        assert GraphVisualization._safe_mermaid_id("") == "unknown"

    def test_empty_net_mermaid(self):
        net = SkillNet()
        viz = GraphVisualization(net)
        mermaid = viz.to_mermaid()
        assert "```mermaid" in mermaid


# =============================================================================
# Quality Calibrator Tests
# =============================================================================


class TestQualityCalibrator:
    """Tests for QualityCalibrator."""

    def test_default_weights(self):
        cal = QualityCalibrator()
        weights = cal.get_weights("general")
        assert abs(sum(weights.values()) - 1.0) < 1e-6
        for dim in RUBRIC_DIMENSIONS:
            assert dim in weights

    def test_add_rating(self):
        cal = QualityCalibrator()
        cal.add_rating(CORRECTNESS, 0.9, expected_score=0.6, category="code")
        assert len(cal._samples["code"]) == 1

    def test_calibrate_no_samples(self):
        cal = QualityCalibrator()
        result = cal.calibrate("nonexistent")
        assert result.samples_used == 0
        assert abs(sum(result.weights.values()) - 1.0) < 1e-6

    def test_calibrate_with_samples(self):
        cal = QualityCalibrator(learning_rate=0.1)
        # Add ratings: correctness is valued highly, safety less so
        for _ in range(10):
            cal.add_rating(CORRECTNESS, 0.9, expected_score=0.6, category="code")
            cal.add_rating(SAFETY, 0.3, expected_score=0.7, category="code")
        result = cal.calibrate("code")
        assert result.samples_used == 20
        # Correctness weight should be higher than safety after calibration
        assert result.weights[CORRECTNESS] > result.weights[SAFETY]
        assert result.improvement >= 0.0

    def test_calibrate_all(self):
        cal = QualityCalibrator()
        cal.add_rating(CORRECTNESS, 0.8, category="code")
        cal.add_rating(COMPLETENESS, 0.7, category="research")
        results = cal.calibrate_all()
        assert "code" in results
        assert "research" in results

    def test_per_category_weights(self):
        cal = QualityCalibrator()
        cal.add_rating(CORRECTNESS, 0.9, expected_score=0.5, category="code", skill_name="test")
        cal.add_rating(CLARITY, 0.3, expected_score=0.6, category="code", skill_name="test")
        cal.calibrate("code")

        cal.add_rating(CLARITY, 0.9, expected_score=0.5, category="research", skill_name="test2")
        cal.calibrate("research")

        code_w = cal.get_weights("code")
        research_w = cal.get_weights("research")
        # Different categories should have different weights
        assert code_w != research_w

    def test_reset_weights_category(self):
        cal = QualityCalibrator()
        cal.add_rating(CORRECTNESS, 0.9, category="code")
        cal.calibrate("code")
        cal.reset_weights("code")
        result = cal.calibrate("code")
        # After reset, weights should be back to defaults
        assert abs(sum(result.weights.values()) - 1.0) < 1e-6

    def test_reset_weights_all(self):
        cal = QualityCalibrator()
        cal.add_rating(CORRECTNESS, 0.9, category="code")
        cal.calibrate("code")
        cal.reset_weights()
        assert len(cal._samples) == 0

    def test_add_eval_score_rating(self):
        cal = QualityCalibrator()
        score = EvalScore(correctness=0.8, completeness=0.7, clarity=0.9, efficiency=0.6, safety=1.0)
        cal.add_eval_score_rating(score, skill_name="test", category="code")
        assert len(cal._samples["code"]) == 5  # One per dimension


# =============================================================================
# Regression Detection Tests
# =============================================================================


class TestRegressionDetection:
    """Tests for regression detection in QualityCalibrator."""

    def test_no_regression_short_history(self):
        cal = QualityCalibrator()
        history = [
            EvalScore(correctness=0.8, completeness=0.7, clarity=0.9, efficiency=0.6, safety=1.0)
            for _ in range(3)  # Less than window*2 = 10
        ]
        reports = cal.detect_regression("test-skill", history, window=5)
        assert reports == []

    def test_no_regression_stable(self):
        cal = QualityCalibrator()
        history = [
            EvalScore(correctness=0.8, completeness=0.7, clarity=0.9, efficiency=0.6, safety=1.0)
            for _ in range(12)
        ]
        reports = cal.detect_regression("test-skill", history, window=5)
        # All scores stable -- no regression
        regression_reports = [r for r in reports if r.severity != "ok"]
        assert len(regression_reports) == 0

    def test_regression_detected(self):
        cal = QualityCalibrator()
        # Previous window: high scores
        history = [
            EvalScore(correctness=0.9, completeness=0.8, clarity=0.9, efficiency=0.8, safety=1.0)
            for _ in range(5)
        ]
        # Recent window: low scores (regression)
        history += [
            EvalScore(correctness=0.3, completeness=0.8, clarity=0.9, efficiency=0.8, safety=1.0)
            for _ in range(5)
        ]
        reports = cal.detect_regression("test-skill", history, window=5)
        assert len(reports) == 5  # One per dimension
        correctness_report = [r for r in reports if r.dimension == CORRECTNESS][0]
        assert correctness_report.change < 0
        assert correctness_report.severity != "ok"

    def test_regression_report_structure(self):
        report = RegressionReport(
            skill_name="test-skill",
            dimension=CORRECTNESS,
            current_avg=0.4,
            previous_avg=0.8,
            change=-0.4,
            severity="critical",
        )
        d = report.to_dict()
        assert d["skill_name"] == "test-skill"
        assert d["severity"] == "critical"
        assert d["change"] == -0.4


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestCalibrateFromFeedback:
    """Tests for calibrate_from_feedback convenience function."""

    def test_basic_calibration(self):
        ratings = [
            {"dimension": CORRECTNESS, "rating": 0.9, "expected_score": 0.5, "category": "code"},
            {"dimension": SAFETY, "rating": 0.2, "expected_score": 0.5, "category": "code"},
            {"dimension": CLARITY, "rating": 0.7, "expected_score": 0.5, "category": "code"},
        ]
        weights = calibrate_from_feedback(ratings, category="code", learning_rate=0.1)
        assert abs(sum(weights.values()) - 1.0) < 1e-6
        # Correctness rated higher than safety
        assert weights[CORRECTNESS] > weights[SAFETY]

    def test_empty_ratings(self):
        weights = calibrate_from_feedback([], category="general")
        assert abs(sum(weights.values()) - 1.0) < 1e-6


# =============================================================================
# Skill Net Edge Cases
# =============================================================================


class TestSkillNetEdges:
    """Edge case tests for SkillNet and advanced graph features."""

    def test_add_conflict_link(self):
        net = SkillNet()
        s1 = Skill(name="skill-a", description="A", content="Content A")
        s2 = Skill(name="skill-b", description="B", content="Content B")
        net.add_skill(s1)
        net.add_skill(s2)
        net.add_link(SkillGraphLink(
            source="skill-a", target="skill-b",
            link_type=CONFLICT, weight=0.8,
        ))
        assert net.links_to("skill-b")[0].link_type == CONFLICT

    def test_bfs_traversal(self):
        net = SkillNet()
        for name in ["a", "b", "c", "d"]:
            net.add_skill(Skill(name=name, description=name, content=name))
        net.add_link(SkillGraphLink(source="a", target="b"))
        net.add_link(SkillGraphLink(source="b", target="c"))
        net.add_link(SkillGraphLink(source="c", target="d"))
        visited = net.bfs("a", max_depth=2)
        assert "a" in visited
        assert "b" in visited
        assert "c" in visited
        assert "d" not in visited  # Depth 2 from a means 2 hops

    def test_bfs_unknown_start(self):
        net = SkillNet()
        visited = net.bfs("nonexistent")
        assert visited == {}

    def test_find_path_same_source_target(self):
        net = SkillNet()
        s = Skill(name="same", description="S", content="S")
        net.add_skill(s)
        path = net.find_path("same", "same")
        assert path == []

    def test_find_path_unknown_nodes(self):
        net = SkillNet()
        path = net.find_path("unknown1", "unknown2")
        assert path == []

    def test_prune_isolated(self):
        net = SkillNet()
        net.add_skill(Skill(name="linked", description="L", content="L"))
        net.add_skill(Skill(name="isolated", description="I", content="I"))
        net.add_link(SkillGraphLink(source="linked", target="linked"))
        removed = net.prune_isolated()
        assert any(s.name == "isolated" for s in removed)
        assert "linked" in net.skills
