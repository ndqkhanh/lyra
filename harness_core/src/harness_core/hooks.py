"""Hook system: pre/post tool-use handlers that can block or annotate."""
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Callable, Optional

from .messages import ToolCall, ToolResult


class HookEvent(str, enum.Enum):
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    STOP = "Stop"


@dataclass
class HookDecision:
    """Outcome of a hook invocation."""

    block: bool = False
    reason: str = ""
    annotation: str = ""  # additional text to add to the tool result / transcript


Handler = Callable[[ToolCall, Optional[ToolResult]], HookDecision]


@dataclass
class Hook:
    name: str
    event: HookEvent
    matcher: str = "*"  # fnmatch pattern on tool name
    handler: Optional[Handler] = None


class HookRegistry:
    def __init__(self) -> None:
        self._hooks: list[Hook] = []

    def register(self, hook: Hook) -> None:
        if hook.handler is None:
            raise ValueError(f"Hook {hook.name!r} has no handler")
        self._hooks.append(hook)

    def run(
        self,
        event: HookEvent,
        call: ToolCall,
        result: Optional[ToolResult] = None,
    ) -> HookDecision:
        """Run all hooks for an event in registration order. First block wins."""
        import fnmatch

        combined = HookDecision(block=False, reason="", annotation="")
        for h in self._hooks:
            if h.event != event:
                continue
            if not (fnmatch.fnmatchcase(call.name, h.matcher) or h.matcher == "*"):
                continue
            assert h.handler is not None  # registered guarantees this
            d = h.handler(call, result)
            if d.annotation:
                combined.annotation = (
                    f"{combined.annotation}\n{d.annotation}".strip()
                )
            if d.block:
                return HookDecision(
                    block=True,
                    reason=f"{h.name}: {d.reason}",
                    annotation=combined.annotation,
                )
        return combined
