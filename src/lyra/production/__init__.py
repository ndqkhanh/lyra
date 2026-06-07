"""Lyra Production — Production Reliability + Agent Containment."""

from .conformal import ConformalRouter
from .escape_prevention import EscapePrevention
from .failure_patterns import FailurePatternGuard
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
from .trajectory import TrajectoryOptimizer

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
