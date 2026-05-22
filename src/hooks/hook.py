"""
Hook data models and types.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class HookType(str, Enum):
    """Types of hooks that can be registered."""

    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    STOP = "stop"


@dataclass
class HookContext:
    """
    Context passed to hook handlers.

    Contains information about the event that triggered the hook.
    """

    hook_type: HookType
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[Any] = None
    session_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HookResult:
    """
    Result returned by hook handlers.

    Indicates whether the hook succeeded and any modifications to make.
    """

    success: bool
    modified_args: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def ok(modified_args: Optional[Dict[str, Any]] = None) -> "HookResult":
        """Create a successful result."""
        return HookResult(success=True, modified_args=modified_args)

    @staticmethod
    def fail(message: str) -> "HookResult":
        """Create an error result."""
        return HookResult(success=False, error=message)


@dataclass
class Hook:
    """
    Hook definition.

    Defines when and how a hook should be executed.
    """

    hook_id: str
    hook_type: HookType
    handler: Callable[[HookContext], HookResult]
    description: str
    tool_filter: Optional[str] = None  # Tool name pattern (e.g., "Edit", "Write")
    file_pattern: Optional[str] = None  # File pattern (e.g., "**/*.py")
    priority: int = 0  # Higher priority hooks run first
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def matches(self, context: HookContext) -> bool:
        """
        Check if this hook should fire for the given context.

        Args:
            context: Hook context

        Returns:
            True if hook should fire
        """
        if not self.enabled:
            return False

        # Check hook type
        if self.hook_type != context.hook_type:
            return False

        # Check tool filter
        if self.tool_filter and context.tool_name:
            if not self._matches_pattern(context.tool_name, self.tool_filter):
                return False

        # Check file pattern (if tool_args contains file_path)
        if self.file_pattern and context.tool_args:
            file_path = context.tool_args.get("file_path")
            if file_path and not self._matches_pattern(file_path, self.file_pattern):
                return False

        return True

    def _matches_pattern(self, value: str, pattern: str) -> bool:
        """
        Check if value matches pattern.

        Args:
            value: Value to check
            pattern: Pattern (supports * wildcard)

        Returns:
            True if matches
        """
        import fnmatch
        return fnmatch.fnmatch(value, pattern)
