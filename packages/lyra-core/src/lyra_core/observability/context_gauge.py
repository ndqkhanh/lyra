"""Context saturation gauge, skill activation panel, and agent DAG (Phase 8).

Three complementary transparency primitives:

  ContextGauge   — tracks token usage against the context window cap;
                   renders a fill bar with per-zone breakdown (prompt /
                   cached / output) and a saturation percentage alert.

  SkillPanel     — tracks which skills were activated this session and
                   when; renders a Rich Table with activation timestamps
                   and usage counts.

  AgentDAG       — directed acyclic graph of agent spawn relationships;
                   renders as a Rich Tree (same visual as ProcessTree but
                   edges are explicit and can carry metadata like cost).

All three expose ``on_event(event)`` so they can attach to the EventBus
inline alongside LiveDisplay, or be queried from a snapshot.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# ContextGauge
# ---------------------------------------------------------------------------

_DEFAULT_WINDOW = 200_000  # tokens — Claude Sonnet 4 / DeepSeek-V3


@dataclass
class ContextGauge:
    """Tracks token consumption against the context window cap.

    Updates from ``LLMCallStarted`` (prompt_tokens) and
    ``LLMCallFinished`` (input/output/cache breakdown).
    """

    max_tokens: int = _DEFAULT_WINDOW

    prompt_tokens: int = 0
    cache_tokens: int = 0
    output_tokens: int = 0

    # History for saturation trend (last 10 readings)
    _history: list[float] = field(default_factory=list, repr=False)

    def update_from_started(self, prompt_tokens: int) -> None:
        self.prompt_tokens = prompt_tokens
        self._record()

    def update_from_finished(
        self, input_tokens: int, output_tokens: int, cache_tokens: int
    ) -> None:
        self.prompt_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cache_tokens = cache_tokens
        self._record()

    def used_tokens(self) -> int:
        return self.prompt_tokens + self.output_tokens

    def saturation_pct(self) -> float:
        return min(100.0, self.used_tokens() * 100.0 / max(1, self.max_tokens))

    def cache_hit_pct(self) -> float:
        return min(100.0, self.cache_tokens * 100.0 / max(1, self.prompt_tokens))

    def is_saturated(self) -> bool:
        return self.saturation_pct() >= 80.0

    def trend(self) -> str:
        """Return 'rising', 'falling', or 'stable' from last 3 readings."""
        if len(self._history) < 2:
            return "stable"
        delta = self._history[-1] - self._history[-3 if len(self._history) >= 3 else -2]
        if delta > 2.0:
            return "rising"
        if delta < -2.0:
            return "falling"
        return "stable"

    def _record(self) -> None:
        self._history.append(self.saturation_pct())
        if len(self._history) > 10:
            self._history.pop(0)

    def render(self) -> "rich.panel.Panel":  # type: ignore[name-defined]
        from rich import box
        from rich.columns import Columns
        from rich.panel import Panel
        from rich.progress import BarColumn, Progress, TextColumn
        from rich.text import Text

        pct = self.saturation_pct()
        if pct >= 95:
            color = "red"
        elif pct >= 80:
            color = "orange1"
        elif pct >= 50:
            color = "yellow"
        else:
            color = "green"

        prog = Progress(
            TextColumn("[dim]{task.description}"),
            BarColumn(bar_width=30),
            TextColumn(f"[{color}]{{task.percentage:>4.1f}}%[/]"),
            expand=False,
        )
        prog.add_task("context", total=self.max_tokens, completed=self.used_tokens())

        info = Text()
        info.append(f"prompt: {self.prompt_tokens:,}  ", style="dim")
        info.append(f"output: {self.output_tokens:,}  ", style="dim")
        cache_color = "green" if self.cache_hit_pct() >= 50 else "yellow"
        info.append(f"cache: {self.cache_tokens:,} ({self.cache_hit_pct():.0f}%)", style=cache_color)
        trend = self.trend()
        trend_sym = {"rising": "↑", "falling": "↓", "stable": "→"}.get(trend, "→")
        info.append(f"  {trend_sym}", style="dim")

        return Panel(
            Columns([prog, info]),
            title="Context Saturation",
            box=box.ROUNDED,
        )

    def on_event(self, event: Any) -> None:
        try:
            from lyra_core.observability.event_bus import LLMCallFinished, LLMCallStarted
        except ImportError:
            return
        if isinstance(event, LLMCallStarted):
            self.update_from_started(event.prompt_tokens)
        elif isinstance(event, LLMCallFinished):
            self.update_from_finished(event.input_tokens, event.output_tokens,
                                      event.cache_read_tokens)


# ---------------------------------------------------------------------------
# SkillPanel
# ---------------------------------------------------------------------------


@dataclass
class SkillEntry:
    name: str
    activated_at: float = field(default_factory=time.time)
    use_count: int = 1

    def activated_str(self) -> str:
        return datetime.fromtimestamp(self.activated_at, tz=timezone.utc).strftime("%H:%M:%S")


class SkillPanel:
    """Tracks which skills were activated this session."""

    def __init__(self) -> None:
        self._skills: dict[str, SkillEntry] = {}

    def activate(self, name: str) -> None:
        if name in self._skills:
            self._skills[name].use_count += 1
        else:
            self._skills[name] = SkillEntry(name=name)

    def active_skills(self) -> list[SkillEntry]:
        return sorted(self._skills.values(), key=lambda e: e.activated_at)

    def total_activations(self) -> int:
        return sum(e.use_count for e in self._skills.values())

    def render(self) -> "rich.panel.Panel":  # type: ignore[name-defined]
        from rich import box
        from rich.panel import Panel
        from rich.table import Table

        table = Table(box=box.SIMPLE, expand=True, show_header=True)
        table.add_column("Skill", overflow="fold")
        table.add_column("Activated", width=9, style="dim")
        table.add_column("Uses", justify="right", width=5)

        for entry in self.active_skills():
            table.add_row(entry.name, entry.activated_str(), str(entry.use_count))

        if not self._skills:
            table.add_row("[dim]No skills activated yet[/dim]", "—", "—")

        return Panel(table, title="Skills", box=box.ROUNDED)

    def on_event(self, _event: Any) -> None:
        # SkillActivated events are not yet in the core EventBus;
        # callers drive activate() directly or from custom events.
        pass


# ---------------------------------------------------------------------------
# AgentDAG
# ---------------------------------------------------------------------------


@dataclass
class DAGEdge:
    parent_id: str
    child_id: str
    spawned_at: float = field(default_factory=time.time)
    cost_usd: float = 0.0


@dataclass
class DAGNode:
    node_id: str
    role: str
    status: str = "running"
    cost_usd: float = 0.0
    spawned_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "role": self.role,
            "status": self.status,
            "cost_usd": self.cost_usd,
        }


class AgentDAG:
    """Explicit directed acyclic graph of agent spawn relationships.

    Edges carry spawn metadata (timestamp, cost) for cost attribution.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, DAGNode] = {}
        self._edges: list[DAGEdge] = []

    def add_node(self, node_id: str, role: str) -> DAGNode:
        if node_id not in self._nodes:
            self._nodes[node_id] = DAGNode(node_id=node_id, role=role)
        return self._nodes[node_id]

    def add_edge(self, parent_id: str, child_id: str) -> DAGEdge:
        edge = DAGEdge(parent_id=parent_id, child_id=child_id)
        self._edges.append(edge)
        return edge

    def children_of(self, node_id: str) -> list[DAGNode]:
        child_ids = {e.child_id for e in self._edges if e.parent_id == node_id}
        return [self._nodes[cid] for cid in child_ids if cid in self._nodes]

    def roots(self) -> list[DAGNode]:
        child_ids = {e.child_id for e in self._edges}
        return [n for nid, n in self._nodes.items() if nid not in child_ids]

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return len(self._edges)

    def total_cost(self) -> float:
        return sum(n.cost_usd for n in self._nodes.values())

    def on_event(self, event: Any) -> None:
        try:
            from lyra_core.observability.event_bus import (
                LLMCallStarted,
                SubagentFinished,
                SubagentSpawned,
            )
        except ImportError:
            return

        if isinstance(event, LLMCallStarted):
            self.add_node(event.session_id, "root")

        elif isinstance(event, SubagentSpawned):
            self.add_node(event.session_id, "root")
            self.add_node(event.agent_id, event.agent_role)
            self.add_edge(event.session_id, event.agent_id)

        elif isinstance(event, SubagentFinished):
            node = self._nodes.get(event.agent_id)
            if node:
                node.status = event.status
                node.cost_usd += event.cost_usd

    def render(self) -> "rich.tree.Tree":  # type: ignore[name-defined]
        from rich.tree import Tree

        label = (
            f"[bold]Agent DAG[/bold]  nodes={self.node_count()}"
            f"  edges={self.edge_count()}"
            f"  cost=${self.total_cost():.4f}"
        )
        rich_tree = Tree(label)

        _STATUS_COLOR = {
            "running": "green",
            "done": "dim",
            "failed": "red",
            "stopped": "dim",
        }

        def _add(parent_branch: Any, node: DAGNode) -> None:
            color = _STATUS_COLOR.get(node.status, "white")
            line = (
                f"[{color}]{node.role}[/{color}]  "
                f"[dim]{node.node_id[:16]}[/dim]  "
                f"status={node.status}  cost=${node.cost_usd:.4f}"
            )
            branch = parent_branch.add(line)
            for child in self.children_of(node.node_id):
                _add(branch, child)

        for root in self.roots():
            _add(rich_tree, root)

        if not self._nodes:
            rich_tree.add("[dim]No agents tracked yet[/dim]")

        return rich_tree

    def to_dict(self) -> dict:
        return {
            "nodes": {nid: n.to_dict() for nid, n in self._nodes.items()},
            "edges": [
                {"parent": e.parent_id, "child": e.child_id, "cost_usd": e.cost_usd}
                for e in self._edges
            ],
        }


__all__ = [
    "AgentDAG",
    "ContextGauge",
    "DAGEdge",
    "DAGNode",
    "SkillEntry",
    "SkillPanel",
]
