"""Lyra Production — Production Reliability + Agent Containment."""

from .models import (
    ConformalPrediction,
    ContainmentEvent,
    EscapeVector,
    ExecutionState,
    FailureMode,
    FailureSignal,
    ReliabilitySnapshot,
    ReliabilityTier,
    TrajectorySegment,
)
from .reliability import ThreeLayerReliability
from .failure_patterns import FailurePatternGuard
from .trajectory import TrajectoryOptimizer
from .conformal import ConformalRouter
from .escape_prevention import EscapePrevention

__version__ = "0.1.0"

__all__ = [
    "FailureMode",
    "ReliabilityTier",
    "ExecutionState",
    "EscapeVector",
    "FailureSignal",
    "ReliabilitySnapshot",
    "TrajectorySegment",
    "ConformalPrediction",
    "ContainmentEvent",
    "ThreeLayerReliability",
    "FailurePatternGuard",
    "TrajectoryOptimizer",
    "ConformalRouter",
    "EscapePrevention",
]
