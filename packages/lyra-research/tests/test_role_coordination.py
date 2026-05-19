"""Tests for role coordination and handoff protocols.

Tests:
- Role state machine (5 tests)
- Handoff protocol (8 tests)
- Role coordinator (10 tests)
- Parallel execution (4 tests)
- Progress tracking (3 tests)
"""
import asyncio
from datetime import datetime, timezone
from typing import Any

import pytest

from lyra_core.context.layered_context import LayeredContextManager
from lyra_research.coordination.role_state_machine import (
    RoleState,
    RoleStateMachine,
    RoleTransition,
)
from lyra_research.coordination.handoff_protocol import (
    HandoffData,
    HandoffProtocol,
)
from lyra_research.coordination.role_coordinator import RoleCoordinator
from lyra_research.coordination.parallel_executor import ParallelExecutor
from lyra_research.coordination.progress_tracker import ProgressTracker
from lyra_research.roles.role_base import Role, RoleResult, RoleStatus


# Mock Role for testing
class MockRole(Role):
    """Mock role for testing."""

    def __init__(self, name: str, should_fail: bool = False):
        super().__init__(name, "mock-model", LayeredContextManager())
        self.should_fail = should_fail
        self.execution_count = 0

    async def execute(self, input_data: Any) -> RoleResult:
        """Execute mock role."""
        self.execution_count += 1
        await asyncio.sleep(0.01)  # Simulate work

        if self.should_fail:
            raise RuntimeError(f"Mock {self.name} failed")

        return RoleResult(
            role_name=self.name,
            status=RoleStatus.SUCCESS,
            data=f"output_{self.name}_{input_data}",
        )

    def validate_input(self, input_data: Any) -> bool:
        """Validate input."""
        return input_data is not None

    def validate_output(self, output: Any) -> bool:
        """Validate output."""
        return output is not None and isinstance(output, str)


# ============================================================================
# Role State Machine Tests (5 tests)
# ============================================================================


def test_role_state_machine_initial_state():
    """Test initial state is PENDING."""
    sm = RoleStateMachine()
    assert sm.get_state("test_role") == RoleState.PENDING


def test_role_state_machine_transition_pending_to_running():
    """Test transition from PENDING to RUNNING."""
    sm = RoleStateMachine()
    success, error = sm.transition("test_role", "start")

    assert success is True
    assert error is None
    assert sm.get_state("test_role") == RoleState.RUNNING


def test_role_state_machine_transition_running_to_completed():
    """Test transition from RUNNING to COMPLETED."""
    sm = RoleStateMachine()
    sm.set_state("test_role", RoleState.RUNNING)

    success, error = sm.transition("test_role", "complete")

    assert success is True
    assert error is None
    assert sm.get_state("test_role") == RoleState.COMPLETED


def test_role_state_machine_invalid_transition():
    """Test invalid transition returns error."""
    sm = RoleStateMachine()
    # Try to complete from PENDING (should fail)
    success, error = sm.transition("test_role", "complete")

    assert success is False
    assert error is not None
    assert "No transition" in error


def test_role_state_machine_get_available_events():
    """Test getting available events for current state."""
    sm = RoleStateMachine()

    # PENDING state should have "start" event
    events = sm.get_available_events("test_role")
    assert "start" in events

    # RUNNING state should have multiple events
    sm.set_state("test_role", RoleState.RUNNING)
    events = sm.get_available_events("test_role")
    assert "complete" in events
    assert "fail" in events
    assert "wait" in events


# ============================================================================
# Handoff Protocol Tests (8 tests)
# ============================================================================


def test_handoff_data_creation():
    """Test creating handoff data."""
    handoff = HandoffData(
        role_from="RoleA",
        role_to="RoleB",
        data={"key": "value"},
        metadata={"meta": "data"},
    )

    assert handoff.role_from == "RoleA"
    assert handoff.role_to == "RoleB"
    assert handoff.data == {"key": "value"}
    assert handoff.metadata == {"meta": "data"}
    assert isinstance(handoff.timestamp, datetime)


def test_handoff_data_validation_success():
    """Test handoff data validation succeeds with valid data."""
    handoff = HandoffData(
        role_from="RoleA",
        role_to="RoleB",
        data={"key": "value"},
    )

    assert handoff.validate() is True
    assert handoff.validated is True
    assert len(handoff.validation_errors) == 0


def test_handoff_data_validation_missing_fields():
    """Test handoff data validation fails with missing fields."""
    handoff = HandoffData(
        role_from="",
        role_to="RoleB",
        data=None,
    )

    assert handoff.validate() is False
    assert handoff.validated is False
    assert len(handoff.validation_errors) > 0


def test_handoff_data_validation_empty_data():
    """Test handoff data validation fails with empty data."""
    handoff = HandoffData(
        role_from="RoleA",
        role_to="RoleB",
        data=[],  # Empty list
    )

    assert handoff.validate() is False
    assert "cannot be empty" in handoff.validation_errors[0]


def test_handoff_protocol_prepare():
    """Test preparing handoff."""
    protocol = HandoffProtocol()
    role_a = MockRole("RoleA")
    role_b = MockRole("RoleB")

    handoff = protocol.prepare_handoff(role_a, role_b, "test_data")

    assert handoff.role_from == "RoleA"
    assert handoff.role_to == "RoleB"
    assert handoff.data == "test_data"
    assert handoff.get_metadata("from_model") == "mock-model"
    assert handoff.get_metadata("to_model") == "mock-model"


def test_handoff_protocol_execute_success():
    """Test executing successful handoff."""
    protocol = HandoffProtocol()
    role_a = MockRole("RoleA")
    role_b = MockRole("RoleB")

    handoff = protocol.prepare_handoff(role_a, role_b, "test_data")
    success, error = protocol.execute_handoff(handoff, role_a, role_b)

    assert success is True
    assert error is None
    assert len(protocol.get_handoff_history()) == 1


def test_handoff_protocol_execute_validation_failure():
    """Test executing handoff with validation failure."""
    protocol = HandoffProtocol()
    role_a = MockRole("RoleA")
    role_b = MockRole("RoleB")

    # Create handoff with invalid data (None)
    handoff = HandoffData(role_from="RoleA", role_to="RoleB", data=None)
    success, error = protocol.execute_handoff(handoff, role_a, role_b)

    assert success is False
    assert error is not None
    assert len(protocol.get_failed_handoffs()) == 1


def test_handoff_protocol_get_chain():
    """Test getting handoff chain."""
    protocol = HandoffProtocol()
    role_a = MockRole("RoleA")
    role_b = MockRole("RoleB")
    role_c = MockRole("RoleC")

    # Execute handoffs
    handoff1 = protocol.prepare_handoff(role_a, role_b, "data1")
    protocol.execute_handoff(handoff1, role_a, role_b)

    handoff2 = protocol.prepare_handoff(role_b, role_c, "data2")
    protocol.execute_handoff(handoff2, role_b, role_c)

    chain = protocol.get_handoff_chain()
    assert chain == ["RoleA", "RoleB", "RoleC"]


# ============================================================================
# Parallel Executor Tests (4 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_parallel_executor_execute_parallel():
    """Test executing multiple roles in parallel."""
    executor = ParallelExecutor()
    roles = [MockRole(f"Role{i}") for i in range(3)]

    results = await executor.execute_parallel_roles(roles, "input")

    assert len(results) == 3
    for i, result in enumerate(results):
        assert result.role_name == f"Role{i}"
        assert result.status == RoleStatus.SUCCESS


@pytest.mark.asyncio
async def test_parallel_executor_with_timeout_success():
    """Test executing role with timeout (success)."""
    executor = ParallelExecutor()
    role = MockRole("TestRole")

    result = await executor.execute_with_timeout(role, "input", timeout_seconds=5)

    assert result.status == RoleStatus.SUCCESS
    assert result.role_name == "TestRole"


@pytest.mark.asyncio
async def test_parallel_executor_with_timeout_failure():
    """Test executing role with timeout (timeout)."""
    executor = ParallelExecutor()

    # Create role that takes too long
    class SlowRole(MockRole):
        async def execute(self, input_data: Any) -> RoleResult:
            await asyncio.sleep(10)  # Takes 10 seconds
            return await super().execute(input_data)

    role = SlowRole("SlowRole")
    result = await executor.execute_with_timeout(role, "input", timeout_seconds=1)

    assert result.status == RoleStatus.FAILED
    assert "timed out" in result.error.lower()


@pytest.mark.asyncio
async def test_parallel_executor_with_retries():
    """Test executing role with retries."""
    executor = ParallelExecutor()

    # Create role that fails first 2 times, then succeeds
    class FlakyRole(MockRole):
        def __init__(self, name: str):
            super().__init__(name)
            self.attempt = 0

        async def execute(self, input_data: Any) -> RoleResult:
            self.attempt += 1
            if self.attempt < 3:
                raise RuntimeError("Flaky failure")
            return await super().execute(input_data)

    role = FlakyRole("FlakyRole")
    result = await executor.execute_with_retries(
        role, "input", max_retries=3, retry_delay_seconds=0.01
    )

    assert result.status == RoleStatus.SUCCESS
    assert role.attempt == 3


# ============================================================================
# Progress Tracker Tests (3 tests)
# ============================================================================


def test_progress_tracker_initialization():
    """Test progress tracker initialization."""
    tracker = ProgressTracker(["Role1", "Role2", "Role3"])

    assert tracker.get_pipeline_progress() == 0.0
    assert tracker.get_role_progress("Role1") == 0.0


def test_progress_tracker_role_progress():
    """Test tracking role progress."""
    tracker = ProgressTracker(["Role1", "Role2"])

    tracker.start_role("Role1")
    tracker.update_role_progress("Role1", 0.5)

    assert tracker.get_role_progress("Role1") == 0.5
    assert tracker.get_pipeline_progress() == 0.25  # (0.5 + 0.0) / 2


def test_progress_tracker_complete_role():
    """Test completing role."""
    tracker = ProgressTracker(["Role1"])

    tracker.start_role("Role1")
    tracker.complete_role("Role1")

    status = tracker.get_role_status("Role1")
    assert status["state"] == RoleState.COMPLETED.value
    assert status["progress"] == 1.0
    assert status["duration_seconds"] > 0


# ============================================================================
# Role Coordinator Tests (10 tests)
# ============================================================================


@pytest.mark.asyncio
async def test_role_coordinator_initialization():
    """Test role coordinator initialization."""
    context_manager = LayeredContextManager()
    coordinator = RoleCoordinator(context_manager)

    assert coordinator.discovery is not None
    assert coordinator.analysis is not None
    assert coordinator.synthesis is not None
    assert coordinator.review is not None
    assert coordinator.curator is not None


@pytest.mark.asyncio
async def test_role_coordinator_get_role_state():
    """Test getting role state."""
    context_manager = LayeredContextManager()
    coordinator = RoleCoordinator(context_manager)

    state = coordinator.get_role_state("Discovery")
    assert state == RoleState.PENDING


@pytest.mark.asyncio
async def test_role_coordinator_get_role_progress():
    """Test getting role progress."""
    context_manager = LayeredContextManager()
    coordinator = RoleCoordinator(context_manager)

    progress = coordinator.get_role_progress("Discovery")
    assert progress == 0.0


@pytest.mark.asyncio
async def test_role_coordinator_get_pipeline_progress():
    """Test getting pipeline progress."""
    context_manager = LayeredContextManager()
    coordinator = RoleCoordinator(context_manager)

    progress = coordinator.get_pipeline_progress()
    assert progress == 0.0


@pytest.mark.asyncio
async def test_role_coordinator_get_coordination_stats():
    """Test getting coordination statistics."""
    context_manager = LayeredContextManager()
    coordinator = RoleCoordinator(context_manager)

    stats = coordinator.get_coordination_stats()

    assert "handoff_stats" in stats
    assert "progress_stats" in stats
    assert "role_states" in stats
    assert len(stats["role_states"]) == 5


@pytest.mark.asyncio
async def test_role_coordinator_reset():
    """Test resetting coordinator."""
    context_manager = LayeredContextManager()
    coordinator = RoleCoordinator(context_manager)

    # Set some state
    coordinator.state_machine.set_state("Discovery", RoleState.RUNNING)
    coordinator.progress_tracker.start_role("Discovery")

    # Reset
    coordinator.reset()

    # Verify reset
    assert coordinator.get_role_state("Discovery") == RoleState.PENDING
    assert coordinator.get_role_progress("Discovery") == 0.0


@pytest.mark.asyncio
async def test_role_coordinator_state_transitions():
    """Test role state transitions during execution."""
    context_manager = LayeredContextManager()
    coordinator = RoleCoordinator(context_manager)

    # Initial state
    assert coordinator.get_role_state("Discovery") == RoleState.PENDING

    # After starting (would need to mock execution)
    coordinator.state_machine.transition("Discovery", "start")
    assert coordinator.get_role_state("Discovery") == RoleState.RUNNING

    # After completing
    coordinator.state_machine.transition("Discovery", "complete")
    assert coordinator.get_role_state("Discovery") == RoleState.COMPLETED


@pytest.mark.asyncio
async def test_role_coordinator_progress_tracking():
    """Test progress tracking during execution."""
    context_manager = LayeredContextManager()
    coordinator = RoleCoordinator(context_manager)

    # Start role
    coordinator.progress_tracker.start_role("Discovery")
    assert coordinator.get_role_progress("Discovery") == 0.0

    # Update progress
    coordinator.progress_tracker.update_role_progress("Discovery", 0.5)
    assert coordinator.get_role_progress("Discovery") == 0.5

    # Complete role
    coordinator.progress_tracker.complete_role("Discovery")
    assert coordinator.get_role_progress("Discovery") == 1.0


@pytest.mark.asyncio
async def test_role_coordinator_handoff_validation():
    """Test handoff validation between roles."""
    context_manager = LayeredContextManager()
    coordinator = RoleCoordinator(context_manager)

    # Use mock roles for handoff validation test
    role_a = MockRole("RoleA")
    role_b = MockRole("RoleB")

    # Prepare handoff
    handoff = coordinator.handoff_protocol.prepare_handoff(
        role_a,
        role_b,
        "test_data",
    )

    # Validate handoff
    is_valid, errors = coordinator.handoff_protocol.validate_handoff(
        handoff, role_a, role_b
    )

    # Should be valid (mock roles accept any non-None data)
    assert is_valid is True
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_role_coordinator_coordination_stats():
    """Test coordination statistics collection."""
    context_manager = LayeredContextManager()
    coordinator = RoleCoordinator(context_manager)

    # Execute some operations
    coordinator.state_machine.transition("Discovery", "start")
    coordinator.progress_tracker.start_role("Discovery")

    stats = coordinator.get_coordination_stats()

    assert stats["handoff_stats"]["total_handoffs"] == 0
    assert stats["progress_stats"]["total_roles"] == 5
    assert stats["role_states"]["Discovery"] == RoleState.RUNNING.value
