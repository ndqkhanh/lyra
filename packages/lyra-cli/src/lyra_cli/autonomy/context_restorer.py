"""Context Restorer - Rich context restoration for session continuation.

Reconstructs full execution context from checkpoints, including active goals,
task progress, error state, and working memory.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class RestoreStatus(StrEnum):
    """Outcome of a context restoration attempt."""

    FULL = "full"               # Complete context restored
    PARTIAL = "partial"          # Some context restored, some lost
    DEGRADED = "degraded"       # Minimal context restored
    FAILED = "failed"            # Could not restore


@dataclass(frozen=True)
class RestoredContext:
    """A fully restored execution context from a checkpoint."""

    session_id: str
    status: RestoreStatus
    goals: tuple[dict[str, Any], ...]
    active_tasks: tuple[dict[str, Any], ...]
    completed_tasks: tuple[dict[str, Any], ...]
    failed_tasks: tuple[dict[str, Any], ...]
    errors: tuple[str, ...]
    working_memory: dict[str, Any]
    budget_state: dict[str, Any]
    metadata: dict[str, Any]
    restored_at: str
    fidelity_pct: float  # 0.0-100.0, how much context was recovered


@dataclass(frozen=True)
class ContextFragment:
    """A piece of context that can be restored."""

    fragment_id: str
    category: str  # goal, task, error, memory, budget, metadata
    data: dict[str, Any]
    priority: int  # 1=critical, 5=optional
    restored: bool = False


class ContextRestorer:
    """Restores rich execution context from session checkpoints.

    Reconstructs goals, tasks, errors, working memory, budget state,
    and metadata to enable seamless session continuation.

    Features:
    - Multi-fragment context restoration with priority ordering
    - Fidelity scoring to quantify restoration quality
    - Graceful degradation when partial data is available
    - Categorized restoration: goals, tasks, errors, memory, budget
    - Context diffing to identify what changed between sessions
    """

    def __init__(self, max_fragments: int = 100):
        self._fragments: dict[str, ContextFragment] = {}
        self._max_fragments = max_fragments

    def store_fragment(self, fragment: ContextFragment) -> None:
        """Store a context fragment for later restoration.

        Args:
            fragment: Context fragment to store
        """
        self._fragments[fragment.fragment_id] = fragment
        if len(self._fragments) > self._max_fragments:
            oldest = min(
                self._fragments.keys(),
                key=lambda k: self._fragments[k].priority,
            )
            del self._fragments[oldest]

    def restore(
        self,
        session_id: str,
        checkpoint_data: dict[str, Any],
        priorities: tuple[str, ...] = (
            "goal", "task", "error", "memory", "budget", "metadata",
        ),
    ) -> RestoredContext:
        """Restore execution context from checkpoint data.

        Args:
            session_id: Session identifier
            checkpoint_data: Raw checkpoint data
            priorities: Restoration priority order

        Returns:
            RestoredContext with recovered state
        """
        restored: dict[str, list[dict[str, Any]]] = {
            "goals": [],
            "tasks": [],
            "errors": [],
            "memory": [],
            "budget": [],
            "metadata": [],
        }

        # Restore goals
        goals_raw = checkpoint_data.get("goals", [])
        restored["goals"] = list(goals_raw) if isinstance(goals_raw, list) else []

        # Restore tasks
        tasks_raw = checkpoint_data.get("tasks", checkpoint_data.get("active_tasks", []))
        if isinstance(tasks_raw, list):
            restored["tasks"] = tasks_raw

        # Restore errors
        errors_raw = checkpoint_data.get("errors", [])
        if isinstance(errors_raw, list):
            restored["errors"] = errors_raw

        # Restore working memory
        memory_raw = checkpoint_data.get("working_memory", checkpoint_data.get("context", {}))
        if isinstance(memory_raw, dict):
            restored["memory"] = [memory_raw]

        # Restore budget
        budget_raw = checkpoint_data.get("budget", checkpoint_data.get("budget_state", {}))
        if isinstance(budget_raw, dict):
            restored["budget"] = [budget_raw]

        # Metadata
        meta = {k: v for k, v in checkpoint_data.items()
                if k not in ("goals", "tasks", "active_tasks", "errors",
                              "working_memory", "context", "budget", "budget_state")}
        restored["metadata"] = [meta]

        # Calculate fidelity
        total_categories = len(priorities)
        restored_categories = sum(
            1 for cat in priorities
            if restored.get(cat if cat != "goal" else "goals", [])
        )
        categories_map = {
            "goal": "goals", "task": "tasks", "error": "errors",
            "memory": "memory", "budget": "budget", "metadata": "metadata",
        }
        restored_categories = sum(
            1 for cat in priorities
            if restored.get(categories_map.get(cat, cat), [])
        )
        fidelity = (restored_categories / total_categories * 100) if total_categories > 0 else 0.0

        # Determine status
        if fidelity >= 95:
            status = RestoreStatus.FULL
        elif fidelity >= 60:
            status = RestoreStatus.PARTIAL
        elif fidelity >= 20:
            status = RestoreStatus.DEGRADED
        else:
            status = RestoreStatus.FAILED

        # Extract active/completed/failed tasks
        tasks = restored["tasks"]
        active = [t for t in tasks if t.get("status") in ("pending", "running", "in_progress")]
        completed = [t for t in tasks if t.get("status") == "completed"]
        failed = [t for t in tasks if t.get("status") == "failed"]

        return RestoredContext(
            session_id=session_id,
            status=status,
            goals=tuple(restored["goals"]),
            active_tasks=tuple(active),
            completed_tasks=tuple(completed),
            failed_tasks=tuple(failed),
            errors=tuple(str(e) for e in restored["errors"]),
            working_memory=restored["memory"][0] if restored["memory"] else {},
            budget_state=restored["budget"][0] if restored["budget"] else {},
            metadata=restored["metadata"][0] if restored["metadata"] else {},
            restored_at=datetime.now().isoformat(),
            fidelity_pct=fidelity,
        )

    def diff_contexts(
        self, previous: RestoredContext, current: dict[str, Any]
    ) -> dict[str, Any]:
        """Compute the difference between restored and current context.

        Args:
            previous: Previously restored context
            current: Current context state

        Returns:
            Dict of changes: {category: {added: [], removed: [], modified: []}}
        """
        diff: dict[str, Any] = {}

        # Compare tasks
        prev_task_ids = {t.get("task_id") for t in previous.active_tasks}
        curr_task_ids = {t.get("task_id") for t in current.get("tasks", [])}
        diff["tasks"] = {
            "added": list(curr_task_ids - prev_task_ids),
            "removed": list(prev_task_ids - curr_task_ids),
            "still_active": list(prev_task_ids & curr_task_ids),
        }

        # Compare goals
        prev_goal_ids = {g.get("goal_id") for g in previous.goals}
        curr_goal_ids = {g.get("goal_id") for g in current.get("goals", [])}
        diff["goals"] = {
            "added": list(curr_goal_ids - prev_goal_ids),
            "removed": list(prev_goal_ids - curr_goal_ids),
        }

        return diff

    def get_restore_summary(self, context: RestoredContext) -> str:
        """Generate a human-readable restoration summary.

        Args:
            context: Restored context

        Returns:
            Summary string
        """
        parts = [
            f"Session: {context.session_id}",
            f"Status: {context.status.value} ({context.fidelity_pct:.0f}% restored)",
            f"Active tasks: {len(context.active_tasks)}",
            f"Completed: {len(context.completed_tasks)}",
            f"Failed: {len(context.failed_tasks)}",
        ]
        if context.errors:
            parts.append(f"Errors: {len(context.errors)}")
        return " | ".join(parts)

    def clear(self) -> None:
        """Clear all stored fragments."""
        self._fragments.clear()
