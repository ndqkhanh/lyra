"""
Reliability core for Lyra agent operations.

Provides:
- RetryPolicy + async retry() (exponential backoff with jitter)
- CircuitBreaker (CLOSED / OPEN / HALF_OPEN state machine)
- CheckpointManager (save / restore agent state at step boundaries)
"""

from lyra.reliability.retry import RetryPolicy, retry
from lyra.reliability.circuit_breaker import CircuitBreaker, CircuitState
from lyra.reliability.checkpoint import CheckpointManager

__version__ = "0.1.0"

__all__ = [
    "RetryPolicy",
    "retry",
    "CircuitBreaker",
    "CircuitState",
    "CheckpointManager",
]
