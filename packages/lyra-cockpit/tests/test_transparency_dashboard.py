"""Tests for the transparency dashboard module."""

from __future__ import annotations

import time

import pytest

from lyra_cockpit.transparency_dashboard import (
    DashboardSnapshot,
    EvidenceGraph,
    EvidenceNode,
    PillarType,
    TransparencyDashboard,
    TransparencyMetric,
)


class TestPillarType:
    def test_pillar_values(self) -> None:
        assert PillarType.DECISION_OBSERVABILITY.value == "decision_observability"
        assert PillarType.POLICY_TRACEABILITY.value == "policy_traceability"
        assert PillarType.DATA_LINEAGE.value == "data_lineage"
        assert PillarType.BEHAVIORAL_AUDITABILITY.value == "behavioral_auditability"
        assert PillarType.CONTINUOUS_EVALUATION.value == "continuous_evaluation"

    def test_five_pillars(self) -> None:
        assert len(list(PillarType)) == 5


class TestTransparencyMetric:
    def test_creation(self) -> None:
        metric = TransparencyMetric(
            pillar=PillarType.DECISION_OBSERVABILITY,
            score=0.85,
            details=("10 decisions logged",),
            timestamp=1000.0,
        )
        assert metric.pillar == PillarType.DECISION_OBSERVABILITY
        assert metric.score == 0.85
        assert metric.details == ("10 decisions logged",)
        assert metric.timestamp == 1000.0

    def test_frozen(self) -> None:
        metric = TransparencyMetric(PillarType.DECISION_OBSERVABILITY, 0.5, (), 0.0)
        with pytest.raises(AttributeError):
            metric.score = 1.0  # type: ignore[misc]


class TestDashboardSnapshot:
    def test_creation(self) -> None:
        metric = TransparencyMetric(PillarType.DATA_LINEAGE, 1.0, (), 0.0)
        snapshot = DashboardSnapshot(
            metrics=(metric,),
            overall_score=1.0,
            generated_at=1000.0,
        )
        assert len(snapshot.metrics) == 1
        assert snapshot.overall_score == 1.0
        assert snapshot.generated_at == 1000.0

    def test_empty_metrics(self) -> None:
        snapshot = DashboardSnapshot(metrics=(), overall_score=0.0, generated_at=0.0)
        assert snapshot.metrics == ()
        assert snapshot.overall_score == 0.0


class TestEvidenceNode:
    def test_creation(self) -> None:
        node = EvidenceNode(
            node_id="n1",
            description="System check passed",
            parent_ids=(),
            confidence=0.95,
            data_source="agent_monitor",
        )
        assert node.node_id == "n1"
        assert node.confidence == 0.95

    def test_with_parents(self) -> None:
        node = EvidenceNode(
            node_id="n3",
            description="Final verdict",
            parent_ids=("n1", "n2"),
            confidence=0.8,
            data_source="audit",
        )
        assert len(node.parent_ids) == 2

    def test_frozen(self) -> None:
        node = EvidenceNode("n1", "desc", (), 0.5, "src")
        with pytest.raises(AttributeError):
            node.description = "changed"  # type: ignore[misc]


class TestEvidenceGraph:
    def test_creation(self) -> None:
        graph = EvidenceGraph(
            nodes=(
                EvidenceNode("n1", "First", (), 0.9, "src"),
                EvidenceNode("n2", "Second", ("n1",), 0.8, "src"),
            ),
            edges=(("n1", "n2"),),
        )
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1

    def test_empty(self) -> None:
        graph = EvidenceGraph(nodes=(), edges=())
        assert graph.nodes == ()
        assert graph.edges == ()


class TestTransparencyDashboard:
    def test_compute_metrics_empty(self) -> None:
        dashboard = TransparencyDashboard()
        snapshot = dashboard.compute_metrics()
        assert len(snapshot.metrics) == 5
        assert snapshot.overall_score == 0.0
        assert all(m.score == 0.0 for m in snapshot.metrics)

    def test_compute_metrics_with_events(self) -> None:
        dashboard = TransparencyDashboard()
        dashboard.log_decision("d1", "Selected strategy A")
        dashboard.log_decision("d2", "Rejected strategy B")
        dashboard.log_policy_check("p1", "passed")
        snapshot = dashboard.compute_metrics()
        assert snapshot.overall_score > 0.0
        # Decision observability should have a score
        decision_score = next(
            m for m in snapshot.metrics
            if m.pillar == PillarType.DECISION_OBSERVABILITY
        )
        assert decision_score.score > 0.0

    def test_get_pillar_score_empty(self) -> None:
        dashboard = TransparencyDashboard()
        score = dashboard.get_pillar_score(PillarType.DATA_LINEAGE)
        assert score == 0.0

    def test_get_pillar_score_with_events(self) -> None:
        dashboard = TransparencyDashboard()
        dashboard.log_data_access("d1", "database")
        dashboard.log_data_access("d2", "cache")
        score = dashboard.get_pillar_score(PillarType.DATA_LINEAGE)
        assert score > 0.0

    def test_log_decision(self) -> None:
        dashboard = TransparencyDashboard()
        dashboard.log_decision("d1", "Reasoning text")
        snapshot = dashboard.compute_metrics()
        d_obs = next(m for m in snapshot.metrics if m.pillar == PillarType.DECISION_OBSERVABILITY)
        assert "1 total" in d_obs.details[0]

    def test_log_policy_check(self) -> None:
        dashboard = TransparencyDashboard()
        dashboard.log_policy_check("policy-1", "compliant")
        snapshot = dashboard.compute_metrics()
        p_trace = next(m for m in snapshot.metrics if m.pillar == PillarType.POLICY_TRACEABILITY)
        assert p_trace.score > 0.0

    def test_log_data_access(self) -> None:
        dashboard = TransparencyDashboard()
        dashboard.log_data_access("data-1", "file_system")
        score = dashboard.get_pillar_score(PillarType.DATA_LINEAGE)
        assert score > 0.0

    def test_log_behavior(self) -> None:
        dashboard = TransparencyDashboard()
        dashboard.log_behavior("agent_spawn", "Agent created")
        score = dashboard.get_pillar_score(PillarType.BEHAVIORAL_AUDITABILITY)
        assert score > 0.0

    def test_log_evaluation(self) -> None:
        dashboard = TransparencyDashboard()
        dashboard.log_evaluation("response_time", 150.0)
        score = dashboard.get_pillar_score(PillarType.CONTINUOUS_EVALUATION)
        assert score > 0.0

    def test_build_evidence_graph_empty(self) -> None:
        dashboard = TransparencyDashboard()
        graph = dashboard.build_evidence_graph([])
        assert graph.nodes == ()
        assert graph.edges == ()

    def test_build_evidence_graph_single(self) -> None:
        dashboard = TransparencyDashboard()
        graph = dashboard.build_evidence_graph([
            {"id": "d1", "description": "First decision", "confidence": 0.9, "source": "agent"},
        ])
        assert len(graph.nodes) == 1
        assert graph.nodes[0].node_id == "d1"

    def test_build_evidence_graph_chain(self) -> None:
        dashboard = TransparencyDashboard()
        graph = dashboard.build_evidence_graph([
            {"id": "d1", "description": "First"},
            {"id": "d2", "description": "Second"},
            {"id": "d3", "description": "Third"},
        ])
        assert len(graph.nodes) == 3
        assert len(graph.edges) == 2
        assert graph.edges[0] == ("d1", "d2")
        assert graph.edges[1] == ("d2", "d3")

    def test_build_evidence_graph_defaults(self) -> None:
        dashboard = TransparencyDashboard()
        graph = dashboard.build_evidence_graph([{}])
        assert len(graph.nodes) == 1
        assert graph.nodes[0].description == "Decision 0"
        assert graph.nodes[0].confidence == 0.5
        assert graph.nodes[0].data_source == "unknown"
        assert graph.nodes[0].parent_ids == ()
