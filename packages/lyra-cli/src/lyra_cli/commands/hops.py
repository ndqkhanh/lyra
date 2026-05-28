"""``lyra hops`` — view IRCoT hop trace for a research session (Phase C).

Reads hop traces from ``.lyra/hops/<session>.jsonl`` (one HopRecord per line).
If no session is given, finds the most recent session.

    lyra hops                       — latest session's hop trace
    lyra hops --session SESSION_ID  — specific session
    lyra hops --json                — machine-readable JSON
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

hops_app = typer.Typer(
    name="hops",
    help="View IRCoT hop traces for research sessions with provenance.",
    no_args_is_help=False,
    invoke_without_command=True,
)


def _find_latest_session(hops_dir: Path) -> Path | None:
    if not hops_dir.exists():
        return None
    candidates = sorted(
        (p for p in hops_dir.glob("*.jsonl") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _load_hops(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return []
    out: list[dict] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _support_color(score: float) -> str:
    if score >= 0.75:
        return "green"
    if score >= 0.5:
        return "yellow"
    return "red"


@hops_app.callback(invoke_without_command=True)
def hops_command(
    ctx: typer.Context,
    repo_root: Path = typer.Option(Path.cwd(), "--repo-root", "-C", help="Repo root."),
    session: str | None = typer.Option(
        None, "--session", "-s", help="Session ID (defaults to most recent)."
    ),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """View multi-hop reasoning trace for a research session."""
    if ctx.invoked_subcommand is not None:
        return

    hops_dir = repo_root / ".lyra" / "hops"
    if session:
        path = hops_dir / f"{session}.jsonl"
    else:
        path = _find_latest_session(hops_dir)
        if path is None:
            _console.print(
                "[dim]No hop traces found "
                "(.lyra/hops/*.jsonl). Run a research session first.[/dim]"
            )
            raise typer.Exit(code=0)

    hops = _load_hops(path)
    if json_out:
        _console.print_json(data={"session": path.stem, "hops": hops})
        return

    if not hops:
        _console.print(f"[dim]No hops in {path}[/dim]")
        raise typer.Exit(code=0)

    mean_support = sum(float(h.get("support_score", 0.0)) for h in hops) / len(hops)
    header = (
        f"Session: [bold]{path.stem}[/bold]   "
        f"Hops: [bold]{len(hops)}[/bold]   "
        f"Mean support: [{_support_color(mean_support)}]{mean_support:.2f}[/]"
    )
    _console.print(Panel(header, border_style="blue"))

    table = Table(
        title="Hop Trace",
        box=box.SIMPLE_HEAVY,
        title_style="bold",
    )
    table.add_column("#", justify="right")
    table.add_column("query", overflow="fold")
    table.add_column("support", justify="right")
    table.add_column("reasoning", overflow="fold")
    table.add_column("sources", justify="right")

    for h in hops:
        score = float(h.get("support_score", 0.0))
        idx = h.get("hop_index", "")
        table.add_row(
            str(idx),
            str(h.get("query", ""))[:60],
            f"[{_support_color(score)}]{score:.2f}[/]",
            str(h.get("reasoning", ""))[:80],
            str(len(h.get("source_refs", []) or [])),
        )
    _console.print(table)


__all__ = ["hops_app"]
