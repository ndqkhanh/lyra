"""Extended tools package — file, search, shell, code, text, data, git, and web tools."""

from __future__ import annotations

from .code_tools import CodeLanguage, CodeMetrics, CodeSymbol, CodeTool, LintFinding, SymbolKind
from .data_tools import DataFormat, DataSchema, DataTool, DataTransformResult
from .file_tools import FileDiff, FileInfo, FileOperation, FileTool
from .git_tools import GitCommit, GitDiff, GitFileStatus, GitOperation, GitStatus, GitTool
from .search_tools import FileIndex, ReplaceOperation, SearchMatch, SearchMode, SearchResult, SearchTool
from .shell_tools import ShellMode, ShellResult, ShellSession, ShellTool
from .text_tools import TextDiff, TextOperation, TextStats, TextTool
from .types import ToolCategory, ToolDefinition, ToolExecution, ToolParameter, ToolPermission, ToolResult, ToolRisk
from .web_tools import RateLimitConfig, WebMethod, WebRequest, WebResponse, WebTool

__all__ = [
    # Types
    "ToolCategory",
    "ToolDefinition",
    "ToolExecution",
    "ToolParameter",
    "ToolPermission",
    "ToolResult",
    "ToolRisk",
    # File
    "FileDiff",
    "FileInfo",
    "FileOperation",
    "FileTool",
    # Search
    "FileIndex",
    "ReplaceOperation",
    "SearchMatch",
    "SearchMode",
    "SearchResult",
    "SearchTool",
    # Shell
    "ShellMode",
    "ShellResult",
    "ShellSession",
    "ShellTool",
    # Code
    "CodeLanguage",
    "CodeMetrics",
    "CodeSymbol",
    "CodeTool",
    "LintFinding",
    "SymbolKind",
    # Text
    "TextDiff",
    "TextOperation",
    "TextStats",
    "TextTool",
    # Data
    "DataFormat",
    "DataSchema",
    "DataTool",
    "DataTransformResult",
    # Git
    "GitCommit",
    "GitDiff",
    "GitFileStatus",
    "GitOperation",
    "GitStatus",
    "GitTool",
    # Web
    "RateLimitConfig",
    "WebMethod",
    "WebRequest",
    "WebResponse",
    "WebTool",
]
