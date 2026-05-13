"""Tests for observability/live_display.py (Phase 3 — Live Transparency Panel)."""
from __future__ import annotations

import pytest

from lyra_core.observability.event_bus import (
    CronJobFired,
    DaemonIteration,
    EventBus,
    LLMCallFinished,
    LLMCallStarted,
    PermissionDecision,
    StopHookFired,
    SubagentFinished,
    SubagentSpawned,
    ToolCallBlocked,
    ToolCallFinished,
    ToolCallStarted,
)
from lyra_core.observability.live_display import (
    DisplayState,
    LiveDisplay,
    build_layout,
    render_agent_table,
    render_event_log,
    render_header,
    render_stats,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _state(**kwargs) -> DisplayState:
    return DisplayState(**kwargs)


def _llm_started(session="s1", model="claude", turn=1) -> LLMCallStarted:
    return LLMCallStarted(session_id=session, model=model, prompt_tokens=100, turn=turn)


def _llm_finished(session="s1", inp=500, out=200, cache=300, ms=1000.0) -> LLMCallFinished:
    return LLMCallFinished(session_id=session, input_tokens=inp, output_tokens=out,
                           cache_read_tokens=cache, duration_ms=ms)


def _tool_started(session="s1", name="bash") -> ToolCallStarted:
    return ToolCallStarted(session_id=session, tool_name=name, args_preview="ls")


def _tool_finished(session="s1", name="bash", ms=420.0, err=False) -> ToolCallFinished:
    return ToolCallFinished(session_id=session, tool_name=name, duration_ms=ms, is_error=err)


# ---------------------------------------------------------------------------
# DisplayState — LLM events
# ---------------------------------------------------------------------------


def test_state_on_llm_started_sets_model():
    state = _state()
    state.on_event(_llm_started(model="gpt-4o"))
    assert state.model == "gpt-4o"


def test_state_on_llm_started_creates_agent_row():
    state = _state()
    state.on_event(_llm_started(session="s1"))
    assert "s1" in state.agents


def test_state_on_llm_started_updates_turn():
    state = _state()
    state.on_event(_llm_started(session="s1", turn=5))
    assert state.agents["s1"].current_step == 5


def test_state_on_llm_finished_accumulates_tokens():
    state = _state()
    state.on_event(_llm_started())
    state.on_event(_llm_finished(inp=500, out=200, cache=300))
    state.on_event(_llm_finished(inp=200, out=100, cache=100))
    assert state.token_in_total == 700
    assert state.token_out_total == 300
    assert state.cache_hit_total == 400


# ---------------------------------------------------------------------------
# DisplayState — tool events
# ---------------------------------------------------------------------------


def test_state_tool_started_adds_event():
    state = _state()
    state.on_event(_tool_started())
    assert len(state.events) == 1
    assert state.events[0].status == "running"
    assert state.events[0].name == "bash"


def test_state_tool_finished_updates_event():
    state = _state()
    state.on_event(_llm_started())
    state.on_event(_tool_started(name="read"))
    state.on_event(_tool_finished(name="read", ms=100.0))
    entry = next(e for e in state.events if e.name == "read")
    assert entry.status == "done"
    assert entry.duration_ms == pytest.approx(100.0)


def test_state_tool_error_increments_counter():
    state = _state()
    state.on_event(_tool_started())
    state.on_event(_tool_finished(err=True))
    assert state.tool_error_count == 1


def test_state_tool_blocked_increments_block_count():
    state = _state()
    state.on_event(ToolCallBlocked(session_id="s1", tool_name="rm", reason="destructive"))
    assert state.hook_block_count == 1


def test_state_event_log_max_size():
    state = _state()
    for i in range(12):
        state.on_event(ToolCallStarted(session_id="s", tool_name=f"t{i}", args_preview=""))
    assert len(state.events) == DisplayState.MAX_EVENTS


# ---------------------------------------------------------------------------
# DisplayState — subagent events
# ---------------------------------------------------------------------------


def test_state_subagent_spawned_adds_row():
    state = _state()
    state.on_event(SubagentSpawned(session_id="s", agent_id="a1", agent_role="planner"))
    assert "a1" in state.agents
    assert state.agents["a1"].agent_role == "planner"


def test_state_subagent_finished_updates_status():
    state = _state()
    state.on_event(SubagentSpawned(session_id="s", agent_id="a1", agent_role="evaluator"))
    state.on_event(SubagentFinished(session_id="s", agent_id="a1", status="done", cost_usd=0.05))
    assert state.agents["a1"].status == "done"


# ---------------------------------------------------------------------------
# DisplayState — misc events
# ---------------------------------------------------------------------------


def test_state_stop_hook_sets_status():
    state = _state()
    state.on_event(_llm_started(session="s1"))
    state.on_event(StopHookFired(session_id="s1", reason="budget"))
    assert state.agents["s1"].status == "stopped"


def test_state_permission_decision_updates_mode():
    state = _state()
    state.on_event(PermissionDecision(session_id="s", tool_name="bash", decision="ALLOWED",
                                       mode="plan"))
    assert state.permission_mode == "plan"


def test_state_daemon_iteration_updates_counter():
    state = _state()
    state.on_event(DaemonIteration(iteration=7))
    assert state.daemon_iteration == 7


def test_state_cron_job_fired_updates_last_job():
    state = _state()
    state.on_event(CronJobFired(job_name="daily_retro"))
    assert state.cron_last_job == "daily_retro"


# ---------------------------------------------------------------------------
# Health score
# ---------------------------------------------------------------------------


def test_health_score_perfect():
    state = _state()
    # no errors, high cache = high health
    state.on_event(_llm_finished(inp=1000, out=200, cache=900))
    score = state.health_score()
    assert 0.0 <= score <= 1.0


def test_health_score_degrades_on_errors():
    state = _state()
    for _ in range(10):
        state.on_event(_tool_started())
        state.on_event(_tool_finished(err=True))
    score_bad = state.health_score()
    assert score_bad < 0.7


def test_burn_rate_positive():
    state = _state()
    state.on_event(_llm_finished(inp=600, out=200, cache=0))
    rate = state.burn_rate_per_min()
    assert rate > 0


# ---------------------------------------------------------------------------
# Rich rendering — smoke tests (just ensure no exceptions)
# ---------------------------------------------------------------------------


def test_render_header_no_error():
    state = _state(session_id="s1")
    panel = render_header(state)
    assert panel is not None


def test_render_agent_table_empty():
    state = _state()
    panel = render_agent_table(state)
    assert panel is not None


def test_render_agent_table_with_row():
    state = _state()
    state.on_event(_llm_started(session="s1"))
    panel = render_agent_table(state)
    assert panel is not None


def test_render_event_log_empty():
    state = _state()
    panel = render_event_log(state)
    assert panel is not None


def test_render_event_log_with_entries():
    state = _state()
    state.on_event(_tool_started(name="read"))
    panel = render_event_log(state)
    assert panel is not None


def test_render_stats_no_error():
    state = _state()
    state.on_event(_llm_finished(inp=500, out=100, cache=200))
    panel = render_stats(state)
    assert panel is not None


def test_build_layout_no_error():
    state = _state(session_id="sess")
    state.on_event(_llm_started())
    state.on_event(_tool_started())
    layout = build_layout(state)
    assert layout is not None


# ---------------------------------------------------------------------------
# LiveDisplay construction
# ---------------------------------------------------------------------------


def test_live_display_constructs():
    bus = EventBus()
    display = LiveDisplay(bus=bus, session_id="test")
    assert display.state.session_id == "test"


def test_live_display_drains_queue():
    bus = EventBus()
    display = LiveDisplay(bus=bus)
    bus.subscribe(display._queue)
    bus.emit(_tool_started())
    display._drain_queue()
    assert len(display.state.events) == 1
