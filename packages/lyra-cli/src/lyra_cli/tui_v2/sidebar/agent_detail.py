"""AgentDetailModal — full detail overlay for a selected sub-agent.

Pushed by AgentsTab when the user presses Enter on an agent row.
Shows session ID, PID, state, token breakdown, cost, elapsed time,
and the last few tool calls from the transparency layer.

Dismiss with Escape or Q.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Footer, Static


def _fmt_cost(usd: float) -> str:
    if usd < 0.001:
        return "<$0.001"
    return f"${usd:.4f}"


def _fmt_elapsed(secs: float) -> str:
    m, s = divmod(int(secs), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def _humanise_tokens(n: int) -> str:
    if n < 1_000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1_000:.1f}k"
    return f"{n / 1_000_000:.1f}M"


def _build_detail_markup(proc: object) -> str:
    """Build Rich-markup detail block for an AgentProcess (or duck-type object)."""
    session_id = getattr(proc, "session_id", "—")
    pid = getattr(proc, "pid", "—")
    state = getattr(proc, "state", "—")
    project = getattr(proc, "project_path", "—")
    current_tool = getattr(proc, "current_tool", "—") or "—"
    tokens_in = getattr(proc, "tokens_in", 0)
    tokens_out = getattr(proc, "tokens_out", 0)
    context_tokens = getattr(proc, "context_tokens", 0)
    context_limit = getattr(proc, "context_limit", 0)
    cost_usd = getattr(proc, "cost_usd", 0.0)
    elapsed_s = getattr(proc, "elapsed_s", 0.0)
    parent = getattr(proc, "parent_session_id", "") or "—"
    children = getattr(proc, "children", ())

    state_style = {
        "running": "bold green",
        "waiting": "bold yellow",
        "blocked": "bold orange1",
        "error": "bold red",
        "done": "dim",
    }.get(state, "white")

    pct = (context_tokens / context_limit * 100) if context_limit > 0 else 0.0

    children_str = ", ".join(children[:5]) if children else "none"
    if len(children) > 5:
        children_str += f" +{len(children) - 5} more"

    lines = [
        f"[bold]Agent Detail[/bold]",
        "",
        f"[dim]Session  [/] {session_id}",
        f"[dim]PID      [/] {pid}",
        f"[dim]State    [/] [{state_style}]{state}[/]",
        f"[dim]Project  [/] {project}",
        f"[dim]Tool now [/] {current_tool}",
        f"[dim]Parent   [/] {parent}",
        f"[dim]Children [/] {children_str}",
        "",
        "[bold]Tokens[/bold]",
        f"  ↑ in:      {_humanise_tokens(tokens_in)}",
        f"  ↓ out:     {_humanise_tokens(tokens_out)}",
        f"  ctx used:  {_humanise_tokens(context_tokens)} / {_humanise_tokens(context_limit)} ({pct:.1f}%)",
        "",
        "[bold]Cost & Time[/bold]",
        f"  cost:     {_fmt_cost(cost_usd)}",
        f"  elapsed:  {_fmt_elapsed(elapsed_s)}",
    ]

    # Fetch recent tool events if transparency layer is available.
    try:
        from lyra_core.transparency.event_store import EventStore

        store = EventStore()
        recent = store.tail(5, session_id=session_id)
        if recent:
            lines.append("")
            lines.append("[bold]Recent events[/bold]")
            for ev in recent[-5:]:
                tool = getattr(ev, "tool_name", "") or getattr(ev, "hook_type", "?")
                lines.append(f"  [dim]{ev.hook_type:<22}[/] {tool}")
    except Exception:
        pass

    lines += ["", "[dim]Esc / Q to close[/]"]
    return "\n".join(lines)


class AgentDetailModal(ModalScreen):
    """Modal overlay showing full detail for a selected AgentProcess."""

    BINDINGS = [
        Binding("escape,q", "dismiss", "Close", show=True),
    ]

    DEFAULT_CSS = """
    AgentDetailModal {
        align: center middle;
    }
    AgentDetailModal > Static {
        width: 70;
        height: auto;
        max-height: 35;
        border: round $primary;
        padding: 1 2;
        background: $surface;
    }
    """

    def __init__(self, proc: object) -> None:
        super().__init__()
        self._proc = proc

    def compose(self) -> ComposeResult:
        yield Static(_build_detail_markup(self._proc))
        yield Footer()
