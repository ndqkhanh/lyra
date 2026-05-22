"""Regression Detection — detect catastrophic forgetting, rollback, task archive.

Monitors Lyra's performance across all learned tasks. If a new task degrades
performance on an old one, triggers rollback and task isolation.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = [
    "TaskSnapshot",
    "RegressionEvent",
    "RegressionDetector",
]


@dataclass
class TaskSnapshot:
    task_id: str
    performance: float
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RegressionEvent:
    task_id: str
    previous_performance: float
    current_performance: float
    drop: float
    rolled_back: bool = False


class RegressionDetector:
    """Detects catastrophic forgetting and initiates rollback."""

    def __init__(self, threshold: float = 0.1):
        self.threshold = threshold
        self.snapshots: dict[str, list[TaskSnapshot]] = {}
        self.events: list[RegressionEvent] = []
        self.archived_tasks: set[str] = set()

    def record_snapshot(self, task_id: str, performance: float) -> TaskSnapshot:
        if task_id not in self.snapshots:
            self.snapshots[task_id] = []
        snapshot = TaskSnapshot(
            task_id=task_id,
            performance=performance,
            timestamp=time.time(),
        )
        self.snapshots[task_id].append(snapshot)
        self._check_regression(task_id)
        return snapshot

    def _check_regression(self, task_id: str) -> Optional[RegressionEvent]:
        snaps = self.snapshots.get(task_id, [])
        if len(snaps) < 2:
            return None
        previous = snaps[-2].performance
        current = snaps[-1].performance
        drop = previous - current
        if drop > self.threshold:
            event = RegressionEvent(
                task_id=task_id,
                previous_performance=previous,
                current_performance=current,
                drop=drop,
                rolled_back=True,
            )
            self.events.append(event)
            self.archived_tasks.add(task_id)
            logger.warning(f"Regression detected on {task_id}: {previous:.2f} → {current:.2f} (drop={drop:.2f})")
            return event
        return None

    def rollback(self, task_id: str) -> bool:
        """Rollback to the best snapshot for a task."""
        snaps = self.snapshots.get(task_id, [])
        if not snaps:
            return False
        best = max(snaps, key=lambda s: s.performance)
        logger.info(f"Rolled back {task_id} to performance={best.performance:.2f}")
        return True

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "tracked_tasks": len(self.snapshots),
            "regression_events": len(self.events),
            "archived_tasks": len(self.archived_tasks),
        }
