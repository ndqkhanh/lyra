"""Transparency dashboard — 5-pillar transparency framework.

Provides structured observability into agent decisions, policy traceability,
data lineage, behavioral auditability, and continuous evaluation.
"""

from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass


class PillarType(enum.Enum):
    """The five pillars of the transparency framework."""

    DECISION_OBSERVABILITY = "decision_observability"
    POLICY_TRACEABILITY = "policy_traceability"
    DATA_LINEAGE = "data_lineage"
    BEHAVIORAL_AUDITABILITY = "behavioral_auditability"
    CONTINUOUS_EVALUATION = "continuous_evaluation"


@dataclass(frozen=True)
class TransparencyMetric:
    """A single transparency metric for a given pillar.

    Attributes:
        pillar: The pillar this metric belongs to.
        score: Numeric score between 0.0 and 1.0.
        details: Tuple of detail strings describing the metric.
        timestamp: Unix timestamp when the metric was recorded.
    """

    pillar: PillarType
    score: float
    details: tuple[str, ...]
    timestamp: float


@dataclass(frozen=True)
class DashboardSnapshot:
    """A snapshot of the transparency dashboard at a point in time.

    Attributes:
        metrics: Tuple of TransparencyMetric instances.
        overall_score: Aggregate score across all pillars (0.0 to 1.0).
        generated_at: Unix timestamp of snapshot generation.
    """

    metrics: tuple[TransparencyMetric, ...]
    overall_score: float
    generated_at: float


@dataclass(frozen=True)
class EvidenceNode:
    """A single node in the evidence graph.

    Attributes:
        node_id: Unique identifier for this node.
        description: Human-readable description of the evidence.
        parent_ids: Tuple of parent node IDs that this node depends on.
        confidence: Confidence score (0.0 to 1.0).
        data_source: Source system or component that produced this evidence.
    """

    node_id: str
    description: str
    parent_ids: tuple[str, ...]
    confidence: float
    data_source: str


@dataclass(frozen=True)
class EvidenceGraph:
    """A directed graph of evidence nodes.

    Attributes:
        nodes: Tuple of EvidenceNode instances.
        edges: Tuple of (parent_id, child_id) directed edge pairs.
    """

    nodes: tuple[EvidenceNode, ...]
    edges: tuple[tuple[str, str], ...]


class TransparencyDashboard:
    """Five-pillar transparency framework for agent observability.

    Provides metrics computation, evidence graph building, and pillar-level
    score retrieval.
    """

    def __init__(self) -> None:
        self._pillar_logs: dict[PillarType, list[dict]] = {
            pillar: [] for pillar in PillarType
        }

    def _log_event(self, pillar: PillarType, event: dict) -> None:
        """Record an event log entry for a given pillar."""
        self._pillar_logs[pillar].append({"timestamp": time.time(), **event})

    def log_decision(self, decision_id: str, reasoning: str) -> None:
        """Log a decision event under DECISION_OBSERVABILITY."""
        self._log_event(
            PillarType.DECISION_OBSERVABILITY,
            {"type": "decision", "decision_id": decision_id, "reasoning": reasoning},
        )

    def log_policy_check(self, policy_id: str, result: str) -> None:
        """Log a policy traceability event under POLICY_TRACEABILITY."""
        self._log_event(
            PillarType.POLICY_TRACEABILITY,
            {"type": "policy_check", "policy_id": policy_id, "result": result},
        )

    def log_data_access(self, data_id: str, source: str) -> None:
        """Log a data lineage event under DATA_LINEAGE."""
        self._log_event(
            PillarType.DATA_LINEAGE,
            {"type": "data_access", "data_id": data_id, "source": source},
        )

    def log_behavior(self, behavior_type: str, details: str) -> None:
        """Log a behavioral auditability event under BEHAVIORAL_AUDITABILITY."""
        self._log_event(
            PillarType.BEHAVIORAL_AUDITABILITY,
            {"type": "behavior", "behavior_type": behavior_type, "details": details},
        )

    def log_evaluation(self, metric_name: str, value: float) -> None:
        """Log a continuous evaluation event under CONTINUOUS_EVALUATION."""
        self._log_event(
            PillarType.CONTINUOUS_EVALUATION,
            {"type": "evaluation", "metric_name": metric_name, "value": value},
        )

    def compute_metrics(self) -> DashboardSnapshot:
        """Compute transparency metrics across all five pillars.

        Returns:
            A DashboardSnapshot with per-pillar scores and overall score.
        """
        metrics_list: list[TransparencyMetric] = []
        now = time.time()

        for pillar in PillarType:
            logs = self._pillar_logs[pillar]
            if not logs:
                score = 0.0
                details = ("No events recorded for this pillar",)
            else:
                # Compute score based on log volume and recency
                recent_count = sum(
                    1 for log in logs if log["timestamp"] > now - 3600
                )
                score = min(recent_count / 10.0, 1.0)
                details = (
                    f"{len(logs)} total events",
                    f"{recent_count} events in last hour",
                )

            metrics_list.append(
                TransparencyMetric(
                    pillar=pillar,
                    score=score,
                    details=details,
                    timestamp=now,
                )
            )

        overall_score = (
            sum(m.score for m in metrics_list) / len(metrics_list)
            if metrics_list
            else 0.0
        )

        return DashboardSnapshot(
            metrics=tuple(metrics_list),
            overall_score=overall_score,
            generated_at=now,
        )

    def build_evidence_graph(self, decision_log: list[dict]) -> EvidenceGraph:
        """Build an evidence graph from a decision log.

        Args:
            decision_log: A list of decision event dictionaries. Each dict
                should have at least an "id" key.

        Returns:
            An EvidenceGraph with nodes and directed edges.
        """
        nodes: list[EvidenceNode] = []
        edges: list[tuple[str, str]] = []

        if not decision_log:
            return EvidenceGraph(nodes=(), edges=())

        for i, entry in enumerate(decision_log):
            node_id = entry.get("id", str(uuid.uuid4()))
            description = entry.get("description", f"Decision {i}")
            parent_ids: tuple[str, ...] = ()
            if i > 0:
                parent_id = decision_log[i - 1].get(
                    "id", f"decision-{i - 1}"
                )
                parent_ids = (parent_id,)
                edges.append((parent_id, node_id))

            nodes.append(
                EvidenceNode(
                    node_id=node_id,
                    description=description,
                    parent_ids=parent_ids,
                    confidence=entry.get("confidence", 0.5),
                    data_source=entry.get("source", "unknown"),
                )
            )

        return EvidenceGraph(nodes=tuple(nodes), edges=tuple(edges))

    def get_pillar_score(self, pillar: PillarType) -> float:
        """Get the current transparency score for a single pillar.

        Args:
            pillar: The PillarType to query.

        Returns:
            A float score between 0.0 and 1.0.
        """
        logs = self._pillar_logs[pillar]
        if not logs:
            return 0.0
        recent_count = sum(
            1 for log in logs if log["timestamp"] > time.time() - 3600
        )
        return min(recent_count / 10.0, 1.0)
