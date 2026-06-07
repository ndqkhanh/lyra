"""
Command system — slash command dispatcher for TUI interaction.
"""

from src.commands.dispatcher import (
    Command,
    CommandContext,
    CommandDispatcher,
)

__version__ = "0.1.0"

__all__ = [
    "Command",
    "CommandContext",
    "CommandDispatcher",
]
