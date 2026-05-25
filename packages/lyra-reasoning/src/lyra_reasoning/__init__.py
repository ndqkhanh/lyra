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

# New models (ReflAct / GRPO / strategies)
from .models import (
    AnaloguePair,
    GRPOTrajectory,
    ReasoningStep as ReflActStep,
    ReasoningTrace as ReflActTrace,
    ReflActEpisode,
    SpiralSample,
    ThoughtNode,
)

# ReflAct reasoner
from .reflect import ReflActReasoner

# GRPO trainer
from .grpo import GRPOTrainer

# Advanced reasoning strategies
from .strategies import (
    AnalogicalReasoning,
    ChainOfThought,
    SelfConsistency,
    StepBack,
    TreeOfThoughts,
)

# SR2AM — Self-Regulated Simulative Planning
from .sr2am import (
    ExecutionTrace,
    PlanNode,
    PlanningConfig,
    PlanningStats,
    SR2AMPlanner,
    SystemLevel,
    TaskComplexity,
)

# Reasoning Graph — structured CoT persistence
from .reasoning_graph import (
    EvidenceNode,
    ReasoningEdge,
    ReasoningGraph,
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
