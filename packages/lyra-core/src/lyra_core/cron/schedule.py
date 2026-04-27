"""Schedule expression parsing for Lyra ``/cron``.

Three accepted forms (hermes-agent parity):

* ``"30m"`` / ``"2h"`` / ``"45s"`` — one-shot delay; fires once.
* ``"every 1h"`` / ``"every 15m"`` — recurring interval.
* ``"0 9 * * *"`` — classic 5-field cron (``minute hour dom month dow``).

Each expression produces a :class:`Schedule` whose ``next_run(now)``
returns the next ``datetime`` at or after ``now`` when the job should
fire. The parser is deliberately small — this scaffold locks the
surface area; richer cron features (ranges, steps, named months) can
be added behind the same ``next_run`` contract.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal

__all__ = ["Schedule", "ScheduleParseError", "parse_schedule"]

ScheduleKind = Literal["once", "recurring", "cron"]

_DELTA_RE = re.compile(r"^\s*(?P<n>\d+)\s*(?P<unit>[smh])\s*$", re.IGNORECASE)
_EVERY_RE = re.compile(r"^\s*every\s+(?P<n>\d+)\s*(?P<unit>[smh])\s*$", re.IGNORECASE)

_UNIT_TO_KW = {"s": "seconds", "m": "minutes", "h": "hours"}


class ScheduleParseError(ValueError):
    """Raised when a schedule string cannot be parsed."""


@dataclass(frozen=True)
class Schedule:
    kind: ScheduleKind
    expr: str
    delta: timedelta = field(default=timedelta())

    def next_run(
        self,
        now: datetime,
        *,
        last_run: datetime | None = None,
    ) -> datetime:
        """Compute the next fire time at or after ``now``."""
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        if self.kind == "once":
            return now + self.delta
        if self.kind == "recurring":
            base = last_run if last_run is not None else now
            if base.tzinfo is None:
                base = base.replace(tzinfo=timezone.utc)
            return base + self.delta
        return _next_cron(self.expr, now)


def parse_schedule(expr: str) -> Schedule:
    """Parse ``expr`` into a :class:`Schedule`.

    Accepts the one-shot delta, ``every N<unit>`` recurring, or a
    5-field cron. Raises :class:`ScheduleParseError` on unknown syntax.
    """
    if not expr or not expr.strip():
        raise ScheduleParseError("empty schedule expression")

    every = _EVERY_RE.match(expr)
    if every:
        n = int(every.group("n"))
        unit = every.group("unit").lower()
        return Schedule(
            kind="recurring",
            expr=expr,
            delta=timedelta(**{_UNIT_TO_KW[unit]: n}),
        )

    delta = _DELTA_RE.match(expr)
    if delta:
        n = int(delta.group("n"))
        unit = delta.group("unit").lower()
        return Schedule(
            kind="once",
            expr=expr,
            delta=timedelta(**{_UNIT_TO_KW[unit]: n}),
        )

    fields = expr.split()
    if len(fields) == 5:
        for f in fields:
            if f != "*" and not re.match(r"^\d+(,\d+)*$", f):
                raise ScheduleParseError(
                    f"only integers and '*' are supported in classic cron "
                    f"scaffold; got field {f!r}"
                )
        return Schedule(kind="cron", expr=expr)

    raise ScheduleParseError(f"unrecognised schedule expression: {expr!r}")


def _match_cron_field(field: str, value: int) -> bool:
    if field == "*":
        return True
    return value in {int(x) for x in field.split(",")}


def _next_cron(expr: str, now: datetime) -> datetime:
    """Minimal classic-cron ``next_run`` for the scaffold.

    Steps minute-by-minute up to one year ahead. Good enough for
    hourly/daily jobs which is what ``0 9 * * *`` style expressions
    target. Richer algorithms can slot in behind the same signature.
    """
    minute_f, hour_f, dom_f, month_f, dow_f = expr.split()
    cur = now.replace(second=0, microsecond=0) + timedelta(minutes=1)

    for _ in range(60 * 24 * 366):
        if (
            _match_cron_field(minute_f, cur.minute)
            and _match_cron_field(hour_f, cur.hour)
            and _match_cron_field(dom_f, cur.day)
            and _match_cron_field(month_f, cur.month)
            and _match_cron_field(dow_f, cur.isoweekday() % 7)
        ):
            return cur
        cur += timedelta(minutes=1)

    raise ScheduleParseError(
        f"no upcoming run within 1 year for cron expression {expr!r}"
    )
