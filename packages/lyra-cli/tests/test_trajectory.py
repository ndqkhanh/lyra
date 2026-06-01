"""Tests for ResearchTrajectory — action-result tree, metrics, serialization."""

from __future__ import annotations

import pytest
from lyra_cli.research.trajectory import (
    ResearchAction,
    ResearchResult,
    ResearchTrajectory,
)


def _action(
    id: str,
    query: str = "q",
    strategy: str = "breadth_first",
    depth: int = 0,
    parent_id: str | None = None,
) -> ResearchAction:
    return ResearchAction(
        action_id=id,
        action_type="search",
        query=query,
        strategy=strategy,
        depth=depth,
        parent_id=parent_id,
    )


def _result(
    id: str,
    action_id: str,
    findings: tuple[str, ...] = (),
    sources: tuple[str, ...] = (),
    confidence: float = 1.0,
) -> ResearchResult:
    return ResearchResult(
        result_id=id,
        action_id=action_id,
        findings=findings,
        sources=sources,
        confidence=confidence,
        source_count=len(sources),
    )


# ── Dataclass contracts ─────────────────────────────────────────────────


class TestResearchAction:
    def test_action_immutable_defaults(self):
        a = ResearchAction(
            action_id="a1", action_type="search", query="test", strategy="breadth_first", depth=0
        )
        assert a.parent_id is None
        assert a.timestamp

    def test_action_with_parent(self):
        a = ResearchAction(
            action_id="a2",
            action_type="analyze",
            query="deep",
            strategy="depth_first",
            depth=2,
            parent_id="a1",
        )
        assert a.parent_id == "a1"
        assert a.depth == 2


class TestResearchResult:
    def test_result_defaults(self):
        r = ResearchResult(result_id="r1", action_id="a1")
        assert r.findings == ()
        assert r.sources == ()
        assert r.confidence == 1.0
        assert r.source_count == 0

    def test_result_with_data(self):
        r = ResearchResult(
            result_id="r1", action_id="a1", findings=("f1", "f2"), sources=("s1",), confidence=0.85
        )
        assert len(r.findings) == 2
        assert r.confidence == 0.85


# ── Tree operations ─────────────────────────────────────────────────────


class TestAddAction:
    def test_add_action_returns_id(self):
        t = ResearchTrajectory()
        aid = t.add_action(_action("a1", query="root"))
        assert aid == "a1"
        assert t.get_action_count() == 1

    def test_add_action_sets_root(self):
        t = ResearchTrajectory()
        t.add_action(_action("a1"))
        root = t.get_root()
        assert root is not None
        assert root.action_id == "a1"

    def test_add_action_builds_parent_child_tree(self):
        t = ResearchTrajectory()
        t.add_action(_action("root", depth=0))
        t.add_action(_action("child", depth=1, parent_id="root"))
        node = t.get_node("child")
        assert node is not None
        assert node.parent is not None
        assert node.parent.action.action_id == "root"


class TestAddResult:
    def test_add_result_attaches_to_action(self):
        t = ResearchTrajectory()
        t.add_action(_action("a1"))
        t.add_result(_result("r1", "a1", findings=("found",)))
        node = t.get_node("a1")
        assert node is not None
        assert node.result is not None
        assert "found" in node.result.findings

    def test_add_result_missing_action_raises(self):
        t = ResearchTrajectory()
        with pytest.raises(KeyError, match="No action found"):
            t.add_result(_result("r1", "nonexistent"))


class TestGetPathTo:
    def test_get_path_root_to_leaf(self):
        t = ResearchTrajectory()
        t.add_action(_action("root", depth=0))
        t.add_action(_action("mid", depth=1, parent_id="root"))
        t.add_action(_action("leaf", depth=2, parent_id="mid"))
        path = t.get_path_to("leaf")
        assert [a.action_id for a in path] == ["root", "mid", "leaf"]

    def test_get_path_missing_raises(self):
        t = ResearchTrajectory()
        with pytest.raises(KeyError):
            t.get_path_to("nope")


class TestLeafNodes:
    def test_leaf_nodes(self):
        t = ResearchTrajectory()
        t.add_action(_action("root"))
        t.add_action(_action("child", parent_id="root"))
        leaves = t.get_leaf_nodes()
        assert len(leaves) == 1
        assert leaves[0].action.action_id == "child"

    def test_leaf_nodes_single_root(self):
        t = ResearchTrajectory()
        t.add_action(_action("root"))
        leaves = t.get_leaf_nodes()
        assert len(leaves) == 1


# ── Metrics ─────────────────────────────────────────────────────────────


class TestCoverageMetrics:
    def test_empty_trajectory_metrics(self):
        t = ResearchTrajectory()
        m = t.get_coverage_metrics()
        assert m["total_actions"] == 0
        assert m["max_depth"] == 0

    def test_metrics_with_data(self):
        t = ResearchTrajectory()
        t.add_action(_action("root", depth=0))
        t.add_action(_action("child", depth=1, parent_id="root"))
        t.add_action(_action("grandchild", depth=2, parent_id="child"))
        t.add_result(_result("r1", "root", findings=("f1",), sources=("s1", "s2")))
        t.add_result(_result("r2", "child", findings=("f2",), sources=("s3",)))
        m = t.get_coverage_metrics()
        assert m["total_actions"] == 3
        assert m["total_results"] == 2
        assert m["max_depth"] == 2
        assert m["leaf_count"] == 1
        assert m["unique_sources"] == 3
        assert m["unique_findings"] == 2


class TestGetAllFindings:
    def test_get_all_findings_dedup(self):
        t = ResearchTrajectory()
        t.add_action(_action("a1"))
        t.add_action(_action("a2"))
        t.add_result(_result("r1", "a1", findings=("dup", "unique1")))
        t.add_result(_result("r2", "a2", findings=("dup", "unique2")))
        findings = t.get_all_findings()
        assert len(findings) == 3
        assert "dup" in findings


# ── Serialization ───────────────────────────────────────────────────────


class TestSerialization:
    def test_to_dict_roundtrip(self):
        t = ResearchTrajectory()
        t.add_action(_action("root", query="test query", depth=0))
        t.add_action(_action("child", query="sub query", depth=1, parent_id="root"))
        t.add_result(_result("r1", "root", findings=("f1",), sources=("s1",)))
        t.add_result(_result("r2", "child", findings=("f2",), sources=("s2",)))

        d = t.to_dict()
        assert d["root_id"] == "root"
        assert len(d["actions"]) == 2
        assert len(d["results"]) == 2

        t2 = ResearchTrajectory()
        t2.from_dict(d)
        assert t2.get_action_count() == 2
        root = t2.get_root()
        assert root is not None
        assert root.action_id == "root"
        assert len(t2.get_all_findings()) == 2

    def test_from_dict_clears_existing_state(self):
        t = ResearchTrajectory()
        t.add_action(_action("old"))
        t.from_dict({"root_id": "new_root", "actions": [], "results": []})
        assert t.get_action_count() == 0
        assert t.get_root() is None
