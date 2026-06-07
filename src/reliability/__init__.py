"""
Reliability core for Lyra agent operations.

Provides:
- RetryPolicy + async retry() (exponential backoff with jitter)
- CircuitBreaker (CLOSED / OPEN / HALF_OPEN state machine)
- CheckpointManager (save / restore agent state at step boundaries)
"""

from src.reliability.retry import RetryPolicy, retry
from src.reliability.circuit_breaker import CircuitBreaker, CircuitState
from src.reliability.checkpoint import CheckpointManager

__version__ = "0.1.0"

__all__ = [
    "RetryPolicy",
    "retry",
    "CircuitBreaker",
    "CircuitState",
    "CheckpointManager",
]
