"""Skill / prompt evolver + PRISM drift detector.

GEPA: Genetic-Pareto Prompt Evolution (Khattab et al., 2024) —
a reflective mutate-and-Pareto-filter loop for prompt optimization.

PRISM: Prompt Drift Detection (arXiv 2605.14454) —
automated detection of LLM prompt degradation with auto-repair.
"""
from __future__ import annotations

from .drift_detector import (
    DriftDetector,
    DriftMetric,
    DriftSeverity,
    DriftSnapshot,
    RepairResult,
    RepairStatus,
)
from .gepa import (
    EvolveCandidate,
    EvolveHistoryEntry,
    EvolveReport,
    EvolveTrainExample,
    Mutator,
    ScoreFn,
    evolve,
    pareto_front,
    score_candidate,
    templated_mutator,
)

__all__ = [
    "DriftDetector",
    "DriftMetric",
    "DriftSeverity",
    "DriftSnapshot",
    "EvolveCandidate",
    "EvolveHistoryEntry",
    "EvolveReport",
    "EvolveTrainExample",
    "Mutator",
    "RepairResult",
    "RepairStatus",
    "ScoreFn",
    "evolve",
    "pareto_front",
    "score_candidate",
    "templated_mutator",
]
