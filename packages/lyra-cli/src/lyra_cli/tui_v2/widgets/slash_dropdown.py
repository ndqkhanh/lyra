"""SlashDropdown — inline dropdown that appears when typing /.

Appears below the cursor when user types / in the Composer.
Shows matching slash commands with fuzzy filtering.
Handles keyboard navigation (↑↓ Enter Esc Tab).
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import ListItem, ListView, Static

from lyra_cli.interactive.command_palette import fuzzy_filter


class SlashDropdown(Vertical):
    """Inline dropdown for slash command completion."""

    DEFAULT_CSS = """
    SlashDropdown {
        height: auto;
        max-height: 8;
        width: 50;
        background: $surface;
        border: tall $primary;
        layer: overlay;
    }
    SlashDropdown ListView {
        height: auto;
        max-height: 8;
        background: $surface;
    }
    SlashDropdown ListItem {
        height: 1;
        padding: 0 1;
    }
    SlashDropdown .command-name {
        color: $primary;
        text-style: bold;
    }
    SlashDropdown .command-desc {
        color: $text-muted;
    }
    """

    def __init__(self, search_query: str = "") -> None:
        super().__init__()
        self.search_query = search_query
        self.commands = self._get_matching_commands(search_query)
        self.selected_index = 0

    def compose(self) -> ComposeResult:
        """Compose the dropdown with matching commands."""
        items = []
        for i, spec in enumerate(self.commands[:8]):  # Limit to 8 items
            # Format: /command - description
            label = f"/{spec.name}"
            if spec.args_hint:
                label += f" {spec.args_hint}"
            label += f" — {spec.description[:50]}"

            item = ListItem(Static(label), id=f"cmd-{i}")
            if i == self.selected_index:
                item.add_class("selected")
            items.append(item)

        if items:
            yield ListView(*items, id="command-list")
        else:
            yield Static("[dim]No matching commands[/]", id="no-match")

    def _get_matching_commands(self, search_query: str) -> list:
        """Get commands matching the query using fuzzy filter."""
        # Remove leading slash if present
        clean_query = search_query.lstrip("/")

        # Use fuzzy_filter from REPL
        return fuzzy_filter(clean_query)

    def update_search(self, search_query: str) -> None:
        """Update the dropdown with new query."""
        self.search_query = search_query
        self.commands = self._get_matching_commands(search_query)
        self.selected_index = 0
        self.refresh(recompose=True)

    def move_selection(self, delta: int) -> None:
        """Move selection up or down."""
        if not self.commands:
            return

        self.selected_index = max(0, min(
            len(self.commands) - 1,
            self.selected_index + delta
        ))
        self.refresh(recompose=True)

    def get_selected_command(self) -> str | None:
        """Get the currently selected command name."""
        if 0 <= self.selected_index < len(self.commands):
            return self.commands[self.selected_index].name
        return None

    def has_matches(self) -> bool:
        """Check if there are any matching commands."""
        return len(self.commands) > 0
