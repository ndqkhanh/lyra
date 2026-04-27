"""Bash / shell tool-call renderer.

Body is the literal command. When a result is attached and the
``exit_code`` is non-zero, we append a short tail (``→ exit 1``)
so failed commands stand out at a glance. A zero-exit success
collapses the tail — we don't shout ``exit_code=0`` at users
running healthy commands.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from ..tool_card import render_tool_card

__all__ = ["render_bash"]


def render_bash(
    name: str,
    args: Mapping[str, Any],
    result: Optional[Mapping[str, Any]],
) -> str:
    command = str(args.get("command", "")).strip()
    preview = f"$ {command}" if command else "$ <no command>"

    is_error = False
    if result is not None:
        exit_code = result.get("exit_code")
        if isinstance(exit_code, int) and exit_code != 0:
            preview = f"{preview} → exit {exit_code}"
            is_error = True
        # Surface the first line of stderr when present, for fast
        # eyeballing without expanding the panel.
        stderr = result.get("stderr") or ""
        if isinstance(stderr, str) and stderr.strip() and exit_code:
            first = stderr.strip().splitlines()[0]
            if len(first) > 60:
                first = first[:59] + "…"
            preview = f"{preview}  ({first})"

    return render_tool_card(name=name, preview=preview, is_error=is_error)
