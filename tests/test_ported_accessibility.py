"""Port of lyra-ui tests/test_accessibility.py → tests TUI accessibility_bridge.py.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.textual


def test_bridge_init():
    from lyra_cli.tui_v2.widgets.accessibility_bridge import AccessibilityBridge
    bridge = AccessibilityBridge()
    assert bridge.high_contrast is False
    assert bridge.current_focus == ""
    assert bridge.announcement == ""


def test_toggle_high_contrast():
    from lyra_cli.tui_v2.widgets.accessibility_bridge import AccessibilityBridge
    bridge = AccessibilityBridge()
    bridge.action_toggle_high_contrast()
    assert bridge.high_contrast is True
    bridge.action_toggle_high_contrast()
    assert bridge.high_contrast is False


def test_announce():
    from lyra_cli.tui_v2.widgets.accessibility_bridge import AccessibilityBridge
    bridge = AccessibilityBridge()
    bridge.announce("Test message")
    assert "Test message" in bridge.announcement


def test_set_focus():
    from lyra_cli.tui_v2.widgets.accessibility_bridge import AccessibilityBridge
    bridge = AccessibilityBridge()
    bridge.set_focus("#btn", "Submit Button")
    assert "Submit Button" in bridge.current_focus


def test_high_contrast_overrides_dict():
    from lyra_cli.tui_v2.widgets.accessibility_bridge import HIGH_CONTRAST_OVERRIDES
    assert "default" in HIGH_CONTRAST_OVERRIDES
    assert "dark" in HIGH_CONTRAST_OVERRIDES
    assert "light" in HIGH_CONTRAST_OVERRIDES
    assert "dracula" in HIGH_CONTRAST_OVERRIDES
    assert "catppuccin" in HIGH_CONTRAST_OVERRIDES
    assert "nord" in HIGH_CONTRAST_OVERRIDES


def test_get_high_contrast_colors():
    from lyra_cli.tui_v2.widgets.accessibility_bridge import AccessibilityBridge
    bridge = AccessibilityBridge()
    bridge.current_theme = "dracula"
    colors = bridge.get_high_contrast_colors()
    assert isinstance(colors, dict)
    assert "primary" in colors
    assert "foreground" in colors


def test_theme_has_high_contrast():
    from lyra_cli.tui_v2.widgets.accessibility_bridge import AccessibilityBridge
    assert AccessibilityBridge.theme_has_high_contrast("dracula") is True
    assert AccessibilityBridge.theme_has_high_contrast("catppuccin") is True
    assert AccessibilityBridge.theme_has_high_contrast("unknown") is False


def test_watchers_no_crash():
    from lyra_cli.tui_v2.widgets.accessibility_bridge import AccessibilityBridge
    bridge = AccessibilityBridge()
    bridge.current_focus = "#test"
    bridge.announcement = "hello"
    bridge.high_contrast = True


def test_high_contrast_keys():
    from lyra_cli.tui_v2.widgets.accessibility_bridge import HIGH_CONTRAST_OVERRIDES
    for theme, overrides in HIGH_CONTRAST_OVERRIDES.items():
        assert "primary" in overrides
        assert "foreground" in overrides
        assert "background" in overrides
        assert "border" in overrides
