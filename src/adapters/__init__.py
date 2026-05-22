"""
Adapters module for cross-platform support.

Enables Lyra to work across multiple AI harnesses:
- Claude Code (native)
- Cursor IDE
- VS Code
- JetBrains
- Zed
- GitHub Copilot
- Codex
- OpenCode
"""

from adapters.base import (
    AdapterFactory,
    ClaudeCodeAdapter,
    CursorAdapter,
    HarnessAdapter,
    HarnessType,
    Hook,
    JetBrainsAdapter,
    Message,
    Response,
    Tool,
    VSCodeAdapter,
)

__version__ = "0.1.0"

__all__ = [
    # Base classes
    "HarnessAdapter",
    "HarnessType",
    # Data types
    "Message",
    "Response",
    "Tool",
    "Hook",
    # Adapters
    "ClaudeCodeAdapter",
    "CursorAdapter",
    "VSCodeAdapter",
    "JetBrainsAdapter",
    # Factory
    "AdapterFactory",
]
