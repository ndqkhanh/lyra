"""
SR2AM — Self-Regulated Simulative Planning.

A 3-system architecture where an 8B model can match the planning quality of 1T
systems by self-regulating planning depth:

- **System I** — Reactive: fast, template-based response for simple tasks with
  high confidence and minimal compute.
- **System II** — World-model simulation: chain-of-thought reasoning with a
  causal world model that simulates outcomes before committing to actions.
- **System III** — Learned configurator: decides which system to use and at
  what depth by estimating task complexity and learning from execution traces.

Typical usage::

    from lyra_reasoning.sr2am import SR2AMPlanner

    planner = SR2AMPlanner()
    plan, config = planner.plan("Fix typo in README")
    trace = ExecutionTrace(
        plan_nodes=tuple(plan),
        actual_outcomes=("Done",),
        deviations=(),
        tokens_used=150,
        success=True,
    )
    planner.learn_from_trace(trace)
"""

from __future__ import annotations

from .planner import (
    ExecutionTrace,
    PlanningConfig,
    PlanningStats,
    PlanNode,
    SR2AMPlanner,
    SystemLevel,
    TaskComplexity,
)

__all__ = [
    "ExecutionTrace",
    "PlanNode",
    "PlanningConfig",
    "PlanningStats",
    "SR2AMPlanner",
    "SystemLevel",
    "TaskComplexity",
]
