"""
Lyra Reasoning — Deep Reasoning Research Agent.

A comprehensive reasoning system combining:
- ReflAct reasoning (Reflexion + Acting loop)
- GRPO / SPIRAL training (Group Relative Policy Optimization)
- Multiple advanced reasoning strategies
- Multi-level verification
- Reasoning memory and self-improvement

Example:
    >>> from lyra_reasoning import ReflActReasoner, ChainOfThought
    >>>
    >>> reasoner = ReflActReasoner()
    >>> trace = reasoner.reason("Explain the impact of attention mechanisms in transformers")
    >>> lessons = reasoner.reflect(trace)
"""

__version__ = "1.1.0"

# Existing (legacy) exports — keep backward compatibility
from .agent import DeepReasoningAgent

# GRPO trainer
from .grpo import GRPOTrainer

# New models (ReflAct / GRPO / strategies)
from .models import (
    AnaloguePair,
    GRPOTrajectory,
    ReflActEpisode,
    SpiralSample,
    ThoughtNode,
)
from .models import (
    ReasoningStep as ReflActStep,
)
from .models import (
    ReasoningTrace as ReflActTrace,
)

# Reasoning Graph — structured CoT persistence
from .reasoning_graph import (
    EvidenceNode,
    ReasoningEdge,
    ReasoningGraph,
)

# ReflAct reasoner
from .reflect import ReflActReasoner

# SR2AM — Self-Regulated Simulative Planning
from .sr2am import (
    ExecutionTrace,
    PlanningConfig,
    PlanningStats,
    PlanNode,
    SR2AMPlanner,
    SystemLevel,
    TaskComplexity,
)

# Advanced reasoning strategies
from .strategies import (
    AnalogicalReasoning,
    ChainOfThought,
    SelfConsistency,
    StepBack,
    TreeOfThoughts,
)
from .types import (
    ComputeBudget,
    DifficultyEstimate,
    DifficultyLevel,
    ReasoningConfig,
    ReasoningDepth,
    ReasoningPattern,
    ReasoningResult,
    ReasoningStrategy,
    StepType,
    StrategyPerformance,
    VerificationResult,
)

__all__ = [
    # Legacy
    "DeepReasoningAgent",
    "ReasoningConfig",
    "ReasoningStrategy",
    "ReasoningDepth",
    "ReasoningResult",
    "ReasoningPattern",
    "StrategyPerformance",
    "VerificationResult",
    "ComputeBudget",
    "DifficultyEstimate",
    "DifficultyLevel",
    "StepType",
    # Models
    "ReflActStep",
    "ReflActTrace",
    "ReflActEpisode",
    "GRPOTrajectory",
    "SpiralSample",
    "ThoughtNode",
    "AnaloguePair",
    # ReflAct
    "ReflActReasoner",
    # GRPO
    "GRPOTrainer",
    # Strategies
    "ChainOfThought",
    "TreeOfThoughts",
    "SelfConsistency",
    "StepBack",
    "AnalogicalReasoning",
    # SR2AM
    "ExecutionTrace",
    "PlanNode",
    "PlanningConfig",
    "PlanningStats",
    "SR2AMPlanner",
    "SystemLevel",
    "TaskComplexity",
    # Reasoning Graph
    "EvidenceNode",
    "ReasoningEdge",
    "ReasoningGraph",
]
