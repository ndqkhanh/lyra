"""Port of lyra-ui tests/test_accessibility.py → tests TUI accessibility_bridge.py.

Verifies AccessibilityBridge, high-contrast toggles, screen reader cues.
"""
from __future__ import annotations

import pytest

pytest.importorskip("textual", reason="requires textual")


def test_a11y_bridge_init():
    from lyra_cli.tui_v2.widgets.accessibility_bridge import AccessibilityBridge
    bridge = AccessibilityBridge()
    assert bridge is not None
    assert bridge.high_contrast is False


def test_a11y_toggle():
    from lyra_cli.tui_v2.widgets.accessibility_bridge import AccessibilityBridge
    bridge = AccessibilityBridge()
    bridge.action_toggle_high_contrast()
    assert bridge.high_contrast is True
    bridge.action_toggle_high_contrast()
    assert bridge.high_contrast is False


def test_a11y_announce():
    from lyra_cli.tui_v2.widgets.accessibility_bridge import AccessibilityBridge
    bridge = AccessibilityBridge()
    bridge.announce("Test announcement")
    assert "Test announcement" in bridge.announcement


def test_a11y_set_focus():
    from lyra_cli.tui_v2.widgets.accessibility_bridge import AccessibilityBridge
    bridge = AccessibilityBridge()
    bridge.set_focus("#test-button", "Test Button")
    assert "Test Button" in bridge.current_focus


def test_high_contrast_overrides():
    from lyra_cli.tui_v2.widgets.accessibility_bridge import (
        HIGH_CONTRAST_OVERRIDES, AccessibilityBridge,
    )
    assert "default" in HIGH_CONTRAST_OVERRIDES
    assert "dracula" in HIGH_CONTRAST_OVERRIDES
    assert "catppuccin" in HIGH_CONTRAST_OVERRIDES

    bridge = AccessibilityBridge()
    overrides = bridge.get_high_contrast_colors()
    assert isinstance(overrides, dict)


def test_theme_has_high_contrast():
    from lyra_cli.tui_v2.widgets.accessibility_bridge import (
        AccessibilityBridge,
    )
    assert AccessibilityBridge.theme_has_high_contrast("dracula") is True
    assert AccessibilityBridge.theme_has_high_contrast("nonexistent") is False


def test_a11y_watch():
    from lyra_cli.tui_v2.widgets.accessibility_bridge import AccessibilityBridge
    bridge = AccessibilityBridge()
    # Check that setting reactive triggers watcher without error
    bridge.current_focus = "#test"
    bridge.announcement = "hello"
    bridge.high_contrast = True
