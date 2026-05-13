"""``lyra status`` — real-time process transparency panel (Phase 3).

    lyra status              — snapshot from .lyra/process_state.json
    lyra status --live       — live Rich dashboard (4 Hz refresh, Ctrl-C to stop)
    lyra status --session ID — pin to a specific session ID

Research grounding: Claude-Code-Usage-Monitor Rich Live() pattern,
claude_code_agent_farm process_state.json schema.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

_console = Console()

status_app = typer.Typer(
    name="status",
    help="Show real-time process transparency panel.",
    no_args_is_help=False,
    invoke_without_command=True,
)


@status_app.callback(invoke_without_command=True)
def status_command(
    live: bool = typer.Option(
        False,
        "--live",
        "-l",
        help="Run the live Rich dashboard (4 Hz refresh, Ctrl-C to stop).",
    ),
    session_id: Optional[str] = typer.Option(
        None,
        "--session",
        "-s",
        help="Pin to a specific session ID.",
    ),
    repo_root: Path = typer.Option(
        Path.cwd(),
        "--repo-root",
        "-C",
        help="Repository root (default: cwd).",
    ),
) -> None:
    """Show process transparency: snapshot or live dashboard."""
    if live:
        _run_live(session_id or "")
    else:
        _run_snapshot(repo_root, session_id)


def _run_live(session_id: str) -> None:
    """Start the live Rich dashboard subscribing to the global EventBus."""
    try:
        from lyra_core.observability.event_bus import get_event_bus
        from lyra_core.observability.live_display import LiveDisplay
    except ImportError as exc:  # pragma: no cover
        _console.print(f"[red]lyra-core not installed: {exc}[/red]")
        raise typer.Exit(1) from exc

    bus = get_event_bus()
    display = LiveDisplay(bus=bus, session_id=session_id)
    _console.print("[dim]Lyra Status — live dashboard (Ctrl-C to stop)[/dim]")
    display.run()


def _run_snapshot(repo_root: Path, session_id: Optional[str]) -> None:
    """Render a one-shot snapshot from .lyra/process_state.json."""
    try:
        from lyra_core.observability.live_display import DisplayState, build_layout
    except ImportError as exc:  # pragma: no cover
        _console.print(f"[red]lyra-core not installed: {exc}[/red]")
        raise typer.Exit(1) from exc

    state_path = repo_root / ".lyra" / "process_state.json"
    if not state_path.exists():
        _console.print("[dim]No process state found. Run a Lyra session first.[/dim]")
        raise typer.Exit(0)

    try:
        data = json.loads(state_path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        _console.print(f"[red]Failed to read process state: {exc}[/red]")
        raise typer.Exit(1) from exc

    sid = session_id or str(data.get("session_id", ""))
    state = DisplayState(session_id=sid)

    layout = build_layout(state)
    _console.print(layout)
