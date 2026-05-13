"""ProcessRegistry — single source of truth for all running agent processes."""
from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path
from typing import Callable

from .event_store import EventStore
from .models import AgentProcess
from .process_scanner import scan_agent_processes
from .session_reader import list_session_files, read_session_tokens, read_last_tool, extract_session_id

_DEFAULT_CONTEXT_LIMIT = 200_000


def _build_process(
    pid: int,
    session_id: str,
    project_path: str,
    *,
    store: EventStore | None = None,
) -> AgentProcess:
    tokens_in, tokens_out = 0, 0
    last_tool = ""

    root = Path.home() / ".claude" / "projects"
    for jsonl in list_session_files(root):
        if extract_session_id(jsonl) == session_id:
            tokens_in, tokens_out = read_session_tokens(jsonl)
            last_tool = read_last_tool(jsonl)
            break

    state = "running"
    if store:
        recent = store.tail(10, session_id=session_id)
        for ev in reversed(recent):
            if ev.hook_type == "PermissionRequest":
                state = "blocked"
                break
            elif ev.hook_type in ("PostToolUseFailure",):
                state = "error"
                break
            elif ev.hook_type in ("Stop", "SessionEnd"):
                state = "done"
                break

    return AgentProcess(
        pid=pid,
        session_id=session_id,
        project_path=project_path,
        state=state,
        current_tool=last_tool,
        context_tokens=tokens_in + tokens_out,
        context_limit=_DEFAULT_CONTEXT_LIMIT,
        context_pct=min(1.0, (tokens_in + tokens_out) / _DEFAULT_CONTEXT_LIMIT),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=0.0,
        elapsed_s=0.0,
        parent_session_id="",
        children=(),
        last_event_at=time.time(),
    )


class ProcessRegistry:
    """Live registry of all running agent processes."""

    def __init__(self, store: EventStore | None = None) -> None:
        self._store = store
        self._processes: dict[str, AgentProcess] = {}
        self._callbacks: list[Callable[[AgentProcess], None]] = []

    def refresh(self) -> None:
        """Scan OS processes and update registry."""
        raw_procs = scan_agent_processes()
        seen: set[str] = set()
        for rp in raw_procs:
            session_id = f"pid-{rp.pid}"
            seen.add(session_id)
            proc = _build_process(rp.pid, session_id, rp.cwd, store=self._store)
            self._processes[session_id] = proc
            for cb in self._callbacks:
                cb(proc)
        for sid in list(self._processes.keys()):
            if sid not in seen:
                old = self._processes[sid]
                done = replace(old, state="done")
                self._processes[sid] = done

    def get_all(self) -> list[AgentProcess]:
        return list(self._processes.values())

    def get(self, session_id: str) -> AgentProcess | None:
        return self._processes.get(session_id)

    def update_from_event(self, session_id: str, hook_type: str) -> None:
        """Update a single process's state from a hook event."""
        if session_id not in self._processes:
            return
        proc = self._processes[session_id]
        state_map = {
            "PermissionRequest": "blocked",
            "PostToolUseFailure": "error",
            "Stop": "done",
            "SessionEnd": "done",
            "PreToolUse": "running",
            "PostToolUse": "running",
            "SubagentStart": "running",
        }
        new_state = state_map.get(hook_type, proc.state)
        updated = replace(proc, state=new_state, last_event_at=time.time())
        self._processes[session_id] = updated
        for cb in self._callbacks:
            cb(updated)

    def subscribe(self, callback: Callable[[AgentProcess], None]) -> None:
        self._callbacks.append(callback)
