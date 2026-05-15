"""Lightweight status source for the slim REPL footer.

The footer row in Claude-Code/opencode-style CLIs shows a one-line
contextual status: ``cwd · mode · model · LSP:N · MCP:M``. We centralize
the source of truth in :class:`StatusSource` so the AgentLoop (or any
other owner) can ``update(...)`` it without the REPL knowing the
producer's internals. The REPL's bottom-toolbar function calls
:meth:`render` each refresh.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Literal


@dataclass
class SubAgentRecord:
    """One tracked sub-agent shown in the agent panel below the spinner."""

    agent_id: str
    role: str
    description: str
    started_at: float
    tokens_down: int = 0
    state: str = "running"  # "running" | "done" | "error"


@dataclass
class TaskItem:
    """One tracked sub-task shown in the checklist below the spinner."""

    id: str
    description: str
    state: Literal["pending", "running", "done"] = "pending"


_TURN_VERBS = [
    "Thinking", "Researching", "Analyzing", "Galloping",
    "Reasoning", "Exploring", "Synthesizing", "Planning",
]


@dataclass
class StatusSource:
    """Shared bag of footer-line fields.

    Fields are plain strings (or integers for counts). All writes go
    through :meth:`update` to stay thread-safe since the AgentLoop may
    run plugins on worker threads.
    """

    cwd: Path = field(default_factory=Path.cwd)
    mode: str = "edit_automatically"
    model: str = "unknown"
    permissions: str = ""  # "" | "normal" | "strict" | "yolo" — empty hides the field
    lsp_count: int = 0
    mcp_count: int = 0
    tokens: int = 0
    cost_usd: float = 0.0
    turn: int = 0
    branch: str = ""
    session_id: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    # Per-turn token download counter (resets on reset_turn)
    tokens_down_turn: int = 0
    # Active background agent count (synced from ProcessRegistry)
    bg_task_count: int = 0
    # Rotating verb shown in the spinner header
    current_verb: str = "Thinking"
    # Sub-task checklist (cleared each turn)
    task_list: list[TaskItem] = field(default_factory=list)
    # Active sub-agent records shown in the agent panel
    sub_agents: list[SubAgentRecord] = field(default_factory=list)

    _lock: Lock = field(default_factory=Lock, repr=False)
    _verb_idx: int = field(default=0, repr=False)

    def update(self, **kv: object) -> None:
        """Update any subset of fields atomically."""
        with self._lock:
            for key, value in kv.items():
                if key == "extra" and isinstance(value, dict):
                    self.extra.update({str(k): str(v) for k, v in value.items()})
                elif hasattr(self, key):
                    setattr(self, key, value)

    def reset_turn(self) -> None:
        """Called on TurnStarted — clears per-turn counters and advances verb."""
        with self._lock:
            self.tokens_down_turn = 0
            self.task_list.clear()
            self._verb_idx = (self._verb_idx + 1) % len(_TURN_VERBS)
            self.current_verb = _TURN_VERBS[self._verb_idx]

    def add_task(self, task_id: str, description: str) -> None:
        """Register a new sub-task in the checklist (deduplicates by id)."""
        with self._lock:
            if any(t.id == task_id for t in self.task_list):
                return
            self.task_list.append(TaskItem(id=task_id, description=description))

    def start_task(self, task_id: str) -> None:
        """Mark a task as running."""
        with self._lock:
            for t in self.task_list:
                if t.id == task_id:
                    t.state = "running"
                    return

    def complete_task(self, task_id: str) -> None:
        """Mark a task as done."""
        with self._lock:
            for t in self.task_list:
                if t.id == task_id:
                    t.state = "done"
                    return

    def snapshot_tasks(self) -> list[TaskItem]:
        """Return a thread-safe snapshot of the task list."""
        with self._lock:
            return [
                TaskItem(id=t.id, description=t.description, state=t.state)
                for t in self.task_list
            ]

    # ----- sub-agent panel API -------------------------------------------

    def add_sub_agent(self, record: SubAgentRecord) -> None:
        """Register a sub-agent record (deduplicates by agent_id)."""
        with self._lock:
            if any(r.agent_id == record.agent_id for r in self.sub_agents):
                return
            self.sub_agents = [*self.sub_agents, record]

    def update_sub_agent(self, agent_id: str, **kwargs: object) -> None:
        """Update fields on a sub-agent record by agent_id (immutable replace)."""
        with self._lock:
            self.sub_agents = [
                SubAgentRecord(**{**vars(r), **kwargs})
                if r.agent_id == agent_id
                else r
                for r in self.sub_agents
            ]

    def remove_sub_agent(self, agent_id: str) -> None:
        """Remove a sub-agent record by agent_id."""
        with self._lock:
            self.sub_agents = [r for r in self.sub_agents if r.agent_id != agent_id]

    def active_sub_agents(self) -> list[SubAgentRecord]:
        """Return a snapshot of sub-agents currently in 'running' state."""
        with self._lock:
            return [r for r in self.sub_agents if r.state == "running"]

    def render(self, *, max_width: int | None = None) -> str:
        """Return the compact footer string.

        The cwd is shortened with ``~`` expansion so even deep paths
        fit; numeric fields are hidden when zero so the footer doesn't
        shout ``LSP:0 · MCP:0`` at users who aren't using them.
        """
        with self._lock:
            cwd = str(self.cwd)
            home = str(Path.home())
            if cwd.startswith(home):
                cwd = "~" + cwd[len(home):]

            parts = [f"cwd:{cwd}", f"mode:{self.mode}", f"model:{self.model}"]
            if self.lsp_count:
                parts.append(f"LSP:{self.lsp_count}")
            if self.mcp_count:
                parts.append(f"MCP:{self.mcp_count}")
            if self.tokens:
                parts.append(f"{self.tokens} tokens")
            if self.cost_usd:
                parts.append(f"${self.cost_usd:.2f}")
            if self.bg_task_count:
                label = "task" if self.bg_task_count == 1 else "tasks"
                parts.append(f"{self.bg_task_count} background {label}")
            for key, value in self.extra.items():
                parts.append(f"{key}:{value}")

        line = " · ".join(parts)
        if max_width is not None and len(line) > max_width:
            line = line[: max_width - 1] + "…"
        return line

    @classmethod
    def from_env(cls) -> StatusSource:
        """Factory that populates sensible defaults from the environment."""
        return cls(
            cwd=Path(os.environ.get("PWD", Path.cwd())),
            mode=os.environ.get("OPEN_HARNESS_MODE", "edit_automatically"),
            model=os.environ.get("OPEN_HARNESS_MODEL", "unknown"),
        )


__all__ = ["StatusSource", "SubAgentRecord", "TaskItem"]
