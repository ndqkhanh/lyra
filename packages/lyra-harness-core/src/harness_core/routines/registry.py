"""RoutineRegistry — server-side config + dispatch + fire history.

The registry is the single source of truth for which routines exist, who can
fire them (bearer token), and when cron-driven routines should fire next.
Production wires this to a database; in-process is the test + cold-start
substrate.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .cron import next_fire_after, parse_cron
from .types import Routine, RoutineFire, TriggerKind


@dataclass(frozen=True)
class FireResult:
    """The outcome of a routine fire."""

    fire: RoutineFire
    success: bool
    output: Any = None
    error: str = ""

    @property
    def routine_id(self) -> str:
        return self.fire.routine_id


@dataclass
class RoutineRegistry:
    """In-memory routine registry with fire history.

    >>> registry = RoutineRegistry()
    >>> def handler(*, fire): return f"fired {fire.routine_id}"
    >>> r = Routine(routine_id="r1", name="test", handler=handler)
    >>> registry.register(r)
    >>> result = registry.fire(routine_id="r1", triggered_by=TriggerKind.MANUAL,
    ...                         token=r.bearer_token)
    >>> result.success
    True
    """

    _routines: dict[str, Routine] = field(default_factory=dict)
    _fire_history: list[FireResult] = field(default_factory=list)
    _last_fired: dict[str, float] = field(default_factory=dict)

    # --- Registration -----------------------------------------------------

    def register(self, routine: Routine) -> Routine:
        """Register a routine. Replaces any existing entry with the same id."""
        # Validate cron expression early — fail loud at registration, not at fire.
        if routine.schedule is not None:
            parse_cron(routine.schedule)  # raises CronParseError on malformed
        self._routines[routine.routine_id] = routine
        return routine

    def unregister(self, routine_id: str) -> bool:
        if routine_id in self._routines:
            del self._routines[routine_id]
            return True
        return False

    def get(self, routine_id: str) -> Optional[Routine]:
        return self._routines.get(routine_id)

    def list_routines(self, *, enabled_only: bool = False) -> list[Routine]:
        out = list(self._routines.values())
        if enabled_only:
            out = [r for r in out if r.enabled]
        return out

    # --- Cron scheduling --------------------------------------------------

    def list_due(self, now: float) -> list[Routine]:
        """List enabled cron routines whose next-fire-time has passed.

        A routine is "due" if it has a cron schedule, is enabled, and its
        next-fire-time (computed from last-fire or registration) is <= now.
        """
        due: list[Routine] = []
        for r in self._routines.values():
            if not r.enabled or r.schedule is None:
                continue
            last = self._last_fired.get(r.routine_id, now - 60)
            nxt = next_fire_after(r.schedule, after=last)
            if nxt is not None and nxt <= now:
                due.append(r)
        return due

    def next_fire_time(self, routine_id: str, *, after: float) -> Optional[float]:
        """When the routine will next fire, given its schedule + last-fire."""
        r = self._routines.get(routine_id)
        if r is None or r.schedule is None:
            return None
        return next_fire_after(r.schedule, after=after)

    # --- Firing -----------------------------------------------------------

    def fire(
        self,
        *,
        routine_id: str,
        triggered_by: TriggerKind,
        token: str,
        payload: Optional[dict[str, Any]] = None,
        now: Optional[float] = None,
    ) -> FireResult:
        """Fire a routine.

        Authenticates against the routine's bearer token, then invokes the
        handler with a fresh :class:`RoutineFire`. Records the result in
        history.

        ``triggered_by=TriggerKind.CRON`` updates the last-fired time so
        :meth:`list_due` won't re-flag the routine immediately.
        """
        routine = self._routines.get(routine_id)
        ts = now if now is not None else time.time()
        if routine is None:
            fire = RoutineFire(
                fire_id=str(uuid.uuid4()),
                routine_id=routine_id,
                triggered_by=triggered_by,
                triggered_at=ts,
            )
            result = FireResult(fire=fire, success=False, error="routine not found")
            self._fire_history.append(result)
            return result

        if not routine.enabled:
            fire = RoutineFire(
                fire_id=str(uuid.uuid4()),
                routine_id=routine_id,
                triggered_by=triggered_by,
                triggered_at=ts,
            )
            result = FireResult(fire=fire, success=False, error="routine disabled")
            self._fire_history.append(result)
            return result

        if not routine.authenticates(token):
            fire = RoutineFire(
                fire_id=str(uuid.uuid4()),
                routine_id=routine_id,
                triggered_by=triggered_by,
                triggered_at=ts,
            )
            result = FireResult(fire=fire, success=False, error="invalid token")
            self._fire_history.append(result)
            return result

        fire = RoutineFire(
            fire_id=str(uuid.uuid4()),
            routine_id=routine_id,
            triggered_by=triggered_by,
            triggered_at=ts,
            payload=payload or {},
        )

        try:
            output = routine.handler(fire=fire)
            result = FireResult(fire=fire, success=True, output=output)
        except Exception as exc:
            result = FireResult(
                fire=fire,
                success=False,
                error=f"{exc.__class__.__name__}: {exc}",
            )

        self._fire_history.append(result)
        if triggered_by == TriggerKind.CRON or result.success:
            self._last_fired[routine_id] = ts
        return result

    # --- History + observability -----------------------------------------

    def history(
        self,
        *,
        routine_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[FireResult]:
        h = self._fire_history
        if routine_id is not None:
            h = [r for r in h if r.routine_id == routine_id]
        # Most-recent first.
        return list(reversed(h[-limit:]))

    def stats(self) -> dict[str, int]:
        successes = sum(1 for r in self._fire_history if r.success)
        failures = len(self._fire_history) - successes
        by_trigger: dict[str, int] = {k.value: 0 for k in TriggerKind}
        for r in self._fire_history:
            by_trigger[r.fire.triggered_by.value] += 1
        return {
            "routines": len(self._routines),
            "enabled": sum(1 for r in self._routines.values() if r.enabled),
            "fires_total": len(self._fire_history),
            "fires_success": successes,
            "fires_failure": failures,
            **{f"trigger_{k}": v for k, v in by_trigger.items()},
        }


__all__ = ["FireResult", "RoutineRegistry"]
