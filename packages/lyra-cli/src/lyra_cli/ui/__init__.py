"""Lyra UI - Claude Code-style terminal formatting system

Complete UI system for rendering Claude Code-style terminal output with:
- Hierarchical tree structures
- Expandable/collapsible content
- Tool call formatting
- Status tracking
- ANSI colors and Unicode symbols
"""

from .symbols import SymbolRegistry, STATUS_SYMBOLS, BOX_CHARS
from .colors import ColorEngine, COLORS
from .layout import LayoutEngine, TextSegment
from .renderer import LyraUIRenderer
from .tree import TreeNode, TreeRenderer, RenderContext
from .expandable import (
    ExpandableSection,
    CollapseState,
    TruncationEngine,
    ExpandableRenderer,
)
from .tool_formatter import (
    ToolCall,
    ToolResult,
    Diagnostic,
    DiffHunk,
    ToolCallFormatter,
)
from .fixed_input import FixedInputBox
from .status_line import StatusLine
from .response_formatter import ResponseFormatter

__all__ = [
    # Symbols
    "SymbolRegistry",
    "STATUS_SYMBOLS",
    "BOX_CHARS",
    # Colors
    "ColorEngine",
    "COLORS",
    # Layout
    "LayoutEngine",
    "TextSegment",
    # Renderer
    "LyraUIRenderer",
    # Tree
    "TreeNode",
    "TreeRenderer",
    "RenderContext",
    # Expandable
    "ExpandableSection",
    "CollapseState",
    "TruncationEngine",
    "ExpandableRenderer",
    # Tool Formatter
    "ToolCall",
    "ToolResult",
    "Diagnostic",
    "DiffHunk",
    "ToolCallFormatter",
    # Fixed UI
    "FixedInputBox",
    "StatusLine",
    # Response Formatter
    "ResponseFormatter",
]

__version__ = "1.0.0"
