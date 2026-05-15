"""Lyra CLI module - Claude Code-style streaming interface.

This module provides a streaming CLI interface inspired by Claude Code,
replacing the Textual-based TUI with a simpler, more portable solution.
"""

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

__all__ = [
    "AssistantMessage",
    "Message",
    "ResultMessage",
    "StreamEvent",
    "SystemMessage",
    "ToolMessage",
    "UserMessage",
    "launch_streaming_repl",
]
