"""Tool call timeline — ordered sequence of ToolEvent records."""
from __future__ import annotations

import json
import time
from typing import Optional

from .event_store import EventStore
from .models import HookEvent, ToolEvent


def _args_preview(payload_json: str, max_len: int = 80) -> str:
    try:
        payload = json.loads(payload_json)
        args = payload.get("args") or payload.get("tool_input") or {}
        if isinstance(args, dict):
            preview = ", ".join(f"{k}={str(v)[:30]}" for k, v in list(args.items())[:3])
        else:
            preview = str(args)[:max_len]
    except Exception:
        preview = ""
    return preview[:max_len]


def _result_preview(payload_json: str, max_len: int = 80) -> str:
    try:
        payload = json.loads(payload_json)
        result = payload.get("result") or payload.get("output") or ""
        preview = str(result).strip()[:max_len]
        return preview.replace("\n", " ")
    except Exception:
        return ""


def build_tool_timeline(
    store: EventStore,
    *,
    session_id: Optional[str] = None,
    n: int = 100,
) -> list[ToolEvent]:
    """Build an ordered tool call timeline from hook events."""
    raw_events = store.tail(n * 3, session_id=session_id)
    tool_events: list[ToolEvent] = []
    pending: dict[str, HookEvent] = {}

    for ev in raw_events:
        if ev.hook_type == "PreToolUse":
            pending[ev.session_id + ev.tool_name] = ev
            tool_events.append(
                ToolEvent(
                    event_id=ev.event_id,
                    session_id=ev.session_id,
                    hook_type="PreToolUse",
                    tool_name=ev.tool_name,
                    args_preview=_args_preview(ev.payload_json),
                    result_preview="",
                    status="pending",
                    duration_ms=0,
                    timestamp=ev.received_at,
                )
            )
        elif ev.hook_type in ("PostToolUse", "PostToolUseFailure"):
            key = ev.session_id + ev.tool_name
            pre_ev = pending.pop(key, None)
            duration_ms = 0
            if pre_ev:
                duration_ms = int((ev.received_at - pre_ev.received_at) * 1000)
            status = "success" if ev.hook_type == "PostToolUse" else "error"
            tool_events.append(
                ToolEvent(
                    event_id=ev.event_id,
                    session_id=ev.session_id,
                    hook_type=ev.hook_type,  # type: ignore[arg-type]
                    tool_name=ev.tool_name,
                    args_preview=_args_preview(ev.payload_json),
                    result_preview=_result_preview(ev.payload_json),
                    status=status,
                    duration_ms=duration_ms,
                    timestamp=ev.received_at,
                )
            )
        elif ev.hook_type == "PermissionRequest":
            tool_events.append(
                ToolEvent(
                    event_id=ev.event_id,
                    session_id=ev.session_id,
                    hook_type="PreToolUse",
                    tool_name=ev.tool_name,
                    args_preview=_args_preview(ev.payload_json),
                    result_preview="",
                    status="blocked",
                    duration_ms=0,
                    timestamp=ev.received_at,
                )
            )

    return tool_events[-n:]
