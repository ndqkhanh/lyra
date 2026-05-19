"""
Tests for adaptive task decomposition.
"""
import pytest

from lyra_research.adaptive_coordination import AdaptiveTaskGraph
from lyra_research.coordination import Task


def test_adaptive_task_graph_initialization():
    """Test adaptive task graph initialization."""
    graph = AdaptiveTaskGraph()

    assert len(graph.tasks) == 0
    assert len(graph.adaptation_history) == 0


def test_adapt_graph_insufficient_sources():
    """Test adaptation when insufficient sources found."""
    graph = AdaptiveTaskGraph()

    # Simulate insufficient sources (< 10)
    results = [
        {"sources": ["s1", "s2", "s3"]},  # Only 3 sources
    ]

    new_tasks = graph.adapt_graph(results)

    assert len(new_tasks) > 0
    assert all(t.agent_type == "discovery" for t in new_tasks)
    assert len(graph.adaptation_history) == 1
    assert graph.adaptation_history[0]["reason"] == "insufficient_sources"


def test_adapt_graph_sufficient_sources():
    """Test no adaptation when sufficient sources found."""
    graph = AdaptiveTaskGraph()

    # Simulate sufficient sources (>= 10)
    results = [
        {"sources": [f"s{i}" for i in range(15)]},  # 15 sources
    ]

    new_tasks = graph.adapt_graph(results)

    # Should not add discovery tasks
    discovery_tasks = [t for t in new_tasks if t.agent_type == "discovery"]
    assert len(discovery_tasks) == 0


def test_adapt_graph_contradictions_detected():
    """Test adaptation when contradictions detected."""
    graph = AdaptiveTaskGraph()

    # Simulate contradictions
    results = [
        {
            "sources": [f"s{i}" for i in range(15)],  # Sufficient sources
            "contradictions": [("claim1", "claim2"), ("claim3", "claim4")],
        }
    ]

    new_tasks = graph.adapt_graph(results)

    falsification_tasks = [t for t in new_tasks if t.agent_type == "falsification"]
    assert len(falsification_tasks) > 0
    assert len(graph.adaptation_history) == 1
    assert graph.adaptation_history[0]["reason"] == "contradictions_detected"


def test_adapt_graph_no_contradictions():
    """Test no adaptation when no contradictions."""
    graph = AdaptiveTaskGraph()

    results = [
        {
            "sources": [f"s{i}" for i in range(15)],
            "contradictions": [],
        }
    ]

    new_tasks = graph.adapt_graph(results)

    falsification_tasks = [t for t in new_tasks if t.agent_type == "falsification"]
    assert len(falsification_tasks) == 0


def test_adapt_graph_low_quality_sources():
    """Test adaptation when low-quality sources detected."""
    graph = AdaptiveTaskGraph()

    results = [
        {
            "sources": [f"s{i}" for i in range(15)],
            "quality_score": 0.5,  # Low quality
        }
    ]

    new_tasks = graph.adapt_graph(results)

    analysis_tasks = [t for t in new_tasks if t.agent_type == "analysis"]
    assert len(analysis_tasks) > 0
    assert len(graph.adaptation_history) == 1
    assert graph.adaptation_history[0]["reason"] == "low_quality_sources"


def test_adapt_graph_high_quality_sources():
    """Test no adaptation when high-quality sources."""
    graph = AdaptiveTaskGraph()

    results = [
        {
            "sources": [f"s{i}" for i in range(15)],
            "quality_score": 0.9,  # High quality
        }
    ]

    new_tasks = graph.adapt_graph(results)

    analysis_tasks = [t for t in new_tasks if t.agent_type == "analysis"]
    assert len(analysis_tasks) == 0


def test_adapt_graph_multiple_adaptations():
    """Test multiple adaptations in sequence."""
    graph = AdaptiveTaskGraph()

    # First adaptation: insufficient sources
    results1 = [{"sources": ["s1", "s2"]}]
    new_tasks1 = graph.adapt_graph(results1)

    # Second adaptation: contradictions
    results2 = [
        {
            "sources": [f"s{i}" for i in range(15)],
            "contradictions": [("c1", "c2")],
        }
    ]
    new_tasks2 = graph.adapt_graph(results2)

    assert len(graph.adaptation_history) == 2
    assert graph.adaptation_history[0]["reason"] == "insufficient_sources"
    assert graph.adaptation_history[1]["reason"] == "contradictions_detected"


def test_adapt_graph_combined_issues():
    """Test adaptation with multiple issues simultaneously."""
    graph = AdaptiveTaskGraph()

    results = [
        {
            "sources": ["s1", "s2"],  # Insufficient
            "contradictions": [("c1", "c2")],  # Has contradictions
            "quality_score": 0.5,  # Low quality
        }
    ]

    new_tasks = graph.adapt_graph(results)

    # Should add tasks for all issues
    discovery_tasks = [t for t in new_tasks if t.agent_type == "discovery"]
    falsification_tasks = [t for t in new_tasks if t.agent_type == "falsification"]
    analysis_tasks = [t for t in new_tasks if t.agent_type == "analysis"]

    assert len(discovery_tasks) > 0
    assert len(falsification_tasks) > 0
    assert len(analysis_tasks) > 0
    assert len(graph.adaptation_history) == 3


def test_adapt_graph_contradiction_count_scaling():
    """Test falsification tasks scale with contradiction count."""
    graph = AdaptiveTaskGraph()

    # Many contradictions
    results = [
        {
            "sources": [f"s{i}" for i in range(15)],
            "contradiction_count": 10,
        }
    ]

    new_tasks = graph.adapt_graph(results)

    falsification_tasks = [t for t in new_tasks if t.agent_type == "falsification"]
    # Should create multiple falsification tasks for many contradictions
    assert len(falsification_tasks) >= 2


def test_adapt_graph_low_confidence():
    """Test adaptation for low confidence results."""
    graph = AdaptiveTaskGraph()

    results = [
        {
            "sources": [f"s{i}" for i in range(15)],
            "confidence": 0.6,  # Low confidence
        }
    ]

    new_tasks = graph.adapt_graph(results)

    analysis_tasks = [t for t in new_tasks if t.agent_type == "analysis"]
    assert len(analysis_tasks) > 0


def test_get_adaptation_history():
    """Test getting adaptation history."""
    graph = AdaptiveTaskGraph()

    results = [{"sources": ["s1", "s2"]}]
    graph.adapt_graph(results)

    history = graph.get_adaptation_history()

    assert len(history) == 1
    assert history[0]["reason"] == "insufficient_sources"
    assert "tasks_added" in history[0]


def test_adaptation_history_immutable():
    """Test adaptation history returns copy."""
    graph = AdaptiveTaskGraph()

    results = [{"sources": ["s1", "s2"]}]
    graph.adapt_graph(results)

    history1 = graph.get_adaptation_history()
    history1.append({"fake": "entry"})

    history2 = graph.get_adaptation_history()

    assert len(history2) == 1  # Original unchanged
