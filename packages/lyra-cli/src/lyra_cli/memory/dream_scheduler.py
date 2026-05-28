"""Cron-based enrichment scheduler for dream consolidation.

Schedules periodic consolidation runs at configured intervals:
- Cycle (6h), Deep (24h), Review (7d), Prune (30d), Archive (90d)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum


class DreamScheduleTrigger(StrEnum):
    CYCLE = "consolidation.cycle"
    DEEP = "consolidation.deep"
    REVIEW = "consolidation.review"
    PRUNE = "consolidation.prune"
    ARCHIVE = "consolidation.archive"


@dataclass(frozen=True)
class ScheduleEntry:
    trigger: DreamScheduleTrigger
    interval_sec: float
    last_run: float
    next_run: float
    enabled: bool = True


@dataclass(frozen=True)
class SchedulerState:
    entries: list[ScheduleEntry]
    total_runs: int
    last_action: str
    timestamp: float


class DreamScheduler:
    """Cron-like scheduler for periodic dream consolidation runs.

    Default schedule:
    - CYCLE:   Every 6 hours  — full dream cycle on recent traces
    - DEEP:    Every 24 hours — deep consolidation with cross-session weaving
    - REVIEW:  Every 7 days   — spaced repetition review of aging memories
    - PRUNE:   Every 30 days  — full prune pass on all memory tiers
    - ARCHIVE: Every 90 days  — archive cold memories to external storage
    """

    DEFAULT_INTERVALS: dict[DreamScheduleTrigger, float] = {
        DreamScheduleTrigger.CYCLE: 6 * 3600,
        DreamScheduleTrigger.DEEP: 24 * 3600,
        DreamScheduleTrigger.REVIEW: 7 * 24 * 3600,
        DreamScheduleTrigger.PRUNE: 30 * 24 * 3600,
        DreamScheduleTrigger.ARCHIVE: 90 * 24 * 3600,
    }

    def __init__(self) -> None:
        now = time.time()
        self._entries: dict[DreamScheduleTrigger, ScheduleEntry] = {}
        for trigger, interval in self.DEFAULT_INTERVALS.items():
            self._entries[trigger] = ScheduleEntry(
                trigger=trigger,
                interval_sec=interval,
                last_run=0.0,
                next_run=now + interval,
                enabled=True,
            )
        self._total_runs = 0
        self._handlers: dict[DreamScheduleTrigger, object] = {}

    def register_handler(self, trigger: DreamScheduleTrigger, handler: object) -> None:
        self._handlers[trigger] = handler

    def tick(self) -> list[DreamScheduleTrigger]:
        """Check which triggers are due. Returns list of triggers to run."""
        now = time.time()
        due: list[DreamScheduleTrigger] = []

        for entry in self._entries.values():
            if not entry.enabled:
                continue
            if now >= entry.next_run:
                due.append(entry.trigger)

        return due

    def mark_run(self, trigger: DreamScheduleTrigger) -> ScheduleEntry:
        now = time.time()
        entry = self._entries[trigger]
        updated = ScheduleEntry(
            trigger=entry.trigger,
            interval_sec=entry.interval_sec,
            last_run=now,
            next_run=now + entry.interval_sec,
            enabled=entry.enabled,
        )
        self._entries[trigger] = updated
        self._total_runs += 1
        return updated

    def run_due(self) -> SchedulerState:
        due = self.tick()
        action = "none"
        for trigger in due:
            if trigger in self._handlers:
                try:
                    self._handlers[trigger].run()  # type: ignore[union-attr]
                except Exception:
                    pass
            self.mark_run(trigger)
            action = trigger.value

        return self.get_state(last_action=action)

    def get_state(self, last_action: str = "none") -> SchedulerState:
        return SchedulerState(
            entries=list(self._entries.values()),
            total_runs=self._total_runs,
            last_action=last_action,
            timestamp=time.time(),
        )

    def get_entry(self, trigger: DreamScheduleTrigger) -> ScheduleEntry | None:
        return self._entries.get(trigger)

    def disable(self, trigger: DreamScheduleTrigger) -> None:
        entry = self._entries.get(trigger)
        if entry:
            self._entries[trigger] = ScheduleEntry(
                trigger=entry.trigger,
                interval_sec=entry.interval_sec,
                last_run=entry.last_run,
                next_run=entry.next_run,
                enabled=False,
            )

    def enable(self, trigger: DreamScheduleTrigger) -> None:
        entry = self._entries.get(trigger)
        if entry:
            self._entries[trigger] = ScheduleEntry(
                trigger=entry.trigger,
                interval_sec=entry.interval_sec,
                last_run=entry.last_run,
                next_run=time.time(),
                enabled=True,
            )

    def set_interval(self, trigger: DreamScheduleTrigger, seconds: float) -> None:
        entry = self._entries.get(trigger)
        if entry:
            self._entries[trigger] = ScheduleEntry(
                trigger=entry.trigger,
                interval_sec=seconds,
                last_run=entry.last_run,
                next_run=entry.last_run + seconds,
                enabled=entry.enabled,
            )

    def stats(self) -> dict:
        return {
            "total_runs": self._total_runs,
            "entries": {
                e.trigger.value: {
                    "interval_h": round(e.interval_sec / 3600, 1),
                    "last_run": e.last_run,
                    "next_run": e.next_run,
                    "enabled": e.enabled,
                    "due": time.time() >= e.next_run if e.enabled else False,
                }
                for e in self._entries.values()
            },
        }
