"""Lyra CLI module - Claude Code-style streaming interface.

This module provides a streaming CLI interface inspired by Claude Code,
replacing the Textual-based TUI with a simpler, more portable solution.
"""

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
from .repl import launch_streaming_repl

# New CLI exports (Phase 2)
from .app import app as cli_app
from .output import console, OutputFormatter

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
    # New CLI
    "cli_app",
    "console",
    "OutputFormatter",
]
