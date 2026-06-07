"""
Tests for core task and result types.
"""


import pytest

from lyra.core.task import (
    AgentPerformance,
    ExecutionMetrics,
    Result,
    Task,
    TaskPriority,
    TaskStatus,
    TaskType,
)


class TestTask:
    """Test Task class."""

    def test_task_creation(self):
        """Test basic task creation."""
        task = Task(
            type=TaskType.CODE_GENERATION,
            description="Generate a function",
            priority=TaskPriority.HIGH,
        )

        assert task.task_id is not None
        assert task.type == TaskType.CODE_GENERATION
        assert task.description == "Generate a function"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING

    def test_task_with_params(self):
        """Test task with parameters."""
        params = {"language": "python", "function_name": "calculate"}
        task = Task(
            type=TaskType.CODE_GENERATION,
            description="Generate function",
            params=params,
        )

        assert task.params == params
        assert task.params["language"] == "python"

    def test_task_assignment(self):
        """Test task assignment to agent."""
        task = Task(type=TaskType.GENERIC, description="Test task")

        assert task.status == TaskStatus.PENDING
        assert task.assigned_to is None

        task.assign_to("agent_1")

        assert task.status == TaskStatus.ASSIGNED
        assert task.assigned_to == "agent_1"

    def test_task_lifecycle(self):
        """Test task status transitions."""
        task = Task(type=TaskType.GENERIC, description="Test task")

        # Pending -> Assigned
        task.assign_to("agent_1")
        assert task.status == TaskStatus.ASSIGNED

        # Assigned -> In Progress
        task.start()
        assert task.status == TaskStatus.IN_PROGRESS

        # In Progress -> Completed
        task.complete()
        assert task.status == TaskStatus.COMPLETED

    def test_task_failure(self):
        """Test task failure."""
        task = Task(type=TaskType.GENERIC, description="Test task")
        task.start()
        task.fail()

        assert task.status == TaskStatus.FAILED

    def test_task_cancellation(self):
        """Test task cancellation."""
        task = Task(type=TaskType.GENERIC, description="Test task")
        task.cancel()

        assert task.status == TaskStatus.CANCELLED

    def test_task_validation(self):
        """Test task validation."""
        with pytest.raises(ValueError):
            Task(type=TaskType.GENERIC)  # No description or params


class TestResult:
    """Test Result class."""

    def test_successful_result(self):
        """Test successful result creation."""
        result = Result(
            task_id="task_123",
            success=True,
            data={"output": "success"},
            agent_id="agent_1",
        )

        assert result.task_id == "task_123"
        assert result.success is True
        assert result.data == {"output": "success"}
        assert result.agent_id == "agent_1"
        assert result.error is None

    def test_failed_result(self):
        """Test failed result creation."""
        result = Result(
            task_id="task_123",
            success=False,
            error="Something went wrong",
            agent_id="agent_1",
        )

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.data is None

    def test_result_validation(self):
        """Test result validation."""
        with pytest.raises(ValueError):
            Result(
                task_id="task_123",
                success=False,  # Failed but no error message
                agent_id="agent_1",
            )

    def test_result_with_metrics(self):
        """Test result with execution metrics."""
        result = Result(
            task_id="task_123",
            success=True,
            data="output",
            agent_id="agent_1",
            duration=1.5,
            cost=0.05,
        )

        assert result.duration == 1.5
        assert result.cost == 0.05


class TestExecutionMetrics:
    """Test ExecutionMetrics class."""

    def test_metrics_creation(self):
        """Test metrics creation."""
        metrics = ExecutionMetrics(
            agent_id="agent_1",
            task_type=TaskType.CODE_GENERATION,
            success=True,
            duration=2.5,
            cost=0.10,
        )

        assert metrics.agent_id == "agent_1"
        assert metrics.task_type == TaskType.CODE_GENERATION
        assert metrics.success is True
        assert metrics.duration == 2.5
        assert metrics.cost == 0.10


class TestAgentPerformance:
    """Test AgentPerformance class."""

    def test_performance_creation(self):
        """Test performance stats creation."""
        perf = AgentPerformance(
            agent_id="agent_1",
            total_tasks=100,
            success_rate=0.95,
            avg_duration=2.5,
            avg_cost=0.08,
        )

        assert perf.agent_id == "agent_1"
        assert perf.total_tasks == 100
        assert perf.success_rate == 0.95
        assert perf.avg_duration == 2.5
        assert perf.avg_cost == 0.08
