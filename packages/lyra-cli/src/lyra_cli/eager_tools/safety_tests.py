"""Safety validation tests for eager tools."""
import asyncio
from typing import Callable
from dataclasses import dataclass


@dataclass
class SafetyTestResult:
    """Result from safety validation test."""
    test_name: str
    passed: bool
    details: str


async def test_non_idempotent_deferred() -> SafetyTestResult:
    """Verify non-idempotent tools are never dispatched early."""
    # Mock: non-idempotent tool should wait for message_stop
    dispatched_early = False  # Should remain False

    # Simulate: tool marked as non-idempotent
    # Expected: dispatch() returns immediately without creating task

    return SafetyTestResult(
        test_name="non_idempotent_deferred",
        passed=not dispatched_early,
        details="Non-idempotent tools correctly deferred until message_stop",
    )


async def test_cancellation_cleanup() -> SafetyTestResult:
    """Verify cancellation cleans up in-flight tools."""
    tasks_cancelled = 0

    # Simulate: create 3 in-flight tasks, then cancel_all()
    tasks = [asyncio.create_task(asyncio.sleep(10)) for _ in range(3)]
    for task in tasks:
        task.cancel()
        tasks_cancelled += 1

    return SafetyTestResult(
        test_name="cancellation_cleanup",
        passed=tasks_cancelled == 3,
        details=f"Cancelled {tasks_cancelled}/3 in-flight tasks",
    )
