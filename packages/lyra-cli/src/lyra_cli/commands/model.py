"""``lyra model`` — show current routing policy and last N route decisions.

Phase B of the Lyra 322-326 evolution plan. Reads routing decisions from
``.lyra/routing/decisions.jsonl`` and the current policy snapshot from
``.lyra/routing/policy.json``.

    lyra model                  — show policy + last 5 decisions
    lyra model --tail N         — show last N decisions (default 5)
    lyra model --json           — machine-readable JSON
"""
from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

_console = Console()

model_app = typer.Typer(
    name="model",
    help="Show current routing policy and recent tier decisions.",
    no_args_is_help=False,
    invoke_without_command=True,
)


_TIER_COLORS = {
    "fast": "cyan",
    "reasoning": "magenta",
    "advisor": "yellow",
}


def _color_tier(tier: str) -> str:
    color = _TIER_COLORS.get(tier, "white")
    return f"[{color}]{tier}[/{color}]"


def _load_policy(repo_root: Path) -> dict:
    path = repo_root / ".lyra" / "routing" / "policy.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _load_decisions(repo_root: Path, tail: int) -> list[dict]:
    path = repo_root / ".lyra" / "routing" / "decisions.jsonl"
    if not path.exists():
        return []
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return []
    rows: list[dict] = []
    for line in lines[-tail:]:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


@model_app.callback(invoke_without_command=True)
def model_command(
    ctx: typer.Context,
    repo_root: Path = typer.Option(Path.cwd(), "--repo-root", "-C", help="Repo root."),
    tail: int = typer.Option(5, "--tail", "-n", help="Number of recent decisions to show."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of tables."),
) -> None:
    """Show current routing policy and last N route decisions."""
    if ctx.invoked_subcommand is not None:
        return

    policy = _load_policy(repo_root)
    decisions = _load_decisions(repo_root, tail=tail)

    if json_out:
        _console.print_json(data={"policy": policy, "decisions": decisions})
        return

    if not policy and not decisions:
        _console.print(
            "[dim]No routing data found. "
            "TrajectoryRouter has not emitted any decisions yet.[/dim]"
        )
        raise typer.Exit(code=0)

    if policy:
        body = "\n".join(f"[bold]{k}[/bold]: {v}" for k, v in policy.items())
        _console.print(Panel(body, title="Routing Policy", border_style="blue"))

    if not decisions:
        _console.print("[dim]No decisions logged yet.[/dim]")
        return

    table = Table(
        title=f"Last {len(decisions)} routing decisions",
        box=box.SIMPLE_HEAVY,
        title_style="bold",
    )
    table.add_column("ts", style="dim")
    table.add_column("session")
    table.add_column("turn", justify="right")
    table.add_column("tier")
    table.add_column("reason")
    table.add_column("cost", justify="right")

    for d in decisions:
        table.add_row(
            str(d.get("ts", ""))[-19:],
            str(d.get("session_id", ""))[:12],
            str(d.get("turn", "")),
            _color_tier(str(d.get("tier", ""))),
            str(d.get("reason", ""))[:48],
            f"${float(d.get('cost_usd', 0.0)):.4f}",
        )
    _console.print(table)


__all__ = ["model_app"]
