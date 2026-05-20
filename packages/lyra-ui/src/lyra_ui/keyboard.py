"""
Keyboard Navigation - Vim-style keyboard navigation and shortcuts.

Features:
- Vim-style navigation (hjkl, gg/G, etc.)
- Command palette
- Quick actions
- Custom keybindings
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional


class NavigationMode(Enum):
    """Navigation mode."""

    NORMAL = "normal"
    INSERT = "insert"
    VISUAL = "visual"
    COMMAND = "command"


@dataclass
class KeyBinding:
    """Key binding definition."""

    key: str
    action: str
    description: str
    mode: NavigationMode = NavigationMode.NORMAL


class VimNavigator:
    """
    Vim-style keyboard navigator.

    Features:
    - hjkl navigation
    - gg/G top/bottom
    - Ctrl+D/U page up/down
    - / search
    """

    def __init__(self):
        """Initialize Vim navigator."""
        self.mode = NavigationMode.NORMAL
        self.bindings: Dict[str, KeyBinding] = {}
        self._setup_default_bindings()

    def _setup_default_bindings(self):
        """Set up default Vim bindings."""
        default_bindings = [
            # Navigation
            KeyBinding("h", "move_left", "Move left"),
            KeyBinding("j", "move_down", "Move down"),
            KeyBinding("k", "move_up", "Move up"),
            KeyBinding("l", "move_right", "Move right"),
            KeyBinding("gg", "goto_top", "Go to top"),
            KeyBinding("G", "goto_bottom", "Go to bottom"),
            KeyBinding("ctrl+d", "page_down", "Page down"),
            KeyBinding("ctrl+u", "page_up", "Page up"),
            # Word navigation
            KeyBinding("w", "word_forward", "Word forward"),
            KeyBinding("b", "word_backward", "Word backward"),
            # Search
            KeyBinding("/", "search_forward", "Search forward"),
            KeyBinding("?", "search_backward", "Search backward"),
            KeyBinding("n", "next_match", "Next match"),
            KeyBinding("N", "prev_match", "Previous match"),
            # Mode switching
            KeyBinding("i", "insert_mode", "Insert mode"),
            KeyBinding("v", "visual_mode", "Visual mode"),
            KeyBinding("escape", "normal_mode", "Normal mode"),
        ]

        for binding in default_bindings:
            self.bindings[binding.key] = binding

    def get_binding(self, key: str) -> Optional[KeyBinding]:
        """
        Get key binding.

        Args:
            key: Key combination

        Returns:
            Key binding or None
        """
        return self.bindings.get(key)

    def add_binding(self, binding: KeyBinding):
        """
        Add custom key binding.

        Args:
            binding: Key binding
        """
        self.bindings[binding.key] = binding

    def remove_binding(self, key: str):
        """
        Remove key binding.

        Args:
            key: Key combination
        """
        if key in self.bindings:
            del self.bindings[key]

    def set_mode(self, mode: NavigationMode):
        """
        Set navigation mode.

        Args:
            mode: Navigation mode
        """
        self.mode = mode

    def get_mode(self) -> NavigationMode:
        """Get current mode."""
        return self.mode

    def list_bindings(self, mode: Optional[NavigationMode] = None) -> List[KeyBinding]:
        """
        List key bindings.

        Args:
            mode: Filter by mode (None for all)

        Returns:
            List of key bindings
        """
        if mode is None:
            return list(self.bindings.values())
        return [b for b in self.bindings.values() if b.mode == mode]


class CommandPalette:
    """
    Command palette with fuzzy search.

    Features:
    - Fuzzy search
    - Command history
    - Command categories
    """

    def __init__(self):
        """Initialize command palette."""
        self.commands: Dict[str, Callable] = {}
        self.history: List[str] = []
        self.categories: Dict[str, List[str]] = {}

    def register_command(
        self,
        name: str,
        callback: Callable,
        category: str = "general",
    ):
        """
        Register command.

        Args:
            name: Command name
            callback: Command callback
            category: Command category
        """
        self.commands[name] = callback

        if category not in self.categories:
            self.categories[category] = []
        self.categories[category].append(name)

    def execute_command(self, name: str, *args, **kwargs):
        """
        Execute command.

        Args:
            name: Command name
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        if name in self.commands:
            self.history.append(name)
            return self.commands[name](*args, **kwargs)

    def search_commands(self, query: str) -> List[str]:
        """
        Search commands with fuzzy matching.

        Args:
            query: Search query

        Returns:
            List of matching command names
        """
        query_lower = query.lower()
        matches = []

        for name in self.commands.keys():
            if query_lower in name.lower():
                matches.append(name)

        return sorted(matches)

    def get_recent_commands(self, limit: int = 10) -> List[str]:
        """
        Get recent commands.

        Args:
            limit: Maximum number of commands

        Returns:
            List of recent command names
        """
        return self.history[-limit:]

    def get_category_commands(self, category: str) -> List[str]:
        """
        Get commands by category.

        Args:
            category: Category name

        Returns:
            List of command names
        """
        return self.categories.get(category, [])

    def list_categories(self) -> List[str]:
        """
        List all categories.

        Returns:
            List of category names
        """
        return list(self.categories.keys())


class QuickActions:
    """
    Quick action shortcuts.

    Features:
    - @ file picker
    - # skill picker
    - / command picker
    """

    def __init__(self):
        """Initialize quick actions."""
        self.actions: Dict[str, str] = {
            "@": "file_picker",
            "#": "skill_picker",
            "/": "command_picker",
        }

    def get_action(self, prefix: str) -> Optional[str]:
        """
        Get action for prefix.

        Args:
            prefix: Action prefix

        Returns:
            Action name or None
        """
        return self.actions.get(prefix)

    def add_action(self, prefix: str, action: str):
        """
        Add quick action.

        Args:
            prefix: Action prefix
            action: Action name
        """
        self.actions[prefix] = action

    def remove_action(self, prefix: str):
        """
        Remove quick action.

        Args:
            prefix: Action prefix
        """
        if prefix in self.actions:
            del self.actions[prefix]

    def list_actions(self) -> Dict[str, str]:
        """
        List all quick actions.

        Returns:
            Dictionary of prefix to action
        """
        return self.actions.copy()
