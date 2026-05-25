"""Native tool implementations for Lyra."""
from __future__ import annotations

from .ask_user_question import AskCallback, make_ask_user_question_tool
from .tool_search import (
    DiscoveryStats,
    ToolCategory,
    ToolContextBudget,
    ToolRegistry,
    ToolSchema,
    ToolSearchResult,
)
from .builtin import EditTool, GlobTool, GrepTool, ReadTool, WriteTool, register_builtin_tools
from .todo_write import make_todo_write_tool
from .toolsets import (
    ToolsetApplication,
    ToolsetRegistry,
    apply_toolset,
    default_toolsets,
    get_registry,
    get_toolset,
    list_toolsets,
    register_toolset,
)
from .web_fetch import make_web_fetch_tool, WebFetchTool
from .web_search import make_web_search_tool, WebSearchTool

__all__ = [
    "AskCallback",
    "DiscoveryStats",
    "EditTool",
    "GlobTool",
    "GrepTool",
    "ReadTool",
    "ToolCategory",
    "ToolContextBudget",
    "ToolRegistry",
    "ToolSchema",
    "ToolSearchResult",
    "ToolsetApplication",
    "ToolsetRegistry",
    "WebFetchTool",
    "WebSearchTool",
    "WriteTool",
    "apply_toolset",
    "default_toolsets",
    "get_registry",
    "get_toolset",
    "list_toolsets",
    "make_ask_user_question_tool",
    "make_todo_write_tool",
    "make_web_fetch_tool",
    "make_web_search_tool",
    "register_builtin_tools",
    "register_toolset",
]
