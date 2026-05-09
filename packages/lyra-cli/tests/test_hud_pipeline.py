"""Phase 6i — HUD pipeline + widget unit tests."""

from __future__ import annotations

import pytest

from lyra_cli.hud import HudState, available_presets, load_preset, render
from lyra_cli.hud.testing import sample_state, strip_ansi
from lyra_cli.hud.widgets import widget_names
from lyra_cli.hud.width import column_width, pad_to_columns, truncate_to_columns

# ---------------------------------------------------------------------------
# width.py
# ---------------------------------------------------------------------------


def test_column_width_ascii() -> None:
    assert column_width("hello world") == 11


def test_column_width_cjk_doubles_each_char() -> None:
    # Each Han character occupies 2 columns.
    assert column_width("漢字") == 4
    assert column_width("hi漢bye") == 7  # 2 + 2 + 3


def test_column_width_combining_marks_are_zero() -> None:
    # 'a' + COMBINING ACUTE ACCENT renders as one column wide.
    assert column_width("a\u0301") == 1


def test_truncate_to_columns_appends_ellipsis() -> None:
    out = truncate_to_columns("hello world", 8)
    assert column_width(out) <= 8
    assert out.endswith("…")


def test_truncate_returns_input_when_under_budget() -> None:
    assert truncate_to_columns("short", 100) == "short"


def test_pad_to_columns_left_aligns_default() -> None:
    out = pad_to_columns("hi", 5)
    assert out == "hi   "
    assert column_width(out) == 5


def test_pad_to_columns_right_align() -> None:
    assert pad_to_columns("hi", 5, align="right") == "   hi"


def test_pad_to_columns_rejects_wide_fillchar() -> None:
    with pytest.raises(ValueError):
        pad_to_columns("hi", 10, fillchar="漢")


# ---------------------------------------------------------------------------
# config.py
# ---------------------------------------------------------------------------


def test_available_presets_returns_known_names() -> None:
    presets = set(available_presets())
    assert {"minimal", "compact", "full", "inline"} <= presets


def test_load_preset_unknown_raises_value_error() -> None:
    with pytest.raises(ValueError, match="unknown HUD preset"):
        load_preset("not-a-real-preset")


def test_full_preset_lists_known_widgets() -> None:
    cfg = load_preset("full")
    registered = set(widget_names())
    for w in cfg.widgets:
        assert w in registered, f"preset 'full' references unknown widget {w!r}"


def test_inline_preset_is_single_line_capable() -> None:
    cfg = load_preset("inline")
    assert cfg.max_width <= 100  # narrow enough for a tmux status bar
    assert "identity_line" in cfg.widgets


# ---------------------------------------------------------------------------
# pipeline.render
# ---------------------------------------------------------------------------


def test_render_full_preset_includes_all_widget_lines() -> None:
    out = render(sample_state(), config=load_preset("full"))
    plain = strip_ansi(out)
    # Each widget contributes a line; sample_state populates everything.
    for marker in (
        "lyra",
        "ctx",
        "USD",
        "tools:",
        "agents:",
        "todos:",
        "git:",
        "cache:",
        "tracer:",
    ):
        assert marker in plain, f"'full' preset missing {marker!r} in output"


def test_render_minimal_preset_only_shows_identity() -> None:
    out = render(sample_state(), config=load_preset("minimal"))
    plain = strip_ansi(out)
    assert "lyra" in plain
    # Other widgets must NOT show up.
    for marker in ("ctx", "tools:", "agents:", "todos:", "git:"):
        assert marker not in plain


def test_render_omits_empty_widgets() -> None:
    """Widgets that have nothing to show (no git, no cache, no tools)
    should produce zero lines, not blank lines."""
    state = HudState(
        session_id="empty-session",
        mode="ask",
        model="anthropic:claude-3-5-sonnet",
        # everything else default — no tools, no agents, no todos, no git, no cache.
    )
    out = render(state, config=load_preset("full"))
    plain = strip_ansi(out)

    # Identity is always shown.
    assert "lyra" in plain
    # These widgets ought to be absent because their state is empty.
    for missing in ("tools:", "agents:", "todos:", "git:", "cache:", "tracer:"):
        assert missing not in plain, f"empty widget {missing!r} leaked into output"


def test_render_unknown_widget_in_config_renders_clear_error(monkeypatch) -> None:
    from lyra_cli.hud.config import HudConfig

    bad_cfg = HudConfig(name="bad", widgets=("identity_line", "no_such_widget"))
    out = render(sample_state(), config=bad_cfg)
    plain = strip_ansi(out)
    assert "unknown widget" in plain
    assert "'no_such_widget'" in plain


def test_render_respects_max_width_truncation() -> None:
    """Each rendered line should be ≤ max_width columns wide."""
    out = render(sample_state(), config=load_preset("full"), max_width=40)
    for line in strip_ansi(out).splitlines():
        assert column_width(line) <= 40, (
            f"line exceeded width cap: {line!r} → {column_width(line)} cols"
        )


# ---------------------------------------------------------------------------
# Specific widget assertions
# ---------------------------------------------------------------------------


def test_context_bar_shows_percentage() -> None:
    state = HudState(context_used=50_000, context_max=200_000)
    out = render(state, config=load_preset("compact"))
    assert "25%" in strip_ansi(out)


def test_usage_line_omits_burn_when_zero() -> None:
    state = HudState(cost_usd=0.5, burn_usd_per_hour=0.0)
    out = render(state, config=load_preset("compact"))
    plain = strip_ansi(out)
    assert "$0.500 USD" in plain
    assert "burn" not in plain


def test_todos_line_glyph_per_status() -> None:
    state = sample_state(
        todos=[
            ("a", "pending"),
            ("b", "in_progress"),
            ("c", "completed"),
            ("d", "cancelled"),
        ],
    )
    out = render(state, config=load_preset("full"))
    plain = strip_ansi(out)
    # All 4 todo glyphs present:
    for glyph in ("○", "◐", "●", "✕"):
        assert glyph in plain, f"todos_line missing glyph {glyph!r}"


def test_git_line_shows_clean_when_no_dirty() -> None:
    state = sample_state(git_branch="main", git_dirty_count=0)
    out = render(state, config=load_preset("full"))
    plain = strip_ansi(out)
    assert "git:" in plain
    assert "clean" in plain


def test_git_line_hidden_when_not_a_repo() -> None:
    state = sample_state(git_branch="", git_dirty_count=-1)
    out = render(state, config=load_preset("full"))
    assert "git:" not in strip_ansi(out)
