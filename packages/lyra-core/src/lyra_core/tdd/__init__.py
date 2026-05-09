"""Wave-F Task 1: TDD phase as first-class state.

Exposes the agent-loop state machine plus the evidence dataclasses
that power strict transitions. The companion slash command lives
in ``lyra_cli.interactive.session`` behind ``/phase``.
"""
from __future__ import annotations

from .state import (
    GreenPassArtifact,
    HistoryEntry,
    IllegalTDDTransition,
    PlanArtifact,
    RedFailureArtifact,
    RefactorArtifact,
    ShipArtifact,
    TDDPhase,
    TDDState,
    TDDStateMachine,
    TransitionError,
)

__all__ = [
    "GreenPassArtifact",
    "HistoryEntry",
    "IllegalTDDTransition",
    "PlanArtifact",
    "RedFailureArtifact",
    "RefactorArtifact",
    "ShipArtifact",
    "TDDPhase",
    "TDDState",
    "TDDStateMachine",
    "TransitionError",
]
