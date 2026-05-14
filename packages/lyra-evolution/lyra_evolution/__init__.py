"""lyra-evolution: closed-loop self-evolution for Lyra (Phase E)."""
from __future__ import annotations

from .control_record import ControlRecord, new_control_record
from .controller import ClosedLoopController, ControllerConfig, HaltSignal
from .reflexion import ReflexionEngine, ReflexionLesson
from .stability import BudgetViolation, StabilityBudget, StabilityState
from .voyager import SkillCandidate, SkillLibrary, VoyagerAccumulator

__version__ = "0.1.0"

__all__ = [
    "BudgetViolation",
    "ClosedLoopController",
    "ControlRecord",
    "ControllerConfig",
    "HaltSignal",
    "ReflexionEngine",
    "ReflexionLesson",
    "SkillCandidate",
    "SkillLibrary",
    "StabilityBudget",
    "StabilityState",
    "VoyagerAccumulator",
    "new_control_record",
]
