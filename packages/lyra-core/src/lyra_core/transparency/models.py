"""Transparency layer data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class HookEvent:
    """A single hook event received from Claude Code / Lyra."""
    event_id: str
    session_id: str
    hook_type: str
    tool_name: str        # empty string if not a tool event
    payload_json: str     # JSON-serialised payload (str avoids mutable-dict in dataclass)
    received_at: float    # Unix timestamp


@dataclass(frozen=True)
class AgentProcess:
    """Live state of a single agent process."""
    pid: int
    session_id: str
    project_path: str
    state: Literal["running", "waiting", "blocked", "error", "done", "idle"]
    current_tool: str
    context_tokens: int
    context_limit: int
    context_pct: float
    tokens_in: int
    tokens_out: int
    cost_usd: float
    elapsed_s: float
    parent_session_id: str    # empty string if root
    children: tuple[str, ...] # session IDs of direct children
    last_event_at: float


@dataclass(frozen=True)
class ToolEvent:
    """One tool call lifecycle record."""
    event_id: str
    session_id: str
    hook_type: Literal["PreToolUse", "PostToolUse", "PostToolUseFailure"]
    tool_name: str
    args_preview: str
    result_preview: str
    status: Literal["pending", "success", "error", "blocked"]
    duration_ms: int
    timestamp: float


@dataclass(frozen=True)
class SessionCost:
    """Accumulated token/cost totals for one session."""
    session_id: str
    tokens_in: int
    tokens_out: int
    tokens_cache_read: int
    tokens_cache_write: int
    cost_usd: float
