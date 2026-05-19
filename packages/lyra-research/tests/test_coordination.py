"""Tests for agent coordination primitives."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from lyra_research.coordination import (
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


# ---------------------------------------------------------------------------
# Task State Machine Tests
# ---------------------------------------------------------------------------


def test_task_initial_state() -> None:
    """New task starts in PENDING state."""
    task = Task()
    assert task.state == TaskState.PENDING
    assert task.retry_count == 0
    assert task.started_at is None
    assert task.completed_at is None


def test_task_start_transition() -> None:
    """Task transitions from PENDING to RUNNING."""
    task = Task()
    task.start()
    assert task.state == TaskState.RUNNING
    assert task.started_at is not None


def test_task_start_from_retry() -> None:
    """Task can transition from RETRY to RUNNING."""
    task = Task(state=TaskState.RETRY)
    task.start()
    assert task.state == TaskState.RUNNING


def test_task_start_invalid_state() -> None:
    """Cannot start task from COMPLETED state."""
    task = Task(state=TaskState.COMPLETED)
    with pytest.raises(ValueError, match="Cannot start task"):
        task.start()


def test_task_complete_transition() -> None:
    """Task transitions from RUNNING to COMPLETED."""
    task = Task()
    task.start()
    task.complete()
    assert task.state == TaskState.COMPLETED
    assert task.completed_at is not None


def test_task_complete_invalid_state() -> None:
    """Cannot complete task from PENDING state."""
    task = Task()
    with pytest.raises(ValueError, match="Cannot complete task"):
        task.complete()


def test_task_fail_transient_with_retries() -> None:
    """Transient failure with retries available → RETRY state."""
    task = Task(max_retries=2)
    task.start()
    task.fail("Network error", FailureType.TRANSIENT)
    assert task.state == TaskState.RETRY
    assert task.retry_count == 1
    assert task.error == "Network error"


def test_task_fail_transient_no_retries() -> None:
    """Transient failure with no retries left → FAILED state."""
    task = Task(max_retries=2, retry_count=2)
    task.start()
    task.fail("Network error", FailureType.TRANSIENT)
    assert task.state == TaskState.FAILED
    assert task.retry_count == 2  # Doesn't increment when max reached


def test_task_fail_logic_error() -> None:
    """Logic error → FAILED state (no retry)."""
    task = Task(max_retries=2)
    task.start()
    task.fail("Invalid input", FailureType.LOGIC)
    assert task.state == TaskState.FAILED
    assert task.retry_count == 0


def test_task_fail_timeout() -> None:
    """Timeout failure → TIMEOUT state."""
    task = Task()
    task.start()
    task.fail("Exceeded 5 minutes", FailureType.TIMEOUT)
    assert task.state == TaskState.TIMEOUT


def test_task_elapsed_seconds() -> None:
    """Elapsed time calculation works correctly."""
    task = Task()
    task.start()
    time.sleep(0.1)
    elapsed = task.elapsed_seconds()
    assert elapsed >= 0.1
    assert elapsed < 1.0


def test_task_elapsed_seconds_not_started() -> None:
    """Elapsed time is 0 for unstarted task."""
    task = Task()
    assert task.elapsed_seconds() == 0.0


def test_task_is_terminal_completed() -> None:
    """COMPLETED is a terminal state."""
    task = Task(state=TaskState.COMPLETED)
    assert task.is_terminal()


def test_task_is_terminal_failed() -> None:
    """FAILED is a terminal state."""
    task = Task(state=TaskState.FAILED)
    assert task.is_terminal()


def test_task_is_terminal_timeout() -> None:
    """TIMEOUT is a terminal state."""
    task = Task(state=TaskState.TIMEOUT)
    assert task.is_terminal()


def test_task_is_terminal_running() -> None:
    """RUNNING is not a terminal state."""
    task = Task(state=TaskState.RUNNING)
    assert not task.is_terminal()


def test_task_should_retry() -> None:
    """Task in RETRY state should retry."""
    task = Task(state=TaskState.RETRY)
    assert task.should_retry()


def test_task_should_not_retry_failed() -> None:
    """Task in FAILED state should not retry."""
    task = Task(state=TaskState.FAILED)
    assert not task.should_retry()


# ---------------------------------------------------------------------------
# Retry Policy Tests
# ---------------------------------------------------------------------------


def test_retry_policy_should_retry_transient() -> None:
    """Transient failure with retries left → should retry."""
    policy = RetryPolicy(max_retries=2)
    task = Task(retry_count=1, failure_type=FailureType.TRANSIENT)
    assert policy.should_retry(task)


def test_retry_policy_should_not_retry_logic() -> None:
    """Logic error → should not retry."""
    policy = RetryPolicy(max_retries=2)
    task = Task(retry_count=0, failure_type=FailureType.LOGIC)
    assert not policy.should_retry(task)


def test_retry_policy_should_not_retry_max_reached() -> None:
    """Max retries reached → should not retry."""
    policy = RetryPolicy(max_retries=2)
    task = Task(retry_count=2, failure_type=FailureType.TRANSIENT)
    assert not policy.should_retry(task)


def test_retry_policy_get_delay_exponential() -> None:
    """Delay follows exponential backoff: 1s, 2s, 4s."""
    policy = RetryPolicy(base_delay=1.0)
    assert policy.get_delay(0) == 1.0
    assert policy.get_delay(1) == 2.0
    assert policy.get_delay(2) == 4.0


def test_retry_policy_wait_before_retry() -> None:
    """Wait actually sleeps for the correct duration."""
    policy = RetryPolicy(base_delay=0.1)
    task = Task(retry_count=1)  # First retry
    start = time.time()
    policy.wait_before_retry(task)
    elapsed = time.time() - start
    assert elapsed >= 0.1  # Should wait at least base_delay


# ---------------------------------------------------------------------------
# Circuit Breaker Tests
# ---------------------------------------------------------------------------


def test_circuit_breaker_stats_initial() -> None:
    """Initial stats are all zeros."""
    stats = CircuitBreakerStats()
    assert stats.total == 0
    assert stats.succeeded == 0
    assert stats.failed == 0
    assert stats.success_rate == 0.0
    assert stats.failure_rate == 1.0


def test_circuit_breaker_stats_success_rate() -> None:
    """Success rate calculation is correct."""
    stats = CircuitBreakerStats(total=10, succeeded=7, failed=3)
    assert stats.success_rate == 0.7
    assert abs(stats.failure_rate - 0.3) < 0.0001  # Float comparison tolerance


def test_circuit_breaker_record_success() -> None:
    """Recording success updates stats correctly."""
    breaker = CircuitBreaker()
    breaker.record_success("discovery")
    stats = breaker.get_stats("discovery")
    assert stats is not None
    assert stats.total == 1
    assert stats.succeeded == 1
    assert stats.failed == 0


def test_circuit_breaker_record_failure() -> None:
    """Recording failure updates stats correctly."""
    breaker = CircuitBreaker()
    breaker.record_failure("analysis")
    stats = breaker.get_stats("analysis")
    assert stats is not None
    assert stats.total == 1
    assert stats.succeeded == 0
    assert stats.failed == 1


def test_circuit_breaker_check_threshold_pass() -> None:
    """≥50% success rate passes threshold."""
    breaker = CircuitBreaker(min_success_rate=0.5)
    breaker.record_success("synthesis")
    breaker.record_success("synthesis")
    breaker.record_failure("synthesis")
    # 2/3 = 66.7% ≥ 50%
    assert breaker.check_threshold("synthesis")


def test_circuit_breaker_check_threshold_fail() -> None:
    """<50% success rate fails threshold."""
    breaker = CircuitBreaker(min_success_rate=0.5)
    breaker.record_success("synthesis")
    breaker.record_failure("synthesis")
    breaker.record_failure("synthesis")
    # 1/3 = 33.3% < 50%
    assert not breaker.check_threshold("synthesis")


def test_circuit_breaker_check_threshold_exact() -> None:
    """Exactly 50% success rate passes threshold."""
    breaker = CircuitBreaker(min_success_rate=0.5)
    breaker.record_success("discovery")
    breaker.record_failure("discovery")
    # 1/2 = 50% ≥ 50%
    assert breaker.check_threshold("discovery")


def test_circuit_breaker_check_threshold_no_data() -> None:
    """No data → passes threshold (allow to proceed)."""
    breaker = CircuitBreaker(min_success_rate=0.5)
    assert breaker.check_threshold("unknown")


def test_circuit_breaker_should_proceed_pass() -> None:
    """Should proceed when threshold met."""
    breaker = CircuitBreaker(min_success_rate=0.5)
    breaker.record_success("discovery")
    breaker.record_success("discovery")
    should_proceed, error = breaker.should_proceed("discovery")
    assert should_proceed
    assert error == ""


def test_circuit_breaker_should_proceed_fail() -> None:
    """Should not proceed when threshold not met."""
    breaker = CircuitBreaker(min_success_rate=0.5)
    breaker.record_failure("discovery")
    breaker.record_failure("discovery")
    should_proceed, error = breaker.should_proceed("discovery")
    assert not should_proceed
    assert "Circuit breaker triggered" in error
    assert "0/2" in error


def test_circuit_breaker_reset_specific() -> None:
    """Reset specific agent type clears its stats."""
    breaker = CircuitBreaker()
    breaker.record_success("discovery")
    breaker.record_success("analysis")
    breaker.reset("discovery")
    assert breaker.get_stats("discovery") is None
    assert breaker.get_stats("analysis") is not None


def test_circuit_breaker_reset_all() -> None:
    """Reset without argument clears all stats."""
    breaker = CircuitBreaker()
    breaker.record_success("discovery")
    breaker.record_success("analysis")
    breaker.reset()
    assert breaker.get_stats("discovery") is None
    assert breaker.get_stats("analysis") is None


# ---------------------------------------------------------------------------
# Timeout Enforcer Tests
# ---------------------------------------------------------------------------


def test_timeout_enforcer_defaults() -> None:
    """Default timeout values are correct."""
    enforcer = TimeoutEnforcer()
    assert enforcer.task_timeout == 300
    assert enforcer.phase_timeout == 900
    assert enforcer.research_timeout == 3600


def test_timeout_enforcer_check_task_timeout_not_exceeded() -> None:
    """Task within timeout → not timed out."""
    enforcer = TimeoutEnforcer(task_timeout=10)
    task = Task(timeout_seconds=10)
    task.start()
    assert not enforcer.check_task_timeout(task)


def test_timeout_enforcer_check_task_timeout_exceeded() -> None:
    """Task exceeding timeout → timed out."""
    enforcer = TimeoutEnforcer(task_timeout=1)
    task = Task(timeout_seconds=0.1)
    task.start()
    time.sleep(0.2)
    assert enforcer.check_task_timeout(task)


def test_timeout_enforcer_check_task_timeout_not_running() -> None:
    """Non-running task → not timed out."""
    enforcer = TimeoutEnforcer()
    task = Task(state=TaskState.PENDING)
    assert not enforcer.check_task_timeout(task)


def test_timeout_enforcer_check_phase_timeout_not_exceeded() -> None:
    """Phase within timeout → not timed out."""
    enforcer = TimeoutEnforcer(phase_timeout=10)
    phase_start = datetime.now(timezone.utc)
    assert not enforcer.check_phase_timeout(phase_start)


def test_timeout_enforcer_check_phase_timeout_exceeded() -> None:
    """Phase exceeding timeout → timed out."""
    enforcer = TimeoutEnforcer(phase_timeout=0.1)
    phase_start = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert enforcer.check_phase_timeout(phase_start)


def test_timeout_enforcer_check_research_timeout_not_exceeded() -> None:
    """Research within timeout → not timed out."""
    enforcer = TimeoutEnforcer(research_timeout=10)
    research_start = datetime.now(timezone.utc)
    assert not enforcer.check_research_timeout(research_start)


def test_timeout_enforcer_check_research_timeout_exceeded() -> None:
    """Research exceeding timeout → timed out."""
    enforcer = TimeoutEnforcer(research_timeout=0.1)
    research_start = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert enforcer.check_research_timeout(research_start)


def test_timeout_enforcer_enforce_task_timeout() -> None:
    """Enforce kills task that exceeded timeout."""
    enforcer = TimeoutEnforcer(task_timeout=0.1)
    task = Task(timeout_seconds=0.1)
    task.start()
    time.sleep(0.2)
    enforcer.enforce_task_timeout(task)
    assert task.state == TaskState.TIMEOUT
    assert "exceeded" in task.error.lower()


def test_timeout_enforcer_enforce_task_timeout_not_exceeded() -> None:
    """Enforce does nothing if timeout not exceeded."""
    enforcer = TimeoutEnforcer(task_timeout=10)
    task = Task(timeout_seconds=10)
    task.start()
    enforcer.enforce_task_timeout(task)
    assert task.state == TaskState.RUNNING


# ---------------------------------------------------------------------------
# Health Checker Tests
# ---------------------------------------------------------------------------


def test_health_metrics_initial() -> None:
    """Initial health metrics are zeros."""
    metrics = HealthMetrics(agent_type="discovery")
    assert metrics.spawned == 0
    assert metrics.completed == 0
    assert metrics.hanging == 0
    assert metrics.memory_exceeded == 0


def test_health_metrics_spawn_rate() -> None:
    """Spawn rate calculation is correct."""
    metrics = HealthMetrics(
        agent_type="discovery",
        spawned=10,
        last_spawn_time=datetime.now(timezone.utc) - timedelta(seconds=60),
    )
    rate = metrics.spawn_rate_per_minute()
    assert rate > 0


def test_health_checker_record_spawn() -> None:
    """Recording spawn updates metrics."""
    checker = HealthChecker()
    checker.record_spawn("discovery")
    metrics = checker.get_metrics("discovery")
    assert metrics is not None
    assert metrics.spawned == 1
    assert metrics.last_spawn_time is not None


def test_health_checker_record_completion() -> None:
    """Recording completion updates metrics."""
    checker = HealthChecker()
    checker.record_completion("analysis")
    metrics = checker.get_metrics("analysis")
    assert metrics is not None
    assert metrics.completed == 1
    assert metrics.last_completion_time is not None


def test_health_checker_check_memory_not_exceeded() -> None:
    """Task within memory limit → not exceeded."""
    checker = HealthChecker(max_memory_mb=2048)
    task = Task(memory_mb=1024)
    assert not checker.check_memory(task)


def test_health_checker_check_memory_exceeded() -> None:
    """Task exceeding memory limit → exceeded."""
    checker = HealthChecker(max_memory_mb=2048)
    task = Task(memory_mb=3000)
    assert checker.check_memory(task)


def test_health_checker_check_hanging_not_hanging() -> None:
    """Task within hang timeout → not hanging."""
    checker = HealthChecker(hang_timeout=10)
    task = Task()
    task.start()
    assert not checker.check_hanging(task)


def test_health_checker_check_hanging_exceeded() -> None:
    """Task exceeding hang timeout → hanging."""
    checker = HealthChecker(hang_timeout=0.1)
    task = Task()
    task.start()
    time.sleep(0.2)
    assert checker.check_hanging(task)


def test_health_checker_check_hanging_not_running() -> None:
    """Non-running task → not hanging."""
    checker = HealthChecker()
    task = Task(state=TaskState.PENDING)
    assert not checker.check_hanging(task)


def test_health_checker_check_spawn_rate_healthy() -> None:
    """Spawn rate above threshold → healthy."""
    checker = HealthChecker(min_spawn_rate=1.0)
    checker.record_spawn("discovery")
    time.sleep(0.1)
    checker.record_spawn("discovery")
    assert checker.check_spawn_rate("discovery")


def test_health_checker_check_spawn_rate_no_data() -> None:
    """No data → healthy (allow to proceed)."""
    checker = HealthChecker()
    assert checker.check_spawn_rate("unknown")


def test_health_checker_kill_if_unhealthy_memory() -> None:
    """Kill task exceeding memory limit."""
    checker = HealthChecker(max_memory_mb=2048)
    task = Task(memory_mb=3000, agent_type="discovery")
    task.start()
    killed = checker.kill_if_unhealthy(task)
    assert killed
    assert task.state == TaskState.FAILED
    assert "memory" in task.error.lower()


def test_health_checker_kill_if_unhealthy_hanging() -> None:
    """Kill hanging task."""
    checker = HealthChecker(hang_timeout=0.1)
    task = Task(agent_type="analysis")
    task.start()
    time.sleep(0.2)
    killed = checker.kill_if_unhealthy(task)
    assert killed
    assert task.state == TaskState.FAILED  # Hanging uses LOGIC failure type
    assert "hanging" in task.error.lower()


def test_health_checker_kill_if_unhealthy_healthy() -> None:
    """Don't kill healthy task."""
    checker = HealthChecker()
    task = Task()
    task.start()
    killed = checker.kill_if_unhealthy(task)
    assert not killed
    assert task.state == TaskState.RUNNING


def test_health_checker_reset_specific() -> None:
    """Reset specific agent type clears its metrics."""
    checker = HealthChecker()
    checker.record_spawn("discovery")
    checker.record_spawn("analysis")
    checker.reset("discovery")
    assert checker.get_metrics("discovery") is None
    assert checker.get_metrics("analysis") is not None


def test_health_checker_reset_all() -> None:
    """Reset without argument clears all metrics."""
    checker = HealthChecker()
    checker.record_spawn("discovery")
    checker.record_spawn("analysis")
    checker.reset()
    assert checker.get_metrics("discovery") is None
    assert checker.get_metrics("analysis") is None


# ---------------------------------------------------------------------------
# Coordination Manager Tests
# ---------------------------------------------------------------------------


def test_coordination_manager_create_task() -> None:
    """Create task registers it and records spawn."""
    manager = CoordinationManager()
    task = manager.create_task(agent_type="discovery")
    assert task.id in manager.tasks
    metrics = manager.health_checker.get_metrics("discovery")
    assert metrics is not None
    assert metrics.spawned == 1


def test_coordination_manager_start_task() -> None:
    """Start task transitions to RUNNING."""
    manager = CoordinationManager()
    task = manager.create_task()
    manager.start_task(task)
    assert task.state == TaskState.RUNNING


def test_coordination_manager_complete_task() -> None:
    """Complete task updates state and metrics."""
    manager = CoordinationManager()
    task = manager.create_task(agent_type="discovery")
    manager.start_task(task)
    manager.complete_task(task)
    assert task.state == TaskState.COMPLETED
    stats = manager.circuit_breaker.get_stats("discovery")
    assert stats is not None
    assert stats.succeeded == 1


def test_coordination_manager_fail_task() -> None:
    """Fail task updates state and metrics."""
    manager = CoordinationManager()
    task = manager.create_task(agent_type="analysis")
    manager.start_task(task)
    manager.fail_task(task, "Test error", FailureType.LOGIC)
    assert task.state == TaskState.FAILED
    stats = manager.circuit_breaker.get_stats("analysis")
    assert stats is not None
    assert stats.failed == 1


def test_coordination_manager_fail_task_retry() -> None:
    """Fail task with retry doesn't update circuit breaker."""
    manager = CoordinationManager()
    task = manager.create_task(agent_type="discovery")
    manager.start_task(task)
    manager.fail_task(task, "Network error", FailureType.TRANSIENT)
    assert task.state == TaskState.RETRY
    stats = manager.circuit_breaker.get_stats("discovery")
    # Should not record failure for retry state
    assert stats is None or stats.failed == 0


def test_coordination_manager_check_and_enforce_timeout() -> None:
    """Check and enforce kills timed out task."""
    manager = CoordinationManager(
        timeout_enforcer=TimeoutEnforcer(task_timeout=0.1)
    )
    task = manager.create_task(timeout_seconds=0.1)
    manager.start_task(task)
    time.sleep(0.2)
    healthy = manager.check_and_enforce(task)
    assert not healthy
    assert task.state == TaskState.TIMEOUT


def test_coordination_manager_check_and_enforce_memory() -> None:
    """Check and enforce kills task exceeding memory."""
    manager = CoordinationManager(
        health_checker=HealthChecker(max_memory_mb=2048)
    )
    task = manager.create_task()
    task.memory_mb = 3000
    manager.start_task(task)
    healthy = manager.check_and_enforce(task)
    assert not healthy
    assert task.state == TaskState.FAILED


def test_coordination_manager_check_and_enforce_healthy() -> None:
    """Check and enforce allows healthy task."""
    manager = CoordinationManager()
    task = manager.create_task()
    manager.start_task(task)
    healthy = manager.check_and_enforce(task)
    assert healthy
    assert task.state == TaskState.RUNNING


def test_coordination_manager_get_task() -> None:
    """Get task retrieves by ID."""
    manager = CoordinationManager()
    task = manager.create_task()
    retrieved = manager.get_task(task.id)
    assert retrieved is task


def test_coordination_manager_get_task_not_found() -> None:
    """Get task returns None for unknown ID."""
    manager = CoordinationManager()
    assert manager.get_task("unknown") is None


def test_coordination_manager_get_all_tasks() -> None:
    """Get all tasks returns all registered tasks."""
    manager = CoordinationManager()
    task1 = manager.create_task()
    task2 = manager.create_task()
    all_tasks = manager.get_all_tasks()
    assert len(all_tasks) == 2
    assert task1 in all_tasks
    assert task2 in all_tasks


def test_coordination_manager_reset() -> None:
    """Reset clears all state."""
    manager = CoordinationManager()
    task = manager.create_task(agent_type="discovery")
    manager.start_task(task)
    manager.complete_task(task)
    manager.reset()
    assert len(manager.tasks) == 0
    assert manager.circuit_breaker.get_stats("discovery") is None
    assert manager.health_checker.get_metrics("discovery") is None


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


def test_integration_full_task_lifecycle() -> None:
    """Full task lifecycle: create → start → complete."""
    manager = CoordinationManager()
    task = manager.create_task(agent_type="discovery")
    assert task.state == TaskState.PENDING

    manager.start_task(task)
    assert task.state == TaskState.RUNNING

    manager.complete_task(task)
    assert task.state == TaskState.COMPLETED
    assert task.is_terminal()


def test_integration_retry_then_succeed() -> None:
    """Task fails with retry, then succeeds on retry."""
    manager = CoordinationManager()
    task = manager.create_task(agent_type="discovery", max_retries=2)

    manager.start_task(task)
    manager.fail_task(task, "Network error", FailureType.TRANSIENT)
    assert task.state == TaskState.RETRY
    assert task.retry_count == 1

    # Retry
    manager.start_task(task)
    manager.complete_task(task)
    assert task.state == TaskState.COMPLETED


def test_integration_circuit_breaker_blocks_phase() -> None:
    """Circuit breaker blocks phase when <50% succeed."""
    manager = CoordinationManager()

    # Run 4 tasks: 1 success, 3 failures
    for i in range(4):
        task = manager.create_task(agent_type="discovery")
        manager.start_task(task)
        if i == 0:
            manager.complete_task(task)
        else:
            manager.fail_task(task, "Error", FailureType.LOGIC)

    # Check if phase should proceed
    should_proceed, error = manager.circuit_breaker.should_proceed("discovery")
    assert not should_proceed
    assert "Circuit breaker triggered" in error


def test_integration_circuit_breaker_allows_phase() -> None:
    """Circuit breaker allows phase when ≥50% succeed."""
    manager = CoordinationManager()

    # Run 4 tasks: 3 success, 1 failure
    for i in range(4):
        task = manager.create_task(agent_type="discovery")
        manager.start_task(task)
        if i < 3:
            manager.complete_task(task)
        else:
            manager.fail_task(task, "Error", FailureType.LOGIC)

    # Check if phase should proceed
    should_proceed, error = manager.circuit_breaker.should_proceed("discovery")
    assert should_proceed
    assert error == ""


def test_integration_timeout_kills_hanging_task() -> None:
    """Timeout enforcer kills task exceeding timeout."""
    manager = CoordinationManager(
        timeout_enforcer=TimeoutEnforcer(task_timeout=0.1)
    )
    task = manager.create_task(timeout_seconds=0.1)
    manager.start_task(task)
    time.sleep(0.2)

    healthy = manager.check_and_enforce(task)
    assert not healthy
    assert task.state == TaskState.TIMEOUT


def test_integration_health_checker_kills_memory_hog() -> None:
    """Health checker kills task exceeding memory limit."""
    manager = CoordinationManager(
        health_checker=HealthChecker(max_memory_mb=2048)
    )
    task = manager.create_task(agent_type="analysis")
    task.memory_mb = 3000
    manager.start_task(task)

    healthy = manager.check_and_enforce(task)
    assert not healthy
    assert task.state == TaskState.FAILED
    assert "memory" in task.error.lower()
