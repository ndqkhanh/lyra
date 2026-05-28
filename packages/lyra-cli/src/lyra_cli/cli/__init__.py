"""Lyra CLI module - Claude Code-style streaming interface.

This module provides a streaming CLI interface inspired by Claude Code,
replacing the Textual-based TUI with a simpler, more portable solution.
"""

from rich.console import Console

# New CLI exports (Phase 2)
from .app import app as cli_app

# Legacy exports (keep for backward compatibility)
from .messages import (
    AssistantMessage,
    Message,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    ToolMessage,
    UserMessage,
)
from .output import OutputFormatter
from .repl import LyraREPL, launch_streaming_repl

# Create console instance
console = Console()

__all__ = [
    # Legacy
    "AssistantMessage",
    "Message",
    "ResultMessage",
    "StreamEvent",
    "SystemMessage",
    "ToolMessage",
    "UserMessage",
    "launch_streaming_repl",
    "LyraREPL",
    # New CLI
    "cli_app",
    "console",
    "OutputFormatter",
]
