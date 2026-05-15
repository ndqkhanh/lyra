"""Meta commands: ``/status``, ``/version``, ``/exit``.

``/status`` is the Lyra equivalent of Claude Code's setup summary — the
TUI shows the active model/mode/cwd/budget at a glance. ``/exit`` is a
muscle-memory alias for the harness-tui builtin ``/quit``. ``/version``
prints the running Lyra CLI version.
"""
from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from harness_tui.commands.registry import register_command

if TYPE_CHECKING:  # pragma: no cover
    from harness_tui.app import HarnessApp


@register_command(
    name="model",
    description="Switch model — '/model' picker · '/model <name>' direct",
    category="Lyra",
    examples=["/model", "/model anthropic", "/model deepseek"],
)
async def cmd_model(app: "HarnessApp", args: str) -> None:
    """Override the harness-tui builtin so '/model' (no args) opens the
    Lyra picker; '/model <name>' keeps the direct-set behaviour."""
    name = (args or "").strip()
    if not name:
        from lyra_cli.tui_v2.modals import ModelPicker

        chosen = await app.push_screen(
            ModelPicker(current=app.cfg.model or ""), wait_for_dismiss=True
        )
        if not chosen:
            return
        app.cfg.model = chosen
        app.shell.status_line.set_segment("model", chosen)
        app.shell.chat_log.write_system(f"model: {chosen}")
        return
    app.cfg.model = name
    app.shell.status_line.set_segment("model", name)
    app.shell.chat_log.write_system(f"model: {name}")


@register_command(
    name="status",
    description="Show Lyra setup — model, mode, repo, cwd, runtime",
    category="Lyra",
    examples=["/status"],
)
async def cmd_status(app: "HarnessApp", _args: str) -> None:
    cfg = app.cfg
    repo = Path(cfg.working_dir).resolve() if cfg.working_dir else Path.cwd()
    rows = [
        ("model", cfg.model or "auto"),
        ("mode", app.mode),
        ("repo", str(repo)),
        ("transport", getattr(cfg.transport, "name", "?")),
        ("python", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"),
        ("platform", f"{platform.system()} {platform.release()}"),
        ("cols x rows", f"{app.size.width} x {app.size.height}"),
    ]
    width = max(len(k) for k, _ in rows)
    body = "\n".join(f"  {k.ljust(width)}  {v}" for k, v in rows)
    app.shell.chat_log.write_system("status\n" + body)


@register_command(
    name="version",
    description="Print the Lyra CLI version",
    category="Lyra",
    examples=["/version"],
)
async def cmd_version(app: "HarnessApp", _args: str) -> None:
    from lyra_cli import __version__

    app.shell.chat_log.write_system(f"lyra {__version__}")


@register_command(
    name="exit",
    description="Exit the TUI (alias for /quit)",
    category="Session",
    examples=["/exit"],
)
async def cmd_exit(app: "HarnessApp", _args: str) -> None:
    app.exit()


@register_command(
    name="cwd",
    description="Print the working directory",
    category="Lyra",
    hidden=False,
    examples=["/cwd"],
)
async def cmd_cwd(app: "HarnessApp", _args: str) -> None:
    cwd = app.cfg.working_dir or os.getcwd()
    app.shell.chat_log.write_system(f"cwd: {cwd}")
