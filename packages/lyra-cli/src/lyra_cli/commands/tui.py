"""Lyra `tui` command — opens the harness-tui shell with Lyra branding.

Lyra already ships a polished prompt_toolkit-based REPL via `lyra` (no
subcommand). This command is an *alternative* entry point for users who
prefer the harness-tui shell (sidebar + sessions + multi-pane layout).

Future work (see `research/tui-framework-and-rollout.md` §3.12) replaces
the existing REPL outright; for v0 the two coexist.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import typer

from harness_tui import HarnessApp, ProjectConfig
from harness_tui.theme import Theme
from harness_tui.themes import catppuccin_mocha
from harness_tui.transport import HTTPTransport, MockTransport


LYRA_LOGO = r"""
   [bold #FACC15]╭─╮[/]
   [bold #FACC15]│[/] [bold]L[/] [bold #FACC15]│[/]
   [bold #FACC15]├─┤[/]    [dim]Lyra[/]
   [bold #FACC15]│[/] [bold]Y[/] [bold #FACC15]│[/]
   [bold #FACC15]╰─╯[/]
""".strip("\n")


def lyra_theme() -> Theme:
    return catppuccin_mocha().with_brand(
        name="lyra",
        primary="#FACC15",
        primary_alt="#A16207",
        accent="#C084FC",
        ascii_logo=LYRA_LOGO,
        spinner_frames=("♪", "♫", "♪", "♫"),
    )


tui_app = typer.Typer(no_args_is_help=False, help="Open the Lyra TUI (harness-tui shell).")


@tui_app.callback(invoke_without_command=True)
def main(
    repo_root: Path = typer.Option(
        Path.cwd, "--repo-root", help="Repository root (default: cwd)."
    ),
    url: Optional[str] = typer.Option(None, "--url", help="HTTP backend URL (optional)."),
    mock: bool = typer.Option(False, "--mock", help="Use scripted demo transport."),
) -> None:
    """Open the Lyra TUI."""
    repo_root = Path(repo_root).resolve()
    if mock or not url:
        # Lyra's primary backend is in-process; until the daemon split,
        # default to MockTransport for the harness-tui shell. The full Typer
        # CLI (`lyra run`, `lyra plan`, etc.) remains the primary surface.
        transport = MockTransport() if not url else HTTPTransport(url)
    else:
        transport = HTTPTransport(url)

    cfg = ProjectConfig(
        name="lyra",
        description="General-purpose, CLI-native agent harness",
        theme=lyra_theme(),
        transport=transport,
        model=os.environ.get("LYRA_MODEL", "auto"),
        working_dir=str(repo_root),
    )
    app = HarnessApp(cfg)
    app.run()
    summary = getattr(app, "last_exit_summary", None)
    if summary:
        typer.echo(summary.render())
