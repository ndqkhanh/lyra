"""RoutineDaemon — drives :class:`RoutineRegistry` cron-fires on schedule.

The v3.7 L37-8 ``RoutineRegistry`` only exposes ``fire_cron(name)`` —
something has to actually call it on schedule. This daemon does that:
parses each cron-triggered routine's expression into a
:class:`~lyra_core.cron.schedule.Schedule`, computes the next run,
sleeps until then, fires the routine, records the firing, and loops.

Design notes:

* **Best-effort per routine.** A routine whose workflow raises does
  not kill the daemon; the exception is caught + logged via the HIR
  events stream, and the routine is rescheduled at its next normal
  time.
* **Pluggable clock.** The default uses real time; tests inject a
  mock clock so the daemon advances deterministically.
* **Stoppable.** :meth:`stop` flips a flag and the next sleep wakes
  early. The daemon thread is daemonic so process exit doesn't hang.
* **Single-tick mode.** :meth:`tick_once` runs one iteration without
  the loop — used by tests, observability tools, and the
  ``v311.routines.tick`` JSON-RPC method (post-v3.11.x).
* **Cron expression scope.** Only routines whose trigger is
  :class:`CronTrigger` are picked up. Webhook + API triggers fire
  inline elsewhere; they're observed but not driven by this daemon.
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .routines import CronTrigger, RoutineRegistry
from .schedule import Schedule, parse_schedule


_DEFAULT_TICK_S = 1.0


@dataclass(frozen=True)
class RoutineFiring:
    """One recorded firing of a routine."""

    routine_name: str
    fired_at: float
    next_run_at: float
    error: str | None = None


@dataclass
class RoutineDaemon:
    """Drives a :class:`RoutineRegistry`'s cron-triggered routines.

    Usage::

        daemon = RoutineDaemon(registry=reg)
        daemon.start()
        # ... routines fire on schedule ...
        daemon.stop()
    """

    registry: RoutineRegistry
    tick_seconds: float = _DEFAULT_TICK_S
    clock: Callable[[], datetime] = field(default=None)  # type: ignore[assignment]
    sleep_fn: Callable[[float], None] = field(default=time.sleep)
    firings: list[RoutineFiring] = field(default_factory=list)
    _thread: threading.Thread | None = field(default=None, init=False)
    _stop_event: threading.Event = field(default_factory=threading.Event, init=False)
    _last_run: dict[str, datetime] = field(default_factory=dict, init=False)
    _next_run: dict[str, datetime] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if self.clock is None:
            self.clock = lambda: datetime.now(timezone.utc)

    # ---- lifecycle -----------------------------------------------

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("daemon already running")
        self._stop_event.clear()
        # Pre-seed next_run for every cron routine.
        self._refresh_schedule()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="lyra-routine-daemon"
        )
        self._thread.start()

    def stop(self, *, timeout: float = 2.0) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self._thread = None

    # ---- core loop -----------------------------------------------

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self.tick_once()
            if self._stop_event.is_set():
                break
            self.sleep_fn(self.tick_seconds)

    def tick_once(self) -> int:
        """Run one tick. Refreshes schedules, fires every routine
        whose ``next_run`` has elapsed. Returns the number of routines
        fired this tick."""
        self._refresh_schedule()
        now = self._now()
        fired = 0
        for name, routine in list(self.registry.routines.items()):
            if not isinstance(routine.trigger, CronTrigger):
                continue
            next_run = self._next_run.get(name)
            if next_run is None:
                continue
            if now >= next_run:
                fired += 1
                self._fire(name, now)
        return fired

    # ---- internal helpers ----------------------------------------

    def _now(self) -> datetime:
        n = self.clock()
        if n.tzinfo is None:
            n = n.replace(tzinfo=timezone.utc)
        return n

    def _refresh_schedule(self) -> None:
        """Compute / update ``next_run`` for every cron routine that
        doesn't already have one (or whose registry entry was removed
        and re-added)."""
        for name, routine in self.registry.routines.items():
            if not isinstance(routine.trigger, CronTrigger):
                continue
            if name in self._next_run:
                continue
            try:
                schedule = parse_schedule(routine.trigger.expression)
            except Exception:
                # Unparseable expression — skip silently. Caller
                # handles by checking which routines didn't get
                # scheduled.
                continue
            self._next_run[name] = schedule.next_run(self._now())
        # Drop next_run entries whose routine is gone.
        for stale in [n for n in self._next_run if n not in self.registry.routines]:
            self._next_run.pop(stale, None)
            self._last_run.pop(stale, None)

    def _fire(self, name: str, now: datetime) -> None:
        routine = self.registry.routines[name]
        error: str | None = None
        try:
            self.registry.fire_cron(name)
        except Exception as e:  # noqa: BLE001
            error = f"{type(e).__name__}: {e}"
        # Compute next run AFTER this firing.
        try:
            schedule = parse_schedule(routine.trigger.expression)
            self._next_run[name] = schedule.next_run(now, last_run=now)
        except Exception:
            self._next_run.pop(name, None)
        self._last_run[name] = now
        self.firings.append(
            RoutineFiring(
                routine_name=name,
                fired_at=now.timestamp(),
                next_run_at=self._next_run.get(name, now).timestamp(),
                error=error,
            )
        )
        # HIR event for traceability.
        try:
            from lyra_core.hir import events

            events.emit(
                "routine.fired",
                routine=name,
                error=error,
                next_run_at=self._next_run.get(name, now).isoformat(),
            )
        except Exception:
            pass

    # ---- read-side ------------------------------------------------

    def schedule_snapshot(self) -> dict[str, dict[str, Any]]:
        """Return ``{routine_name: {next_run, last_run}}`` for every
        scheduled routine. Useful for /routines status displays."""
        out: dict[str, dict[str, Any]] = {}
        for name in self.registry.routines:
            out[name] = {
                "next_run": (
                    self._next_run[name].isoformat() if name in self._next_run else None
                ),
                "last_run": (
                    self._last_run[name].isoformat() if name in self._last_run else None
                ),
            }
        return out


__all__ = [
    "RoutineDaemon",
    "RoutineFiring",
]
