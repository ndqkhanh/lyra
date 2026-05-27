"""
Core module for Lyra.

Provides fundamental data structures and types used across the system.
"""

from src.core.task import (
    Task,
    TaskType,
    TaskPriority,
    TaskStatus,
    Result,
    ExecutionMetrics,
    AgentPerformance,
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
