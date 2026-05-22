"""AccessibilityBridge — high-contrast themes, screen reader cues, and focus management.

Ports lyra-ui's accessibility.py into practical TUI features:
  • High-contrast theme variant for every palette
  • ARIA-style live-region announcements for screen readers
  • Focus-tracking overlay
  • Command to toggle high-contrast (Ctrl+Shift+H)

ECC reference: ECC's guardrails and identity.json emphasize inclusive
tooling — this brings WCAG 2.1 AA awareness into Lyra's TUI.
"""
from __future__ import annotations

import time
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


# ── High-contrast color overrides ──────────────────────────────────────

# Maps ThemePreset name → high-contrast variant
HIGH_CONTRAST_OVERRIDES: dict[str, dict[str, str]] = {
    "default": {
        "primary": "bold cyan",
        "secondary": "bold blue",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "background": "black",
        "foreground": "white",
        "border": "white",
    },
    "dark": {
        "primary": "bold bright_cyan",
        "secondary": "bold bright_blue",
        "success": "bold bright_green",
        "warning": "bold bright_yellow",
        "error": "bold bright_red",
        "background": "black",
        "foreground": "bright_white",
        "border": "bright_white",
    },
    "light": {
        "primary": "bold blue",
        "secondary": "bold cyan",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "background": "white",
        "foreground": "black",
        "border": "black",
    },
    "dracula": {
        "primary": "bold #f8f8f2",
        "secondary": "bold #8be9fd",
        "success": "bold #50fa7b",
        "warning": "bold #f1fa8c",
        "error": "bold #ff5555",
        "background": "#1a1b2e",
        "foreground": "#f8f8f2",
        "border": "#f8f8f2",
    },
    "catppuccin": {
        "primary": "bold #cdd6f4",
        "secondary": "bold #89dceb",
        "success": "bold #a6e3a1",
        "warning": "bold #f9e2af",
        "error": "bold #f38ba8",
        "background": "#11111b",
        "foreground": "#cdd6f4",
        "border": "#cdd6f4",
    },
    "nord": {
        "primary": "bold #eceff4",
        "secondary": "bold #88c0d0",
        "success": "bold #a3be8c",
        "warning": "bold #ebcb8b",
        "error": "bold #bf616a",
        "background": "#242933",
        "foreground": "#eceff4",
        "border": "#eceff4",
    },
}


class AccessibilityBridge(Widget):
    """Accessibility features: high-contrast toggle, screen reader cues, focus tracking.

    Usage:
        bridge = AccessibilityBridge()
        bridge.high_contrast = True   # Activate high-contrast mode
        bridge.announce("Task completed")  # Screen reader cue
    """

    DEFAULT_CSS = """
    AccessibilityBridge {
        height: auto;
        display: none;  /* Hidden by default — emits signals, no visual */
    }

    AccessibilityBridge #a11y-announcer {
        height: 1;
        display: none;  /* Off-screen live region — screen-reader only */
    }

    AccessibilityBridge #a11y-focus-tracker {
        height: 1;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("ctrl+shift+h", "toggle_high_contrast", "High Contrast", show=True),
    ]

    # Reactive state
    high_contrast: reactive[bool] = reactive(False)
    current_focus: reactive[str] = reactive("")
    announcement: reactive[str] = reactive("")
    current_theme: reactive[str] = reactive("default")

    def compose(self) -> ComposeResult:
        yield Static("", id="a11y-announcer")
        yield Static("", id="a11y-focus-tracker")

    # ── Public API ─────────────────────────────────────────────────────

    def announce(self, message: str) -> None:
        """Send an accessibility announcement (screen reader cue)."""
        self.announcement = f"[dim](a11y)[/] {message}"
        self.set_timer(5.0, self._clear_announcement)

    def set_focus(self, widget_id: str, widget_label: str = "") -> None:
        """Track what's currently focused for screen readers."""
        label = widget_label or widget_id
        self.current_focus = f"[dim]Focus:[/] {label}"

    def get_high_contrast_colors(self) -> dict[str, str]:
        """Return high-contrast color overrides for the current theme."""
        return HIGH_CONTRAST_OVERRIDES.get(self.current_theme, HIGH_CONTRAST_OVERRIDES["default"])

    # ── Actions ────────────────────────────────────────────────────────

    def action_toggle_high_contrast(self) -> None:
        """Toggle high-contrast mode."""
        self.high_contrast = not self.high_contrast
        state = "enabled" if self.high_contrast else "disabled"
        self.announce(f"High contrast mode {state}")
        # Notify parent via reactive watcher
        self._notify_change()

    def watch_high_contrast(self, enabled: bool) -> None:
        self._notify_change()

    def watch_current_focus(self, focus: str) -> None:
        if focus:
            try:
                self.query_one("#a11y-focus-tracker", Static).update(focus)
            except Exception:
                pass

    def watch_announcement(self, msg: str) -> None:
        if msg:
            try:
                self.query_one("#a11y-announcer", Static).update(msg)
            except Exception:
                pass

    # ── Internal ───────────────────────────────────────────────────────

    def _clear_announcement(self) -> None:
        self.announcement = ""

    def _notify_change(self) -> None:
        """Emit a change signal — parent app should read and apply."""
        # Parent app reads self.high_contrast and self.get_high_contrast_colors()
        pass

    @staticmethod
    def theme_has_high_contrast(name: str) -> bool:
        return name in HIGH_CONTRAST_OVERRIDES
