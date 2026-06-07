"""
Reliability core for Lyra agent operations.

Provides:
- RetryPolicy + async retry() (exponential backoff with jitter)
- CircuitBreaker (CLOSED / OPEN / HALF_OPEN state machine)
- CheckpointManager (save / restore agent state at step boundaries)
- Gardening agents (auto entropy management for doc, code, test)
- SMTSandbox (SMT-backed deterministic sandbox for query governance)
- FormalQueryLoopGovernance (verify agent actions against formal spec)
"""

from lyra.reliability.retry import RetryPolicy, retry
from lyra.reliability.circuit_breaker import CircuitBreaker, CircuitState
from lyra.reliability.checkpoint import CheckpointManager
from lyra.reliability.gardening_agents import (
    CodeGardeningAgent,
    DocGardeningAgent,
    GardeningIssue,
    GardeningIssueCategory,
    GardeningReport,
    GardeningSchedule,
    GardeningSystem,
    ScheduleFrequency,
    TestGardeningAgent,
)
from lyra.reliability.self_diagnosing_harness import GardenHealth
from lyra.reliability.smt_sandbox import (
    ActionSMT,
    ConstraintOperator,
    FormalQueryLoopGovernance,
    SMTSandbox,
    VerificationStatus,
)

__version__ = "0.1.0"

__all__ = [
    "RetryPolicy",
    "retry",
    "CircuitBreaker",
    "CircuitState",
    "CheckpointManager",
    "GardeningSystem",
    "GardeningSchedule",
    "GardeningReport",
    "GardeningIssue",
    "GardeningIssueCategory",
    "ScheduleFrequency",
    "DocGardeningAgent",
    "CodeGardeningAgent",
    "TestGardeningAgent",
    "GardenHealth",
    "SMTSandbox",
    "FormalQueryLoopGovernance",
    "ActionSMT",
    "ConstraintOperator",
    "VerificationStatus",
]
