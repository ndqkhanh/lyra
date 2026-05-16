"""
Orchestration module for Lyra - Advanced Agent Orchestration.

Implements:
- MASAI-style specialist agents (Planner, Editor, Debugger, Tester)
- Model routing by task slot (Haiku/Sonnet/Opus)
- Closed-loop control with verification
"""

from lyra_cli.orchestration.specialist_agents import (
    AgentRole,
    AgentCapability,
    AgentTask,
    SpecialistAgent,
    AgentOrchestrator,
)

from lyra_cli.orchestration.model_router import (
    ModelTier,
    TaskComplexity,
    RoutingDecision,
    ModelRouter,
)

from lyra_cli.orchestration.closed_loop import (
    VerificationResult,
    LoopIteration,
    ClosedLoopExecution,
    ClosedLoopController,
    SimpleVerifier,
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
