"""Per-tool renderer registry.

Each tool gets a small renderer function that knows how to format its
arguments and (optionally) result into a claw-code-style ANSI card.
Unknown tool names fall through to :func:`generic.render_generic`.

Renderers are pure functions:

.. code-block:: python

    Renderer = Callable[[str, Mapping[str, Any], Optional[Mapping[str, Any]]], str]

— ``name`` echoes the tool name (lets one renderer cover several
aliases), ``args`` is the call's keyword payload, ``result`` is the
provider's response (``None`` while the tool is still in flight).

The registry is closed over at module load — adding a new tool means
landing a new file in this package and registering it in :data:`_REGISTRY`.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Optional

from .bash import render_bash
from .file import render_edit, render_read, render_write
from .generic import render_generic
from .search import render_glob, render_grep

Renderer = Callable[
    [str, Mapping[str, Any], Optional[Mapping[str, Any]]], str
]

_REGISTRY: dict[str, Renderer] = {
    # bash family
    "bash": render_bash,
    "Bash": render_bash,
    "shell": render_bash,
    "Shell": render_bash,
    # file family
    "read_file": render_read,
    "Read": render_read,
    "ReadFile": render_read,
    "write_file": render_write,
    "Write": render_write,
    "WriteFile": render_write,
    "edit_file": render_edit,
    "Edit": render_edit,
    "EditFile": render_edit,
    # search family
    "grep": render_grep,
    "Grep": render_grep,
    "glob": render_glob,
    "Glob": render_glob,
}


def get_renderer(name: str) -> Renderer:
    """Return the registered renderer for ``name`` or :func:`render_generic`."""
    return _REGISTRY.get(name, render_generic)


def render(
    *,
    name: str,
    args: Mapping[str, Any],
    result: Optional[Mapping[str, Any]],
) -> str:
    """Convenience wrapper: pick the renderer and call it."""
    return get_renderer(name)(name, args, result)


__all__ = ["Renderer", "get_renderer", "render"]
