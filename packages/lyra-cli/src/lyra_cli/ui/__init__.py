"""Lyra UI - Claude Code-style terminal formatting system

Complete UI system for rendering Claude Code-style terminal output with:
- Hierarchical tree structures
- Expandable/collapsible content
- Tool call formatting
- Status tracking
- ANSI colors and Unicode symbols
"""

from .agent_tree import AgentNode, AgentTree
from .colors import COLORS, ColorEngine
from .expandable import (
    CollapseState,
    ExpandableRenderer,
    ExpandableSection,
    TruncationEngine,
)
from .fixed_input import FixedInputBox
from .layout import LayoutEngine, TextSegment
from .renderer import LyraUIRenderer
from .response_formatter import ResponseFormatter
from .scroll_manager import ScrollManager
from .selection_menu import MenuOption, SelectionMenu
from .status_line import StatusLine
from .symbols import BOX_CHARS, STATUS_SYMBOLS, SymbolRegistry
from .tool_formatter import (
    Diagnostic,
    DiffHunk,
    ToolCall,
    ToolCallFormatter,
    ToolResult,
)
from .tree import RenderContext, TreeNode, TreeRenderer
from .welcome_banner import print_welcome_banner

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
    # Agent Tree
    "AgentTree",
    "AgentNode",
    # Selection Menu
    "SelectionMenu",
    "MenuOption",
    # Scroll Manager
    "ScrollManager",
    # Welcome Banner
    "print_welcome_banner",
]

__version__ = "1.0.0"
