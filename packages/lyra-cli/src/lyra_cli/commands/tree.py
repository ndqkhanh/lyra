"""``lyra tree`` — process tree visualization (Phase 4).

    lyra tree                   — render tree from .lyra/process_state.json
    lyra tree --live            — live-updating tree via EventBus (Ctrl-C)
    lyra tree --json            — emit tree as JSON

Research grounding: pstree / ps -ejH semantics applied to agent hierarchies.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
import typer
from rich.console import Console

_console = Console()

tree_app = typer.Typer(
    name="tree",
    help="Show the agent process tree (parent→child hierarchy).",
    no_args_is_help=False,
    invoke_without_command=True,
)


@tree_app.callback(invoke_without_command=True)
def tree_command(
    live: bool = typer.Option(
        False,
        "--live",
        "-l",
        help="Poll and re-render the tree every 2 s (Ctrl-C to stop).",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit the tree as JSON instead of rendering it.",
    ),
    repo_root: Path = typer.Option(
        Path.cwd(),
        "--repo-root",
        "-C",
        help="Repository root (default: cwd).",
    ),
) -> None:
    """Render the Lyra agent process tree."""
    state_path = repo_root / ".lyra" / "process_state.json"

    if not state_path.exists():
        _console.print("[dim]No process state found. Run a Lyra session first.[/dim]")
        raise typer.Exit(0)

    try:
        from lyra_core.observability.process_tree import ProcessTree
    except ImportError as exc:  # pragma: no cover
        _console.print(f"[red]lyra-core not installed: {exc}[/red]")
        raise typer.Exit(1) from exc

    if json_out:
        tree = ProcessTree.from_state_file(state_path)
        typer.echo(json.dumps(tree.to_dict(), indent=2))
        return

    if live:
        _run_live(state_path, ProcessTree)
    else:
        tree = ProcessTree.from_state_file(state_path)
        _console.print(tree.render())


def _run_live(state_path: Path, ProcessTree_cls: type) -> None:
    """Poll and re-render the tree every 2 seconds."""
    _console.print("[dim]Live tree — polling every 2 s (Ctrl-C to stop)[/dim]")
    try:
        while True:
            if state_path.exists():
                try:
                    tree = ProcessTree_cls.from_state_file(state_path)
                    _console.clear()
                    _console.print(tree.render())
                except (OSError, ValueError, KeyError):
                    pass
            time.sleep(2)
    except KeyboardInterrupt:
        pass
