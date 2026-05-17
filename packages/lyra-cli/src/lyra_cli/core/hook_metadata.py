"""Hook metadata models."""
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class HookType(Enum):
    """Hook execution types."""
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    STOP = "Stop"
    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"
    PRE_COMPACT = "PreCompact"


@dataclass
class HookMetadata:
    """Metadata for a hook."""

    name: str
    description: str
    hook_type: HookType
    script: str
    enabled: bool = True
    file_path: Optional[str] = None
