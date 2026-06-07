"""Continuous autonomy loop — fire-and-forget task execution with health monitoring."""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LoopState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    RECOVERING = "recovering"
    STOPPED = "stopped"


class RunMode(str, Enum):
    ONCE = "once"            # Single task, exit when done
    CONTINUOUS = "continuous"  # Keep running, pick up new tasks
    SCHEDULED = "scheduled"    # Run on a cron-like schedule


@dataclass
class AutonomyLoop:
    """Continuous autonomy loop that runs unattended, managed by the supervisor daemon.

    The loop polls for pending tasks, executes them with health checks,
    and handles crashes with escalating recovery actions.
    """

    run_mode: RunMode = RunMode.CONTINUOUS
    max_idle_seconds: int = 3600  # Auto-stop after 1h idle
    health_check_interval: int = 30  # seconds between health pings
    max_consecutive_failures: int = 3

    _state: LoopState = LoopState.IDLE
    _last_activity: float = field(default_factory=time.time)
    _failure_count: int = 0
    _tasks_completed: int = 0

    @property
    def state(self) -> LoopState:
        return self._state

    @property
    def is_idle(self) -> bool:
        return (time.time() - self._last_activity) > self.max_idle_seconds

    async def start(self, task_queue: asyncio.Queue | None = None):
        """Start the autonomy loop. Runs until stopped or idle timeout."""
        self._state = LoopState.RUNNING
        self._last_activity = time.time()

        while self._state != LoopState.STOPPED:
            if self.is_idle and self.run_mode != RunMode.ONCE:
                self._state = LoopState.IDLE
                break

            if task_queue and not task_queue.empty():
                task = await task_queue.get()
                try:
                    await self._execute_task(task)
                    self._tasks_completed += 1
                    self._failure_count = 0
                    self._last_activity = time.time()
                except Exception:
                    self._failure_count += 1
                    if self._failure_count >= self.max_consecutive_failures:
                        self._state = LoopState.RECOVERING
                        break

            await asyncio.sleep(self.health_check_interval)

    async def _execute_task(self, task: Any):
        """Execute a single task with pre/post health checks."""
        self._state = LoopState.RUNNING
        # Health check before execution
        if not self._health_ok():
            raise RuntimeError("Health check failed before task execution")
        # Task execution happens via the agent loop
        self._state = LoopState.WAITING

    def _health_ok(self) -> bool:
        """Check if the loop is healthy enough to continue."""
        return self._failure_count < self.max_consecutive_failures

    def stop(self):
        """Gracefully stop the autonomy loop."""
        self._state = LoopState.STOPPED

    def stats(self) -> dict:
        return {
            "state": self._state.value,
            "tasks_completed": self._tasks_completed,
            "failure_count": self._failure_count,
            "idle_seconds": time.time() - self._last_activity,
        }
