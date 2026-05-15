"""Lyra-specific slash commands for the harness-tui shell.

Phase 2 of the v3.14 rewrite. harness-tui already ships 16 generic
builtins (``/help`` ``/clear`` ``/theme`` ``/model`` ``/cost``
``/context`` ``/why`` ``/resume`` ``/plan`` ``/auto`` ``/default``
``/quit`` ``/find`` ``/voice`` ``/test`` ``/recipe``); this package
adds the Lyra-only daily-driver set plus an escape hatch for the long
tail of legacy commands.

Long-tail commands (e.g. ``/investigate``, ``/burn``, ``/evolve``,
``/retro``, ``/ultrareview``, ``/autopilot``) reach the user via
``/lyra <subcommand>`` — they run Typer subcommands in-process so the
TUI inherits Lyra's full CLI surface without a 128-way port.
"""
from __future__ import annotations

from . import budget, claude_compat, escape, meta, mode, sessions, skills_mcp  # noqa: F401

__all__ = ["register_lyra_commands"]


def register_lyra_commands() -> None:
    """Idempotent registration hook for ``ProjectConfig.extra_commands``.

    Importing the sub-modules registers their commands as a side
    effect (the ``@register_command`` decorator runs at import time).
    Calling this function is the public, explicit way to ensure those
    imports have happened — useful when test isolation has wiped the
    registry between cases.
    """
    # Module imports above already ran the decorators. Touch them so
    # static analysers don't strip the imports as unused.
    _ = (budget, escape, meta, mode, sessions, skills_mcp, claude_compat)
