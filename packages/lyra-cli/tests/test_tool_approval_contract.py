"""Wave-D Task 7: tool-approval prompt cached per session.

The REPL holds a single :class:`ToolApprovalCache` instance. When a
high-risk tool (Edit, Shell, Write, …) is about to fire and the
session's permission mode is ``normal`` or ``strict``, the cache
asks: have we approved this tool *for this session* yet? If yes, the
call proceeds. If no, an inquiry returns ``"deny"`` (the parent UI
prompts the user) and only an explicit
``cache.approve(tool_name)`` flips the bit.

Six RED tests:

1. New cache returns ``"prompt"`` for unknown tools.
2. After ``approve(name)`` the same tool returns ``"allow"``.
3. ``deny(name)`` returns ``"deny"`` and is sticky.
4. ``yolo`` mode short-circuits to ``"allow"`` regardless of cache state.
5. ``strict`` mode forces a re-prompt every call (no caching).
6. ``forget(name)`` removes a previous decision so the next inquiry
   re-prompts again.
"""
from __future__ import annotations

import pytest


def test_unknown_tool_returns_prompt() -> None:
    from lyra_cli.interactive.tool_approval import ToolApprovalCache

    cache = ToolApprovalCache(mode="normal")
    assert cache.inquire("Edit") == "prompt"


def test_approve_then_inquiry_returns_allow() -> None:
    from lyra_cli.interactive.tool_approval import ToolApprovalCache

    cache = ToolApprovalCache(mode="normal")
    cache.approve("Edit")
    assert cache.inquire("Edit") == "allow"


def test_deny_is_sticky() -> None:
    from lyra_cli.interactive.tool_approval import ToolApprovalCache

    cache = ToolApprovalCache(mode="normal")
    cache.deny("Shell")
    assert cache.inquire("Shell") == "deny"
    assert cache.inquire("Shell") == "deny"


def test_yolo_short_circuits_to_allow() -> None:
    from lyra_cli.interactive.tool_approval import ToolApprovalCache

    cache = ToolApprovalCache(mode="yolo")
    assert cache.inquire("Edit") == "allow"
    assert cache.inquire("Shell") == "allow"


def test_strict_always_reprompts() -> None:
    from lyra_cli.interactive.tool_approval import ToolApprovalCache

    cache = ToolApprovalCache(mode="strict")
    cache.approve("Edit")
    # Still prompts — strict mode never trusts the cache.
    assert cache.inquire("Edit") == "prompt"


def test_forget_clears_decision() -> None:
    from lyra_cli.interactive.tool_approval import ToolApprovalCache

    cache = ToolApprovalCache(mode="normal")
    cache.approve("Edit")
    cache.forget("Edit")
    assert cache.inquire("Edit") == "prompt"
