"""Tests for the automation engine."""

from __future__ import annotations

import time

from lyra_cli.autonomy.automation_engine import AutomationEngine, Schedule, ScheduleKind


class TestAutomationEngine:
    """Suite: AutomationEngine scheduling and firing."""

    def test_add_recurring_schedule(self) -> None:
        engine = AutomationEngine()
        calls: list[str] = []

        def cb() -> None:
            calls.append("fired")

        engine.add_recurring("test_rec", 0.01, cb)
        assert engine.pending_count() == 1

        time.sleep(0.02)
        fired = engine.run_once()
        assert "test_rec" in fired
        assert len(calls) >= 1

    def test_add_one_shot_removes_after_fire(self) -> None:
        engine = AutomationEngine()
        calls: list[str] = []

        def cb() -> None:
            calls.append("fired")

        engine.add_one_shot("test_os", cb, delay=0.0)
        assert engine.pending_count() == 1

        fired = engine.run_once()
        assert "test_os" in fired
        assert len(calls) == 1
        # One-shot should be removed after fire
        assert engine.pending_count() == 0

    def test_remove_schedule(self) -> None:
        engine = AutomationEngine()
        engine.add_recurring("removable", 10.0, lambda: None)
        assert engine.remove_schedule("removable") is True
        assert engine.remove_schedule("nonexistent") is False
        assert engine.pending_count() == 0

    def test_run_once_fires_multiple_due(self) -> None:
        engine = AutomationEngine()
        fired_ids: list[str] = []

        def make_cb(sid: str):
            def cb() -> None:
                fired_ids.append(sid)

            return cb

        engine.add_one_shot("a", make_cb("a"), delay=0.0)
        engine.add_one_shot("b", make_cb("b"), delay=0.0)

        result = engine.run_once()
        assert set(result) == {"a", "b"}
        assert set(fired_ids) == {"a", "b"}

    def test_stop_flag(self) -> None:
        engine = AutomationEngine()
        assert engine.is_running is False
        engine.add_recurring("r", 60.0, lambda: None)
        engine.run_once()
        engine.stop()
        assert engine.is_running is False

    def test_schedule_kind_enum(self) -> None:
        assert ScheduleKind.ONE_SHOT.value == "one_shot"
        assert ScheduleKind.RECURRING.value == "recurring"

    def test_schedule_jitter_produces_different_values(self) -> None:
        schedule = Schedule(
            id="jitter_test",
            kind=ScheduleKind.ONE_SHOT,
            interval_seconds=100.0,
            callback=lambda: None,
        )
        # Multiple calls should yield different jitter
        values = {schedule.compute_next_run(1000.0) for _ in range(5)}
        # With jitter fraction 0.1 and interval 100s, values should differ
        assert len(values) > 1, "Jitter should produce different next_run values"
