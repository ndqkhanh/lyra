"""Tests for agent_panel.render_agent_panel."""
from __future__ import annotations

import time

from lyra_cli.interactive.agent_panel import _fmt_elapsed, _fmt_tokens, render_agent_panel
from lyra_cli.interactive.status_source import SubAgentRecord


def _rec(
    agent_id: str = "a1",
    role: str = "general-purpose",
    desc: str = "running task",
    state: str = "running",
    tokens: int = 0,
) -> SubAgentRecord:
    return SubAgentRecord(
        agent_id=agent_id,
        role=role,
        description=desc,
        started_at=time.monotonic(),
        tokens_down=tokens,
        state=state,
    )


# ---- render_agent_panel -----------------------------------------------------


def test_empty_returns_empty():
    assert render_agent_panel([]) == []


def test_active_agent_uses_active_icon():
    r = _rec(state="running")
    lines = render_agent_panel([r], now=r.started_at + 5)
    assert lines[0].startswith(_fmt_elapsed.__module__ and "⏺")


def test_active_icon_is_bullet():
    r = _rec(state="running")
    lines = render_agent_panel([r], now=r.started_at)
    assert lines[0].startswith("⏺")


def test_done_agent_uses_idle_icon():
    r = _rec(state="done")
    lines = render_agent_panel([r], now=r.started_at + 5)
    assert lines[0].startswith("◯")


def test_error_agent_uses_idle_icon():
    r = _rec(state="error")
    lines = render_agent_panel([r], now=r.started_at + 5)
    assert lines[0].startswith("◯")


def test_elapsed_under_60s_shown_in_line():
    r = _rec()
    lines = render_agent_panel([r], now=r.started_at + 45)
    assert "45s" in lines[0]


def test_elapsed_over_60s_shown_in_line():
    r = _rec()
    lines = render_agent_panel([r], now=r.started_at + 184)
    assert "3m 4s" in lines[0]


def test_token_count_under_1000():
    r = _rec(tokens=500)
    lines = render_agent_panel([r], now=r.started_at)
    assert "↓ 500 tokens" in lines[0]


def test_token_count_over_1000_formatted():
    r = _rec(tokens=63600)
    lines = render_agent_panel([r], now=r.started_at)
    assert "63.6k" in lines[0]


def test_description_truncated_at_40_chars():
    long_desc = "A" * 50
    r = _rec(desc=long_desc)
    lines = render_agent_panel([r], now=r.started_at)
    assert "A" * 40 in lines[0]
    assert "A" * 41 not in lines[0]


def test_short_description_not_padded():
    r = _rec(desc="short")
    lines = render_agent_panel([r], now=r.started_at)
    assert "short" in lines[0]


def test_role_appears_in_line():
    r = _rec(role="executor")
    lines = render_agent_panel([r], now=r.started_at)
    assert "executor" in lines[0]


def test_multiple_agents_produce_multiple_lines():
    recs = [_rec("a1"), _rec("a2"), _rec("a3")]
    now = recs[0].started_at + 10
    lines = render_agent_panel(recs, now=now)
    assert len(lines) == 3


def test_line_contains_separator():
    r = _rec()
    lines = render_agent_panel([r], now=r.started_at + 5)
    assert "·" in lines[0]


# ---- _fmt_elapsed -----------------------------------------------------------


def test_fmt_elapsed_zero():
    assert _fmt_elapsed(0) == "0s"


def test_fmt_elapsed_under_60():
    assert _fmt_elapsed(30) == "30s"
    assert _fmt_elapsed(59) == "59s"


def test_fmt_elapsed_exactly_60():
    assert _fmt_elapsed(60) == "1m 0s"


def test_fmt_elapsed_over_60():
    assert _fmt_elapsed(184) == "3m 4s"
    assert _fmt_elapsed(3661) == "61m 1s"


# ---- _fmt_tokens ------------------------------------------------------------


def test_fmt_tokens_zero():
    assert _fmt_tokens(0) == "0"


def test_fmt_tokens_under_1000():
    assert _fmt_tokens(999) == "999"


def test_fmt_tokens_exactly_1000():
    assert _fmt_tokens(1000) == "1.0k"


def test_fmt_tokens_1500():
    assert _fmt_tokens(1500) == "1.5k"


def test_fmt_tokens_large():
    assert _fmt_tokens(63600) == "63.6k"
