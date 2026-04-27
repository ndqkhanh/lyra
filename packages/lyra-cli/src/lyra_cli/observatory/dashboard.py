"""Rich-based snapshot dashboard for ``lyra burn``."""
from __future__ import annotations

import datetime as _dt
from typing import Optional

from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .aggregator import BurnReport


def render_dashboard(
    report: BurnReport,
    *,
    console: Optional[Console] = None,
) -> RenderableType:
    if report.total_turns == 0:
        return Panel(
            Text("no data - run a session, then come back.", style="dim"),
            title="Lyra Burn",
        )

    header = _build_header(report)
    by_model = _build_breakdown_table(
        "by model",
        [(m.model, f"${m.cost_usd:.2f}", str(m.turns),
          f"{m.one_shot_rate*100:.0f}%") for m in report.by_model],
        ["model", "cost", "turns", "1-shot"],
    )
    by_cat = _build_breakdown_table(
        "by category",
        [(c.category, f"${c.cost_usd:.2f}", str(c.turns))
         for c in report.by_category],
        ["category", "cost", "turns"],
    )
    sessions = _build_sessions_table(report)

    return Panel(
        Group(header, by_model, by_cat, sessions),
        title=f"Lyra Burn - {_period_label(report)}",
        title_align="left",
    )


def _build_header(rep: BurnReport) -> Table:
    t = Table.grid(padding=(0, 2))
    t.add_column(); t.add_column(); t.add_column(); t.add_column()
    t.add_row(
        Text("Total spend", style="dim"), f"${rep.total_cost_usd:.2f}",
        Text("Total turns", style="dim"), str(rep.total_turns),
    )
    t.add_row(
        Text("Tokens in", style="dim"), _humanize(rep.total_tokens_in),
        Text("Tokens out", style="dim"), _humanize(rep.total_tokens_out),
    )
    t.add_row(
        Text("One-shot rate", style="dim"), f"{rep.one_shot_rate*100:.0f}%",
        Text("Retry rate", style="dim"), f"{rep.retry_rate*100:.0f}%",
    )
    return t


def _build_breakdown_table(title: str, rows, headers) -> Table:
    t = Table(title=title, show_header=True, header_style="bold cyan",
              expand=True, pad_edge=False)
    for h in headers:
        t.add_column(h)
    for r in rows[:10]:
        t.add_row(*r)
    return t


def _build_sessions_table(rep: BurnReport) -> Table:
    t = Table(title="recent sessions", show_header=True,
              header_style="bold cyan", expand=True)
    for h in ("session", "age", "turns", "cost", "category"):
        t.add_column(h)
    now = _dt.datetime.now().timestamp()
    for s in rep.by_session[:10]:
        age = _humanize_age(max(0.0, now - s.last_turn_at))
        t.add_row(s.session_id, age, str(s.turns),
                  f"${s.cost_usd:.2f}", s.primary_category)
    return t


def _humanize(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f} M"
    if n >= 1_000:
        return f"{n/1_000:.1f} K"
    return str(n)


def _humanize_age(secs: float) -> str:
    if secs < 60:
        return f"{int(secs)}s ago"
    if secs < 3600:
        return f"{int(secs/60)}m ago"
    if secs < 86400:
        return f"{int(secs/3600)}h ago"
    return f"{int(secs/86400)}d ago"


def _period_label(rep: BurnReport) -> str:
    a = (
        _dt.datetime.fromtimestamp(rep.period_start).strftime("%Y-%m-%d")
        if rep.period_start else "?"
    )
    b = (
        _dt.datetime.fromtimestamp(rep.period_end).strftime("%Y-%m-%d")
        if rep.period_end else "?"
    )
    return f"{a} -> {b}"
