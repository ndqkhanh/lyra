"""
Hook data models and types for Hook Engine v2.

Provides the core types for the interceptor pipeline:
HookAction, HookType, HookContext, HookResult, and Hook.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.routing.provider.types import CompletionRequest, CompletionResponse


class HookAction(str, Enum):
    """Actions a hook can return to control the interceptor pipeline."""

    ALLOW = "allow"
    MODIFY = "modify"
    BLOCK = "block"
    ASK_USER = "ask_user"


class HookType(str, Enum):
    """Types of hooks that can be registered."""

    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    PRE_MODEL_CALL = "pre_model_call"
    POST_MODEL_CALL = "post_model_call"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    # Deprecated: kept for backward compatibility with v1 registrations
    STOP = "stop"


@dataclass(frozen=True)
class HookContext:
    """
    Context passed to hook handlers.

    Contains information about the event that triggered the hook.
    Frozen (immutable) -- handlers return a new HookContext via MODIFY if
    they need to change the context.

    New in v2: fields for model request/response and agent_id.
    """

    hook_type: HookType
    tool_name: str | None = None
    # v1 backward-compatible field (synced with tool_input)
    tool_args: dict[str, Any] | None = None
    # v2 alias for tool_args
    tool_input: dict[str, Any] | None = None
    model_request: Any | None = None
    model_response: Any | None = None
    agent_id: str | None = None
    session_id: str | None = None
    # v1 backward-compatible field
    tool_result: Any | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Sync tool_args and tool_input for backward compatibility.

        If only one of tool_args / tool_input is provided, the other is
        set to the same value so that both v1 and v2 handlers see data.
        """
        if self.tool_args is not None and self.tool_input is None:
            object.__setattr__(self, "tool_input", self.tool_args)
        elif self.tool_input is not None and self.tool_args is None:
            object.__setattr__(self, "tool_args", self.tool_input)


@dataclass(frozen=True)
class HookResult:
    """
    Result returned by hook handlers.

    New in v2: action-based result with immutable state.  The action
    field controls whether the pipeline should ALLOW, MODIFY, BLOCK,
    or ASK_USER.

    Backward-compatible properties (success, error, modified_args) and
    static methods (ok, fail) are provided so v1 handlers work without
    changes.
    """

    action: HookAction = HookAction.ALLOW
    modified_context: HookContext | None = None
    reason: str = ""
    hook_name: str = ""

    # -- Backward compatible properties (v1) --

    @property
    def success(self) -> bool:
        """True when the action is ALLOW or MODIFY."""
        return self.action in (HookAction.ALLOW, HookAction.MODIFY)

    @property
    def error(self) -> str | None:
        """Reason for failure when action is BLOCK or ASK_USER."""
        return None if self.success else self.reason

    @property
    def modified_args(self) -> dict[str, Any] | None:
        """Extract modified tool arguments from modified_context."""
        if self.modified_context is not None:
            return self.modified_context.tool_args or self.modified_context.tool_input
        return None

    # -- Backward compatible static methods (v1) --

    @staticmethod
    def ok(modified_args: dict[str, Any] | None = None) -> "HookResult":
        """Create an ALLOW result (or MODIFY when *modified_args* given)."""
        ctx: HookContext | None = None
        if modified_args is not None:
            ctx = HookContext(
                hook_type=HookType.PRE_TOOL_USE,
                tool_args=modified_args,
                tool_input=modified_args,
            )
        return HookResult(
            action=HookAction.ALLOW if modified_args is None else HookAction.MODIFY,
            modified_context=ctx,
        )

    @staticmethod
    def fail(message: str) -> "HookResult":
        """Create a BLOCK result with the given reason message."""
        return HookResult(action=HookAction.BLOCK, reason=message)

    # -- New v2 convenience constructors --

    @staticmethod
    def allow(hook_name: str = "") -> "HookResult":
        """Continue the pipeline (ALLOW)."""
        return HookResult(action=HookAction.ALLOW, hook_name=hook_name)

    @staticmethod
    def modify(
        context: "HookContext",
        hook_name: str = "",
        reason: str = "",
    ) -> "HookResult":
        """Pipeline should continue with a modified context."""
        return HookResult(
            action=HookAction.MODIFY,
            modified_context=context,
            hook_name=hook_name,
            reason=reason,
        )

    @staticmethod
    def block(reason: str, hook_name: str = "") -> "HookResult":
        """Stop the pipeline immediately."""
        return HookResult(action=HookAction.BLOCK, reason=reason, hook_name=hook_name)

    @staticmethod
    def ask_user(reason: str, hook_name: str = "") -> "HookResult":
        """Defer to user input."""
        return HookResult(
            action=HookAction.ASK_USER, reason=reason, hook_name=hook_name
        )


@dataclass
class Hook:
    """
    Hook definition.

    Defines when and how a hook should be executed.  The handler is
    called with a HookContext and must return a HookResult.
    """

    hook_id: str
    hook_type: HookType
    handler: Callable[["HookContext"], "HookResult"]
    description: str = ""
    tool_filter: str | None = None  # Tool name pattern (e.g., "Edit", "Write")
    file_pattern: str | None = None  # File pattern (e.g., "**/*.py")
    priority: int = 0  # Higher priority hooks run first
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def matches(self, context: HookContext) -> bool:
        """
        Check whether this hook should fire for the given context.

        Args:
            context: Hook context.

        Returns:
            True if the hook should fire.
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

    @staticmethod
    def _matches_pattern(value: str, pattern: str) -> bool:
        """Check *value* against *pattern* (supports ``*`` wildcard)."""
        import fnmatch

        return fnmatch.fnmatch(value, pattern)
