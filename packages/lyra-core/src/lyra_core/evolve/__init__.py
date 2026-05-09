"""Skill / prompt evolver — GEPA + DSPy-inspired reflective optimiser.

Inspired by *GEPA: Genetic-Pareto Prompt Evolution* (Khattab et al.,
2024) and *NousResearch/hermes-agent-self-evolution*. The argument:
hand-tuned prompts live on the Pareto front of (score, length, latency)
already, but humans search that front linearly. GEPA replaces the
linear hand-tune with a **reflective mutate-and-Pareto-filter** loop:

1. Score each candidate against a small (input, expected) training set.
2. Mutate the front via canonical reflective rewrites (or an LLM).
3. Re-score; keep the non-dominated front; repeat for ``generations``.

The implementation is intentionally model-agnostic — the caller
provides a ``model_call`` callable (``(prompt, input) -> output``) and
optionally a custom mutator. Tests use a deterministic stub model so
the contract is exercisable without wiring a live LLM.

Public surface:

* :class:`EvolveCandidate`    — one prompt + its score / length / lineage.
* :class:`EvolveTrainExample` — one ``(input, expected)`` pair.
* :class:`EvolveReport`       — best candidate + Pareto front + history.
* :func:`score_candidate`     — eval one prompt over the training set.
* :func:`pareto_front`        — non-dominated (score↑, length↓) subset.
* :func:`templated_mutator`   — built-in deterministic mutator.
* :func:`evolve`              — main GEPA loop.
"""
from __future__ import annotations

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
    "EvolveCandidate",
    "EvolveHistoryEntry",
    "EvolveReport",
    "EvolveTrainExample",
    "Mutator",
    "ScoreFn",
    "evolve",
    "pareto_front",
    "score_candidate",
    "templated_mutator",
]
