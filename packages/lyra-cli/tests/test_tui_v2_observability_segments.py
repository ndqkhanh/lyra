"""Tests for Phase 6 observability status segments in tui_v2/status.py."""
from __future__ import annotations

import pytest

from lyra_cli.tui_v2.status import (
    format_daemon_segment,
    format_health_segment,
    format_permission_badge,
    format_tool_card,
)


# ---------------------------------------------------------------------------
# format_health_segment
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "score,expected_color,expected_glyph",
    [
        (1.0, "bold green", "●"),
        (0.7, "bold green", "●"),
        (0.69, "bold yellow", "◐"),
        (0.4, "bold yellow", "◐"),
        (0.39, "bold red", "○"),
        (0.0, "bold red", "○"),
    ],
)
def test_health_segment_colors(score, expected_color, expected_glyph):
    out = format_health_segment(score)
    assert expected_color in out
    assert expected_glyph in out


def test_health_segment_clamps_above_one():
    out = format_health_segment(1.5)
    assert "100%" in out
    assert "bold green" in out


def test_health_segment_clamps_below_zero():
    out = format_health_segment(-0.5)
    assert "0%" in out
    assert "bold red" in out


def test_health_segment_percentage_format():
    out = format_health_segment(0.85)
    assert "85%" in out


# ---------------------------------------------------------------------------
# format_permission_badge
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mode,expected_style",
    [
        ("plan", "bold cyan"),
        ("auto", "bold green"),
        ("ask", "bold yellow"),
        ("agent", "bold magenta"),
    ],
)
def test_permission_badge_known_modes(mode, expected_style):
    out = format_permission_badge(mode)
    assert expected_style in out
    assert mode in out


def test_permission_badge_unknown_mode():
    out = format_permission_badge("custom")
    assert "custom" in out


def test_permission_badge_empty():
    out = format_permission_badge("")
    assert "—" in out


def test_permission_badge_dash():
    out = format_permission_badge("—")
    assert "—" in out


def test_permission_badge_case_insensitive():
    out_lower = format_permission_badge("plan")
    out_upper = format_permission_badge("PLAN")
    # Both should use the plan style
    assert "bold cyan" in out_lower
    assert "bold cyan" in out_upper


# ---------------------------------------------------------------------------
# format_daemon_segment
# ---------------------------------------------------------------------------


def test_daemon_segment_zero_iteration_returns_empty():
    assert format_daemon_segment(0) == ""


def test_daemon_segment_negative_returns_empty():
    assert format_daemon_segment(-1) == ""


def test_daemon_segment_shows_iteration():
    out = format_daemon_segment(5)
    assert "iter=5" in out
    assert "⊙" in out


def test_daemon_segment_shows_last_job():
    out = format_daemon_segment(3, last_job="daily_retro")
    assert "cron=daily_retro" in out


def test_daemon_segment_no_job_when_dash():
    out = format_daemon_segment(3, last_job="—")
    assert "cron=" not in out


def test_daemon_segment_no_job_when_empty():
    out = format_daemon_segment(3, last_job="")
    assert "cron=" not in out


# ---------------------------------------------------------------------------
# format_tool_card
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status,expected_style",
    [
        ("running", "yellow"),
        ("done", "green"),
        ("error", "red"),
        ("blocked", "bold red"),
    ],
)
def test_tool_card_known_statuses(status, expected_style):
    out = format_tool_card("bash", status)
    assert expected_style in out
    assert "bash" in out
    assert "⚙" in out


def test_tool_card_includes_duration():
    out = format_tool_card("read", "done", duration_ms=420.0)
    assert "420ms" in out


def test_tool_card_no_duration_when_none():
    out = format_tool_card("bash", "running", duration_ms=None)
    assert "ms" not in out


def test_tool_card_unknown_status_uses_white():
    out = format_tool_card("custom_tool", "pending")
    assert "custom_tool" in out
    assert "pending" in out


def test_tool_card_includes_tool_name():
    out = format_tool_card("web_search", "done", 1200.0)
    assert "web_search" in out
    assert "1200ms" in out
