"""Autonomy subsystem for Lyra — full autonomous operation.

Provides state-machine-driven autonomy, goal decomposition, session
management, scheduling, lifecycle hooks, and budget tracking.
"""

from __future__ import annotations

from lyra_cli.autonomy.state_machine import (
    AutonomyState,
    StateTransition,
    StateMachine,
    TransitionError,
)
from lyra_cli.autonomy.goal_decomposer import (
    Goal,
    Subtask,
    DependencyGraph,
    GoalDecomposer,
    CyclicDependencyError,
)
from lyra_cli.autonomy.session_manager import (
    SessionCheckpoint,
    SessionManager,
    CheckpointNotFoundError,
)
from lyra_cli.autonomy.automation_engine import (
    Schedule,
    ScheduleKind,
    AutomationEngine,
)
from lyra_cli.autonomy.hooks_manager import (
    HookEvent,
    HookHandler,
    HooksManager,
)
from lyra_cli.autonomy.budget_manager import (
    CostEntry,
    BudgetSummary,
    BudgetManager,
    BudgetExceededError,
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
