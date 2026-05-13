"""Process tree for multi-agent transparency (Phase 4).

Tracks parent→child agent relationships using EventBus events and renders
them as a Rich Tree.  Designed to mirror ``pstree`` / ``ps -ejH`` semantics
for the Lyra agent hierarchy.

    ProcessTree.from_state_file(path)  — reconstruct from JSON snapshot
    ProcessTree.from_event_bus(bus)    — subscribe and update live

Key data model:
    root (session) → subagent A → subagent A1
                   → subagent B
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Enums / dataclasses
# ---------------------------------------------------------------------------


class AgentLifecycleState(str, Enum):
    PENDING = "pending"
    SPAWNING = "spawning"
    RUNNING = "running"
    VERIFYING = "verifying"
    PARKED = "parked"
    DONE = "done"
    FAILED = "failed"
    KILLED = "killed"
    STOPPED = "stopped"


@dataclass
class AgentNode:
    """One node in the process tree."""

    node_id: str
    parent_id: str | None
    role: str
    state: AgentLifecycleState = AgentLifecycleState.RUNNING
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    cost_usd: float = 0.0
    token_in: int = 0
    token_out: int = 0
    current_step: int = 0
    last_tool: str = "—"
    children: list[str] = field(default_factory=list)

    def elapsed_s(self) -> float:
        end = self.finished_at or time.time()
        return end - self.started_at

    def is_active(self) -> bool:
        return self.state in (
            AgentLifecycleState.RUNNING,
            AgentLifecycleState.VERIFYING,
            AgentLifecycleState.SPAWNING,
        )

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "parent_id": self.parent_id,
            "role": self.role,
            "state": self.state.value,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "cost_usd": self.cost_usd,
            "token_in": self.token_in,
            "token_out": self.token_out,
            "current_step": self.current_step,
            "last_tool": self.last_tool,
            "children": self.children,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AgentNode":
        state = AgentLifecycleState(d.get("state", "running"))
        return cls(
            node_id=d["node_id"],
            parent_id=d.get("parent_id"),
            role=d.get("role", "unknown"),
            state=state,
            started_at=d.get("started_at", time.time()),
            finished_at=d.get("finished_at"),
            cost_usd=d.get("cost_usd", 0.0),
            token_in=d.get("token_in", 0),
            token_out=d.get("token_out", 0),
            current_step=d.get("current_step", 0),
            last_tool=d.get("last_tool", "—"),
            children=d.get("children", []),
        )


# ---------------------------------------------------------------------------
# ProcessTree
# ---------------------------------------------------------------------------

_STATE_COLOR = {
    AgentLifecycleState.RUNNING: "green",
    AgentLifecycleState.VERIFYING: "yellow",
    AgentLifecycleState.SPAWNING: "blue",
    AgentLifecycleState.PARKED: "yellow",
    AgentLifecycleState.PENDING: "dim blue",
    AgentLifecycleState.DONE: "dim",
    AgentLifecycleState.FAILED: "red",
    AgentLifecycleState.KILLED: "red",
    AgentLifecycleState.STOPPED: "dim",
}


class ProcessTree:
    """Tracks the agent process hierarchy.

    Updates via :meth:`on_event` (connected to EventBus) or reconstructed
    from a JSON snapshot via :meth:`from_dict`.
    """

    def __init__(self, session_id: str = "") -> None:
        self.session_id = session_id
        self._nodes: dict[str, AgentNode] = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def ensure_root(self, session_id: str, role: str = "root") -> AgentNode:
        """Ensure the root (session) node exists."""
        if session_id not in self._nodes:
            node = AgentNode(node_id=session_id, parent_id=None, role=role)
            self._nodes[session_id] = node
            if not self.session_id:
                self.session_id = session_id
        return self._nodes[session_id]

    def spawn(self, agent_id: str, parent_id: str | None, role: str) -> AgentNode:
        node = AgentNode(
            node_id=agent_id,
            parent_id=parent_id,
            role=role,
            state=AgentLifecycleState.SPAWNING,
        )
        self._nodes[agent_id] = node
        if parent_id and parent_id in self._nodes:
            parent = self._nodes[parent_id]
            if agent_id not in parent.children:
                parent.children.append(agent_id)
        return node

    def transition(self, agent_id: str, state: AgentLifecycleState) -> None:
        node = self._nodes.get(agent_id)
        if node:
            node.state = state
            if state in (
                AgentLifecycleState.DONE,
                AgentLifecycleState.FAILED,
                AgentLifecycleState.KILLED,
                AgentLifecycleState.STOPPED,
            ):
                node.finished_at = time.time()

    def on_event(self, event: Any) -> None:
        """Update tree state from EventBus events."""
        from lyra_core.observability.event_bus import (
            LLMCallFinished,
            LLMCallStarted,
            StopHookFired,
            SubagentFinished,
            SubagentSpawned,
            ToolCallFinished,
            ToolCallStarted,
        )

        if isinstance(event, LLMCallStarted):
            root = self.ensure_root(event.session_id)
            root.current_step = event.turn
            root.state = AgentLifecycleState.RUNNING

        elif isinstance(event, LLMCallFinished):
            node = self._nodes.get(event.session_id)
            if node:
                node.token_in += event.input_tokens
                node.token_out += event.output_tokens

        elif isinstance(event, ToolCallStarted):
            node = self._nodes.get(event.session_id)
            if node:
                node.last_tool = event.tool_name

        elif isinstance(event, ToolCallFinished):
            pass  # cost is tracked at LLM level

        elif isinstance(event, SubagentSpawned):
            self.ensure_root(event.session_id)
            self.spawn(
                agent_id=event.agent_id,
                parent_id=event.session_id,
                role=event.agent_role,
            )
            self.transition(event.agent_id, AgentLifecycleState.RUNNING)

        elif isinstance(event, SubagentFinished):
            state = AgentLifecycleState(
                event.status if event.status in AgentLifecycleState._value2member_map_
                else "done"
            )
            self.transition(event.agent_id, state)
            node = self._nodes.get(event.agent_id)
            if node:
                node.cost_usd += event.cost_usd

        elif isinstance(event, StopHookFired):
            self.transition(event.session_id, AgentLifecycleState.STOPPED)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def roots(self) -> list[AgentNode]:
        return [n for n in self._nodes.values() if n.parent_id is None]

    def children_of(self, node_id: str) -> list[AgentNode]:
        node = self._nodes.get(node_id)
        if not node:
            return []
        return [self._nodes[c] for c in node.children if c in self._nodes]

    def all_nodes(self) -> list[AgentNode]:
        return list(self._nodes.values())

    def active_count(self) -> int:
        return sum(1 for n in self._nodes.values() if n.is_active())

    def total_cost(self) -> float:
        return sum(n.cost_usd for n in self._nodes.values())

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "nodes": {nid: node.to_dict() for nid, node in self._nodes.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ProcessTree":
        tree = cls(session_id=d.get("session_id", ""))
        for nid, nd in d.get("nodes", {}).items():
            tree._nodes[nid] = AgentNode.from_dict(nd)
        return tree

    @classmethod
    def from_state_file(cls, path: Path) -> "ProcessTree":
        """Reconstruct a ProcessTree from a .lyra/process_state.json snapshot."""
        data = json.loads(path.read_text())
        # Minimal reconstruction from flat state schema
        session_id = str(data.get("session_id", "unknown"))
        tree = cls(session_id=session_id)
        role = str(data.get("agent_role", "root"))
        status = str(data.get("status", "running"))
        try:
            state = AgentLifecycleState(status)
        except ValueError:
            state = AgentLifecycleState.RUNNING
        node = AgentNode(
            node_id=session_id,
            parent_id=None,
            role=role,
            state=state,
            token_in=int(data.get("token_in", 0)),
            current_step=int(data.get("current_step", 0)),
        )
        last = data.get("last_tool") or {}
        node.last_tool = str(last.get("name", "—"))
        tree._nodes[session_id] = node
        return tree

    # ------------------------------------------------------------------
    # Rich rendering
    # ------------------------------------------------------------------

    def render(self) -> "rich.tree.Tree":  # type: ignore[name-defined]
        from rich.tree import Tree

        label = f"[bold]Lyra Process Tree[/bold]  session={self.session_id or '?'}  active={self.active_count()}"
        rich_tree = Tree(label)

        def _add(parent_rich, node: AgentNode) -> None:
            color = _STATE_COLOR.get(node.state, "white")
            elapsed = int(node.elapsed_s())
            line = (
                f"[{color}]{node.role}[/{color}]"
                f"  [{color}]{node.state.value}[/{color}]"
                f"  step={node.current_step}"
                f"  tok_in={node.token_in:,}"
                f"  elapsed={elapsed}s"
                f"  last={node.last_tool}"
            )
            branch = parent_rich.add(line)
            for child in self.children_of(node.node_id):
                _add(branch, child)

        for root in self.roots():
            _add(rich_tree, root)

        if not self.roots():
            rich_tree.add("[dim]No agents tracked yet[/dim]")

        return rich_tree


__all__ = [
    "AgentLifecycleState",
    "AgentNode",
    "ProcessTree",
]
