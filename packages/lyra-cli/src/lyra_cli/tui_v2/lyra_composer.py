"""LyraComposer — Composer with inline autocomplete support.

Extends harness-tui's Composer to add:
- Slash command dropdown when typing /
- File path completion when typing @
- Keyboard navigation for dropdowns
"""
from __future__ import annotations

from textual import events
from textual.binding import Binding

try:
    from harness_tui.widgets.composer import Composer
except ImportError:
    # Fallback if harness-tui structure changes
    from textual.widgets import TextArea as Composer

from lyra_cli.tui_v2.widgets.slash_dropdown import SlashDropdown


class LyraComposer(Composer):
    """Composer with inline autocomplete."""

    BINDINGS = [
        *Composer.BINDINGS,
        Binding("escape", "hide_dropdown", "Hide dropdown", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.dropdown: SlashDropdown | None = None
        self._dropdown_active = False

    async def _on_key(self, event: events.Key) -> None:
        """Handle key events for autocomplete."""
        # Let parent handle the key first
        await super()._on_key(event)

        # Handle dropdown navigation
        if self._dropdown_active and self.dropdown:
            if event.key == "down":
                self.dropdown.move_selection(1)
                event.prevent_default()
                event.stop()
                return
            elif event.key == "up":
                self.dropdown.move_selection(-1)
                event.prevent_default()
                event.stop()
                return
            elif event.key == "enter" or event.key == "tab":
                # Accept selected command
                selected = self.dropdown.get_selected_command()
                if selected:
                    await self._accept_completion(selected)
                    event.prevent_default()
                    event.stop()
                    return
            elif event.key == "escape":
                await self._hide_dropdown()
                event.prevent_default()
                event.stop()
                return

        # Check if we should show/update dropdown
        await self._update_autocomplete()

    async def _update_autocomplete(self) -> None:
        """Update autocomplete based on current text."""
        text = self.text
        cursor_pos = self.cursor_location

        # Get current line and position
        lines = text.split("\n")
        if cursor_pos[0] >= len(lines):
            return

        current_line = lines[cursor_pos[0]]
        cursor_col = cursor_pos[1]

        # Check for slash command trigger
        if self._should_show_slash_dropdown(current_line, cursor_col):
            query = self._get_slash_query(current_line, cursor_col)
            await self._show_or_update_dropdown(query)
        else:
            await self._hide_dropdown()

    def _should_show_slash_dropdown(self, line: str, cursor_col: int) -> bool:
        """Check if we should show slash dropdown."""
        # Must have at least one character
        if cursor_col == 0:
            return False

        # Find the start of the current word
        word_start = cursor_col - 1
        while word_start > 0 and line[word_start - 1] not in (" ", "\n"):
            word_start -= 1

        # Check if word starts with /
        if word_start < len(line) and line[word_start] == "/":
            return True

        return False

    def _get_slash_query(self, line: str, cursor_col: int) -> str:
        """Extract the slash command query."""
        # Find the start of the current word
        word_start = cursor_col - 1
        while word_start > 0 and line[word_start - 1] not in (" ", "\n"):
            word_start -= 1

        # Extract query (including the /)
        query = line[word_start:cursor_col]
        return query

    async def _show_or_update_dropdown(self, query: str) -> None:
        """Show or update the dropdown with query."""
        if self.dropdown and self._dropdown_active:
            # Update existing dropdown
            self.dropdown.update_search(query)
        else:
            # Create new dropdown
            self.dropdown = SlashDropdown(query)
            if self.dropdown.has_matches():
                await self.app.mount(self.dropdown)
                self._dropdown_active = True
                self._position_dropdown()

    def _position_dropdown(self) -> None:
        """Position dropdown below cursor."""
        if not self.dropdown:
            return

        # Get cursor position
        cursor_y, cursor_x = self.cursor_location

        # Position dropdown below cursor
        # Note: This is a simplified positioning
        # In production, you'd need to handle edge cases
        self.dropdown.styles.offset = (cursor_x, cursor_y + 1)

    async def _hide_dropdown(self) -> None:
        """Hide the dropdown."""
        if self.dropdown and self._dropdown_active:
            await self.dropdown.remove()
            self.dropdown = None
            self._dropdown_active = False

    async def _accept_completion(self, command: str) -> None:
        """Accept the selected completion."""
        text = self.text
        cursor_pos = self.cursor_location

        # Get current line
        lines = text.split("\n")
        if cursor_pos[0] >= len(lines):
            return

        current_line = lines[cursor_pos[0]]
        cursor_col = cursor_pos[1]

        # Find the start of the current word
        word_start = cursor_col - 1
        while word_start > 0 and current_line[word_start - 1] not in (" ", "\n"):
            word_start -= 1

        # Replace the partial command with the full command
        new_line = current_line[:word_start] + f"/{command} " + current_line[cursor_col:]
        lines[cursor_pos[0]] = new_line

        # Update text
        self.text = "\n".join(lines)

        # Move cursor to end of inserted command
        new_cursor_col = word_start + len(command) + 2  # +2 for / and space
        self.cursor_location = (cursor_pos[0], new_cursor_col)

        # Hide dropdown
        await self._hide_dropdown()

    def action_hide_dropdown(self) -> None:
        """Action to hide dropdown."""
        if self._dropdown_active:
            self.run_worker(self._hide_dropdown())
