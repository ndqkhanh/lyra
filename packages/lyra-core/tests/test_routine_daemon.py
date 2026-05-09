"""Tests for RoutineDaemon — drives RoutineRegistry on schedule."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lyra_core.cron import RoutineDaemon, RoutineFiring
from lyra_core.cron.routines import (
    CronTrigger,
    GitHubWebhookTrigger,
    HttpApiTrigger,
    Routine,
    RoutineRegistry,
)


class _MockClock:
    """Deterministic clock for tests."""

    def __init__(self, start: datetime):
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, *, seconds: int = 0, minutes: int = 0, hours: int = 0) -> None:
        self.now += timedelta(seconds=seconds, minutes=minutes, hours=hours)


def _make_registry_with_routine(*, expression: str = "every 1m"):
    reg = RoutineRegistry()
    fired_payloads: list[dict] = []

    def workflow(name: str, payload: dict):
        fired_payloads.append({"name": name, "payload": payload})

    reg.register_workflow("daily-feed", workflow)
    reg.register_routine(
        Routine(name="x.daily", trigger=CronTrigger(expression=expression), workflow="daily-feed")
    )
    return reg, fired_payloads


# ---- schedule + tick basics -----------------------------------------


def test_daemon_initial_schedule_seeded():
    clock = _MockClock(datetime(2026, 5, 9, 9, 0, tzinfo=timezone.utc))
    reg, _ = _make_registry_with_routine()
    d = RoutineDaemon(registry=reg, clock=clock)
    d._refresh_schedule()
    snap = d.schedule_snapshot()
    assert "x.daily" in snap
    assert snap["x.daily"]["next_run"] is not None


def test_daemon_skips_non_cron_triggers():
    reg = RoutineRegistry()
    reg.register_workflow("noop", lambda *_: None)
    reg.register_routine(
        Routine(name="webhook.x", trigger=GitHubWebhookTrigger(repo="o/r", events=("push",)), workflow="noop")
    )
    reg.register_routine(
        Routine(name="api.x", trigger=HttpApiTrigger(path="/x"), workflow="noop")
    )
    d = RoutineDaemon(registry=reg)
    d._refresh_schedule()
    snap = d.schedule_snapshot()
    # Both present, but neither has a next_run because they aren't cron.
    assert snap["webhook.x"]["next_run"] is None
    assert snap["api.x"]["next_run"] is None


def test_daemon_tick_fires_when_next_run_elapsed():
    clock = _MockClock(datetime(2026, 5, 9, 9, 0, tzinfo=timezone.utc))
    reg, fired = _make_registry_with_routine(expression="every 1m")
    d = RoutineDaemon(registry=reg, clock=clock)
    # First tick — schedule seeded, but now == next_run, so it fires immediately.
    n = d.tick_once()
    # The seed sets next_run = now + 1m, so first tick does not fire.
    assert n == 0
    # Advance the clock past the next-run.
    clock.advance(minutes=2)
    n = d.tick_once()
    assert n == 1
    assert len(fired) == 1
    assert fired[0]["name"] == "x.daily"


def test_daemon_records_firings():
    clock = _MockClock(datetime(2026, 5, 9, 9, 0, tzinfo=timezone.utc))
    reg, _ = _make_registry_with_routine(expression="every 1m")
    d = RoutineDaemon(registry=reg, clock=clock)
    d.tick_once()
    clock.advance(minutes=2)
    d.tick_once()
    assert len(d.firings) == 1
    f = d.firings[0]
    assert isinstance(f, RoutineFiring)
    assert f.routine_name == "x.daily"
    assert f.error is None


def test_daemon_records_workflow_error():
    """Workflow that raises is caught + recorded; daemon continues."""
    clock = _MockClock(datetime(2026, 5, 9, 9, 0, tzinfo=timezone.utc))
    reg = RoutineRegistry()

    def boom(name: str, payload: dict):
        raise RuntimeError("workflow exploded")

    reg.register_workflow("explode", boom)
    reg.register_routine(
        Routine(name="x.fail", trigger=CronTrigger(expression="every 1m"), workflow="explode")
    )
    d = RoutineDaemon(registry=reg, clock=clock)
    d.tick_once()
    clock.advance(minutes=2)
    d.tick_once()
    assert len(d.firings) == 1
    assert d.firings[0].error is not None
    assert "workflow exploded" in d.firings[0].error


def test_daemon_advances_next_run_after_firing():
    clock = _MockClock(datetime(2026, 5, 9, 9, 0, tzinfo=timezone.utc))
    reg, _ = _make_registry_with_routine(expression="every 1m")
    d = RoutineDaemon(registry=reg, clock=clock)
    d.tick_once()
    initial_next = d._next_run["x.daily"]
    clock.advance(minutes=2)
    d.tick_once()
    new_next = d._next_run["x.daily"]
    assert new_next > initial_next


# ---- multiple routines ----------------------------------------------


def test_daemon_multiple_routines_independent_schedules():
    clock = _MockClock(datetime(2026, 5, 9, 9, 0, tzinfo=timezone.utc))
    reg = RoutineRegistry()
    counts = {"fast": 0, "slow": 0}

    reg.register_workflow("fast", lambda n, p: counts.__setitem__("fast", counts["fast"] + 1))
    reg.register_workflow("slow", lambda n, p: counts.__setitem__("slow", counts["slow"] + 1))
    reg.register_routine(Routine(name="r.fast", trigger=CronTrigger(expression="every 1m"), workflow="fast"))
    reg.register_routine(Routine(name="r.slow", trigger=CronTrigger(expression="every 5m"), workflow="slow"))

    d = RoutineDaemon(registry=reg, clock=clock)
    d.tick_once()
    # Advance 2m — only "fast" fires.
    clock.advance(minutes=2)
    d.tick_once()
    assert counts["fast"] == 1
    assert counts["slow"] == 0
    # Advance 4 more minutes (total 6m) — both should have fired.
    clock.advance(minutes=4)
    d.tick_once()
    assert counts["slow"] >= 1


def test_daemon_unparseable_expression_skipped():
    clock = _MockClock(datetime(2026, 5, 9, 9, 0, tzinfo=timezone.utc))
    reg = RoutineRegistry()
    reg.register_workflow("noop", lambda *_: None)
    reg.register_routine(
        Routine(name="x.bad", trigger=CronTrigger(expression="not a real schedule"), workflow="noop")
    )
    d = RoutineDaemon(registry=reg, clock=clock)
    d.tick_once()
    snap = d.schedule_snapshot()
    assert snap["x.bad"]["next_run"] is None


# ---- lifecycle ------------------------------------------------------


def test_daemon_start_stop_threaded():
    """Real-thread test — start, stop, ensure no hang."""
    reg, _ = _make_registry_with_routine(expression="every 1h")
    d = RoutineDaemon(registry=reg, tick_seconds=0.05)
    d.start()
    try:
        # Let it tick a couple of times.
        import time as _t
        _t.sleep(0.2)
    finally:
        d.stop(timeout=2.0)
    assert d._thread is None


def test_daemon_start_twice_raises():
    reg, _ = _make_registry_with_routine(expression="every 1h")
    d = RoutineDaemon(registry=reg, tick_seconds=0.05)
    d.start()
    try:
        with pytest.raises(RuntimeError, match="already running"):
            d.start()
    finally:
        d.stop()


def test_daemon_stop_without_start_safe():
    reg, _ = _make_registry_with_routine()
    d = RoutineDaemon(registry=reg)
    d.stop()  # no-op


# ---- HIR event emission ---------------------------------------------


def test_daemon_emits_hir_event(monkeypatch):
    captured: list = []

    def fake_emit(name: str, /, **attrs):
        captured.append((name, attrs))

    from lyra_core.hir import events
    monkeypatch.setattr(events, "emit", fake_emit)

    clock = _MockClock(datetime(2026, 5, 9, 9, 0, tzinfo=timezone.utc))
    reg, _ = _make_registry_with_routine(expression="every 1m")
    d = RoutineDaemon(registry=reg, clock=clock)
    d.tick_once()
    clock.advance(minutes=2)
    d.tick_once()
    names = [n for n, _ in captured]
    assert "routine.fired" in names
