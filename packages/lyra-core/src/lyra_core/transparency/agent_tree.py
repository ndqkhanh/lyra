"""Subagent tree builder — parent-child agent hierarchy from SubagentStart events."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from .event_store import EventStore


@dataclass
class TreeNode:
    """One node in the subagent tree."""
    session_id: str
    parent_id: str       # empty string if root
    state: str           # from latest event
    cost_usd: float
    tokens_total: int
    children: list["TreeNode"] = field(default_factory=list)

    def total_cost(self) -> float:
        return self.cost_usd + sum(c.total_cost() for c in self.children)

    def total_tokens(self) -> int:
        return self.tokens_total + sum(c.total_tokens() for c in self.children)


def build_agent_tree(store: EventStore) -> list[TreeNode]:
    """Build parent-child tree from SubagentStart events. Returns root nodes."""
    events = store.tail(500)
    nodes: dict[str, TreeNode] = {}
    parent_map: dict[str, str] = {}

    for ev in events:
        if ev.hook_type == "SubagentStart":
            try:
                payload = json.loads(ev.payload_json)
                parent_id = payload.get("parent_session_id", "")
            except Exception:
                parent_id = ""
            if ev.session_id not in nodes:
                nodes[ev.session_id] = TreeNode(
                    session_id=ev.session_id,
                    parent_id=parent_id,
                    state="running",
                    cost_usd=0.0,
                    tokens_total=0,
                )
            parent_map[ev.session_id] = parent_id

        elif ev.hook_type == "SubagentStop":
            if ev.session_id in nodes:
                nodes[ev.session_id].state = "done"

        elif ev.hook_type == "SessionStart" and ev.session_id not in nodes:
            nodes[ev.session_id] = TreeNode(
                session_id=ev.session_id,
                parent_id="",
                state="running",
                cost_usd=0.0,
                tokens_total=0,
            )

    for node in nodes.values():
        parent_id = node.parent_id
        if parent_id and parent_id in nodes:
            parent = nodes[parent_id]
            if node not in parent.children:
                parent.children.append(node)

    roots = [n for n in nodes.values() if not n.parent_id or n.parent_id not in nodes]
    return roots


def render_tree_text(roots: list[TreeNode], *, indent: int = 0) -> str:
    """Render agent tree as Rich-marked text."""
    if not roots:
        return "[dim](no subagent tree data)[/]"
    lines: list[str] = []
    for i, node in enumerate(roots):
        is_last = (i == len(roots) - 1)
        _render_node(node, lines, prefix="", is_last=is_last)
    return "\n".join(lines)


def _render_node(node: TreeNode, lines: list[str], prefix: str, is_last: bool) -> None:
    connector = "└── " if is_last else "├── "
    state_colors = {
        "running": "green", "blocked": "orange1", "error": "red",
        "done": "dim", "waiting": "yellow",
    }
    color = state_colors.get(node.state, "white")
    sid = node.session_id[-14:] if len(node.session_id) > 14 else node.session_id
    cost = f"[dim]${node.total_cost():.3f}[/]"
    lines.append(f"{prefix}{connector}[{color}]{sid}[/] [{node.state}] {cost}")
    child_prefix = prefix + ("    " if is_last else "│   ")
    for j, child in enumerate(node.children):
        _render_node(child, lines, child_prefix, j == len(node.children) - 1)
