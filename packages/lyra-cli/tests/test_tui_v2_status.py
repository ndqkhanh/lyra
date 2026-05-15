"""Contract tests for the v3.14 Phase 3 status-line formatting.

Two layers under test:

  * Pure formatting helpers in :mod:`lyra_cli.tui_v2.status` — exercised
    directly with input/output assertions.
  * ``LyraHarnessApp._handle_event`` overrides — exercised via a stub
    parent (we don't mount a real Textual app; the override is a thin
    layer over the parent's segment writes).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from harness_tui import events as ev

from lyra_cli.tui_v2 import status
from lyra_cli.tui_v2.app import LyraHarnessApp


# ---------------------------------------------------------------------
# Threshold colour
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "pct,expected",
    [
        (0.0, "bold green"),
        (49.9, "bold green"),
        (50.0, "bold yellow"),
        (79.9, "bold yellow"),
        (80.0, "bold orange1"),
        (94.9, "bold orange1"),
        (95.0, "bold red"),
        (100.0, "bold red"),
        (150.0, "bold red"),
    ],
)
def test_threshold_colour_matches_hermes_thresholds(pct: float, expected: str) -> None:
    assert status.threshold_colour(pct) == expected


# ---------------------------------------------------------------------
# Token bar formatting
# ---------------------------------------------------------------------


def test_format_token_bar_zero_usage_renders_empty_bar() -> None:
    out = status.format_token_bar(0, 1000)
    # 20 chars empty
    assert out.count("░") == 20
    assert out.count("█") == 0
    assert "0.0%" in out
    assert "0/1.0K" in out


def test_format_token_bar_half_usage_renders_half_bar_yellow() -> None:
    out = status.format_token_bar(50_000, 100_000)
    assert "50.0%" in out
    assert out.count("█") == 10
    assert out.count("░") == 10
    assert "[bold yellow]" in out  # 50% → yellow


def test_format_token_bar_high_usage_goes_red() -> None:
    out = status.format_token_bar(98_000, 100_000)
    assert "[bold red]" in out


def test_format_token_bar_negative_used_clamps_to_zero() -> None:
    out = status.format_token_bar(-100)
    assert "0.0%" in out


def test_format_token_bar_zero_max_falls_back_to_default() -> None:
    """A ``0`` cap would zero-divide; helper must use the documented default."""
    out = status.format_token_bar(1_000, 0)
    # Default 200k → 1000/200000 = 0.5%
    assert "0.5%" in out


def test_format_token_bar_usage_above_max_caps_at_100() -> None:
    out = status.format_token_bar(500, 100)
    assert "100.0%" in out
    assert out.count("█") == 20


# ---------------------------------------------------------------------
# Repo + turn formatting
# ---------------------------------------------------------------------


def test_format_repo_segment_basename() -> None:
    assert status.format_repo_segment("/Users/k/projects/lyra") == "lyra"
    assert status.format_repo_segment("/Users/k/projects/lyra/") == "lyra"


def test_format_repo_segment_root_and_empty() -> None:
    assert status.format_repo_segment("/") == "/"
    assert status.format_repo_segment("") == "—"


def test_format_turn_segment() -> None:
    assert status.format_turn_segment(0) == "#0"
    assert status.format_turn_segment(7) == "#7"
    assert status.format_turn_segment(-3) == "#0"


def test_humanise_compact_widths() -> None:
    assert status._humanise(0) == "0"
    assert status._humanise(999) == "999"
    assert status._humanise(1_500) == "1.5K"
    assert status._humanise(2_500_000) == "2.5M"
    assert status._humanise(3_400_000_000) == "3.4B"


# ---------------------------------------------------------------------
# LyraHarnessApp event overrides
# ---------------------------------------------------------------------


class _StatusLineStub:
    def __init__(self) -> None:
        self.segments: dict[str, str] = {}
        self.refresh_count = 0

    def set_segment(self, key: str, value: str) -> None:
        self.segments[key] = value
        self.refresh_count += 1


def _build_lyra_app(working_dir: str = "/tmp/lyra-test") -> LyraHarnessApp:
    """Construct a LyraHarnessApp without invoking Textual's expensive
    initialisation. We bypass __init__ to avoid mounting Shell + widgets;
    the tests only exercise the event-handling layer, which is pure.
    """
    app = LyraHarnessApp.__new__(LyraHarnessApp)
    app._turn_index = 0
    cfg = SimpleNamespace(
        name="lyra",
        model="auto",
        working_dir=working_dir,
        transport=SimpleNamespace(name="lyra"),
        extra_payload={},
    )
    app.cfg = cfg
    app.shell = SimpleNamespace(
        status_line=_StatusLineStub(),
        header=SimpleNamespace(session_title="", mode="default", project_name="lyra"),
        chat_log=SimpleNamespace(
            write=lambda *_a, **_kw: None,
            write_user=lambda *_a, **_kw: None,
            write_system=lambda *_a, **_kw: None,
            stream_text=lambda *_a, **_kw: None,
            mount_card=lambda *_a, **_kw: None,
            finalize_turn=lambda *_a, **_kw: None,
        ),
        context_bar=SimpleNamespace(update_budget=lambda **_kw: None),
        subagent_tree=SimpleNamespace(
            upsert=lambda *_a, **_kw: None,
            update_status=lambda *_a, **_kw: None,
        ),
    )
    return app


def test_turn_started_increments_turn_segment() -> None:
    app = _build_lyra_app()
    with patch("harness_tui.app.HarnessApp._handle_event"):
        app._handle_event(ev.TurnStarted(turn_id="t1", user_text="ping"))
        app._handle_event(ev.TurnStarted(turn_id="t2", user_text="pong"))
    assert app.shell.status_line.segments["turn"] == "#2"


def test_turn_finished_replaces_tokens_with_fill_bar() -> None:
    app = _build_lyra_app()
    with patch("harness_tui.app.HarnessApp._handle_event"):
        app._handle_event(
            ev.TurnFinished(
                turn_id="t1", tokens_in=10_000, tokens_out=10_000, cost_usd=0.01
            )
        )
    tokens_seg = app.shell.status_line.segments["tokens"]
    assert "10.0%" in tokens_seg
    assert "█" in tokens_seg  # bar rendered
    # Threshold for 10% is green.
    assert "[bold green]" in tokens_seg


def test_context_budget_event_drives_live_token_bar() -> None:
    app = _build_lyra_app()
    with patch("harness_tui.app.HarnessApp._handle_event"):
        app._handle_event(
            ev.ContextBudget(
                used=160_000, max=200_000, system=0, files=0,
                conversation=0, output=0,
            )
        )
    tokens_seg = app.shell.status_line.segments["tokens"]
    assert "80.0%" in tokens_seg
    assert "[bold orange1]" in tokens_seg  # 80% → orange threshold


def test_negative_token_counts_clamped() -> None:
    """A faulty provider that reports negative tokens must not blow up."""
    app = _build_lyra_app()
    with patch("harness_tui.app.HarnessApp._handle_event"):
        app._handle_event(
            ev.TurnFinished(
                turn_id="t1", tokens_in=-100, tokens_out=-50, cost_usd=0.0
            )
        )
    tokens_seg = app.shell.status_line.segments["tokens"]
    assert "0.0%" in tokens_seg


def test_on_mount_seeds_repo_and_turn_segments(tmp_path) -> None:
    app = _build_lyra_app(working_dir=str(tmp_path / "my-repo"))
    with patch("harness_tui.app.HarnessApp.on_mount"):
        app.on_mount()
    assert app.shell.status_line.segments["repo"] == "my-repo"
    assert app.shell.status_line.segments["turn"] == "#0"
