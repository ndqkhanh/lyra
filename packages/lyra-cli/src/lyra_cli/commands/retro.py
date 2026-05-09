"""`lyra retro <session-id>` — post-session retrospective (stub)."""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from ..paths import RepoLayout

_console = Console()


def retro_command(
    session_id: str = typer.Argument(..., help="Session to review."),
    repo_root: Path = typer.Option(
        Path.cwd(), "--repo-root", "-C", help="Repo where the session ran."
    ),
) -> None:
    """Show a retrospective for a completed session (stub; Phase 5)."""
    layout = RepoLayout(repo_root=repo_root.resolve())
    target = layout.sessions_dir / session_id
    if not target.exists():
        _console.print(f"[red]unknown session[/red]: {session_id}")
        raise typer.Exit(code=2)
    _console.print(f"retro for {session_id}: not yet implemented (Phase 5)")
