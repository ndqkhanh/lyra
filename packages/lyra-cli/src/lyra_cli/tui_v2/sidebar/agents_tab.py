"""AgentsTab — live sub-agents panel matching Claude Code's agent list style.

Replaces the earlier stub with a fully functional widget:

  ⏺ main                                   ↑/↓ to select · Enter to view
  ◯ general-purpose  Deep research: Kilo…  3m 04s · ↓ 63.6k tokens
  ◯ executor         Implement auth flow…    45s · ↓ 12.1k tokens

Data comes from ``ProcessRegistry`` (polled every second). Keyboard nav
selects an agent; Enter pushes ``AgentDetailModal`` on the Textual app.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import Static

_MAX_AGENTS = 8
_TYPE_COL_WIDTH = 16
_DESC_COL_WIDTH = 40


def _infer_agent_type(session_id: str) -> str:
    sid = session_id.lower()
    for keyword in ("executor", "researcher", "planner", "architect", "reviewer", "debugger"):
        if keyword in sid:
            return keyword
    return "general-purpose"


def _fmt_elapsed(secs: float) -> str:
    m, s = divmod(int(secs), 60)
    return f"{m}m {s:02d}s" if m else f"{s}s"


def _humanise_tokens(n: int) -> str:
    if n < 1_000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1_000:.1f}k"
    return f"{n / 1_000_000:.1f}M"


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def _render_agents(agents: list, selected_idx: int) -> str:
    """Render agent list with tree-style hierarchy and current operations."""
    if not agents:
        return "[dim](no background agents)[/]"

    nav_hint = "[dim]↑/↓ to select · Enter to view[/]"
    lines = [f"  [green]⏺[/] [bold]main[/]   {nav_hint}"]

    for i, proc in enumerate(agents[:_MAX_AGENTS]):
        is_selected = i == selected_idx
        dot = "[green]⏺[/]" if is_selected else "[dim]◯[/]"

        # Agent info
        agent_type = _infer_agent_type(getattr(proc, "session_id", ""))
        current_tool = getattr(proc, "current_tool", "") or "—"
        elapsed = _fmt_elapsed(getattr(proc, "elapsed_s", 0.0))
        tokens = _humanise_tokens(getattr(proc, "tokens_out", 0))

        # Format with tree structure if has parent
        has_parent = getattr(proc, "parent_session_id", "")
        is_last = i == len(agents) - 1

        if has_parent:
            glyph = "└" if is_last else "├"
            desc = _truncate(current_tool, _DESC_COL_WIDTH - 2)
            line = f"  {glyph} {dot} {agent_type}  {desc}  {elapsed} · ↓ {tokens} tokens"
        else:
            desc = _truncate(current_tool, _DESC_COL_WIDTH)
            type_col = f"{agent_type:<{_TYPE_COL_WIDTH}}"
            desc_col = f"{desc:<{_DESC_COL_WIDTH}}"
            line = f"  {dot} {type_col} {desc_col}  {elapsed} · ↓ {tokens} tokens"

        lines.append(line)

    return "\n".join(lines)


class AgentsTab(Widget):
    """Live sub-agents panel — Claude Code style agent list with keyboard nav."""

    REFRESH_S = 1.0

    BINDINGS = [
        Binding("up,k", "select_prev", "Previous agent", show=False),
        Binding("down,j", "select_next", "Next agent", show=False),
        Binding("enter", "view_detail", "View agent detail", show=False),
    ]

    DEFAULT_CSS = """
    AgentsTab {
        height: auto;
        padding: 1 0;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._agents: list = []
        self._selected_idx: int = 0
        self._registry = None

    def compose(self) -> ComposeResult:
        yield Static("", id="agents-content")

    def on_mount(self) -> None:
        self._init_registry()
        self._refresh()
        self.set_interval(self.REFRESH_S, self._refresh)

    def _init_registry(self) -> None:
        try:
            from lyra_core.transparency.event_store import EventStore
            from lyra_core.transparency.process_registry import ProcessRegistry

            self._registry = ProcessRegistry(store=EventStore())
        except Exception:
            self._registry = None

    def _refresh(self) -> None:
        if self._registry is not None:
            try:
                self._registry.refresh()
                self._agents = [
                    p for p in self._registry.get_all()
                    if getattr(p, "state", "") in ("running", "waiting", "blocked")
                ]
            except Exception:
                self._agents = []
        if self._agents:
            self._selected_idx = max(0, min(self._selected_idx, len(self._agents) - 1))
        else:
            self._selected_idx = 0
        self._repaint()

    def _repaint(self) -> None:
        try:
            content = self.query_one("#agents-content", Static)
            content.update(_render_agents(self._agents, self._selected_idx))
        except Exception:
            pass

    def refresh_agents(self, agents: list[dict]) -> None:
        """Legacy API — replace agent list with dict rows directly."""
        self._agents = agents  # type: ignore[assignment]
        if agents:
            self._selected_idx = max(0, min(self._selected_idx, len(agents) - 1))
        else:
            self._selected_idx = 0
        self._repaint()

    def action_select_prev(self) -> None:
        if self._agents:
            self._selected_idx = (self._selected_idx - 1) % len(self._agents)
            self._repaint()

    def action_select_next(self) -> None:
        if self._agents:
            self._selected_idx = (self._selected_idx + 1) % len(self._agents)
            self._repaint()

    def action_view_detail(self) -> None:
        if not self._agents or self._selected_idx >= len(self._agents):
            return
        proc = self._agents[self._selected_idx]
        from .agent_detail import AgentDetailModal

        self.app.push_screen(AgentDetailModal(proc))
