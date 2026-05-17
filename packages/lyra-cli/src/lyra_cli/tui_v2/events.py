"""Lyra-specific TUI events extending harness-tui events."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ContextCompacted:
    """Emitted when context window is compacted.

    This event is fired after successful context compaction to provide
    visibility into memory management. Displays token savings and
    preservation details to the user.
    """
    turn_id: str
    utilisation_before: float  # 0.0-1.0
    utilisation_after: float   # 0.0-1.0
    tokens_before: int
    tokens_after: int
    turns_preserved: int
    turns_summarized: int
    reason: str  # "proactive" | "urgent" | "manual"


__all__ = ["ContextCompacted"]
