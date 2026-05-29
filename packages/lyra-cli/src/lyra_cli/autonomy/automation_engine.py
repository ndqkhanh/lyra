"""Cron-like scheduling engine for recurring Lyra autonomy tasks.

Supports one-shot and recurring schedules with random jitter to avoid
thundering-herd effects.
"""

from __future__ import annotations

import enum
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Default jitter window: +/- 10% of interval, max 60 seconds
_DEFAULT_JITTER_FRACTION: float = 0.1
_DEFAULT_JITTER_MAX_SECONDS: float = 60.0
_DEFAULT_POLL_INTERVAL: float = 1.0


class ScheduleKind(enum.Enum):
    """Whether a schedule fires once or repeats."""

    ONE_SHOT = "one_shot"
    RECURRING = "recurring"


@dataclass
class Schedule:
    """A single schedule entry."""

    id: str
    kind: ScheduleKind
    interval_seconds: float
    callback: Callable[[], None]
    next_run: float = 0.0  # epoch-seconds
    jitter_fraction: float = _DEFAULT_JITTER_FRACTION
    metadata: dict[str, Any] = field(default_factory=dict)

    def compute_next_run(self, from_time: float | None = None) -> float:
        """Calculate the next fire time, applying jitter.

        Jitter is uniformly distributed in
        ``[-jitter_fraction * interval, +jitter_fraction * interval]``
        but never wider than ``_DEFAULT_JITTER_MAX_SECONDS``.
        """
        now = from_time if from_time is not None else time.time()
        max_jitter = min(
            self.jitter_fraction * self.interval_seconds,
            _DEFAULT_JITTER_MAX_SECONDS,
        )
        jitter = random.uniform(-max_jitter, max_jitter)
        return now + self.interval_seconds + jitter


@dataclass
class AutomationEngine:
    """Cron-like engine that fires schedules on a polling loop.

    Usage::

        engine = AutomationEngine()
        engine.add_recurring("health_check", 60.0, my_health_callback)
        engine.add_one_shot("deploy", my_deploy_callback, delay=300.0)
        engine.run_once()   # fires any due schedules
        engine.run_forever(poll_interval=0.5)
    """

    schedules: dict[str, Schedule] = field(default_factory=dict)
    _running: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_recurring(
        self,
        schedule_id: str,
        interval_seconds: float,
        callback: Callable[[], None],
        *,
        jitter_fraction: float = _DEFAULT_JITTER_FRACTION,
        start_delay: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> Schedule:
        """Register a recurring schedule.

        Args:
            schedule_id: Unique identifier.
            interval_seconds: Time between firings.
            callback: Invoked when the schedule fires.
            jitter_fraction: Random +/- fraction for jitter.
            start_delay: Seconds to wait before first fire.
            metadata: Arbitrary key-value metadata.
        """
        now = time.time()
        schedule = Schedule(
            id=schedule_id,
            kind=ScheduleKind.RECURRING,
            interval_seconds=interval_seconds,
            callback=callback,
            next_run=now + start_delay,
            jitter_fraction=jitter_fraction,
            metadata=metadata or {},
        )
        self.schedules[schedule_id] = schedule
        logger.info(
            "schedule_added: id=%s kind=recurring interval=%s", schedule_id, interval_seconds
        )
        return schedule

    def add_one_shot(
        self,
        schedule_id: str,
        callback: Callable[[], None],
        *,
        delay: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> Schedule:
        """Register a one-shot schedule.

        Args:
            schedule_id: Unique identifier.
            callback: Invoked when the schedule fires.
            delay: Seconds from now to fire.
            metadata: Arbitrary key-value metadata.
        """
        schedule = Schedule(
            id=schedule_id,
            kind=ScheduleKind.ONE_SHOT,
            interval_seconds=0.0,
            callback=callback,
            next_run=time.time() + delay,
            metadata=metadata or {},
        )
        self.schedules[schedule_id] = schedule
        logger.info("schedule_added: id=%s kind=one_shot delay=%s", schedule_id, delay)
        return schedule

    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a previously registered schedule. Returns True if removed."""
        if schedule_id in self.schedules:
            del self.schedules[schedule_id]
            logger.info("schedule_removed: id=%s", schedule_id)
            return True
        return False

    def run_once(self) -> list[str]:
        """Check and fire all due schedules. Returns IDs of fired schedules."""
        now = time.time()
        fired: list[str] = []
        to_remove: list[str] = []

        for sid, schedule in list(self.schedules.items()):
            if now < schedule.next_run:
                continue
            try:
                schedule.callback()
            except Exception:
                logger.exception("schedule_callback_failed: id=%s", sid)
            fired.append(sid)

            # One-shot: remove after firing
            if schedule.kind == ScheduleKind.ONE_SHOT:
                to_remove.append(sid)
            else:
                schedule.next_run = schedule.compute_next_run(now)

        for sid in to_remove:
            self.schedules.pop(sid, None)

        return fired

    def run_forever(
        self,
        poll_interval: float = _DEFAULT_POLL_INTERVAL,
    ) -> None:
        """Continuously poll and fire schedules until stopped."""
        self._running = True
        try:
            while self._running:
                self.run_once()
                time.sleep(poll_interval)
        except KeyboardInterrupt:
            self._running = False

    def stop(self) -> None:
        """Signal the run_forever loop to exit."""
        self._running = False

    @property
    def is_running(self) -> bool:
        """Return True if the run_forever loop is active."""
        return self._running

    def pending_count(self) -> int:
        """Return the number of registered schedules."""
        return len(self.schedules)
