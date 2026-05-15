"""Shared TaskList — single queue all spoke agents claim from.

Tasks are typed records with status + assignee + parent task. Status
transitions are guarded: a task in DONE/FAILED can't be re-claimed; a task
in IN_PROGRESS belongs to one agent at a time.
"""
from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field, replace
from typing import Any, Optional


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


_TERMINAL_STATES = frozenset({TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.CANCELLED})


@dataclass(frozen=True)
class Task:
    """One unit of work in the shared queue."""

    task_id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None
    parent_task_id: Optional[str] = None
    output: Any = None
    error: str = ""
    priority: int = 0  # higher claims first
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not self.task_id:
            raise ValueError("task_id must be non-empty")
        if not self.description:
            raise ValueError("description must be non-empty")
        if self.status == TaskStatus.IN_PROGRESS and self.assigned_to is None:
            raise ValueError("IN_PROGRESS tasks must have assigned_to")

    @property
    def is_terminal(self) -> bool:
        return self.status in _TERMINAL_STATES

    @property
    def is_claimable(self) -> bool:
        return self.status == TaskStatus.PENDING


@dataclass
class TaskList:
    """Shared task queue — single source of truth for what work exists.

    >>> tasks = TaskList()
    >>> t = tasks.add(description="research X")
    >>> claimed = tasks.claim_next(agent_id="spoke-1")
    >>> claimed.assigned_to
    'spoke-1'
    >>> claimed.status == TaskStatus.IN_PROGRESS
    True
    """

    _tasks: dict[str, Task] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self._tasks)

    def add(
        self,
        *,
        description: str,
        priority: int = 0,
        parent_task_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Task:
        """Add a new PENDING task; returns the created Task."""
        tid = task_id or str(uuid.uuid4())
        if tid in self._tasks:
            raise ValueError(f"task_id {tid!r} already exists")
        task = Task(
            task_id=tid,
            description=description,
            priority=priority,
            parent_task_id=parent_task_id,
        )
        self._tasks[tid] = task
        return task

    def get(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def list_all(self, *, status: Optional[TaskStatus] = None) -> list[Task]:
        out = list(self._tasks.values())
        if status is not None:
            out = [t for t in out if t.status == status]
        # Stable sort: higher priority first, then created_at asc.
        out.sort(key=lambda t: (-t.priority, t.created_at))
        return out

    def claim_next(self, *, agent_id: str) -> Optional[Task]:
        """Atomically claim the next PENDING task for an agent.

        Returns None if no claimable tasks. Highest-priority + oldest-first.
        """
        pending = [t for t in self._tasks.values() if t.is_claimable]
        if not pending:
            return None
        pending.sort(key=lambda t: (-t.priority, t.created_at))
        target = pending[0]
        claimed = replace(
            target,
            status=TaskStatus.IN_PROGRESS,
            assigned_to=agent_id,
            updated_at=time.time(),
        )
        self._tasks[target.task_id] = claimed
        return claimed

    def complete(
        self,
        *,
        task_id: str,
        agent_id: str,
        output: Any = None,
    ) -> Task:
        """Mark a task as DONE. Caller must own the task (assigned_to match)."""
        return self._transition(
            task_id=task_id,
            agent_id=agent_id,
            new_status=TaskStatus.DONE,
            output=output,
            error="",
        )

    def fail(
        self,
        *,
        task_id: str,
        agent_id: str,
        error: str,
    ) -> Task:
        """Mark a task as FAILED."""
        return self._transition(
            task_id=task_id,
            agent_id=agent_id,
            new_status=TaskStatus.FAILED,
            output=None,
            error=error,
        )

    def cancel(self, *, task_id: str) -> Task:
        """Cancel a task (lead-only operation; no agent_id check)."""
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"task {task_id!r} not found")
        if task.is_terminal:
            raise ValueError(f"cannot cancel terminal task ({task.status.value})")
        cancelled = replace(
            task,
            status=TaskStatus.CANCELLED,
            updated_at=time.time(),
        )
        self._tasks[task_id] = cancelled
        return cancelled

    def _transition(
        self,
        *,
        task_id: str,
        agent_id: str,
        new_status: TaskStatus,
        output: Any,
        error: str,
    ) -> Task:
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"task {task_id!r} not found")
        if task.is_terminal:
            raise ValueError(f"task already terminal ({task.status.value})")
        if task.assigned_to != agent_id:
            raise PermissionError(
                f"agent {agent_id!r} cannot transition task {task_id!r} "
                f"assigned to {task.assigned_to!r}"
            )
        new_task = replace(
            task,
            status=new_status,
            output=output,
            error=error,
            updated_at=time.time(),
        )
        self._tasks[task_id] = new_task
        return new_task

    def stats(self) -> dict[str, int]:
        c = {s.value: 0 for s in TaskStatus}
        for t in self._tasks.values():
            c[t.status.value] += 1
        c["total"] = len(self._tasks)
        return c


__all__ = ["Task", "TaskList", "TaskStatus"]
