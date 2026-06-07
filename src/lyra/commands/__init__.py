"""
Command system — slash command dispatcher, custom loader, palette, and REPL.
"""

from lyra.commands.custom_loader import (
    CommandFile,
    CustomCommandLoader,
)
from lyra.commands.dispatcher import (
    Command,
    CommandContext,
    CommandDispatcher,
)
from lyra.commands.palette import (
    CommandPalette,
    HistoryEntry,
    REPLEnhancements,
    SandboxedExecutor,
)

__version__ = "0.2.0"

__all__ = [
    "Command",
    "CommandContext",
    "CommandDispatcher",
    "CommandFile",
    "CommandPalette",
    "CustomCommandLoader",
    "HistoryEntry",
    "REPLEnhancements",
    "SandboxedExecutor",
]
