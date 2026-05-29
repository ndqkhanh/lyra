"""Port of lyra-ui tests/test_keyboard.py → tests TUI keybinding patterns.
"""
from __future__ import annotations


def test_mode_glyph_map():
    from lyra_cli.tui_v2.widgets.status_bar_enhanced import _MODE_GLYPH
    assert "edit_automatically" in _MODE_GLYPH
    assert "plan" in _MODE_GLYPH
    assert "ask" in _MODE_GLYPH
    assert "debug" in _MODE_GLYPH
    assert "research" in _MODE_GLYPH
    assert len(_MODE_GLYPH) >= 6


def test_status_bar_init():
    from lyra_cli.tui_v2.widgets.status_bar_enhanced import StatusBarEnhancedWidget
    sb = StatusBarEnhancedWidget()
    assert sb.mode == "edit_automatically"
    assert sb.model == ""
    assert sb.turn == 0
    assert sb.tokens_used == 0


def test_status_bar_update():
    from lyra_cli.tui_v2.widgets.status_bar_enhanced import StatusBarEnhancedWidget
    sb = StatusBarEnhancedWidget()
    sb.update(mode="research", model="gpt-4o", turn=5, tokens_used=10000)
    assert sb.mode == "research"
    assert sb.model == "gpt-4o"
    assert sb.turn == 5
    assert sb.tokens_used == 10000


def test_status_bar_truncate():
    from lyra_cli.tui_v2.widgets.status_bar_enhanced import StatusBarEnhancedWidget
    assert StatusBarEnhancedWidget._truncate("short", 50) == "short"
    result = StatusBarEnhancedWidget._truncate("a" * 100, 20)
    assert len(result) <= 20
    assert result.startswith("…")


def test_status_bar_build_segments():
    from lyra_cli.tui_v2.widgets.status_bar_enhanced import StatusBarEnhancedWidget
    sb = StatusBarEnhancedWidget()
    sb.update(mode="plan", model="deepseek-chat", turn=7, tokens_used=50000, tokens_max=200000)
    segments = sb._build_segments()
    assert len(segments) >= 3
    assert any("plan" in s for s in segments)
    assert any("deepseek" in s for s in segments)
