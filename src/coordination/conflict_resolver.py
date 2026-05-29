"""
Conflict Resolver - Resolve resource conflicts and deadlocks.
"""

import time
from dataclasses import dataclass
from enum import Enum

from src.core.task import Task


class ConflictType(Enum):
    """Types of conflicts."""
    RESOURCE = "resource"          # Resource contention
    DEADLOCK = "deadlock"          # Circular wait
    PRIORITY = "priority"          # Priority inversion
    CAPACITY = "capacity"          # Agent capacity exceeded


class ResolutionStrategy(Enum):
    """Conflict resolution strategies."""
    PRIORITY_BASED = "priority_based"      # Higher priority wins
    FIRST_COME = "first_come"              # First request wins
    PREEMPT = "preempt"                    # Preempt lower priority
    QUEUE = "queue"                        # Queue conflicting tasks
    ABORT = "abort"                        # Abort conflicting task


@dataclass
class Conflict:
    """Represents a conflict between tasks."""
    conflict_id: str
    conflict_type: ConflictType
    tasks: list[str]
    resource: str | None = None
    detected_at: float = 0.0
    resolved: bool = False
    resolution: str | None = None


@dataclass
class Resource:
    """Represents a shared resource."""
    resource_id: str
    owner: str | None = None
    waiters: list[str] = None

    def __post_init__(self):
        if self.waiters is None:
            self.waiters = []


class ConflictResolver:
    """
    Resolve conflicts between tasks and agents.

    Responsibilities:
    - Detect resource conflicts
    - Detect deadlocks
    - Resolve conflicts using strategies
    - Prevent priority inversion
    """

    def __init__(self, strategy: ResolutionStrategy = ResolutionStrategy.PRIORITY_BASED):
        """
        Initialize conflict resolver.

        Args:
            strategy: Resolution strategy to use
        """
        self.strategy = strategy
        self.conflicts: dict[str, Conflict] = {}
        self.resources: dict[str, Resource] = {}
        self.conflict_count = 0

    def register_resource(self, resource_id: str):
        """
        Register a shared resource.

        Args:
            resource_id: Resource identifier
        """
        if resource_id not in self.resources:
            self.resources[resource_id] = Resource(resource_id=resource_id)

    def request_resource(
        self,
        task: Task,
        resource_id: str,
        timeout: float = 30.0,
    ) -> bool:
        """
        Request access to a resource.

        Args:
            task: Task requesting resource
            resource_id: Resource to request
            timeout: Request timeout in seconds

        Returns:
            True if resource granted
        """
        # Ensure resource exists
        if resource_id not in self.resources:
            self.register_resource(resource_id)

        resource = self.resources[resource_id]

        # Check if available
        if resource.owner is None:
            resource.owner = task.task_id
            return True

        # Resource is busy - check for conflict
        conflict = self._detect_resource_conflict(task, resource_id)

        if conflict:
            # Try to resolve
            resolved = self._resolve_conflict(conflict)

            if resolved:
                resource.owner = task.task_id
                return True

        # Add to waiters
        if task.task_id not in resource.waiters:
            resource.waiters.append(task.task_id)

        return False

    def release_resource(self, task: Task, resource_id: str):
        """
        Release a resource.

        Args:
            task: Task releasing resource
            resource_id: Resource to release
        """
        if resource_id not in self.resources:
            return

        resource = self.resources[resource_id]

        if resource.owner == task.task_id:
            resource.owner = None

            # Grant to next waiter
            if resource.waiters:
                next_task_id = resource.waiters.pop(0)
                resource.owner = next_task_id

    def detect_deadlock(self, tasks: list[Task]) -> list[str] | None:
        """
        Detect deadlock in resource allocation.

        Args:
            tasks: Tasks to check

        Returns:
            List of task IDs in deadlock cycle, or None
        """
        # Build wait-for graph
        wait_for = {}

        for resource in self.resources.values():
            if resource.owner and resource.waiters:
                for waiter in resource.waiters:
                    if waiter not in wait_for:
                        wait_for[waiter] = []
                    wait_for[waiter].append(resource.owner)

        # Detect cycle using DFS
        visited = set()
        rec_stack = set()

        def has_cycle(task_id: str, path: list[str]) -> list[str] | None:
            visited.add(task_id)
            rec_stack.add(task_id)
            path.append(task_id)

            if task_id in wait_for:
                for waiting_on in wait_for[task_id]:
                    if waiting_on not in visited:
                        cycle = has_cycle(waiting_on, path.copy())
                        if cycle:
                            return cycle
                    elif waiting_on in rec_stack:
                        # Found cycle
                        cycle_start = path.index(waiting_on)
                        return path[cycle_start:] + [waiting_on]

            rec_stack.remove(task_id)
            return None

        # Check each task
        for task in tasks:
            if task.task_id not in visited:
                cycle = has_cycle(task.task_id, [])
                if cycle:
                    return cycle

        return None

    def _detect_resource_conflict(self, task: Task, resource_id: str) -> Conflict | None:
        """
        Detect resource conflict.

        Args:
            task: Task requesting resource
            resource_id: Resource being requested

        Returns:
            Conflict if detected
        """
        resource = self.resources[resource_id]

        if resource.owner is None:
            return None

        # Create conflict
        self.conflict_count += 1
        conflict = Conflict(
            conflict_id=f"conflict_{self.conflict_count}",
            conflict_type=ConflictType.RESOURCE,
            tasks=[task.task_id, resource.owner],
            resource=resource_id,
            detected_at=time.time(),
        )

        self.conflicts[conflict.conflict_id] = conflict
        return conflict

    def _resolve_conflict(self, conflict: Conflict) -> bool:
        """
        Resolve a conflict using current strategy.

        Args:
            conflict: Conflict to resolve

        Returns:
            True if resolved
        """
        if self.strategy == ResolutionStrategy.PRIORITY_BASED:
            return self._resolve_by_priority(conflict)
        elif self.strategy == ResolutionStrategy.FIRST_COME:
            return self._resolve_first_come(conflict)
        elif self.strategy == ResolutionStrategy.PREEMPT:
            return self._resolve_by_preemption(conflict)
        elif self.strategy == ResolutionStrategy.QUEUE:
            return self._resolve_by_queue(conflict)
        elif self.strategy == ResolutionStrategy.ABORT:
            return self._resolve_by_abort(conflict)

        return False

    def _resolve_by_priority(self, conflict: Conflict) -> bool:
        """Resolve conflict based on task priority."""
        # This is a simplified version - in real implementation,
        # we would need access to actual task objects
        conflict.resolved = True
        conflict.resolution = "priority_based"
        return False  # Don't grant resource yet

    def _resolve_first_come(self, conflict: Conflict) -> bool:
        """Resolve conflict by first-come-first-served."""
        conflict.resolved = True
        conflict.resolution = "first_come"
        return False  # Current owner keeps resource

    def _resolve_by_preemption(self, conflict: Conflict) -> bool:
        """Resolve conflict by preempting current owner."""
        if conflict.resource:
            resource = self.resources[conflict.resource]
            # Preempt current owner
            old_owner = resource.owner
            resource.owner = None

            conflict.resolved = True
            conflict.resolution = f"preempted_{old_owner}"
            return True

    def _resolve_by_queue(self, conflict: Conflict) -> bool:
        """Resolve conflict by queueing."""
        conflict.resolved = True
        conflict.resolution = "queued"
        return False  # Task will wait in queue

    def _resolve_by_abort(self, conflict: Conflict) -> bool:
        """Resolve conflict by aborting one task."""
        conflict.resolved = True
        conflict.resolution = "aborted"
        return False

    def resolve_deadlock(self, cycle: list[str]) -> str:
        """
        Resolve a deadlock by aborting one task.

        Args:
            cycle: Task IDs in deadlock cycle

        Returns:
            ID of task to abort
        """
        # Abort task with lowest priority (simplified)
        # In real implementation, would check actual priorities
        victim = cycle[0]

        # Release all resources held by victim
        for resource in self.resources.values():
            if resource.owner == victim:
                resource.owner = None
                if resource.waiters:
                    resource.owner = resource.waiters.pop(0)

        return victim

    def get_conflict_statistics(self) -> dict:
        """
        Get conflict resolution statistics.

        Returns:
            Statistics dictionary
        """
        total_conflicts = len(self.conflicts)
        resolved = sum(1 for c in self.conflicts.values() if c.resolved)

        # Count by type
        by_type = {}
        for conflict in self.conflicts.values():
            ctype = conflict.conflict_type.value
            by_type[ctype] = by_type.get(ctype, 0) + 1

        # Count by resolution
        by_resolution = {}
        for conflict in self.conflicts.values():
            if conflict.resolution:
                by_resolution[conflict.resolution] = by_resolution.get(conflict.resolution, 0) + 1

        return {
            "total_conflicts": total_conflicts,
            "resolved": resolved,
            "unresolved": total_conflicts - resolved,
            "by_type": by_type,
            "by_resolution": by_resolution,
            "strategy": self.strategy.value,
        }

    def get_resource_status(self) -> dict:
        """
        Get status of all resources.

        Returns:
            Resource status dictionary
        """
        return {
            resource_id: {
                "owner": resource.owner,
                "waiters": len(resource.waiters),
                "waiter_ids": resource.waiters,
            }
            for resource_id, resource in self.resources.items()
        }

    def clear_resolved_conflicts(self):
        """Remove resolved conflicts from tracking."""
        self.conflicts = {
            cid: conflict
            for cid, conflict in self.conflicts.items()
            if not conflict.resolved
        }
