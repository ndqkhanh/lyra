"""Unit tests for ProcessTab renderer (pure logic, no Textual)."""
from __future__ import annotations

import time

import pytest

from lyra_core.transparency.models import AgentProcess
from lyra_cli.tui_v2.sidebar.process_tab import _render_processes, _spark, _fmt_cost


def _make_proc(**kwargs) -> AgentProcess:
    defaults = dict(
        pid=1, session_id="test-session-id", project_path="/tmp",
        state="running", current_tool="Bash",
        context_tokens=50000, context_limit=200000, context_pct=0.25,
        tokens_in=40000, tokens_out=10000, cost_usd=0.05,
        elapsed_s=42.0, parent_session_id="", children=(),
        last_event_at=time.time(),
    )
    defaults.update(kwargs)
    return AgentProcess(**defaults)


@pytest.mark.unit
def test_render_empty() -> None:
    result = _render_processes([])
    assert "no agents" in result


@pytest.mark.unit
def test_render_single_running() -> None:
    proc = _make_proc(state="running")
    result = _render_processes([proc])
    assert "1 active" in result
    assert "session-id" in result


@pytest.mark.unit
def test_render_blocked_shows_warning() -> None:
    proc = _make_proc(state="blocked")
    result = _render_processes([proc])
    assert "blocked" in result


@pytest.mark.unit
def test_spark_low_pct() -> None:
    bar = _spark(0.3)
    assert "green" in bar
    assert "30%" in bar


@pytest.mark.unit
def test_spark_high_pct() -> None:
    bar = _spark(0.95)
    assert "red" in bar


@pytest.mark.unit
def test_fmt_cost_small() -> None:
    assert "<$0.001" in _fmt_cost(0.0)


@pytest.mark.unit
def test_fmt_cost_normal() -> None:
    assert "$0.050" in _fmt_cost(0.05)
