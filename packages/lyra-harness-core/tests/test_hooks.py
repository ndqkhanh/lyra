"""Tests for expanded hook system: 50+ events, watchdog, crash-loop detection."""
from __future__ import annotations

import time

import pytest

from lyra_harness_core.hooks import (
    Hook,
    HookDecision,
    HookEvent,
    HookExecution,
    HookHealth,
    HookRegistry,
    HookStats,
    HookWatchdog,
)
from lyra_harness_core.messages import ToolCall


# ---------------------------------------------------------------------------
# HookEvent — 50+ events across 12+ categories
# ---------------------------------------------------------------------------


def test_hook_event_count():
    """We have 50+ events (the original 3 plus 47+ new)."""
    assert len(HookEvent) >= 50, f"Expected 50+ events, got {len(HookEvent)}"


def test_hook_event_original_three_preserved():
    """Original 3 events kept for backward compatibility."""
    assert HookEvent.PRE_TOOL_USE == "PreToolUse"
    assert HookEvent.POST_TOOL_USE == "PostToolUse"
    assert HookEvent.STOP == "Stop"


def test_hook_event_by_category():
    cats = HookEvent.by_category()
    assert "session" in cats
    assert "tool" in cats
    assert "memory" in cats
    assert "subagent" in cats
    assert "fleet" in cats
    assert HookEvent.SESSION_STARTED in cats["session"]
    assert HookEvent.MEMORY_WRITE in cats["memory"]
    assert HookEvent.PRE_TOOL_USE in cats["tool"]


def test_hook_event_str_values():
    """All events have distinct, meaningful string values."""
    values = {e.value for e in HookEvent}
    assert len(values) == len(HookEvent), "All event values must be unique"


# ---------------------------------------------------------------------------
# HookWatchdog
# ---------------------------------------------------------------------------


class TestHookWatchdog:
    def test_initial_health_is_healthy(self):
        wd = HookWatchdog()
        assert wd.health("any") == HookHealth.HEALTHY

    def test_single_failure_not_degraded(self):
        wd = HookWatchdog()
        wd.record("h1", False)
        for _ in range(5):
            wd.record("h1", True)
        # 1 failure out of 6 = ~17% < 20% threshold
        assert wd.health("h1") == HookHealth.HEALTHY

    def test_high_failure_rate_degraded(self):
        wd = HookWatchdog()
        wd.record("h1", False)
        wd.record("h1", False)  # 2 failures
        for _ in range(4):
            wd.record("h1", True)
        # 2 failures out of 6 = 33% > 20%, but < 3 failures so not UNSTABLE
        assert wd.health("h1") == HookHealth.DEGRADED

    def test_three_failures_unstable(self):
        wd = HookWatchdog()
        wd.record("h1", False)
        wd.record("h1", False)
        wd.record("h1", False)
        assert wd.health("h1") == HookHealth.UNSTABLE

    def test_five_failures_disabled(self):
        wd = HookWatchdog()
        for _ in range(5):
            wd.record("h1", False)
        assert wd.health("h1") == HookHealth.DISABLED

    def test_is_disabled(self):
        wd = HookWatchdog()
        assert not wd.is_disabled("h1")
        for _ in range(5):
            wd.record("h1", False)
        assert wd.is_disabled("h1")

    def test_reset_clears_history(self):
        wd = HookWatchdog()
        for _ in range(5):
            wd.record("h1", False)
        wd.reset("h1")
        assert wd.health("h1") == HookHealth.HEALTHY

    def test_prune_removes_old_entries(self):
        wd = HookWatchdog(window_seconds=0.0)  # expire immediately
        wd.record("h1", False)
        wd.record("h1", False)
        wd.record("h1", False)
        # All entries pruned because window is 0
        assert wd.health("h1") == HookHealth.HEALTHY

    def test_multiple_hooks_independent(self):
        wd = HookWatchdog()
        for _ in range(5):
            wd.record("bad", False)
        wd.record("good", True)
        assert wd.is_disabled("bad")
        assert not wd.is_disabled("good")


# ---------------------------------------------------------------------------
# HookRegistry — backward compatibility
# ---------------------------------------------------------------------------


class TestHookRegistryBackwardCompat:
    """Original 5 tests from the 3-event API still pass."""

    def test_hook_fires_on_event(self):
        fired = []

        def handler(call, result):
            fired.append(call.name)
            return HookDecision()

        r = HookRegistry()
        r.register(Hook("log", HookEvent.PRE_TOOL_USE, matcher="*", handler=handler))
        r.run(HookEvent.PRE_TOOL_USE, ToolCall(id="c1", name="foo"))
        assert fired == ["foo"]

    def test_hook_matcher_filters_by_tool_name(self):
        fired = []

        def handler(call, result):
            fired.append(call.name)
            return HookDecision()

        r = HookRegistry()
        r.register(Hook("only-edit", HookEvent.PRE_TOOL_USE, matcher="edit", handler=handler))
        r.run(HookEvent.PRE_TOOL_USE, ToolCall(id="c1", name="read"))
        r.run(HookEvent.PRE_TOOL_USE, ToolCall(id="c2", name="edit"))
        assert fired == ["edit"]

    def test_hook_can_block(self):
        def deny(call, result):
            return HookDecision(block=True, reason="not allowed")

        r = HookRegistry()
        r.register(Hook("deny", HookEvent.PRE_TOOL_USE, matcher="*", handler=deny))
        d = r.run(HookEvent.PRE_TOOL_USE, ToolCall(id="c1", name="foo"))
        assert d.block is True
        assert "not allowed" in d.reason

    def test_registering_hook_without_handler_raises(self):
        r = HookRegistry()
        with pytest.raises(ValueError, match="no handler"):
            r.register(Hook("bad", HookEvent.PRE_TOOL_USE))

    def test_hook_event_is_scoped(self):
        calls = []

        def h(call, result):
            calls.append(call.name)
            return HookDecision()

        r = HookRegistry()
        r.register(Hook("post", HookEvent.POST_TOOL_USE, matcher="*", handler=h))
        r.run(HookEvent.PRE_TOOL_USE, ToolCall(id="c1", name="x"))
        r.run(HookEvent.POST_TOOL_USE, ToolCall(id="c2", name="x"))
        assert calls == ["x"]


# ---------------------------------------------------------------------------
# HookRegistry — new features
# ---------------------------------------------------------------------------


class TestHookRegistryNew:
    def test_hook_count_and_list(self):
        r = HookRegistry()
        assert r.hook_count == 0
        r.register(Hook("a", HookEvent.SESSION_STARTED, handler=lambda c, r: HookDecision()))
        r.register(Hook("b", HookEvent.SESSION_ENDED, handler=lambda c, r: HookDecision()))
        assert r.hook_count == 2
        assert r.list_hooks() == ["a", "b"]

    def test_unregister(self):
        r = HookRegistry()
        r.register(Hook("a", HookEvent.SESSION_STARTED, handler=lambda c, r: HookDecision()))
        r.unregister("a")
        assert r.hook_count == 0

    def test_hooks_for_event(self):
        r = HookRegistry()
        r.register(Hook("a", HookEvent.SESSION_STARTED, handler=lambda c, r: HookDecision()))
        r.register(Hook("b", HookEvent.SESSION_ENDED, handler=lambda c, r: HookDecision()))
        assert len(r.hooks_for_event(HookEvent.SESSION_STARTED)) == 1
        assert r.hooks_for_event(HookEvent.SESSION_STARTED)[0].name == "a"

    def test_run_generic_dispatches_to_handler(self):
        received = []

        def handler(ctx):
            received.append(ctx)
            return HookDecision()

        r = HookRegistry()
        r.register(Hook("gen", HookEvent.SESSION_STARTED, handler=handler))
        ctx: dict[str, object] = {"session_id": "s1"}
        r.run_generic(HookEvent.SESSION_STARTED, ctx)
        assert received == [ctx]

    def test_run_generic_can_block(self):
        def handler(ctx):
            return HookDecision(block=True, reason="blocked")

        r = HookRegistry()
        r.register(Hook("blocker", HookEvent.SAFETY_VIOLATION, handler=handler))
        d = r.run_generic(HookEvent.SAFETY_VIOLATION, {"violation": "test"})
        assert d.block is True

    def test_run_generic_skips_disabled_hooks(self):
        r = HookRegistry()
        r.register(Hook("bad", HookEvent.SESSION_STARTED, handler=lambda ctx: HookDecision()))
        for _ in range(5):
            r.watchdog.record("bad", False)
        received = []

        def handler(ctx):
            received.append(ctx)
            return HookDecision()

        r.register(Hook("ok", HookEvent.SESSION_STARTED, handler=handler))
        r.run_generic(HookEvent.SESSION_STARTED, {"x": 1})
        # "bad" is disabled, "ok" should still fire
        assert received == [{"x": 1}]

    def test_stats(self):
        r = HookRegistry()
        r.register(Hook("a", HookEvent.SESSION_STARTED, handler=lambda ctx: HookDecision()))
        r.run_generic(HookEvent.SESSION_STARTED, {})
        s = r.stats()
        assert s.total_executions == 1
        assert s.total_errors == 0
        assert s.success_rate == 1.0

    def test_stats_tracks_blocks(self):
        r = HookRegistry()
        r.register(Hook("b", HookEvent.PRE_TOOL_USE, handler=lambda c, r: HookDecision(block=True, reason="nope")))
        r.run(HookEvent.PRE_TOOL_USE, ToolCall(id="c1", name="x"))
        s = r.stats()
        assert s.total_executions == 1
        assert s.total_blocks == 1

    def test_disabled_hooks_list(self):
        r = HookRegistry()
        r.register(Hook("a", HookEvent.SESSION_STARTED, handler=lambda ctx: HookDecision()))
        r.register(Hook("b", HookEvent.SESSION_STARTED, handler=lambda ctx: HookDecision()))
        for _ in range(5):
            r.watchdog.record("b", False)
        assert r.disabled_hooks() == ["b"]

    def test_reset_watchdog_all(self):
        r = HookRegistry()
        r.register(Hook("a", HookEvent.SESSION_STARTED, handler=lambda ctx: HookDecision()))
        for _ in range(5):
            r.watchdog.record("a", False)
        assert r.disabled_hooks() == ["a"]
        r.reset_watchdog()
        assert r.disabled_hooks() == []

    def test_reset_watchdog_specific(self):
        r = HookRegistry()
        r.register(Hook("a", HookEvent.SESSION_STARTED, handler=lambda ctx: HookDecision()))
        r.register(Hook("b", HookEvent.SESSION_STARTED, handler=lambda ctx: HookDecision()))
        for _ in range(5):
            r.watchdog.record("a", False)
            r.watchdog.record("b", False)
        r.reset_watchdog("a")
        assert r.disabled_hooks() == ["b"]

    def test_timeout_detection(self):
        """Hook that runs too long is skipped but doesn't crash the chain."""

        def slow(call, result):
            time.sleep(0.15)
            return HookDecision()

        def fast(call, result):
            return HookDecision(annotation="fast ran")

        r = HookRegistry(default_timeout=0.05)
        r.register(Hook("slow", HookEvent.PRE_TOOL_USE, handler=slow, timeout_seconds=0.05))
        r.register(Hook("fast", HookEvent.PRE_TOOL_USE, handler=fast))
        d = r.run(HookEvent.PRE_TOOL_USE, ToolCall(id="c1", name="x"))
        assert "fast ran" in d.annotation  # fast still ran after slow timed out

    def test_exception_in_handler_doesnt_crash_chain(self):
        def explode(call, result):
            raise RuntimeError("boom")

        def ok(call, result):
            return HookDecision(annotation="ok ran")

        r = HookRegistry()
        r.register(Hook("explode", HookEvent.PRE_TOOL_USE, handler=explode))
        r.register(Hook("ok", HookEvent.PRE_TOOL_USE, handler=ok))
        d = r.run(HookEvent.PRE_TOOL_USE, ToolCall(id="c1", name="x"))
        assert "ok ran" in d.annotation


# ---------------------------------------------------------------------------
# HookExecution & HookStats
# ---------------------------------------------------------------------------


class TestHookStats:
    def test_hook_stats_defaults(self):
        s = HookStats()
        assert s.total_executions == 0
        assert s.total_blocks == 0
        assert s.total_timeouts == 0
        assert s.total_errors == 0
        assert s.success_rate == 1.0

    def test_hook_stats_error_tracking(self):
        s = HookStats(
            total_executions=10,
            total_errors=3,
        )
        assert s.success_rate == 0.7


class TestHookExecution:
    def test_hook_execution_record(self):
        now = time.monotonic()
        he = HookExecution(
            hook_name="test",
            event=HookEvent.PRE_TOOL_USE,
            started_at=now,
            finished_at=now + 0.1,
            success=True,
        )
        assert he.hook_name == "test"
        assert he.success is True


# ---------------------------------------------------------------------------
# Annotation combination
# ---------------------------------------------------------------------------


def test_annotations_combine_across_hooks():
    def h1(call, result):
        return HookDecision(annotation="first")

    def h2(call, result):
        return HookDecision(annotation="second")

    r = HookRegistry()
    r.register(Hook("h1", HookEvent.PRE_TOOL_USE, handler=h1))
    r.register(Hook("h2", HookEvent.PRE_TOOL_USE, handler=h2))
    d = r.run(HookEvent.PRE_TOOL_USE, ToolCall(id="c1", name="x"))
    assert "first" in d.annotation
    assert "second" in d.annotation
