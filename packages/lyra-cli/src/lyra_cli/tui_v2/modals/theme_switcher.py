"""Theme Switcher Modal — browse & preview themes.

Lets users cycle through all ThemePreset values with live preview
of color swatches. Activated via /theme <name> or Alt+T.
"""
from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView, Static


class ThemeSwitcherModal(ModalScreen[str]):
    """Pick a theme from the available presets."""

    DEFAULT_CSS = """
    ThemeSwitcherModal {
        align: center middle;
    }

    ThemeSwitcherModal > Vertical {
        width: 50;
        height: 60%;
        min-height: 15;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }

    ThemeSwitcherModal #theme-search {
        dock: top;
        margin: 0 0 1 0;
    }

    ThemeSwitcherModal #theme-list {
        height: 1fr;
        border: solid $border;
    }

    ThemeSwitcherModal #theme-list ListItem {
        padding: 0 1;
        height: 2;
    }

    ThemeSwitcherModal #theme-list ListItem:hover {
        background: $accent 20%;
    }

    ThemeSwitcherModal #theme-list .active-theme {
        text-style: bold;
    }

    ThemeSwitcherModal #theme-footer {
        dock: bottom;
        height: 3;
        content-align: center middle;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss(None)", "Cancel", show=False),
        Binding("enter", "select_theme", "Apply", show=True),
        Binding("/", "focus_search", "Search", show=False),
    ]

    def __init__(self, themes: list[tuple[str, str]], current: str = "default"):
        """
        Args:
            themes: List of (preset_name, display_label) tuples
            current: Currently active theme name
        """
        super().__init__()
        self._themes = themes
        self._current = current
        self._filtered = list(themes)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[bold]Theme Switcher[/]  pick a color theme")
            yield Input(placeholder="Filter themes…", id="theme-search")
            yield ListView(id="theme-list")
            yield Label("[/]enter=apply · esc=cancel[/]", id="theme-footer")

    def on_mount(self) -> None:
        self._rebuild()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "theme-search":
            q = event.value.lower().strip()
            if not q:
                self._filtered = list(self._themes)
            else:
                self._filtered = [
                    (n, l) for n, l in self._themes
                    if q in n or q in l.lower()
                ]
            self._rebuild()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.action_select_theme()

    def action_select_theme(self) -> None:
        list_view = self.query_one("#theme-list", ListView)
        if list_view.index is not None and 0 <= list_view.index < len(self._filtered):
            name, _ = self._filtered[list_view.index]
            self.dismiss(name)

    def action_focus_search(self) -> None:
        self.query_one("#theme-search", Input).focus()

    def _rebuild(self) -> None:
        list_view = self.query_one("#theme-list", ListView)
        list_view.clear()
        for name, label in self._filtered:
            marker = "●" if name == self._current else "○"
            item = ListItem(
                Static(f"{marker}  {label}" if marker == "●" else f"   {label}"),
            )
            list_view.append(item)
