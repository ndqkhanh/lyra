"""Tests for ResearchTrajectory."""

import pytest

from lyra_cli.research.trajectory import (
    ResearchAction,
    ResearchResult,
    ResearchTrajectory,
)


class TestResearchTrajectory:
    """Test suite for ResearchTrajectory."""

    def test_add_action_and_get_root(self):
        """Adding a root action and retrieving it works."""
        t = ResearchTrajectory()
        action = ResearchAction(
            action_id="act_001",
            action_type="search",
            query="What is RLHF?",
            strategy="breadth_first",
            depth=0,
        )
        t.add_action(action)

        root = t.get_root()
        assert root is not None
        assert root.action_id == "act_001"
        assert root.query == "What is RLHF?"

    def test_add_result_to_action(self):
        """Attaching a result to an action and reading it back."""
        t = ResearchTrajectory()
        action = ResearchAction(
            action_id="act_001",
            action_type="search",
            query="test",
            strategy="depth_first",
            depth=0,
        )
        t.add_action(action)

        result = ResearchResult(
            result_id="res_001",
            action_id="act_001",
            findings=("finding a", "finding b"),
            sources=("src_001",),
            confidence=0.85,
            source_count=1,
        )
        t.add_result(result)

        node = t.get_node("act_001")
        assert node is not None
        assert node.result is not None
        assert node.result.result_id == "res_001"
        assert "finding a" in node.result.findings

    def test_add_result_missing_action_raises(self):
        """Adding a result for a non-existent action raises KeyError."""
        t = ResearchTrajectory()
        result = ResearchResult(
            result_id="res_001",
            action_id="act_missing",
            findings=(),
        )
        with pytest.raises(KeyError):
            t.add_result(result)

    def test_path_to_action(self):
        """get_path_to returns the ordered path from root."""
        t = ResearchTrajectory()
        root = ResearchAction(
            action_id="act_root", action_type="search",
            query="root", strategy="breadth_first", depth=0,
        )
        child = ResearchAction(
            action_id="act_child", action_type="search",
            query="child", strategy="depth_first", depth=1,
            parent_id="act_root",
        )
        grandchild = ResearchAction(
            action_id="act_gc", action_type="analyze",
            query="grandchild", strategy="best_first", depth=2,
            parent_id="act_child",
        )
        t.add_action(root)
        t.add_action(child)
        t.add_action(grandchild)

        path = t.get_path_to("act_gc")
        assert len(path) == 3
        assert path[0].action_id == "act_root"
        assert path[1].action_id == "act_child"
        assert path[2].action_id == "act_gc"

    def test_get_path_to_missing_raises(self):
        """get_path_to raises KeyError for unknown actions."""
        t = ResearchTrajectory()
        with pytest.raises(KeyError):
            t.get_path_to("act_nonexistent")

    def test_get_leaf_nodes(self):
        """Leaf nodes are actions without children."""
        t = ResearchTrajectory()
        root = ResearchAction(
            action_id="act_root", action_type="search",
            query="root", strategy="breadth_first", depth=0,
        )
        child = ResearchAction(
            action_id="act_child", action_type="search",
            query="child", strategy="depth_first", depth=1,
            parent_id="act_root",
        )
        t.add_action(root)
        t.add_action(child)

        leaves = t.get_leaf_nodes()
        assert len(leaves) == 1
        assert leaves[0].action.action_id == "act_child"

    def test_get_all_findings(self):
        """Collects unique findings across all results."""
        t = ResearchTrajectory()
        a1 = ResearchAction(
            action_id="act_1", action_type="search",
            query="q1", strategy="bf", depth=0,
        )
        a2 = ResearchAction(
            action_id="act_2", action_type="search",
            query="q2", strategy="df", depth=1, parent_id="act_1",
        )
        t.add_action(a1)
        t.add_action(a2)
        t.add_result(ResearchResult(
            result_id="res_1", action_id="act_1",
            findings=("alpha", "beta"),
        ))
        t.add_result(ResearchResult(
            result_id="res_2", action_id="act_2",
            findings=("beta", "gamma"),
        ))

        findings = t.get_all_findings()
        assert set(findings) == {"alpha", "beta", "gamma"}

    def test_coverage_metrics(self):
        """Coverage metrics reflect tree structure."""
        t = ResearchTrajectory()
        root = ResearchAction(
            action_id="act_root", action_type="search",
            query="root", strategy="bf", depth=0,
        )
        c1 = ResearchAction(
            action_id="act_c1", action_type="search",
            query="c1", strategy="bf", depth=1, parent_id="act_root",
        )
        c2 = ResearchAction(
            action_id="act_c2", action_type="search",
            query="c2", strategy="bf", depth=1, parent_id="act_root",
        )
        t.add_action(root)
        t.add_action(c1)
        t.add_action(c2)
        t.add_result(ResearchResult(
            result_id="res_root", action_id="act_root",
            findings=("a",), sources=("s1",),
        ))
        t.add_result(ResearchResult(
            result_id="res_c1", action_id="act_c1",
            findings=("b",), sources=("s2",),
        ))

        metrics = t.get_coverage_metrics()
        assert metrics["total_actions"] == 3
        assert metrics["total_results"] == 2
        assert metrics["unique_findings"] == 2
        assert metrics["unique_sources"] == 2
        assert metrics["leaf_count"] == 2

    def test_empty_trajectory_metrics(self):
        """Empty trajectory returns zeroed metrics."""
        t = ResearchTrajectory()
        metrics = t.get_coverage_metrics()
        assert metrics["total_actions"] == 0
        assert metrics["total_results"] == 0
        assert metrics["max_depth"] == 0

    def test_serialization_roundtrip(self):
        """to_dict / from_dict roundtrip preserves state."""
        t = ResearchTrajectory()
        t.add_action(ResearchAction(
            action_id="act_1", action_type="search",
            query="q1", strategy="bf", depth=0,
        ))
        t.add_action(ResearchAction(
            action_id="act_2", action_type="extract",
            query="q2", strategy="df", depth=1, parent_id="act_1",
        ))
        t.add_result(ResearchResult(
            result_id="res_1", action_id="act_1",
            findings=("x",),
        ))

        data = t.to_dict()

        t2 = ResearchTrajectory()
        t2.from_dict(data)

        assert t2.get_action_count() == 2
        root = t2.get_root()
        assert root is not None
        assert root.action_id == "act_1"
        path = t2.get_path_to("act_2")
        assert len(path) == 2

    def test_get_node_returns_none(self):
        """get_node returns None for missing action ID."""
        t = ResearchTrajectory()
        assert t.get_node("nonexistent") is None

    def test_root_is_none_when_empty(self):
        """get_root returns None on empty trajectory."""
        t = ResearchTrajectory()
        assert t.get_root() is None
