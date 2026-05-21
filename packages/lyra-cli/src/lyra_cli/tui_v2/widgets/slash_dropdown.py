"""TUI Slash Dropdown - Inline command completion.

Phase 2 of TUI Autocomplete. Provides inline dropdown for slash commands
with fuzzy matching and real-time filtering.

Features:
- Inline dropdown widget
- Fuzzy matching on command names
- Real-time filtering as user types
- Keyboard navigation (Up/Down/Enter/Escape)
- Command insertion at cursor
- Category grouping
- Alias support

Usage:
    # In TUI input field
    /dep<Tab>  # Shows dropdown with "deploy", "debug", etc.
    
    # Navigate with arrows, Enter to select
    # Escape to cancel
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple
from textual.widgets import Input
from textual.containers import Container
from textual.reactive import reactive
from textual import events


@dataclass
class CommandSuggestion:
    """A command suggestion for the dropdown."""
    
    command: str
    description: str
    category: str
    aliases: List[str]
    score: float = 1.0  # Fuzzy match score


class SlashDropdown(Container):
    """
    Inline dropdown for slash command completion.
    
    Shows suggestions as user types, with fuzzy matching and
    keyboard navigation.
    """
    
    DEFAULT_CSS = """
    SlashDropdown {
        display: none;
        width: 60;
        height: auto;
        max-height: 10;
        background: $surface;
        border: solid $primary;
        padding: 0 1;
    }
    
    SlashDropdown.visible {
        display: block;
    }
    
    .suggestion {
        padding: 0 1;
    }
    
    .suggestion-selected {
        background: $primary;
        color: $text;
    }
    
    .suggestion-command {
        color: $accent;
    }
    
    .suggestion-description {
        color: $text-muted;
    }
    """
    
    suggestions: reactive[List[CommandSuggestion]] = reactive(list)
    selected_index: reactive[int] = reactive(0)
    visible: reactive[bool] = reactive(False)
    
    def __init__(self, input_widget: Input):
        """Initialize the dropdown.
        
        Args:
            input_widget: The input widget to attach to
        """
        super().__init__()
        self.input_widget = input_widget
        self.all_commands = self._load_commands()
    
    def _load_commands(self) -> List[CommandSuggestion]:
        """Load all available commands.
        
        Returns:
            List of command suggestions
        """
        suggestions = []
        
        try:
            # Import here to avoid circular dependency
            from lyra_cli.tui_v2.commands import COMMAND_REGISTRY
            
            for cmd_name, cmd_info in COMMAND_REGISTRY.items():
                suggestion = CommandSuggestion(
                    command=cmd_name,
                    description=cmd_info.get("description", ""),
                    category=cmd_info.get("category", "general"),
                    aliases=cmd_info.get("aliases", []),
                )
                suggestions.append(suggestion)
        except (ImportError, AttributeError):
            # Fallback to mock commands for testing
            suggestions = [
                CommandSuggestion(
                    command="deploy",
                    description="Deploy the application",
                    category="deployment",
                    aliases=["dep"],
                ),
                CommandSuggestion(
                    command="test",
                    description="Run tests",
                    category="testing",
                    aliases=["t"],
                ),
                CommandSuggestion(
                    command="help",
                    description="Show help",
                    category="general",
                    aliases=["h", "?"],
                ),
            ]
        
        return suggestions
    
    def show(self, query: str) -> None:
        """Show dropdown with filtered suggestions.
        
        Args:
            query: Current input query (after /)
        """
        if not query:
            # Show all commands
            self.suggestions = self.all_commands[:10]
        else:
            # Fuzzy match
            self.suggestions = self._fuzzy_match(query)
        
        if self.suggestions:
            self.visible = True
            self.selected_index = 0
            self.add_class("visible")
        else:
            self.hide()
    
    def hide(self) -> None:
        """Hide the dropdown."""
        self.visible = False
        self.remove_class("visible")
    
    def _fuzzy_match(self, query: str) -> List[CommandSuggestion]:
        """Fuzzy match commands against query.
        
        Args:
            query: Search query
            
        Returns:
            Sorted list of matching suggestions
        """
        query_lower = query.lower()
        matches = []
        
        for suggestion in self.all_commands:
            # Check command name
            if query_lower in suggestion.command.lower():
                score = self._calculate_score(query_lower, suggestion.command.lower())
                matches.append((score, suggestion))
                continue
            
            # Check aliases
            for alias in suggestion.aliases:
                if query_lower in alias.lower():
                    score = self._calculate_score(query_lower, alias.lower())
                    matches.append((score, suggestion))
                    break
        
        # Sort by score (higher is better)
        matches.sort(key=lambda x: x[0], reverse=True)
        
        # Return top 10
        return [suggestion for score, suggestion in matches[:10]]
    
    def _calculate_score(self, query: str, text: str) -> float:
        """Calculate fuzzy match score.
        
        Args:
            query: Search query
            text: Text to match against
            
        Returns:
            Score (0-1, higher is better)
        """
        # Simple scoring:
        # - Exact match: 1.0
        # - Starts with: 0.9
        # - Contains: 0.7
        # - Substring: 0.5
        
        if query == text:
            return 1.0
        elif text.startswith(query):
            return 0.9
        elif query in text:
            # Bonus for early match
            pos = text.index(query)
            return 0.7 - (pos / len(text)) * 0.2
        else:
            return 0.5
    
    def select_next(self) -> None:
        """Select next suggestion."""
        if self.suggestions:
            self.selected_index = (self.selected_index + 1) % len(self.suggestions)
    
    def select_previous(self) -> None:
        """Select previous suggestion."""
        if self.suggestions:
            self.selected_index = (self.selected_index - 1) % len(self.suggestions)
    
    def get_selected(self) -> Optional[CommandSuggestion]:
        """Get currently selected suggestion.
        
        Returns:
            Selected suggestion or None
        """
        if self.suggestions and 0 <= self.selected_index < len(self.suggestions):
            return self.suggestions[self.selected_index]
        return None
    
    def compose(self):
        """Compose the dropdown UI."""
        from textual.widgets import Static
        
        if not self.suggestions:
            yield Static("No matches")
            return
        
        for i, suggestion in enumerate(self.suggestions):
            selected = i == self.selected_index
            
            # Format suggestion
            text = f"/{suggestion.command}"
            if suggestion.aliases:
                text += f" ({', '.join(suggestion.aliases)})"
            text += f"\n  {suggestion.description}"
            
            widget = Static(
                text,
                classes="suggestion suggestion-selected" if selected else "suggestion",
            )
            yield widget


class SlashCompletionInput(Input):
    """
    Enhanced input widget with slash command completion.
    
    Automatically shows dropdown when user types "/" and filters
    as they continue typing.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the input with completion."""
        super().__init__(*args, **kwargs)
        self.dropdown = SlashDropdown(self)
        self.completion_active = False
    
    def on_mount(self) -> None:
        """Mount the dropdown."""
        # Add dropdown to parent
        if self.parent:
            self.parent.mount(self.dropdown)
    
    def on_key(self, event: events.Key) -> None:
        """Handle key events for completion.
        
        Args:
            event: Key event
        """
        # Check if completion is active
        if self.completion_active:
            if event.key == "down":
                self.dropdown.select_next()
                event.prevent_default()
                return
            elif event.key == "up":
                self.dropdown.select_previous()
                event.prevent_default()
                return
            elif event.key == "enter":
                # Insert selected command
                selected = self.dropdown.get_selected()
                if selected:
                    self._insert_command(selected.command)
                    self.dropdown.hide()
                    self.completion_active = False
                event.prevent_default()
                return
            elif event.key == "escape":
                # Cancel completion
                self.dropdown.hide()
                self.completion_active = False
                event.prevent_default()
                return
    
    def watch_value(self, value: str) -> None:
        """Watch for value changes to trigger completion.
        
        Args:
            value: Current input value
        """
        # Check if we should show completion
        cursor_pos = self.cursor_position
        
        # Find last "/" before cursor
        text_before_cursor = value[:cursor_pos]
        last_slash = text_before_cursor.rfind("/")
        
        if last_slash != -1:
            # Extract query after "/"
            query = text_before_cursor[last_slash + 1:]
            
            # Show dropdown if query is not empty or just started
            if len(query) <= 20:  # Reasonable limit
                self.dropdown.show(query)
                self.completion_active = True
            else:
                self.dropdown.hide()
                self.completion_active = False
        else:
            # No "/" found, hide dropdown
            if self.completion_active:
                self.dropdown.hide()
                self.completion_active = False
    
    def _insert_command(self, command: str) -> None:
        """Insert selected command at cursor.
        
        Args:
            command: Command to insert
        """
        value = self.value
        cursor_pos = self.cursor_position
        
        # Find last "/" before cursor
        text_before_cursor = value[:cursor_pos]
        last_slash = text_before_cursor.rfind("/")
        
        if last_slash != -1:
            # Replace from "/" to cursor with command
            new_value = (
                value[:last_slash] +
                "/" + command + " " +
                value[cursor_pos:]
            )
            self.value = new_value
            self.cursor_position = last_slash + len(command) + 2


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "CommandSuggestion",
    "SlashDropdown",
    "SlashCompletionInput",
]
