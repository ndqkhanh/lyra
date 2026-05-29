"""
Core task and result types for the Lyra agent system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class TaskType(str, Enum):
    """Types of tasks that can be executed."""

    CODE_ANALYSIS = "code_analysis"
    CODE_GENERATION = "code_generation"
    CODE_REFACTORING = "refactoring"
    CODE_REVIEW = "code_review"
    RESEARCH = "research"
    WEB_SEARCH = "web_search"
    DOCUMENT_ANALYSIS = "document_analysis"
    TEST_GENERATION = "test_generation"
    TEST_EXECUTION = "test_execution"
    SECURITY_SCAN = "security_scan"
    GENERIC = "generic"


class TaskPriority(int, Enum):
    """Task priority levels (0 = highest)."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Represents a task to be executed by an agent."""

    task_id: str = field(default_factory=lambda: str(uuid4()))
    type: TaskType = TaskType.GENERIC
    description: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    assigned_to: str | None = None
    dependencies: list[str] = field(default_factory=list)
    estimated_cost: float = 0.0
    estimated_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate task after initialization."""
        if not self.description and not self.params:
            raise ValueError("Task must have either description or params")

    def assign_to(self, agent_id: str) -> None:
        """Assign task to an agent."""
        self.assigned_to = agent_id
        self.status = TaskStatus.ASSIGNED

    def start(self) -> None:
        """Mark task as in progress."""
        self.status = TaskStatus.IN_PROGRESS

    def complete(self) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED

    def fail(self) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED

    def cancel(self) -> None:
        """Cancel the task."""
        self.status = TaskStatus.CANCELLED


@dataclass
class Result:
    """Represents the result of a task execution."""

    task_id: str
    success: bool
    data: Any = None
    error: str | None = None
    agent_id: str | None = None
    duration: float = 0.0
    cost: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate result after initialization."""
        if not self.success and not self.error:
            raise ValueError("Failed result must have an error message")


@dataclass
class ExecutionMetrics:
    """Metrics for task execution."""

    agent_id: str
    task_type: TaskType
    success: bool
    duration: float
    cost: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentPerformance:
    """Performance statistics for an agent."""

    agent_id: str
    total_tasks: int
    success_rate: float
    avg_duration: float
    avg_cost: float
    task_type: TaskType | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
