"""Contract tests for ``lyra_core.cron.schedule.parse_schedule``.

Hermes exposes three surface forms for scheduling:

1. ``"30m"`` — one-shot delay, fires once.
2. ``"every 1h"`` — recurring, every N h/m/s.
3. ``"0 9 * * *"`` — classic 5-field cron.

The parser returns a :class:`Schedule` with ``kind`` plus enough
information to compute ``next_run(now)``.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lyra_core.cron.schedule import (
    ScheduleParseError,
    parse_schedule,
)


def test_one_shot_minutes() -> None:
    s = parse_schedule("30m")
    assert s.kind == "once"
    assert s.delta == timedelta(minutes=30)


def test_one_shot_hours_and_seconds() -> None:
    assert parse_schedule("2h").delta == timedelta(hours=2)
    assert parse_schedule("45s").delta == timedelta(seconds=45)


def test_recurring_every_prefix() -> None:
    s = parse_schedule("every 1h")
    assert s.kind == "recurring"
    assert s.delta == timedelta(hours=1)

    s2 = parse_schedule("every 15m")
    assert s2.kind == "recurring"
    assert s2.delta == timedelta(minutes=15)


def test_classic_cron_five_field() -> None:
    s = parse_schedule("0 9 * * *")
    assert s.kind == "cron"
    assert s.expr == "0 9 * * *"


def test_empty_rejected() -> None:
    with pytest.raises(ScheduleParseError):
        parse_schedule("")


def test_bad_unit_rejected() -> None:
    with pytest.raises(ScheduleParseError):
        parse_schedule("5z")


def test_next_run_one_shot_is_delta_from_now() -> None:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    s = parse_schedule("30m")
    assert s.next_run(now) == now + timedelta(minutes=30)


def test_next_run_recurring_is_delta_from_now_then_from_last() -> None:
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    s = parse_schedule("every 10m")
    first = s.next_run(now)
    assert first == now + timedelta(minutes=10)

    second = s.next_run(first, last_run=first)
    assert second == first + timedelta(minutes=10)


def test_next_run_classic_cron_9am_daily() -> None:
    """``0 9 * * *`` at 08:59 UTC → next run is today 09:00 UTC."""
    now = datetime(2026, 1, 1, 8, 59, tzinfo=timezone.utc)
    s = parse_schedule("0 9 * * *")
    nxt = s.next_run(now)
    assert nxt == datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)


def test_next_run_classic_cron_rollover_to_next_day() -> None:
    now = datetime(2026, 1, 1, 9, 1, tzinfo=timezone.utc)
    s = parse_schedule("0 9 * * *")
    nxt = s.next_run(now)
    assert nxt == datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc)
