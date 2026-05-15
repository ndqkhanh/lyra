"""Tests for harness_core.routines — types, cron, registry."""
from __future__ import annotations

import datetime as _dt
import time

import pytest

from harness_core.routines import (
    CronExpression,
    CronParseError,
    FireResult,
    Routine,
    RoutineFire,
    RoutineRegistry,
    TriggerKind,
    next_fire_after,
    parse_cron,
)


# --- types --------------------------------------------------------------


class TestRoutine:
    def test_valid(self):
        r = Routine(routine_id="r1", name="test", handler=lambda *, fire: None)
        assert r.routine_id == "r1"
        assert r.bearer_token  # auto-generated
        assert r.enabled is True

    def test_empty_routine_id_rejected(self):
        with pytest.raises(ValueError):
            Routine(routine_id="", name="x", handler=lambda *, fire: None)

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError):
            Routine(routine_id="r1", name="", handler=lambda *, fire: None)

    def test_empty_token_rejected(self):
        with pytest.raises(ValueError):
            Routine(routine_id="r1", name="x", handler=lambda *, fire: None,
                    bearer_token="")

    def test_authenticates_correct_token(self):
        r = Routine(routine_id="r1", name="x", handler=lambda *, fire: None,
                    bearer_token="secret")
        assert r.authenticates("secret") is True

    def test_authenticates_wrong_token(self):
        r = Routine(routine_id="r1", name="x", handler=lambda *, fire: None,
                    bearer_token="secret")
        assert r.authenticates("wrong") is False

    def test_token_constant_time_compare_handles_different_lengths(self):
        r = Routine(routine_id="r1", name="x", handler=lambda *, fire: None,
                    bearer_token="abc")
        # Different-length tokens shouldn't crash.
        assert r.authenticates("a") is False
        assert r.authenticates("a" * 100) is False


class TestRoutineFire:
    def test_valid(self):
        f = RoutineFire(
            fire_id="f1",
            routine_id="r1",
            triggered_by=TriggerKind.MANUAL,
            triggered_at=time.time(),
        )
        assert f.isolation_key == "f1"

    def test_empty_fire_id_rejected(self):
        with pytest.raises(ValueError):
            RoutineFire(fire_id="", routine_id="r", triggered_by=TriggerKind.MANUAL,
                        triggered_at=0.0)

    def test_negative_timestamp_rejected(self):
        with pytest.raises(ValueError):
            RoutineFire(fire_id="f", routine_id="r",
                        triggered_by=TriggerKind.MANUAL, triggered_at=-1)

    def test_namespace_id_overrides_isolation_key(self):
        f = RoutineFire(
            fire_id="f1", routine_id="r1",
            triggered_by=TriggerKind.MANUAL, triggered_at=0.0,
            namespace_id="custom-ns",
        )
        assert f.isolation_key == "custom-ns"


# --- cron ---------------------------------------------------------------


class TestParseCron:
    def test_wildcard_minute(self):
        c = parse_cron("* * * * *")
        assert c.minute == frozenset(range(60))
        assert c.hour == frozenset(range(24))

    def test_step(self):
        c = parse_cron("*/15 * * * *")
        assert c.minute == frozenset({0, 15, 30, 45})

    def test_range(self):
        c = parse_cron("0 9-17 * * *")
        assert c.hour == frozenset(range(9, 18))

    def test_list(self):
        c = parse_cron("0,30 * * * *")
        assert c.minute == frozenset({0, 30})

    def test_range_with_step(self):
        c = parse_cron("0-30/5 * * * *")
        assert c.minute == frozenset({0, 5, 10, 15, 20, 25, 30})

    def test_weekday_business(self):
        c = parse_cron("0 9 * * 1-5")
        assert c.weekday == frozenset({1, 2, 3, 4, 5})

    def test_invalid_field_count(self):
        with pytest.raises(CronParseError):
            parse_cron("* * * *")
        with pytest.raises(CronParseError):
            parse_cron("* * * * * *")

    def test_invalid_literal(self):
        with pytest.raises(CronParseError):
            parse_cron("abc * * * *")

    def test_out_of_range(self):
        with pytest.raises(CronParseError):
            parse_cron("60 * * * *")  # minute max is 59
        with pytest.raises(CronParseError):
            parse_cron("* 24 * * *")  # hour max is 23

    def test_zero_step_rejected(self):
        with pytest.raises(CronParseError):
            parse_cron("*/0 * * * *")

    def test_empty_expression_rejected(self):
        with pytest.raises(CronParseError):
            parse_cron("")
        with pytest.raises(CronParseError):
            parse_cron("   ")


class TestCronMatchesDt:
    def test_every_minute_matches(self):
        c = parse_cron("* * * * *")
        for hour in (0, 13, 23):
            for minute in (0, 30, 59):
                dt = _dt.datetime(2026, 5, 9, hour, minute, 0)
                assert c.matches_dt(dt)

    def test_specific_time(self):
        c = parse_cron("30 14 * * *")
        assert c.matches_dt(_dt.datetime(2026, 5, 9, 14, 30))
        assert not c.matches_dt(_dt.datetime(2026, 5, 9, 14, 31))
        assert not c.matches_dt(_dt.datetime(2026, 5, 9, 15, 30))

    def test_business_hours(self):
        # Mon-Fri 9-17.
        c = parse_cron("0 9-17 * * 1-5")
        # 2026-05-08 is Friday (Python weekday=4).
        dt = _dt.datetime(2026, 5, 8, 10, 0)
        assert c.matches_dt(dt)
        # Saturday (Python weekday=5 → cron weekday=6) — excluded.
        sat = _dt.datetime(2026, 5, 9, 10, 0)
        assert not c.matches_dt(sat)


class TestNextFireAfter:
    def test_advances_to_next_match(self):
        # 30 14 * * *  fires at 14:30 daily.
        # If now is 2026-05-09 14:00, next fire is 14:30 same day.
        now = _dt.datetime(2026, 5, 9, 14, 0, tzinfo=_dt.timezone.utc).timestamp()
        nxt_ts = next_fire_after("30 14 * * *", after=now)
        assert nxt_ts is not None
        nxt = _dt.datetime.utcfromtimestamp(nxt_ts)
        assert nxt.hour == 14 and nxt.minute == 30

    def test_no_match_returns_none(self):
        # An impossible cron — Feb 30 (only 28/29 days).
        # parse_cron will accept it (1-31 valid range), but Feb 30 never matches.
        # With short horizon, returns None.
        now = _dt.datetime(2026, 1, 1, tzinfo=_dt.timezone.utc).timestamp()
        nxt = next_fire_after("0 0 30 2 *", after=now, horizon_minutes=60)
        assert nxt is None

    def test_advances_past_current_minute(self):
        # If now is exactly the cron time, next fire should be in the future.
        now_dt = _dt.datetime(2026, 5, 9, 14, 30, tzinfo=_dt.timezone.utc)
        nxt_ts = next_fire_after("30 14 * * *", after=now_dt.timestamp())
        assert nxt_ts is not None
        # Next fire is the same time tomorrow.
        nxt = _dt.datetime.utcfromtimestamp(nxt_ts)
        assert (nxt - now_dt.replace(tzinfo=None)).days >= 1


# --- registry -----------------------------------------------------------


class TestRoutineRegistry:
    def _make_handler(self):
        calls = []
        def handler(*, fire):
            calls.append(fire)
            return f"handled {fire.routine_id}"
        return handler, calls

    def test_register_and_get(self):
        registry = RoutineRegistry()
        h, _ = self._make_handler()
        r = Routine(routine_id="r1", name="test", handler=h)
        registry.register(r)
        assert registry.get("r1") is r
        assert registry.get("nonexistent") is None

    def test_register_validates_cron(self):
        registry = RoutineRegistry()
        h, _ = self._make_handler()
        bad = Routine(routine_id="r1", name="x", handler=h, schedule="not cron")
        with pytest.raises(CronParseError):
            registry.register(bad)

    def test_unregister(self):
        registry = RoutineRegistry()
        h, _ = self._make_handler()
        registry.register(Routine(routine_id="r1", name="x", handler=h))
        assert registry.unregister("r1") is True
        assert registry.unregister("r1") is False  # already gone

    def test_list_routines(self):
        registry = RoutineRegistry()
        h, _ = self._make_handler()
        registry.register(Routine(routine_id="r1", name="a", handler=h))
        registry.register(Routine(routine_id="r2", name="b", handler=h, enabled=False))
        assert len(registry.list_routines()) == 2
        assert len(registry.list_routines(enabled_only=True)) == 1

    def test_fire_success(self):
        registry = RoutineRegistry()
        h, calls = self._make_handler()
        r = Routine(routine_id="r1", name="x", handler=h)
        registry.register(r)
        result = registry.fire(
            routine_id="r1",
            triggered_by=TriggerKind.MANUAL,
            token=r.bearer_token,
        )
        assert result.success is True
        assert result.output == "handled r1"
        assert len(calls) == 1
        assert calls[0].triggered_by == TriggerKind.MANUAL

    def test_fire_unknown_routine(self):
        registry = RoutineRegistry()
        result = registry.fire(
            routine_id="missing",
            triggered_by=TriggerKind.MANUAL,
            token="any",
        )
        assert result.success is False
        assert "not found" in result.error

    def test_fire_disabled_routine(self):
        registry = RoutineRegistry()
        h, _ = self._make_handler()
        r = Routine(routine_id="r1", name="x", handler=h, enabled=False)
        registry.register(r)
        result = registry.fire(
            routine_id="r1",
            triggered_by=TriggerKind.MANUAL,
            token=r.bearer_token,
        )
        assert result.success is False
        assert "disabled" in result.error

    def test_fire_invalid_token(self):
        registry = RoutineRegistry()
        h, _ = self._make_handler()
        r = Routine(routine_id="r1", name="x", handler=h)
        registry.register(r)
        result = registry.fire(
            routine_id="r1",
            triggered_by=TriggerKind.MANUAL,
            token="wrong-token",
        )
        assert result.success is False
        assert "invalid token" in result.error

    def test_fire_handler_error_recorded(self):
        registry = RoutineRegistry()
        def failing(*, fire):
            raise RuntimeError("kaboom")
        r = Routine(routine_id="r1", name="x", handler=failing)
        registry.register(r)
        result = registry.fire(
            routine_id="r1",
            triggered_by=TriggerKind.MANUAL,
            token=r.bearer_token,
        )
        assert result.success is False
        assert "RuntimeError" in result.error
        assert "kaboom" in result.error

    def test_fire_payload_threaded_to_handler(self):
        registry = RoutineRegistry()
        captured = {}
        def handler(*, fire):
            captured["payload"] = fire.payload
            return None
        r = Routine(routine_id="r1", name="x", handler=handler)
        registry.register(r)
        registry.fire(
            routine_id="r1",
            triggered_by=TriggerKind.WEBHOOK,
            token=r.bearer_token,
            payload={"event": "push", "ref": "main"},
        )
        assert captured["payload"] == {"event": "push", "ref": "main"}

    def test_history(self):
        registry = RoutineRegistry()
        h, _ = self._make_handler()
        r = Routine(routine_id="r1", name="x", handler=h)
        registry.register(r)
        for _ in range(3):
            registry.fire(routine_id="r1", triggered_by=TriggerKind.MANUAL,
                          token=r.bearer_token)
        history = registry.history(routine_id="r1")
        assert len(history) == 3
        # Most-recent first.
        assert all(h.success for h in history)

    def test_stats(self):
        registry = RoutineRegistry()
        def good(*, fire): return None
        def bad(*, fire): raise RuntimeError()
        registry.register(Routine(routine_id="g", name="g", handler=good))
        registry.register(Routine(routine_id="b", name="b", handler=bad))
        # Use the registered routines' tokens.
        g = registry.get("g")
        b = registry.get("b")
        registry.fire(routine_id="g", triggered_by=TriggerKind.MANUAL,
                      token=g.bearer_token)
        registry.fire(routine_id="b", triggered_by=TriggerKind.CRON,
                      token=b.bearer_token)
        s = registry.stats()
        assert s["routines"] == 2
        assert s["fires_total"] == 2
        assert s["fires_success"] == 1
        assert s["fires_failure"] == 1
        assert s["trigger_manual"] == 1
        assert s["trigger_cron"] == 1


class TestListDue:
    def test_no_cron_routines_no_due(self):
        registry = RoutineRegistry()
        registry.register(Routine(routine_id="r1", name="x",
                                   handler=lambda *, fire: None))  # no schedule
        assert registry.list_due(now=time.time()) == []

    def test_cron_routine_due_after_first_minute(self):
        # "* * * * *" matches every minute — should be due.
        registry = RoutineRegistry()
        h = lambda *, fire: None
        r = Routine(routine_id="r1", name="x", handler=h, schedule="* * * * *")
        registry.register(r)
        # Current time well past registration "last fired" sentinel.
        now = time.time()
        due = registry.list_due(now=now)
        assert any(r.routine_id == "r1" for r in due)

    def test_disabled_routine_not_due(self):
        registry = RoutineRegistry()
        h = lambda *, fire: None
        r = Routine(routine_id="r1", name="x", handler=h,
                    schedule="* * * * *", enabled=False)
        registry.register(r)
        assert registry.list_due(now=time.time()) == []
