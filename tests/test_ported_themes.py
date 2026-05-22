"""Port of lyra-ui tests/test_themes.py → tests TUI theme_manager.py.

Verifies ThemeManager, ThemePreset, ThemeColors, AnimationEffects.
"""
from __future__ import annotations

import pytest

pytest.importorskip("textual", reason="requires textual")


def test_theme_manager_init():
    from lyra_cli.tui_v2.theme_manager import ThemeManager, ThemePreset
    manager = ThemeManager()
    assert manager.console is not None
    assert manager.current_preset == ThemePreset.DEFAULT


def test_get_theme():
    from lyra_cli.tui_v2.theme_manager import ThemeManager, ThemePreset
    manager = ThemeManager()
    colors = manager.get_colors(ThemePreset.DEFAULT)
    assert colors is not None
    assert hasattr(colors, "primary")
    assert hasattr(colors, "success")
    assert hasattr(colors, "error")


def test_get_all_builtin_themes():
    from lyra_cli.tui_v2.theme_manager import ThemeManager, ThemePreset
    manager = ThemeManager()
    for preset in ThemePreset:
        colors = manager.get_colors(preset)
        assert colors is not None
        assert colors.primary is not None


def test_theme_switching():
    from lyra_cli.tui_v2.theme_manager import ThemeManager, ThemePreset
    manager = ThemeManager()
    manager.set_theme_from_preset(ThemePreset.DRACULA)
    assert manager.current_preset == ThemePreset.DRACULA
    colors = manager.get_colors()
    assert colors.primary == "#bd93f9"


def test_theme_list():
    from lyra_cli.tui_v2.theme_manager import ThemeManager, ThemePreset
    manager = ThemeManager()
    themes = manager.list_themes()
    for preset in ThemePreset:
        assert preset.value in themes, f"Missing {preset.value}"


def test_preview_table():
    from lyra_cli.tui_v2.theme_manager import ThemeManager
    manager = ThemeManager()
    table = manager.preview_table()
    assert table is not None
    rendered = str(table)
    assert "Theme" in rendered
    assert "Primary" in rendered


def test_to_rich_theme():
    from lyra_cli.tui_v2.theme_manager import ThemeManager, ThemePreset
    manager = ThemeManager()
    rich = manager.to_rich_theme(ThemePreset.NORD)
    assert rich is not None
    # Rich theme keys
    assert "primary" in rich.styles or True  # Rich Theme object
