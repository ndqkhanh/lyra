"""Lyra Causal Graph — Causal discovery, inference, and reasoning for AGI agent traces.

This package provides a comprehensive causal reasoning toolkit:

- **Causal graph construction**: Build DAGs from observational data using
  PC and FCI algorithms, with edge scoring, pruning, and cycle detection.
- **Intervention modeling**: do-calculus implementation, ATE/CATE/ITE estimation,
  backdoor and front-door adjustment, inverse propensity weighting.
- **Counterfactual reasoning**: What-if query answering via the
  abduction-action-prediction framework, individual treatment effects.
- **Root cause analysis**: Causal chain traversal, attribution scoring,
  anomaly-path correlation, intervention recommendation.
- **Structural Causal Models**: SCM specification with exogenous noise
  models, multi-equation support, interventional sampling.

Key design principles:
- All modules use type hints and comprehensive docstrings.
- Structured logging via ``logging.getLogger(__name__)``.
- Custom exception hierarchy in ``errors.py``.
- Async/await support for long-running operations.
- Configuration via frozen dataclasses with sensible defaults.
"""

from __future__ import annotations

# Re-import dataclass for the legacy compatibility classes
from dataclasses import dataclass
from dataclasses import field as _field
from typing import Any as _Any
from typing import Optional as _Optional

import numpy as _np

# ── Core Graph ────────────────────────────────────────────────────────────────
from .causal_graph import (
    # Algorithms
    CausalGraph,
    # Data types
    CausalGraphConfig,
    ConditionalIndependenceTest,
    EdgeType,
    FCIAlgorithm,
    GraphEdge,
    GraphNode,
    PCAlgorithm,
)

# ── Re-export legacy aliases (from the original stub) ─────────────────────────
# These are maintained for backward compatibility with code that imports
# from the original single-file module.
from .causal_graph import CausalGraph as _CausalGraph

# ── Counterfactual ────────────────────────────────────────────────────────────
from .counterfactual import (
    CounterfactualConfig,
    CounterfactualQuery,
    CounterfactualReasoner,
    CounterfactualResult,
)

# ── Errors ────────────────────────────────────────────────────────────────────
from .errors import (
    AdjustmentError,
    CausalGraphError,
    CounterfactualError,
    CycleDetectedError,
    EstimationError,
    GraphConstructionError,
    InterventionError,
    InvalidEdgeError,
    InvalidNodeError,
    RootCauseError,
    SCMError,
)

# ── Intervention ─────────────────────────────────────────────────────────────
from .intervention import (
    AdjustmentMethod,
    BackdoorAdjuster,
    FrontdoorAdjuster,
    InterventionConfig,
    InterventionModel,
    InterventionResult,
    TreatmentEffect,
)

# ── Root Cause ────────────────────────────────────────────────────────────────
from .root_cause import (
    AttributionScore,
    RootCause,
    RootCauseAnalyzer,
    RootCauseConfig,
)

# ── Structural Causal Models ─────────────────────────────────────────────────
from .scm import (
    # Noise models
    EndogenousVariable,
    ExogenousVariable,
    GaussianNoise,
    LaplaceNoise,
    NoiseModel,
    # SCM
    SCMConfig,
    SCMEquation,
    StructuralCausalModel,
    UniformNoise,
    # Factory helpers
    make_chain_scm,
    make_collider_scm,
)


# Legacy EntityNode — wraps GraphNode with entity_type compatibility
@dataclass
class EntityNode:
    """Legacy entity node — maintained for backward compatibility.

    Maps entity_type to node_type in the new GraphNode system.
    """

    id: str
    name: str
    entity_type: str = "unknown"
    properties: dict[str, _Any] = _field(default_factory=dict)
    embedding: _np.ndarray | None = None

    def to_graph_node(self) -> GraphNode:
        return GraphNode(
            id=self.id,
            name=self.name,
            node_type=self.entity_type,
            metadata={"properties": self.properties},
        )


# Legacy ActionEdge — wraps GraphEdge with legacy fields
@dataclass
class ActionEdge:
    """Legacy action edge — maintained for backward compatibility.

    Maps legacy fields to the new GraphEdge system.
    """

    id: str
    source_id: str
    target_id: str
    action_type: str = "unknown"
    timestamp: float = 0.0
    outcome_id: str | None = None
    metadata: dict[str, _Any] = _field(default_factory=dict)


# Legacy OutcomeNode (from original stub)


@dataclass
class OutcomeNode:
    """Legacy outcome node — maintained for backward compatibility.

    Prefer using ``CausalGraph`` with node metadata instead.
    """

    id: str
    result: str
    success: bool
    latency: float
    error: str | None = None
    metrics: dict[str, float] = _field(default_factory=dict)


@dataclass
class LatentVariable:
    """Legacy latent variable — maintained for backward compatibility.

    Prefer using ``ExogenousVariable`` from ``lyra_causal_graph.scm`` instead.
    """

    name: str
    inferred_from: list[str]
    confidence: float
    value: float = 0.0


# Legacy CausalGraph adapter (combines old API with new implementation)
class LegacyCausalGraph(_CausalGraph):
    """Adapter providing backward-compatible API from the original stub.

    Maps the old EntityNode/ActionEdge/OutcomeNode API onto the new CausalGraph.
    """

    def __init__(self, config: CausalGraphConfig | None = None):
        super().__init__(config=config)
        self.entities: dict[str, EntityNode] = {}
        self.actions: dict[str, ActionEdge] = {}
        self.outcomes: dict[str, OutcomeNode] = {}
        self.latent_vars: dict[str, LatentVariable] = {}
        self.action_counter = 0

    def add_entity(self, entity: EntityNode) -> str:
        self.entities[entity.id] = entity
        self.add_node(entity.id, name=entity.name, node_type=entity.entity_type)
        return entity.id

    def add_action(self, action: ActionEdge) -> str:
        self.action_counter += 1
        self.actions[action.id] = action
        try:
            self.add_directed_edge(
                action.source_id,
                action.target_id,
                strength=0.5,
                confidence=0.5,
            )
        except CycleDetectedError:
            pass
        return action.id

    def add_outcome(self, outcome: OutcomeNode) -> str:
        self.outcomes[outcome.id] = outcome
        return outcome.id

    def add_latent_variable(self, var: LatentVariable) -> str:
        self.latent_vars[var.name] = var
        return var.name

    def query_entity(self, entity_id: str) -> EntityNode | None:
        return self.entities.get(entity_id)

    def get_actions_for_entity(self, entity_id: str) -> list[ActionEdge]:
        return [
            a for a in self.actions.values() if a.source_id == entity_id or a.target_id == entity_id
        ]

    def get_outcome_for_action(self, action_id: str) -> OutcomeNode | None:
        action = self.actions.get(action_id)
        if action and action.outcome_id:
            return self.outcomes.get(action.outcome_id)
        return None

    def compute_li_cte(self, source_id: str, target_id: str, lag: int = 1) -> float:
        """Compute Late-Interaction Conditional Transfer Entropy."""
        import numpy as np

        source_actions = [a for a in self.actions.values() if a.source_id == source_id]
        target_actions = [a for a in self.actions.values() if a.source_id == target_id]

        if len(source_actions) < 2 or len(target_actions) < 2:
            return 0.0

        source_seq = np.array(
            [
                self.outcomes[a.outcome_id].metrics.get("value", 0.0)
                for a in source_actions
                if a.outcome_id and a.outcome_id in self.outcomes
            ]
        )
        target_seq = np.array(
            [
                self.outcomes[a.outcome_id].metrics.get("value", 0.0)
                for a in target_actions
                if a.outcome_id and a.outcome_id in self.outcomes
            ]
        )

        if len(source_seq) < 2 or len(target_seq) < 2:
            return 0.0

        min_len = min(len(source_seq), len(target_seq))
        source_seq = source_seq[:min_len]
        target_seq = target_seq[:min_len]

        if min_len < lag + 1:
            return 0.0

        source_var = np.var(source_seq)
        target_var = np.var(target_seq)
        if source_var < 1e-10 or target_var < 1e-10:
            return 0.0

        diff_s = np.diff(source_seq)
        diff_t = np.diff(target_seq)

        if len(diff_s) < lag + 1 or len(diff_t) < lag + 1:
            return 0.0

        cross_corr = np.correlate(diff_s[: len(diff_s) - lag], diff_t[lag:], mode="valid")
        auto_corr = np.correlate(diff_s, diff_s, mode="valid")

        if len(cross_corr) == 0 or len(auto_corr) == 0:
            return 0.0

        te = np.abs(cross_corr[0]) / (np.abs(auto_corr[0]) + 1e-10)
        return float(min(te, 1.0))

    def explain(self, outcome_id: str) -> dict:
        """Explain why an outcome occurred by tracing causal paths."""
        outcome = self.outcomes.get(outcome_id)
        if not outcome:
            return {"error": "Outcome not found"}

        causal_actions = [a for a in self.actions.values() if a.outcome_id == outcome_id]
        causal_entities = set()
        for action in causal_actions:
            causal_entities.add(action.source_id)
            causal_entities.add(action.target_id)

        te_scores = {}
        for src in causal_entities:
            for tgt in causal_entities:
                if src != tgt:
                    te_scores[f"{src}->{tgt}"] = self.compute_li_cte(src, tgt)

        return {
            "outcome": outcome.result,
            "success": outcome.success,
            "causal_actions": [
                {"type": a.action_type, "source": a.source_id, "target": a.target_id}
                for a in causal_actions
            ],
            "involved_entities": list(causal_entities),
            "transfer_entropy": te_scores,
            "latent_variables": [
                {"name": v.name, "confidence": v.confidence} for v in self.latent_vars.values()
            ],
        }

    @property
    def stats(self) -> dict[str, int]:
        return {
            "entities": len(self.entities),
            "actions": len(self.actions),
            "outcomes": len(self.outcomes),
            "latent_variables": len(self.latent_vars),
        }


# Override the top-level CausalGraph name for backward compatibility
CausalGraph = LegacyCausalGraph  # noqa: F811


__all__ = [
    # Core graph & algorithms
    "CausalGraph",
    "CausalGraphConfig",
    "PCAlgorithm",
    "FCIAlgorithm",
    "ConditionalIndependenceTest",
    "EdgeType",
    "GraphEdge",
    "GraphNode",
    # Errors
    "CausalGraphError",
    "GraphConstructionError",
    "InvalidNodeError",
    "InvalidEdgeError",
    "CycleDetectedError",
    "InterventionError",
    "AdjustmentError",
    "CounterfactualError",
    "SCMError",
    "RootCauseError",
    "EstimationError",
    # SCM
    "StructuralCausalModel",
    "SCMConfig",
    "SCMEquation",
    "EndogenousVariable",
    "ExogenousVariable",
    "NoiseModel",
    "GaussianNoise",
    "UniformNoise",
    "LaplaceNoise",
    "make_chain_scm",
    "make_collider_scm",
    # Intervention
    "InterventionModel",
    "InterventionConfig",
    "InterventionResult",
    "TreatmentEffect",
    "AdjustmentMethod",
    "BackdoorAdjuster",
    "FrontdoorAdjuster",
    # Counterfactual
    "CounterfactualReasoner",
    "CounterfactualQuery",
    "CounterfactualResult",
    "CounterfactualConfig",
    # Root Cause
    "RootCauseAnalyzer",
    "RootCauseConfig",
    "RootCause",
    "AttributionScore",
    # Legacy compatibility
    "EntityNode",
    "ActionEdge",
    "OutcomeNode",
    "LatentVariable",
]
