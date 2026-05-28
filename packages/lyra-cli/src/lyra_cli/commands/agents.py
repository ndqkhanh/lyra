"""``lyra agents`` — fleet view of background sessions (Phase D).

Reads ``.lyra/fleet.json`` (a snapshot produced by lyra_core.transparency.agent_view
FleetView.dump_snapshot) and renders a priority-sorted fleet table.

    lyra agents                 — fleet table sorted by P0..P4
    lyra agents --json          — machine-readable JSON
    lyra agents --priority P0   — filter to one priority level
"""
from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import box
from rich.console import Console
from rich.table import Table

_console = Console()

agents_app = typer.Typer(
    name="agents",
    help="Fleet view of background agents with P0–P4 attention priority sorting.",
    no_args_is_help=False,
    invoke_without_command=True,
)


_PRIORITY_COLORS = {
    "P0": "red",
    "P1": "yellow",
    "P2": "cyan",
    "P3": "white",
    "P4": "dim",
}

_STATE_COLORS = {
    "running": "green",
    "waiting": "yellow",
    "blocked": "red",
    "error": "red",
    "done": "dim",
}


def _color_priority(p: str) -> str:
    color = _PRIORITY_COLORS.get(p, "white")
    return f"[{color}]{p}[/{color}]"


def _color_state(s: str) -> str:
    color = _STATE_COLORS.get(s, "white")
    return f"[{color}]{s}[/{color}]"


def _load_fleet(repo_root: Path) -> list[dict]:
    path = repo_root / ".lyra" / "fleet.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, dict) and "agents" in data:
        agents = data["agents"]
    elif isinstance(data, list):
        agents = data
    else:
        return []
    return list(agents)


def _normalize_priority(p) -> str:
    """Accept int (0..4), str ('P0'..'P4'), or AttentionPriority enum value."""
    if isinstance(p, int):
        return f"P{p}"
    s = str(p).upper()
    if s.startswith("P"):
        return s
    if s.isdigit():
        return f"P{s}"
    return "P3"


@agents_app.callback(invoke_without_command=True)
def agents_command(
    ctx: typer.Context,
    repo_root: Path = typer.Option(Path.cwd(), "--repo-root", "-C", help="Repo root."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
    priority: str | None = typer.Option(
        None, "--priority", "-p", help="Filter to one priority (P0..P4)."
    ),
) -> None:
    """List background agents sorted by attention priority (P0..P4)."""
    if ctx.invoked_subcommand is not None:
        return

    rows = _load_fleet(repo_root)
    if priority:
        wanted = _normalize_priority(priority)
        rows = [r for r in rows if _normalize_priority(r.get("attention_priority", 3)) == wanted]

    if json_out:
        _console.print_json(data=rows)
        return

    if not rows:
        _console.print(
            "[dim]No fleet snapshot found "
            "(.lyra/fleet.json). Start a background agent first.[/dim]"
        )
        raise typer.Exit(code=0)

    rows.sort(key=lambda r: _normalize_priority(r.get("attention_priority", 3)))

    table = Table(
        title=f"Fleet ({len(rows)} agent{'s' if len(rows) != 1 else ''})",
        box=box.SIMPLE_HEAVY,
        title_style="bold",
    )
    table.add_column("priority", justify="left")
    table.add_column("agent_id")
    table.add_column("state")
    table.add_column("summary", overflow="fold")
    table.add_column("attached", justify="center")
    table.add_column("updated", style="dim", justify="right")

    for r in rows:
        prio = _normalize_priority(r.get("attention_priority", 3))
        state = str(r.get("state", "running"))
        attached = "●" if r.get("is_attached") else ""
        updated = str(r.get("last_updated", ""))[:19]
        table.add_row(
            _color_priority(prio),
            str(r.get("agent_id", ""))[:24],
            _color_state(state),
            str(r.get("row_summary", ""))[:60],
            attached,
            updated,
        )
    _console.print(table)


__all__ = ["agents_app"]
