"""Hook data models."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HookType(str, Enum):
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    STOP = "Stop"


@dataclass(frozen=True)
class HookSpec:
    name: str
    hook_type: HookType
    command: str  # Shell command or Python callable path
    matcher: str = "*"  # Tool name pattern (glob)
    timeout_seconds: float = 30.0


@dataclass
class HookResult:
    hook_name: str
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    modified_input: dict[str, Any] | None = None  # For PreToolUse modifications
