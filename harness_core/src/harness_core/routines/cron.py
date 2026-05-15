"""Minimal cron-expression parser for routine schedules.

Supports the common 5-field crontab subset: ``minute hour day-of-month month day-of-week``.
Each field accepts:

    * ``*`` — wildcard
    * integer literal (e.g. ``5``)
    * comma list (``1,3,5``)
    * range (``1-5``)
    * step (``*/15`` or ``0-59/5``)

Doesn't aim to be a complete cron implementation — this is enough for routine
scheduling without external deps. Production deployments that need full cron
semantics (special strings like ``@hourly``, complex day-of-week rules) wire
``croniter`` through the same :func:`next_fire_after` interface.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Optional


class CronParseError(ValueError):
    """Raised when a cron expression cannot be parsed."""


# Field bounds: (min, max).
_FIELD_BOUNDS = [
    (0, 59),  # minute
    (0, 23),  # hour
    (1, 31),  # day-of-month
    (1, 12),  # month
    (0, 6),   # day-of-week (0 = Sunday)
]
_FIELD_NAMES = ["minute", "hour", "day", "month", "weekday"]


@dataclass(frozen=True)
class CronExpression:
    """Parsed cron expression — five sets of allowed values."""

    raw: str
    minute: frozenset[int]
    hour: frozenset[int]
    day: frozenset[int]
    month: frozenset[int]
    weekday: frozenset[int]

    def matches_dt(self, dt: _dt.datetime) -> bool:
        """True if ``dt`` matches this cron expression at minute granularity."""
        # Standard cron: minute, hour, day-of-month, month, day-of-week.
        # day-of-month + day-of-week are OR'd when *both* are restricted, AND'd
        # otherwise. We use OR-when-both-restricted to match crontab(5).
        weekday = dt.weekday()  # Mon=0..Sun=6 in Python
        cron_weekday = (weekday + 1) % 7  # cron uses Sun=0..Sat=6

        m_ok = dt.minute in self.minute
        h_ok = dt.hour in self.hour
        mo_ok = dt.month in self.month
        # day-of-month and day-of-week handling:
        dom_restricted = self.day != frozenset(range(1, 32))
        dow_restricted = self.weekday != frozenset(range(0, 7))
        dom_ok = dt.day in self.day
        dow_ok = cron_weekday in self.weekday
        if dom_restricted and dow_restricted:
            day_ok = dom_ok or dow_ok
        else:
            day_ok = dom_ok and dow_ok
        return m_ok and h_ok and mo_ok and day_ok


def _parse_field(spec: str, *, lo: int, hi: int) -> frozenset[int]:
    """Parse one cron field into the set of allowed integers.

    Supports wildcards, lists, ranges, steps. Raises :class:`CronParseError`
    on malformed input.
    """
    if not spec or not spec.strip():
        raise CronParseError(f"empty field")

    out: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            raise CronParseError(f"empty field part in {spec!r}")

        step = 1
        # Step component (e.g., "*/5" or "1-10/2").
        if "/" in part:
            base, step_str = part.split("/", 1)
            try:
                step = int(step_str)
            except ValueError:
                raise CronParseError(f"invalid step {step_str!r} in {part!r}")
            if step <= 0:
                raise CronParseError(f"step must be > 0, got {step}")
            part = base or "*"

        if part == "*":
            start, end = lo, hi
        elif "-" in part:
            try:
                start_str, end_str = part.split("-", 1)
                start = int(start_str)
                end = int(end_str)
            except ValueError:
                raise CronParseError(f"invalid range {part!r}")
        else:
            try:
                start = end = int(part)
            except ValueError:
                raise CronParseError(f"invalid literal {part!r}")

        if start < lo or end > hi or start > end:
            raise CronParseError(
                f"field out of range [{lo}, {hi}]: got {start}-{end}"
            )
        for v in range(start, end + 1, step):
            out.add(v)

    return frozenset(out)


def parse_cron(expr: str) -> CronExpression:
    """Parse a 5-field cron expression.

    >>> parse_cron("*/15 * * * *").minute == frozenset({0, 15, 30, 45})
    True
    >>> parse_cron("0 9-17 * * 1-5").hour == frozenset(range(9, 18))
    True
    """
    if not expr or not expr.strip():
        raise CronParseError("empty expression")
    parts = expr.strip().split()
    if len(parts) != 5:
        raise CronParseError(
            f"expected 5 fields (minute hour day month weekday); got {len(parts)}"
        )
    parsed: list[frozenset[int]] = []
    for part, name, (lo, hi) in zip(parts, _FIELD_NAMES, _FIELD_BOUNDS):
        try:
            parsed.append(_parse_field(part, lo=lo, hi=hi))
        except CronParseError as exc:
            raise CronParseError(f"{name}: {exc}") from exc

    return CronExpression(
        raw=expr.strip(),
        minute=parsed[0],
        hour=parsed[1],
        day=parsed[2],
        month=parsed[3],
        weekday=parsed[4],
    )


def next_fire_after(
    expr: str,
    *,
    after: float,
    horizon_minutes: int = 60 * 24 * 31,
) -> Optional[float]:
    """Find the next time ``expr`` matches after the given timestamp.

    Walks forward minute-by-minute up to ``horizon_minutes`` (default 31 days).
    Returns None if no match within the horizon. ``after`` is epoch seconds.
    """
    cron = parse_cron(expr)
    base = _dt.datetime.utcfromtimestamp(after)
    # Round up to the next minute.
    base = base.replace(second=0, microsecond=0)
    if _dt.datetime.utcfromtimestamp(after) > base:
        base += _dt.timedelta(minutes=1)
    else:
        base += _dt.timedelta(minutes=1)

    for i in range(horizon_minutes):
        candidate = base + _dt.timedelta(minutes=i)
        if cron.matches_dt(candidate):
            return candidate.replace(tzinfo=_dt.timezone.utc).timestamp()
    return None


__all__ = ["CronExpression", "CronParseError", "next_fire_after", "parse_cron"]
