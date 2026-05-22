"""EffortAppWidget — TUI interactive effort slider (port of effort_app.py).

Ports the 159-line effort_app.py interactive slider into a TUI widget
that lets the user pick reasoning effort via keyboard (←/→ keys, Enter
to confirm). Shows the full slider with marker position and level label.

Alt+E to toggle (shared with EffortWidget — this is the interactive picker).
"""
from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from ...interactive.effort import EffortPicker, EFFORT_LEVELS


class EffortAppWidget(Widget):
    """Interactive effort slider — ←/→ to adjust, Enter to confirm.

    Shows: effort level axis, track with ▲ marker, level label, hint.
    """

    DEFAULT_CSS = """
    EffortAppWidget {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }
    EffortAppWidget.collapsed { height: 1; border: none; }
    EffortAppWidget #ea-header { height: 1; color: $text-muted; }
    EffortAppWidget #ea-slider { height: auto; margin: 0 0 0 1; }
    """

    BINDINGS = [
        Binding("alt+e", "toggle_effort_app", "Effort Picker"),
        Binding("left", "slider_left", "Decrease", show=False),
        Binding("right", "slider_right", "Increase", show=False),
        Binding("enter", "confirm", "Confirm", show=False),
    ]

    expanded: reactive[bool] = reactive(False)
    level: reactive[str] = reactive("medium")
    cursor: reactive[float] = reactive(0.5)

    def __init__(self):
        super().__init__()
        self._picker = EffortPicker()

    def compose(self) -> ComposeResult:
        yield Static("", id="ea-header")
        yield Static("", id="ea-slider")

    def on_mount(self) -> None:
        self.level = self._picker.value
        self.cursor = float(self._picker.cursor)
        self._render()

    def action_toggle_effort_app(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._render()

    def action_slider_left(self) -> None:
        if self.expanded:
            self._picker.left()
            self.cursor = float(self._picker.cursor)
            self.level = self._picker.value
            self._render()

    def action_slider_right(self) -> None:
        if self.expanded:
            self._picker.right()
            self.cursor = float(self._picker.cursor)
            self.level = self._picker.value
            self._render()

    def action_confirm(self) -> None:
        if self.expanded:
            self._picker.confirm()
            self.expanded = False
            self.toggle_class("collapsed", True)
            self._render()

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            hint = "[dim](alt+e · ←/→)[/]"
            if self.expanded:
                self.query_one("#ea-header", Static).update(
                    f"[bold]Effort Picker[/]  {hint}"
                )
                lines = self._picker.render_slider_lines(width=50)
                # lines is a list of 4 strings
                axis, track, level_row, hint_text = lines[:4]
                rendered = (
                    f"  [dim]{axis}[/]\n"
                    f"  {track}\n"
                    f"  [bold]{level_row}[/]\n"
                    f"  [dim]{hint_text}[/]"
                )
                self.query_one("#ea-slider", Static).update(rendered)
            else:
                self.query_one("#ea-header", Static).update(
                    f"[bold]Effort[/]  [dim]{self.level}[/]  {hint}"
                )
                self.query_one("#ea-slider", Static).update("")
        except Exception:
            pass


__all__ = ["EffortAppWidget"]
