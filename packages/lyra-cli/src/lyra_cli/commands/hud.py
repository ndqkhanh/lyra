"""``lyra hud`` Typer subcommand (Phase 6i).

Subcommands:
- ``lyra hud preview [--preset PRESET]`` — render a sample state to
  stdout. Lets users see what the HUD looks like without booting a
  full session.
- ``lyra hud presets`` — list available presets.

Future PRs (out of scope for v3.5):
- ``lyra hud configure`` — interactive layout picker writing
  ``~/.lyra/hud.yaml``.
- ``lyra hud watch`` — live-tail mode that re-renders on session
  state changes (file watcher + Rich Live).
"""

from __future__ import annotations

import typer

from ..hud import (
    HudState,
    available_presets,
    load_preset,
    render,
)
from ..hud.testing import sample_state

hud_app = typer.Typer(
    name="hud",
    help="Live status pane (claude-hud-inspired). Try `lyra hud preview`.",
    no_args_is_help=True,
)


@hud_app.command("preview")
def preview_cmd(
    preset: str = typer.Option(
        "full",
        "--preset",
        "-p",
        help=f"Preset to render. One of: {', '.join(available_presets())}",
    ),
    max_width: int = typer.Option(
        120,
        "--max-width",
        "-w",
        help="Column cap for each rendered line.",
    ),
) -> None:
    """Render a sample HUD state to stdout (no session required)."""
    try:
        cfg = load_preset(preset)
    except ValueError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    state = sample_state()
    typer.echo(render(state, config=cfg, max_width=max_width))


@hud_app.command("presets")
def presets_cmd() -> None:
    """List available built-in HUD presets."""
    for name in available_presets():
        cfg = load_preset(name)
        widget_summary = ", ".join(cfg.widgets) if cfg.widgets else "(none)"
        typer.echo(f"{name:<10}  width={cfg.max_width:<4}  widgets: {widget_summary}")


@hud_app.command("inline")
def inline_cmd() -> None:
    """Render the inline preset (single line) to stdout.

    Useful for piping into status-bar tools like tmux's
    ``status-right`` setting:

        set -g status-right '#(lyra hud inline)'
    """
    from ..hud import render_inline

    state = sample_state()
    typer.echo(render_inline(state))


__all__ = ["hud_app"]


# ---- intentionally unused symbol so static analysers don't flag the
#      HudState re-export above as dead code. The docstring of this
#      module advertises that callers can import HudState here for
#      scripting against `lyra hud`.
_ = HudState
