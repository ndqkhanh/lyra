"""``/mode <name>`` — set the active permission/planning mode.

harness-tui ships individual ``/plan``, ``/default``, ``/auto``
commands and a ``Shift+Tab`` cycle. Lyra users who came from
prompt_toolkit are wired to type ``/mode plan`` (and the muscle memory
from Claude Code's ``/mode`` reinforces it). This adds the named
variant without disturbing the individual aliases.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from harness_tui.commands.registry import register_command

if TYPE_CHECKING:  # pragma: no cover
    from harness_tui.app import HarnessApp


_VALID_MODES = ("plan", "default", "auto")


@register_command(
    name="mode",
    description="Set or show the active mode — plan · default · auto",
    category="Session",
    examples=["/mode plan", "/mode default", "/mode"],
)
async def cmd_mode(app: "HarnessApp", args: str) -> None:
    arg = (args or "").strip().lower()
    if not arg:
        app.shell.chat_log.write_system(
            f"mode: {app.mode}  ·  available: {', '.join(_VALID_MODES)}"
        )
        return
    if arg not in _VALID_MODES:
        app.shell.chat_log.write_system(
            f"unknown mode {arg!r} — available: {', '.join(_VALID_MODES)}"
        )
        return
    app.set_mode(arg)
