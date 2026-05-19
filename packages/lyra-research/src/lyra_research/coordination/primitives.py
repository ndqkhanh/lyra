"""
Agent Coordination Primitives for Lyra Deep Research.

Provides task state management, retry policies, circuit breakers,
timeout enforcement, and health checks for multi-agent coordination.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import uuid4

if TYPE_CHECKING:
    from lyra_core.context.isolation import ContextBoundary


# ---------------------------------------------------------------------------
# Task State Machine
# ---------------------------------------------------------------------------


class TaskState(Enum):
    """Task lifecycle states."""

    PENDING = "pending"
    RUNNING = "running"
    RETRY = "retry"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class FailureType(Enum):
    """Categorizes failures for retry policy decisions."""

    TRANSIENT = "transient"  # Network, rate limit — retry
    LOGIC = "logic"  # Code error, invalid input — don't retry
    TIMEOUT = "timeout"  # Exceeded time limit
    UNKNOWN = "unknown"


@dataclass
class Task:
    """Represents a single research task with state tracking."""

    id: str = field(default_factory=lambda: str(uuid4()))
    state: TaskState = TaskState.PENDING
    retry_count: int = 0
    max_retries: int = 2
    timeout_seconds: int = 300  # 5 minutes
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    failure_type: Optional[FailureType] = None
    agent_type: str = "generic"  # For circuit breaker tracking
    memory_mb: float = 0.0  # Current memory usage
    context_boundary: Optional[ContextBoundary] = None  # For child-task isolation

    def start(self) -> None:
        """Transition to RUNNING state."""
        if self.state != TaskState.PENDING and self.state != TaskState.RETRY:
            raise ValueError(f"Cannot start task in state {self.state}")
        self.state = TaskState.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def complete(self) -> None:
        """Transition to COMPLETED state."""
        if self.state != TaskState.RUNNING:
            raise ValueError(f"Cannot complete task in state {self.state}")
        self.state = TaskState.COMPLETED
        self.completed_at = datetime.now(timezone.utc)

    def fail(self, error: str, failure_type: FailureType = FailureType.UNKNOWN) -> None:
        """Mark task as failed with error details."""
        self.error = error
        self.failure_type = failure_type
        self.completed_at = datetime.now(timezone.utc)

        if failure_type == FailureType.TIMEOUT:
            self.state = TaskState.TIMEOUT
        elif failure_type == FailureType.TRANSIENT and self.retry_count < self.max_retries:
            self.retry_count += 1
            self.state = TaskState.RETRY
        else:
            self.state = TaskState.FAILED

    def elapsed_seconds(self) -> float:
        """Calculate elapsed time since task started."""
        if not self.started_at:
            return 0.0
        end = self.completed_at or datetime.now(timezone.utc)
        return (end - self.started_at).total_seconds()

    def is_terminal(self) -> bool:
        """Check if task is in a terminal state."""
        return self.state in {TaskState.COMPLETED, TaskState.FAILED, TaskState.TIMEOUT}

    def should_retry(self) -> bool:
        """Check if task should be retried."""
        return self.state == TaskState.RETRY


# ---------------------------------------------------------------------------
# Retry Policy
# ---------------------------------------------------------------------------


class RetryPolicy:
    """Implements exponential backoff retry logic."""

    def __init__(self, max_retries: int = 2, base_delay: float = 1.0) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay

    def should_retry(self, task: Task) -> bool:
        """Determine if a task should be retried."""
        if task.retry_count >= self.max_retries:
            return False
        if task.failure_type == FailureType.LOGIC:
            return False
        if task.failure_type == FailureType.TRANSIENT:
            return True
        return False

    def get_delay(self, retry_count: int) -> float:
        """Calculate exponential backoff delay: 1s, 2s, 4s."""
        return self.base_delay * (2**retry_count)

    def wait_before_retry(self, task: Task) -> None:
        """Sleep for the appropriate backoff duration."""
        delay = self.get_delay(task.retry_count - 1)  # -1 because count already incremented
        time.sleep(delay)


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------


@dataclass
class CircuitBreakerStats:
    """Tracks success/failure rates per agent type."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0 to 1.0)."""
        if self.total == 0:
            return 0.0
        return self.succeeded / self.total

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate (0.0 to 1.0)."""
        return 1.0 - self.success_rate


class CircuitBreaker:
    """Monitors agent failure rates and enforces thresholds."""

    def __init__(self, min_success_rate: float = 0.5) -> None:
        """
        Args:
            min_success_rate: Minimum success rate (0.0-1.0) to proceed.
                             Default 0.5 means ≥50% must succeed.
        """
        self.min_success_rate = min_success_rate
        self.stats: Dict[str, CircuitBreakerStats] = {}

    def record_success(self, agent_type: str) -> None:
        """Record a successful task completion."""
        if agent_type not in self.stats:
            self.stats[agent_type] = CircuitBreakerStats()
        self.stats[agent_type].total += 1
        self.stats[agent_type].succeeded += 1

    def record_failure(self, agent_type: str) -> None:
        """Record a failed task."""
        if agent_type not in self.stats:
            self.stats[agent_type] = CircuitBreakerStats()
        self.stats[agent_type].total += 1
        self.stats[agent_type].failed += 1

    def check_threshold(self, agent_type: str) -> bool:
        """Check if agent type meets minimum success rate.

        Returns:
            True if success rate >= threshold, False otherwise.
        """
        if agent_type not in self.stats:
            return True  # No data yet, allow to proceed
        return self.stats[agent_type].success_rate >= self.min_success_rate

    def should_proceed(self, agent_type: str) -> tuple[bool, str]:
        """Determine if phase should proceed based on success rate.

        Returns:
            (should_proceed, error_message)
        """
        if self.check_threshold(agent_type):
            return True, ""

        stats = self.stats[agent_type]
        error = (
            f"Circuit breaker triggered for {agent_type}: "
            f"{stats.succeeded}/{stats.total} succeeded "
            f"({stats.success_rate:.1%} < {self.min_success_rate:.1%} threshold)"
        )
        return False, error

    def get_stats(self, agent_type: str) -> Optional[CircuitBreakerStats]:
        """Get statistics for an agent type."""
        return self.stats.get(agent_type)

    def reset(self, agent_type: Optional[str] = None) -> None:
        """Reset statistics for one or all agent types."""
        if agent_type:
            self.stats.pop(agent_type, None)
        else:
            self.stats.clear()


# ---------------------------------------------------------------------------
# Timeout Hierarchy
# ---------------------------------------------------------------------------


class TimeoutEnforcer:
    """Enforces timeout limits at task, phase, and research levels."""

    # Default timeout values (seconds)
    TASK_TIMEOUT = 300  # 5 minutes
    PHASE_TIMEOUT = 900  # 15 minutes
    RESEARCH_TIMEOUT = 3600  # 60 minutes

    def __init__(
        self,
        task_timeout: int = TASK_TIMEOUT,
        phase_timeout: int = PHASE_TIMEOUT,
        research_timeout: int = RESEARCH_TIMEOUT,
    ) -> None:
        self.task_timeout = task_timeout
        self.phase_timeout = phase_timeout
        self.research_timeout = research_timeout

    def check_task_timeout(self, task: Task) -> bool:
        """Check if task has exceeded its timeout.

        Returns:
            True if timed out, False otherwise.
        """
        if task.state != TaskState.RUNNING:
            return False
        return task.elapsed_seconds() > task.timeout_seconds

    def check_phase_timeout(self, phase_start: datetime) -> bool:
        """Check if phase has exceeded timeout.

        Args:
            phase_start: When the phase started.

        Returns:
            True if timed out, False otherwise.
        """
        elapsed = (datetime.now(timezone.utc) - phase_start).total_seconds()
        return elapsed > self.phase_timeout

    def check_research_timeout(self, research_start: datetime) -> bool:
        """Check if entire research session has exceeded timeout.

        Args:
            research_start: When research started.

        Returns:
            True if timed out, False otherwise.
        """
        elapsed = (datetime.now(timezone.utc) - research_start).total_seconds()
        return elapsed > self.research_timeout

    def enforce_task_timeout(self, task: Task) -> None:
        """Kill task if it has exceeded timeout."""
        if self.check_task_timeout(task):
            task.fail(
                f"Task exceeded {task.timeout_seconds}s timeout",
                FailureType.TIMEOUT,
            )


# ---------------------------------------------------------------------------
# Health Checks
# ---------------------------------------------------------------------------


@dataclass
class HealthMetrics:
    """Tracks agent health metrics."""

    agent_type: str
    spawned: int = 0
    completed: int = 0
    hanging: int = 0
    memory_exceeded: int = 0
    last_spawn_time: Optional[datetime] = None
    last_completion_time: Optional[datetime] = None

    def spawn_rate_per_minute(self) -> float:
        """Calculate agent spawn rate (agents/minute)."""
        if not self.last_spawn_time:
            return 0.0
        elapsed = (datetime.now(timezone.utc) - self.last_spawn_time).total_seconds()
        if elapsed == 0:
            return 0.0
        return (self.spawned / elapsed) * 60


class HealthChecker:
    """Monitors agent health and kills unhealthy agents."""

    MAX_MEMORY_MB = 2048  # 2GB
    MIN_SPAWN_RATE = 1.0  # 1 agent/minute
    HANG_TIMEOUT = 300  # 5 minutes without progress

    def __init__(
        self,
        max_memory_mb: float = MAX_MEMORY_MB,
        min_spawn_rate: float = MIN_SPAWN_RATE,
        hang_timeout: int = HANG_TIMEOUT,
    ) -> None:
        self.max_memory_mb = max_memory_mb
        self.min_spawn_rate = min_spawn_rate
        self.hang_timeout = hang_timeout
        self.metrics: Dict[str, HealthMetrics] = {}

    def record_spawn(self, agent_type: str) -> None:
        """Record agent spawn event."""
        if agent_type not in self.metrics:
            self.metrics[agent_type] = HealthMetrics(agent_type=agent_type)
        self.metrics[agent_type].spawned += 1
        self.metrics[agent_type].last_spawn_time = datetime.now(timezone.utc)

    def record_completion(self, agent_type: str) -> None:
        """Record agent completion event."""
        if agent_type not in self.metrics:
            self.metrics[agent_type] = HealthMetrics(agent_type=agent_type)
        self.metrics[agent_type].completed += 1
        self.metrics[agent_type].last_completion_time = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Task Graph for Parallel Execution
# ---------------------------------------------------------------------------


@dataclass
class BatchedResult:
    """Result of batched parallel task execution."""

    completed: List[Task] = field(default_factory=list)
    failed: List[Task] = field(default_factory=list)
    total_time: float = 0.0


class TaskGraph:
    """
    Task graph for parallel execution of independent tasks.

    Supports:
    - Adding parallel tasks
    - Executing tasks concurrently with max_concurrent limit
    - Batching results for serialization
    """

    def __init__(self) -> None:
        """Initialize task graph."""
        self.tasks: List[Task] = []

    def add_parallel_tasks(self, tasks: List[Task]) -> None:
        """
        Add tasks that can be executed in parallel.

        Args:
            tasks: List of tasks to add
        """
        self.tasks.extend(tasks)

    async def execute_parallel(
        self, tasks: List[Task], max_concurrent: int = 10
    ) -> List[Any]:
        """
        Execute tasks in parallel with concurrency limit.

        Args:
            tasks: Tasks to execute
            max_concurrent: Maximum concurrent tasks

        Returns:
            List of results (one per task)
        """
        import asyncio

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_with_semaphore(task: Task) -> Any:
            async with semaphore:
                # Simulate task execution (in real implementation, call agent)
                await asyncio.sleep(0.1)
                return f"result_{task.id}"

        # Execute all tasks concurrently
        results = await asyncio.gather(
            *[execute_with_semaphore(task) for task in tasks],
            return_exceptions=True,
        )

        return results

    def batch_results(self, results: List[Any]) -> BatchedResult:
        """
        Batch results for serialization to shared memory.

        Args:
            results: List of task results

        Returns:
            Batched result with completed/failed tasks
        """
        completed = []
        failed = []

        for i, result in enumerate(results):
            if i < len(self.tasks):
                task = self.tasks[i]
                if isinstance(result, Exception):
                    task.fail(str(result), FailureType.UNKNOWN)
                    failed.append(task)
                else:
                    task.complete()
                    completed.append(task)

        return BatchedResult(
            completed=completed,
            failed=failed,
            total_time=sum(t.elapsed_seconds() for t in completed + failed),
        )


# ---------------------------------------------------------------------------
# Coordination Manager
# ---------------------------------------------------------------------------


class CoordinationManager:
    """Unified coordination manager combining all primitives."""

    def __init__(
        self,
        retry_policy: Optional[RetryPolicy] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        timeout_enforcer: Optional[TimeoutEnforcer] = None,
        health_checker: Optional[HealthChecker] = None,
    ) -> None:
        self.retry_policy = retry_policy or RetryPolicy()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.timeout_enforcer = timeout_enforcer or TimeoutEnforcer()
        self.health_checker = health_checker or HealthChecker()
        self.tasks: Dict[str, Task] = {}

    def create_task(
        self,
        agent_type: str = "generic",
        timeout_seconds: int = 300,
        max_retries: int = 2,
    ) -> Task:
        """Create and register a new task."""
        task = Task(
            agent_type=agent_type,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        self.tasks[task.id] = task
        self.health_checker.record_spawn(agent_type)
        return task

    def start_task(self, task: Task) -> None:
        """Start a task and begin monitoring."""
        task.start()

    def complete_task(self, task: Task) -> None:
        """Mark task as completed and update metrics."""
        task.complete()
        self.circuit_breaker.record_success(task.agent_type)
        self.health_checker.record_completion(task.agent_type)

    def fail_task(
        self, task: Task, error: str, failure_type: FailureType = FailureType.UNKNOWN
    ) -> None:
        """Mark task as failed and update metrics."""
        task.fail(error, failure_type)
        if task.state == TaskState.FAILED or task.state == TaskState.TIMEOUT:
            self.circuit_breaker.record_failure(task.agent_type)

    def check_and_enforce(self, task: Task) -> bool:
        """Run all health checks and enforce policies.

        Returns:
            True if task is healthy, False if killed.
        """
        # Check timeout
        self.timeout_enforcer.enforce_task_timeout(task)
        if task.state == TaskState.TIMEOUT:
            self.circuit_breaker.record_failure(task.agent_type)
            return False

        # Check health
        if self.health_checker.kill_if_unhealthy(task):
            self.circuit_breaker.record_failure(task.agent_type)
            return False

        return True

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by ID."""
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[Task]:
        """Get all registered tasks."""
        return list(self.tasks.values())

    def reset(self) -> None:
        """Reset all coordination state."""
        self.tasks.clear()
        self.circuit_breaker.reset()
        self.health_checker.reset()
