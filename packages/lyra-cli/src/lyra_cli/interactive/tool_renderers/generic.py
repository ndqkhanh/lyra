"""Generic / fallback renderer for unknown tools.

Delegates to :func:`render_tool_card` so the visual style matches the
rest of Lyra's REPL. Used when no specialised renderer is registered
for the tool name (the ``ToolRegistry`` may load plugin tools we
don't ship cards for).
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from ..tool_card import render_tool_card

__all__ = ["render_generic"]


def _summarise_args(args: Mapping[str, Any]) -> str:
    """Pick a single-line preview from arbitrary kwargs.

    We try a few well-known keys (``command``, ``path``, ``pattern``)
    before falling back to ``repr`` of the whole mapping. Truncated
    to keep the card a single body line.
    """
    if not args:
        return ""
    for key in ("command", "path", "pattern", "glob_pattern", "query"):
        if key in args and isinstance(args[key], str):
            return args[key]
    rendered = ", ".join(f"{k}={v!r}" for k, v in args.items())
    if len(rendered) > 80:
        rendered = rendered[:79] + "…"
    return rendered


def render_generic(
    name: str,
    args: Mapping[str, Any],
    result: Optional[Mapping[str, Any]],
) -> str:
    preview = _summarise_args(args)
    is_error = bool(
        result
        and (result.get("is_error") or result.get("error") or result.get("exit_code"))
    )
    return render_tool_card(name=name, preview=preview, is_error=is_error)
