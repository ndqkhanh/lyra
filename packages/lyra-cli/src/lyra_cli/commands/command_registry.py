"""Command registry - Unified command management"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Callable


@dataclass
class Command:
    """A command definition"""
    name: str
    description: str
    handler: Callable
    aliases: List[str] = None
    category: str = "general"
    source: str = "lyra"  # "lyra" or "ecc"

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


class CommandRegistry:
    """Registry of all commands"""

    def __init__(self):
        self.commands: Dict[str, Command] = {}
        self.aliases: Dict[str, str] = {}  # alias -> command_name

    def register(self, command: Command):
        """Register a command"""
        self.commands[command.name] = command

        # Register aliases
        for alias in command.aliases:
            self.aliases[alias] = command.name

    def get(self, name: str) -> Optional[Command]:
        """Get command by name or alias"""
        # Check if it's an alias
        if name in self.aliases:
            name = self.aliases[name]

        return self.commands.get(name)

    def list(self, category: Optional[str] = None, source: Optional[str] = None) -> List[Command]:
        """List commands"""
        commands = list(self.commands.values())

        if category:
            commands = [c for c in commands if c.category == category]

        if source:
            commands = [c for c in commands if c.source == source]

        return sorted(commands, key=lambda c: c.name)

    def list_categories(self) -> List[str]:
        """List all categories"""
        categories = set(c.category for c in self.commands.values())
        return sorted(categories)

    def exists(self, name: str) -> bool:
        """Check if command exists"""
        return name in self.commands or name in self.aliases

    def merge_duplicate(self, command: Command) -> bool:
        """Merge duplicate command (returns True if merged)"""
        existing = self.get(command.name)
        if existing:
            # Merge aliases
            for alias in command.aliases:
                if alias not in existing.aliases:
                    existing.aliases.append(alias)
                    self.aliases[alias] = command.name
            return True
        return False


# Global registry
_registry = CommandRegistry()


def get_registry() -> CommandRegistry:
    """Get global command registry"""
    return _registry
