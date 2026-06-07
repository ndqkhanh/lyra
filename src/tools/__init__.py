"""
Tools system for Lyra.

Provides tool registration (ToolDef, ToolRegistry), sandboxed execution (ToolExecutor),
sandbox configuration, and built-in tools (ReadFile, WriteFile, RunBash, WebSearch).
"""

from src.tools.builtins import register_builtins
from src.tools.executor import ToolExecutor
from src.tools.registry import ToolDef, ToolHandler, ToolRegistry, ToolResult, validate_parameters
from src.tools.sandbox import (
    DENYLIST_PATTERNS,
    SandboxConfig,
    check_command_safety,
    check_domain_safety,
    check_path_safety,
)

__all__ = [
    # Core types
    "ToolDef",
    "ToolResult",
    "ToolHandler",
    # Registry
    "ToolRegistry",
    "validate_parameters",
    # Executor
    "ToolExecutor",
    # Sandbox
    "SandboxConfig",
    "DENYLIST_PATTERNS",
    "check_command_safety",
    "check_path_safety",
    "check_domain_safety",
    # Built-in tools
    "register_builtins",
]

__version__ = "1.0.0"
