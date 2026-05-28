"""
Orchestration module for Lyra - Advanced Agent Orchestration.

Implements:
- MASAI-style specialist agents (Planner, Editor, Debugger, Tester)
- Model routing by task slot (Haiku/Sonnet/Opus)
- Closed-loop control with verification
"""

from lyra_cli.orchestration.closed_loop import (
    ClosedLoopController,
    ClosedLoopExecution,
    LoopIteration,
    SimpleVerifier,
    VerificationResult,
)
from lyra_cli.orchestration.model_router import (
    ModelRouter,
    ModelTier,
    RoutingDecision,
    TaskComplexity,
)
from lyra_cli.orchestration.specialist_agents import (
    AgentCapability,
    AgentOrchestrator,
    AgentRole,
    AgentTask,
    SpecialistAgent,
)

__all__ = [
    # Specialist Agents
    "AgentRole",
    "AgentCapability",
    "AgentTask",
    "SpecialistAgent",
    "AgentOrchestrator",
    # Model Router
    "ModelTier",
    "TaskComplexity",
    "RoutingDecision",
    "ModelRouter",
    # Closed Loop
    "VerificationResult",
    "LoopIteration",
    "ClosedLoopExecution",
    "ClosedLoopController",
    "SimpleVerifier",
]
