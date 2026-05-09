"""``lyra doctor`` — health check (Phase N.4: ``--json`` mode added).

The legacy command rendered a single Rich table. Phase N.4 keeps the
table for humans and adds a ``--json`` mode that emits the structured
:class:`lyra_cli.diagnostics.Probe` rows verbatim — that's what
``lyra setup`` and the future HTTP API consume to decide what
needs configuring.

Logic stays in :mod:`lyra_cli.diagnostics`; this file is just the
Typer renderer.
"""
from __future__ import annotations

import json as _json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ..diagnostics import Probe, run_all


_console = Console()


def _ok_marker(p: Probe) -> str:
    """Coloured status marker.

    Optional integrations that aren't installed render in *yellow*
    rather than red — they're not failures, just opportunities the
    user might care about.
    """
    if p.ok:
        return "[green]OK[/green]"
    if p.meta.get("optional"):
        return "[yellow]OPT[/yellow]"
    return "[red]MISSING[/red]"


def _exit_code(probes: list[Probe]) -> int:
    """Non-zero when a *required* probe failed.

    Optional integrations and provider keys never trip the exit
    code — a fresh install with no API keys still wants ``lyra
    doctor`` to succeed so the wizard can drive the user through
    setup.
    """
    for p in probes:
        if p.ok:
            continue
        if p.meta.get("optional"):
            continue
        if p.category == "providers":
            continue
        if p.category == "state" and p.name in {"soul-md", "policy", "plans-dir"}:
            # Repo not yet initialised is a soft signal — `lyra init`
            # solves it. Don't surface a hard fail to CI here.
            continue
        return 1
    return 0


def doctor_command(
    repo_root: Path = typer.Option(
        Path.cwd(), "--repo-root", "-C", help="Repo to inspect."
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Emit JSON instead of a Rich table."
    ),
) -> None:
    """Inspect Lyra installation, repo state, and provider keys."""
    repo_root = repo_root.resolve()
    probes = run_all(repo_root)

    if json_out:
        payload = {
            "repo_root": str(repo_root),
            "ok": _exit_code(probes) == 0,
            "probes": [p.to_dict() for p in probes],
        }
        typer.echo(_json.dumps(payload, indent=2))
        raise typer.Exit(code=_exit_code(probes))

    table = Table(title=f"Lyra doctor — {repo_root}")
    table.add_column("category")
    table.add_column("check")
    table.add_column("detail", overflow="fold")
    table.add_column("status", justify="right")

    last_cat = ""
    for p in probes:
        cat = p.category if p.category != last_cat else ""
        last_cat = p.category
        table.add_row(cat, p.name, p.detail, _ok_marker(p))

    _console.print(table)
    raise typer.Exit(code=_exit_code(probes))
