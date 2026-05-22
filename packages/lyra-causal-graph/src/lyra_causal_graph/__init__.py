"""Causal Graph — Streaming causal graph construction using LI-CTE for agent trace analysis."""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    import numpy as np
except ImportError:
    np = None

logger = logging.getLogger(__name__)

__all__ = [
    "EntityNode",
    "ActionEdge",
    "OutcomeNode",
    "LatentVariable",
    "CausalGraph",
]




@dataclass
class EntityNode:
    id: str
    name: str
    entity_type: str  # file, tool, api, concept, user
    properties: dict[str, Any] = field(default_factory=dict)
    embedding: Optional[np.ndarray] = None


@dataclass
class ActionEdge:
    id: str
    source_id: str
    target_id: str
    action_type: str  # read, write, execute, call, observe
    timestamp: float
    outcome_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OutcomeNode:
    id: str
    result: str
    success: bool
    latency: float
    error: Optional[str] = None
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class LatentVariable:
    name: str
    inferred_from: list[str]
    confidence: float
    value: float = 0.0


class CausalGraph:
    """Streaming causal graph with LI-CTE causal inference."""

    def __init__(self):
        self.entities: dict[str, EntityNode] = {}
        self.actions: dict[str, ActionEdge] = {}
        self.outcomes: dict[str, OutcomeNode] = {}
        self.latent_vars: dict[str, LatentVariable] = {}
        self.action_counter = 0

    def add_entity(self, entity: EntityNode) -> str:
        self.entities[entity.id] = entity
        return entity.id

    def add_action(self, action: ActionEdge) -> str:
        self.action_counter += 1
        self.actions[action.id] = action
        return action.id

    def add_outcome(self, outcome: OutcomeNode) -> str:
        self.outcomes[outcome.id] = outcome
        return outcome.id

    def add_latent_variable(self, var: LatentVariable) -> str:
        self.latent_vars[var.name] = var
        return var.name

    def query_entity(self, entity_id: str) -> Optional[EntityNode]:
        return self.entities.get(entity_id)

    def get_actions_for_entity(self, entity_id: str) -> list[ActionEdge]:
        return [a for a in self.actions.values() if a.source_id == entity_id or a.target_id == entity_id]

    def get_outcome_for_action(self, action_id: str) -> Optional[OutcomeNode]:
        action = self.actions.get(action_id)
        if action and action.outcome_id:
            return self.outcomes.get(action.outcome_id)
        return None

    def compute_li_cte(self, source_id: str, target_id: str, lag: int = 1) -> float:
        """Compute Late-Interaction Conditional Transfer Entropy between two entities."""
        if np is None:
            return 0.0
        source_actions = [a for a in self.actions.values() if a.source_id == source_id]
        target_actions = [a for a in self.actions.values() if a.source_id == target_id]

        if len(source_actions) < 2 or len(target_actions) < 2:
            return 0.0

        source_times = np.array([a.timestamp for a in source_actions])
        target_times = np.array([a.timestamp for a in target_actions])

        source_seq = np.array([
            self.outcomes[a.outcome_id].metrics.get("value", 0.0)
            for a in source_actions if a.outcome_id and a.outcome_id in self.outcomes
        ])
        target_seq = np.array([
            self.outcomes[a.outcome_id].metrics.get("value", 0.0)
            for a in target_actions if a.outcome_id and a.outcome_id in self.outcomes
        ])

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

        cross_corr = np.correlate(diff_s[:len(diff_s)-lag], diff_t[lag:], mode='valid')
        auto_corr = np.correlate(diff_s, diff_s, mode='valid')

        if len(cross_corr) == 0 or len(auto_corr) == 0:
            return 0.0

        te = np.abs(cross_corr[0]) / (np.abs(auto_corr[0]) + 1e-10)
        return float(min(te, 1.0))

    def explain(self, outcome_id: str) -> dict[str, Any]:
        """Explain why an outcome occurred by tracing causal paths."""
        outcome = self.outcomes.get(outcome_id)
        if not outcome:
            return {"error": "Outcome not found"}

        causal_actions = [
            a for a in self.actions.values()
            if a.outcome_id == outcome_id
        ]

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
            "causal_actions": [{"type": a.action_type, "source": a.source_id, "target": a.target_id} for a in causal_actions],
            "involved_entities": list(causal_entities),
            "transfer_entropy": te_scores,
            "latent_variables": [{"name": v.name, "confidence": v.confidence} for v in self.latent_vars.values()],
        }

    @property
    def stats(self) -> dict[str, int]:
        return {
            "entities": len(self.entities),
            "actions": len(self.actions),
            "outcomes": len(self.outcomes),
            "latent_variables": len(self.latent_vars),
        }
