"""Diversity-preservation primitives for Lyra's parallel/multi-agent paths.

Designed in direct response to *Diversity Collapse in Multi-Agent LLM Systems*
(Chen et al., NUS, ACL 2026 Findings — arXiv:2604.18005, mirrored under
``papers/diversity-collapse-mas.pdf``).

The paper finds that without explicit countermeasures, multi-agent systems
suffer **diversity collapse** — an interaction-driven contraction of the
explored idea space. Specifically:

- *Compute Efficiency Paradox* (§3): stronger / more aligned models yield
  diminishing marginal diversity with no quality gain.
- *Authority-Induced Collapse* (§4): expert + hierarchy persona mixes
  (``Leader-Led``, ``Interdisciplinary``) collapse to Vendi 4.65–6.93;
  flat junior groups (``Horizontal``) sustain Vendi 8.08; mixed
  (``Vertical``) is the Pareto compromise (Vendi 6.08, OQ 8.32).
- *Group Size Saturation* (§5): Vendi/N drops from 1.03 (N=3) to 0.47
  (N=7) — over 50% efficiency loss with naive scaling.
- *Topology Effect* (§5.2): NGT (silent ideation) maximises *initial*
  diversity; Subgroups maximise *sustained* constructive conflict.

The Lyra response is exposed here as four orthogonal primitives that any
parallel-attempt subsystem (TournamentTts, ReasoningBank.matts_prefix,
the future Software Org Mode, the existing subagent dispatcher) can
plug in:

1. ``DiversityMetric`` — Protocol abstracting Vendi / pairwise distance /
   custom; single source of truth for "how diverse is this set".
2. ``effective_diversity`` — concrete pairwise-distance fallback that needs
   no embedding model (good enough for fast unit tests + small sets).
3. ``mmr_select`` — Maximal Marginal Relevance reranker; the canonical fix
   for ReasoningBank.recall returning near-duplicates.
4. ``ngt_attempt_independence_guard`` — enforces the paper's NGT prescription
   that parallel attempts must be generated *blind* (no shared context
   leakage); the guard accepts a list of generation-context fingerprints
   and raises if they collide.

This is **Phase-0 contract scaffolding**. Concrete diversity-preservation
behaviour lands in v1.8 Phase 6 (TournamentTts wires `effective_diversity`
into the discriminator) and v1.9 Phase 1 (Software Org Mode defaults to
Vertical persona × Subgroups topology).
"""
from __future__ import annotations

from .metrics import (
    DiversityMetric,
    PairwiseDistanceMetric,
    effective_diversity,
    mean_pairwise_distance,
    mmr_select,
    ngt_attempt_independence_guard,
)

__all__ = [
    "DiversityMetric",
    "PairwiseDistanceMetric",
    "effective_diversity",
    "mean_pairwise_distance",
    "mmr_select",
    "ngt_attempt_independence_guard",
]
