"""Provider/model routing layer.

Phase 0 ships only the v1.8 *Confidence-Cascade Router* contract
(Wave-2 §8.2). Future routing strategies (e.g. cost-aware MoE,
locality-aware sticky routing) will live alongside.
"""
from __future__ import annotations

from .cascade import (
    CascadeDecision,
    CascadeResult,
    CascadeStage,
    ConfidenceCascadeRouter,
    ConfidenceEstimator,
    ProviderInvocation,
)

__all__ = [
    "CascadeDecision",
    "CascadeResult",
    "CascadeStage",
    "ConfidenceCascadeRouter",
    "ConfidenceEstimator",
    "ProviderInvocation",
]
