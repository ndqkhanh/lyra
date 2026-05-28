"""Autonomy subsystem for Lyra — full autonomous operation.

Provides state-machine-driven autonomy, goal decomposition, session
management, scheduling, lifecycle hooks, and budget tracking.
"""

from __future__ import annotations

from lyra_cli.autonomy.automation_engine import (
    AutomationEngine,
    Schedule,
    ScheduleKind,
)
from lyra_cli.autonomy.budget_manager import (
    BudgetExceededError,
    BudgetManager,
    BudgetSummary,
    CostEntry,
)
from lyra_cli.autonomy.goal_decomposer import (
    CyclicDependencyError,
    DependencyGraph,
    Goal,
    GoalDecomposer,
    Subtask,
)
from lyra_cli.autonomy.hooks_manager import (
    HookEvent,
    HookHandler,
    HooksManager,
)
from lyra_cli.autonomy.session_manager import (
    CheckpointNotFoundError,
    SessionCheckpoint,
    SessionManager,
)
from lyra_cli.autonomy.state_machine import (
    AutonomyState,
    StateMachine,
    StateTransition,
    TransitionError,
)

__all__ = [
    # State machine
    "AutonomyState",
    "StateTransition",
    "StateMachine",
    "TransitionError",
    # Goal decomposer
    "Goal",
    "Subtask",
    "DependencyGraph",
    "GoalDecomposer",
    "CyclicDependencyError",
    # Session manager
    "SessionCheckpoint",
    "SessionManager",
    "CheckpointNotFoundError",
    # Automation engine
    "Schedule",
    "ScheduleKind",
    "AutomationEngine",
    # Hooks manager
    "HookEvent",
    "HookHandler",
    "HooksManager",
    # Budget manager
    "CostEntry",
    "BudgetSummary",
    "BudgetManager",
    "BudgetExceededError",
]
