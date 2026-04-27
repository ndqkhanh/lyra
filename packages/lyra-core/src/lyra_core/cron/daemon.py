"""Background tick loop that fires due :class:`CronJob` records.

The daemon is deterministic under :meth:`tick` (takes an explicit
``now`` so unit tests never depend on wall clock) and supports an
optional background thread via :meth:`start` / :meth:`stop`.

Design invariants
-----------------

* Runner exceptions are isolated: one bad job must never prevent the
  rest of the tick from completing. Failed recurring jobs are still
  rescheduled so a transient error can't permanently stall a schedule.
* One-shot jobs (``kind == "once"``) are removed after a single
  successful tick.
* The daemon never advances wall-clock time itself; ``next_run_at`` is
  computed from the parsed :class:`Schedule` so cron fidelity is owned
  by :func:`lyra_core.cron.schedule.parse_schedule`.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Callable

from .schedule import Schedule, ScheduleParseError, parse_schedule
from .store import CronJob, CronStore

__all__ = ["CronDaemon"]

UTC = timezone.utc


def _default_clock() -> datetime:
    return datetime.now(UTC)


def _parse_iso(ts: str | None) -> datetime | None:
    if ts is None:
        return None
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


class CronDaemon:
    """Tick loop driving a :class:`CronStore` with an injected runner."""

    def __init__(
        self,
        *,
        store: CronStore,
        runner: Callable[[CronJob], None],
        clock: Callable[[], datetime] = _default_clock,
        tick_interval: float = 1.0,
    ) -> None:
        self._store = store
        self._runner = runner
        self._clock = clock
        self._tick_interval = max(0.001, float(tick_interval))
        self._stop_evt = threading.Event()
        self._thread: threading.Thread | None = None

    # ---- tick loop ---------------------------------------------------

    def tick(self, *, now: datetime | None = None) -> list[str]:
        """Fire every due job; return the list of IDs that ran."""
        moment = now if now is not None else self._clock()
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)

        fired: list[str] = []
        for job in list(self._store.list()):
            if job.state != "active":
                continue
            next_at = _parse_iso(job.next_run_at)
            if next_at is None or next_at > moment:
                continue

            try:
                schedule = parse_schedule(job.schedule)
            except ScheduleParseError:
                continue

            ran_ok = True
            try:
                self._runner(job)
            except Exception:
                ran_ok = False

            if ran_ok:
                fired.append(job.id)

            if schedule.kind == "once":
                self._store.remove(job.id)
                continue

            next_fire = schedule.next_run(moment, last_run=moment)
            self._store.mark_run(
                job.id,
                last_run_at=moment.astimezone(UTC).isoformat(),
                next_run_at=next_fire.astimezone(UTC).isoformat(),
            )

        return fired

    # ---- background mode --------------------------------------------

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if self.is_running():
            return
        self._stop_evt.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="lyra-cron-daemon",
            daemon=True,
        )
        self._thread.start()

    def stop(self, *, timeout: float = 2.0) -> None:
        self._stop_evt.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=timeout)
        self._thread = None

    def _loop(self) -> None:
        while not self._stop_evt.is_set():
            try:
                self.tick()
            except Exception:
                pass  # defence-in-depth; tick already isolates per-job
            if self._stop_evt.wait(self._tick_interval):
                return
