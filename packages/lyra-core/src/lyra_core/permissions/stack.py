"""Wave-D Task 6: layered :class:`PermissionStack`.

The destructive-pattern, secrets-scan and prompt-injection hooks
all live as standalone callables; the agent loop has historically
called them one-by-one. This stack collapses them into a single
guarded surface that the loop (and ``/tools approve`` Wave-D Task 7)
can call once.

The stack is **mode-aware** — Wave-C added a per-session
``permission_mode`` field (``normal | strict | yolo``); the stack
honours those modes uniformly:

* ``yolo`` — short-circuit to allow.
* ``normal`` — run all guards and block on the first failure.
* ``strict`` — same as ``normal`` today, kept distinct so we can
  layer extra rules in a future wave (e.g., always-deny ``Shell``).

Returns a :class:`StackDecision` with the *first* offending guard's
name + reason so the REPL can render "blocked by destructive: rm -rf /"
without reading multiple decisions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from harness_core.hooks import HookDecision
from harness_core.messages import ToolCall

from lyra_core.hooks.destructive_pattern import destructive_pattern_hook
from lyra_core.hooks.secrets_scan import secrets_scan_hook

from .injection import injection_guard


PermissionMode = Literal["normal", "strict", "yolo"]


@dataclass
class StackInput:
    """One pre/post-tool checkpoint passed to the stack."""

    tool_name: str
    args: dict[str, Any]
    output: str | None = None  # populated for post-tool checks


@dataclass
class StackDecision:
    """Verdict emitted by :meth:`PermissionStack.check`."""

    block: bool
    guard: str | None = None
    reason: str | None = None


_GUARDS_PRE: tuple[tuple[str, Any], ...] = (
    ("destructive", destructive_pattern_hook),
    ("secrets", secrets_scan_hook),
)


class PermissionStack:
    """Combine the three guards (+ mode awareness) behind one ``check``."""

    def __init__(self, *, mode: PermissionMode = "normal") -> None:
        self.mode = mode

    def set_mode(self, mode: PermissionMode) -> None:
        """Update the live permission mode (REPL flips this via Alt+M)."""
        self.mode = mode

    # ------------------------------------------------------------------ check
    def check(self, inp: StackInput) -> StackDecision:
        if self.mode == "yolo":
            return StackDecision(block=False)

        # Synthesize a ToolCall for the harness_core hooks. The id is
        # stable-but-unique so we don't surface random ids in test output.
        call = ToolCall(
            id=f"stack-{inp.tool_name}",
            name=inp.tool_name,
            args=dict(inp.args or {}),
        )

        for name, hook in _GUARDS_PRE:
            verdict: HookDecision = hook(call, None)
            if verdict.block:
                return StackDecision(
                    block=True,
                    guard=name,
                    reason=verdict.reason or f"{name} guard blocked the call",
                )

        if inp.output:
            inj = injection_guard(inp.output)
            if inj.block:
                return StackDecision(
                    block=True,
                    guard="injection",
                    reason=inj.reason,
                )

        return StackDecision(block=False)


__all__ = [
    "PermissionMode",
    "PermissionStack",
    "StackDecision",
    "StackInput",
]
