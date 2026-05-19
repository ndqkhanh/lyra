"""Role coordination and handoff protocols for Lyra Research.

This module provides:
- Role state machine for managing role lifecycle
- Handoff protocol for data transfer between roles
- Role coordinator for orchestrating the full pipeline
- Parallel execution support
- Progress tracking

Also re-exports coordination primitives for backward compatibility.
"""

# Import old coordination primitives (backward compatibility)
from lyra_research.coordination.primitives import (
    CircuitBreaker,
    CircuitBreakerStats,
    CoordinationManager,
    FailureType,
    HealthChecker,
    HealthMetrics,
    RetryPolicy,
    Task,
    TaskState,
    TimeoutEnforcer,
)

# Import new role coordination components
from lyra_research.coordination.role_state_machine import (
    RoleState,
    RoleTransition,
    RoleStateMachine,
)
from lyra_research.coordination.handoff_protocol import (
    HandoffData,
    HandoffProtocol,
)
from lyra_research.coordination.role_coordinator import RoleCoordinator
from lyra_research.coordination.parallel_executor import ParallelExecutor
from lyra_research.coordination.progress_tracker import ProgressTracker

__all__ = [
    # Old coordination primitives (backward compatibility)
    "CircuitBreaker",
    "CircuitBreakerStats",
    "CoordinationManager",
    "FailureType",
    "HealthChecker",
    "HealthMetrics",
    "RetryPolicy",
    "Task",
    "TaskState",
    "TimeoutEnforcer",
    # New role coordination components
    "RoleState",
    "RoleTransition",
    "RoleStateMachine",
    "HandoffData",
    "HandoffProtocol",
    "RoleCoordinator",
    "ParallelExecutor",
    "ProgressTracker",
]
