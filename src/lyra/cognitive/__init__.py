"""
Lyra Cognitive Architecture - Dual-System AGI Reasoning Engine.

This package implements a production-grade cognitive architecture with:
- Dual-System Design (Kahneman-style System 1/System 2)
- Theater of Mind Global Workspace (Baars' Global Workspace Theory)
- Multi-Strategy Reasoning Engine
- Meta-Cognitive Mode Switching (DOLORES/APEX-style)
- Cognitive Tick Loop Orchestration
"""

from lyra.cognitive.cognitive_loop import CognitiveLoop
from lyra.cognitive.dual_system import (
    MetaCognitiveController,
    System1Executor,
    System2Planner,
)
from lyra.cognitive.models import (
    AttentionSignal,
    CognitiveState,
    CognitiveTick,
    ConfidenceLevel,
    Plan,
    SystemMode,
    Thought,
)
from lyra.cognitive.reasoning import ReasoningEngine, ReasoningResult, ReasoningTrace
from lyra.cognitive.theater_of_mind import AttentionManager, TheaterOfMind

__version__ = "0.1.0"

__all__ = [
    # Models
    "SystemMode",
    "ConfidenceLevel",
    "AttentionSignal",
    "Thought",
    "Plan",
    "CognitiveState",
    "CognitiveTick",
    # Dual System
    "System2Planner",
    "System1Executor",
    "MetaCognitiveController",
    # Theater of Mind
    "TheaterOfMind",
    "AttentionManager",
    # Cognitive Loop
    "CognitiveLoop",
    # Reasoning
    "ReasoningEngine",
    "ReasoningTrace",
    "ReasoningResult",
]
