"""Port of lyra-ui tests/test_formatter.py → tests TUI theme_manager.py.
"""
from __future__ import annotations

import pytest


def test_formatter_colors():
    from lyra_cli.tui_v2.theme_manager import ThemeColors
    colors = ThemeColors(
        primary="#7C3AED", secondary="#06B6D4", accent="#F59E0B",
        success="#10B981", warning="#F59E0B", error="#EF4444",
        info="#3B82F6",
    )
    assert colors.primary == "#7C3AED"
    assert colors.secondary == "#06B6D4"
    assert colors.accent == "#F59E0B"
    assert colors.success == "#10B981"


def test_formatter_colors_defaults():
    from lyra_cli.tui_v2.theme_manager import ThemeColors
    colors = ThemeColors()
    assert colors.primary == "cyan"
    assert colors.success == "green"
    assert colors.error == "red"


def test_animation_effects():
    from lyra_cli.tui_v2.theme_manager import AnimationEffects
    anim = AnimationEffects()
    assert anim is not None
    anim.success_animation("Test")
    anim.error_animation("Test")
    anim.pulse_effect("Test")


def test_threshold_colour():
    from lyra_cli.tui_v2.theme_manager import threshold_colour
    assert "green" in threshold_colour(25.0)
    assert "yellow" in threshold_colour(65.0)
    assert "orange1" in threshold_colour(85.0)
    assert "red" in threshold_colour(99.0)
