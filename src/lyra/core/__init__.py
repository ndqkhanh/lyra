"""
Core module for Lyra.

Provides fundamental data structures and types used across the system.
"""

from lyra.core.task import (
    AgentPerformance,
    ExecutionMetrics,
    Result,
    Task,
    TaskPriority,
    TaskStatus,
    TaskType,
)

__all__ = [
    "Task",
    "TaskType",
    "TaskPriority",
    "TaskStatus",
    "Result",
    "ExecutionMetrics",
    "AgentPerformance",
]

__version__ = "1.0.0"
