"""Phase 5 — AgentsTab render helpers (pure, no Textual app required)."""
from __future__ import annotations

import pytest

from lyra_cli.tui_v2.sidebar.agents_tab import (
    _fmt_elapsed,
    _humanise_tokens,
    _infer_agent_type,
    _render_agents,
    _truncate,
)


# ---- unit helpers ----

def test_infer_general_purpose():
    assert _infer_agent_type("session-abc-123") == "general-purpose"


def test_infer_executor():
    assert _infer_agent_type("lyra-executor-99") == "executor"


def test_infer_planner():
    assert _infer_agent_type("planner-session") == "planner"


def test_fmt_elapsed_seconds_only():
    assert _fmt_elapsed(45) == "45s"


def test_fmt_elapsed_minutes():
    assert _fmt_elapsed(184) == "3m 04s"


def test_humanise_tokens_small():
    assert _humanise_tokens(500) == "500"


def test_humanise_tokens_k():
    assert _humanise_tokens(63_600) == "63.6k"


def test_truncate_short():
    assert _truncate("hello", 10) == "hello"


def test_truncate_long():
    result = _truncate("a" * 50, 10)
    assert len(result) == 10
    assert result.endswith("…")


# ---- _render_agents ----

class _FakeProc:
    def __init__(self, session_id="sess-1", tool="Read file", elapsed=184.0, tokens_out=63600):
        self.session_id = session_id
        self.current_tool = tool
        self.elapsed_s = elapsed
        self.tokens_out = tokens_out
        self.state = "running"


def test_render_empty_shows_no_agents_message():
    result = _render_agents([], 0)
    assert "no background agents" in result


def test_render_includes_main_header():
    procs = [_FakeProc()]
    result = _render_agents(procs, 0)
    assert "main" in result
    assert "↑/↓" in result


def test_render_includes_elapsed():
    procs = [_FakeProc(elapsed=184.0)]
    result = _render_agents(procs, 0)
    assert "3m 04s" in result


def test_render_includes_token_count():
    procs = [_FakeProc(tokens_out=63_600)]
    result = _render_agents(procs, 0)
    assert "63.6k" in result


def test_render_selected_uses_filled_dot():
    procs = [_FakeProc(), _FakeProc(session_id="sess-2")]
    result = _render_agents(procs, selected_idx=0)
    # First proc is selected — should have ⏺
    lines = result.split("\n")
    agent_lines = [l for l in lines if "◯" in l or "⏺" in l]
    assert any("⏺" in l for l in agent_lines)


def test_render_max_8_agents():
    procs = [_FakeProc(session_id=f"s{i}") for i in range(12)]
    result = _render_agents(procs, 0)
    # Count ◯ or ⏺ dot occurrences — should be ≤ 8 agent rows
    agent_row_count = result.count("◯") + result.count("⏺") - 1  # -1 for header ⏺
    assert agent_row_count <= 8
