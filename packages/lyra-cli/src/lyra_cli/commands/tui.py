"""``lyra tui`` — open the harness-tui shell with Lyra branding.

v3.14 / Phase 1: the shell now runs against Lyra's real agent loop via
:class:`lyra_cli.tui_v2.LyraTransport`. ``--mock`` keeps the scripted
demo transport for snapshots and tests; pass ``--url <base>`` to point
at a future daemon's FastAPI surface instead.

Setting ``LYRA_TUI=v2`` makes bare ``lyra`` (no subcommand) launch this
shell directly — that's the opt-in default-entry switch documented in
``LYRA_V3_14_TUI_REWRITE_PLAN.md`` §6.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from harness_tui import ProjectConfig
from harness_tui.transport import HTTPTransport, MockTransport

from ..tui_v2 import LyraTransport, lyra_theme
from ..tui_v2.app import LyraHarnessApp
from ..tui_v2.commands import register_lyra_commands
from ..tui_v2.sidebar import build_lyra_sidebar_tabs


tui_app = typer.Typer(
    no_args_is_help=False, help="Open the Lyra TUI (harness-tui shell)."
)


@tui_app.callback(invoke_without_command=True)
def main(
    repo_root: Path = typer.Option(
        Path.cwd, "--repo-root", help="Repository root (default: cwd)."
    ),
    url: Optional[str] = typer.Option(
        None, "--url", help="HTTP backend URL (skips the in-process loop)."
    ),
    mock: bool = typer.Option(
        False, "--mock", help="Use scripted demo transport (no real LLM calls)."
    ),
    model: str = typer.Option(
        "auto",
        "--model",
        "--llm",
        help="LLM provider for the in-process agent loop (default: auto).",
    ),
    max_steps: int = typer.Option(
        20, "--max-steps", help="Hard cap on agent loop iterations per turn."
    ),
) -> None:
    """Open the Lyra TUI."""
    repo_root = Path(repo_root).resolve()

    if mock:
        transport = MockTransport()
    elif url:
        transport = HTTPTransport(url)
    else:
        transport = LyraTransport(
            repo_root=repo_root, model=model, max_steps=max_steps
        )

    cfg = ProjectConfig(
        name="lyra",
        description="General-purpose, CLI-native agent harness",
        theme=lyra_theme(),
        transport=transport,
        model=model,
        working_dir=str(repo_root),
        sidebar_tabs=build_lyra_sidebar_tabs(repo_root),
        extra_commands=[register_lyra_commands],
    )
    app = LyraHarnessApp(cfg)
    app.run()

    summary = getattr(app, "last_exit_summary", None)
    if summary is not None:
        typer.echo(summary.render())
