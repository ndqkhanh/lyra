"""Search-tool renderers — grep / glob.

Emphasises the pattern (what was searched for) and the match count
(when known). Both fields are what operators look for first when
grepping their own logs to confirm "did it find anything?".
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from ..tool_card import render_tool_card

__all__ = ["render_grep", "render_glob"]


def _match_count(result: Optional[Mapping[str, Any]]) -> Optional[int]:
    if result is None:
        return None
    for key in ("matches", "match_count", "count", "n_matches"):
        value = result.get(key)
        if isinstance(value, int):
            return value
    files = result.get("files")
    if isinstance(files, list):
        return len(files)
    return None


def render_grep(
    name: str,
    args: Mapping[str, Any],
    result: Optional[Mapping[str, Any]],
) -> str:
    pattern = str(args.get("pattern", "<no pattern>"))
    path = args.get("path") or args.get("target")
    preview = f"/{pattern}/" if pattern else "<no pattern>"
    if isinstance(path, str):
        preview = f"{preview}  in {path}"
    n = _match_count(result)
    if n is not None:
        preview = f"{preview}  → {n} match{'es' if n != 1 else ''}"
    is_error = bool(result and (result.get("is_error") or result.get("error")))
    return render_tool_card(name=name, preview=preview, is_error=is_error)


def render_glob(
    name: str,
    args: Mapping[str, Any],
    result: Optional[Mapping[str, Any]],
) -> str:
    pattern = str(args.get("glob_pattern") or args.get("pattern") or "<no pattern>")
    target = args.get("target_directory")
    preview = pattern
    if isinstance(target, str):
        preview = f"{pattern}  in {target}"
    n = _match_count(result)
    if n is not None:
        preview = f"{preview}  → {n} file{'s' if n != 1 else ''}"
    is_error = bool(result and (result.get("is_error") or result.get("error")))
    return render_tool_card(name=name, preview=preview, is_error=is_error)
