"""File-system tool renderers — read / write / edit.

Each renderer puts the file path front-and-centre because that's what
operators want to see in a long log:

* ``read_file`` — ``📄 src/foo.py``
* ``write_file`` — ``✎ src/foo.py (12 lines)``
* ``edit_file`` — ``✎ src/foo.py  (+3/-1)``

We compute simple line-count diffs for ``edit_file`` rather than
re-implementing unified-diff rendering — the AgentLoop already prints
the full diff above the card, the card just needs the at-a-glance
summary.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from ..tool_card import render_tool_card

__all__ = ["render_read", "render_write", "render_edit"]


def _line_count(s: str) -> int:
    if not s:
        return 0
    return s.count("\n") + (0 if s.endswith("\n") else 1)


def _is_error(result: Optional[Mapping[str, Any]]) -> bool:
    if result is None:
        return False
    return bool(
        result.get("is_error")
        or result.get("error")
        or (
            isinstance(result.get("exit_code"), int)
            and result["exit_code"] != 0
        )
    )


def render_read(
    name: str,
    args: Mapping[str, Any],
    result: Optional[Mapping[str, Any]],
) -> str:
    path = str(args.get("path", "<no path>"))
    offset = args.get("offset")
    limit = args.get("limit")
    preview = path
    if isinstance(offset, int) and isinstance(limit, int):
        preview = f"{path}  (lines {offset}..{offset + limit})"
    elif isinstance(limit, int):
        preview = f"{path}  (first {limit} lines)"
    return render_tool_card(name=name, preview=preview, is_error=_is_error(result))


def render_write(
    name: str,
    args: Mapping[str, Any],
    result: Optional[Mapping[str, Any]],
) -> str:
    path = str(args.get("path", "<no path>"))
    content = args.get("content")
    if isinstance(content, str):
        n_lines = _line_count(content)
        preview = f"{path}  ({n_lines} line{'s' if n_lines != 1 else ''})"
    else:
        preview = path
    return render_tool_card(name=name, preview=preview, is_error=_is_error(result))


def render_edit(
    name: str,
    args: Mapping[str, Any],
    result: Optional[Mapping[str, Any]],
) -> str:
    path = str(args.get("path", "<no path>"))
    old_str = args.get("old_str") or args.get("old_string") or ""
    new_str = args.get("new_str") or args.get("new_string") or ""
    if isinstance(old_str, str) and isinstance(new_str, str):
        added = _line_count(new_str)
        removed = _line_count(old_str)
        # Show net diff stats. The detail panel would show the unified
        # diff; the card just summarises so log-skimming stays fast.
        preview = f"{path}  (+{added}/-{removed})"
    else:
        preview = path
    return render_tool_card(name=name, preview=preview, is_error=_is_error(result))
