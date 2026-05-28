""""By the way" (btw) command — asynchronous non-blocking notifications.

Queues low-priority observations and suggestions that are surfaced
when the agent is idle, without interrupting active work.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum


class BtwPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass(frozen=True)
class BtwNote:
    note_id: str
    message: str
    priority: BtwPriority
    source: str
    created_at: float
    delivered: bool


class BtwQueue:
    """Non-blocking notification queue for "by the way" messages.

    Collects observations during agent work and delivers them
    when the agent is idle, avoiding context-window pollution
    during active tasks.
    """

    MAX_QUEUE_SIZE = 50

    def __init__(self) -> None:
        self._queue: list[BtwNote] = []
        self._delivered: list[BtwNote] = []
        self._counter = 0

    def enqueue(
        self,
        message: str,
        priority: BtwPriority = BtwPriority.NORMAL,
        source: str = "system",
    ) -> BtwNote:
        if len(self._queue) >= self.MAX_QUEUE_SIZE:
            self._queue.pop(0)

        self._counter += 1
        note = BtwNote(
            note_id=f"btw-{self._counter}",
            message=message,
            priority=priority,
            source=source,
            created_at=time.time(),
            delivered=False,
        )
        self._queue.append(note)
        self._queue.sort(key=lambda n: self._priority_weight(n.priority), reverse=True)
        return note

    def deliver(self, max_count: int = 5) -> list[BtwNote]:
        to_deliver = self._queue[:max_count]
        self._queue = self._queue[max_count:]

        delivered = []
        for note in to_deliver:
            updated = BtwNote(
                note_id=note.note_id,
                message=note.message,
                priority=note.priority,
                source=note.source,
                created_at=note.created_at,
                delivered=True,
            )
            self._delivered.append(updated)
            delivered.append(updated)

        return delivered

    def pending_count(self) -> int:
        return len(self._queue)

    def get_pending(self) -> list[BtwNote]:
        return list(self._queue)

    @staticmethod
    def _priority_weight(priority: BtwPriority) -> int:
        return {BtwPriority.HIGH: 3, BtwPriority.NORMAL: 2, BtwPriority.LOW: 1}[priority]

    def stats(self) -> dict:
        return {
            "pending": len(self._queue),
            "delivered": len(self._delivered),
            "by_priority": {
                p.value: sum(1 for n in self._queue if n.priority == p)
                for p in BtwPriority
            },
        }
