"""
Agent Loop v2 — real execution (not simulated).

Replaces asyncio.sleep() with actual LLM calls, tool dispatch, memory
operations, and hook integration.

Planning tools:
- TreeOfThoughts: deliberate problem solving via tree search
- MCTSPlanner: Monte Carlo Tree Search with world model
- AFlowSearch: automated workflow generation
- IdleSpecPlanner: speculative planning during idle time
"""

from lyra.agent_loop.executor import AgentLoopExecutor
from lyra.agent_loop.tree_of_thoughts import (
    AFlowSearch,
    IdleSpecPlanner,
    MCTSPlanner,
    PlanNode,
    SpeculativePlan,
    TreeOfThoughts,
    Workflow,
    WorkflowStep,
)

__all__ = [
    "AgentLoopExecutor",
    "TreeOfThoughts",
    "PlanNode",
    "MCTSPlanner",
    "AFlowSearch",
    "Workflow",
    "WorkflowStep",
    "IdleSpecPlanner",
    "SpeculativePlan",
]
