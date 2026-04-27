"""Command-palette v2 — fuzzy search + grouped renderer.

Backs the ``Ctrl-K`` / ``/?`` palette experience that v2.1.x's flat
``/help`` couldn't match. Designed as two pure functions so unit tests
can drive them headlessly:

* :func:`fuzzy_filter(query)` — substring + initial-char match against
  ``COMMAND_REGISTRY``. Empty query returns the whole registry sorted
  by ``(category_order, name)``.
* :func:`render_palette(specs, *, query, max_height)` — Rich
  :class:`~rich.text.Text` formatted as ``[category]\\n  /name <args>
  — description`` blocks, with the matched query fragment bolded.

The actual TTY-driven picker lives in the REPL (it'll wire stdin reads
+ rerender) but every "what should this look like?" question can be
answered by these two functions, so refactors don't need to keep two
mental models in sync.
"""
from __future__ import annotations

import re
from typing import Optional

from rich.text import Text

__all__ = ["fuzzy_filter", "render_palette"]


# Category display order — matches /help and the welcome screen so
# users see commands in the same buckets across surfaces.
_CATEGORY_ORDER = (
    "session",
    "plan-build-run",
    "build",
    "run",
    "explore",
    "retro",
    "tools",
    "diagnostics",
    "meta",
)


def _category_rank(name: str) -> int:
    """Sort key — anything not in the canonical list lands at the end."""
    try:
        return _CATEGORY_ORDER.index(name)
    except ValueError:
        return len(_CATEGORY_ORDER)


def _matches_query(spec, query: str) -> bool:
    """Substring (over name + aliases + description) OR initials match.

    "Initials" means the query letters appear in order at word
    boundaries — ``ur`` matches ``ultrareview`` (u-, r in '-r-eview').
    Description is matched but only on substring; we don't try to
    initial-match prose because false positives would dominate.
    """
    q = query.lower().strip()
    if not q:
        return True
    name = spec.name.lower()
    aliases = tuple(a.lower() for a in spec.aliases)
    if q in name or any(q in a for a in aliases):
        return True
    if q in spec.description.lower():
        return True
    if _initials_match(q, name):
        return True
    return any(_initials_match(q, a) for a in aliases)


def _initials_match(query: str, target: str) -> bool:
    """Return True iff ``query`` chars appear in order in ``target``.

    Cheap subsequence test — close enough to fzf's flame-graph for the
    interactive lookup case.
    """
    it = iter(target)
    return all(c in it for c in query)


def fuzzy_filter(query: str) -> list:
    """Filter ``COMMAND_REGISTRY`` against ``query``.

    Imports ``COMMAND_REGISTRY`` lazily so the palette module can sit
    above ``session.py`` in the import graph without creating a cycle.
    """
    from .session import COMMAND_REGISTRY

    matches = [spec for spec in COMMAND_REGISTRY if _matches_query(spec, query)]
    matches.sort(key=lambda s: (_category_rank(s.category), s.name))
    return matches


def _highlight(text: str, query: str) -> Text:
    """Return a Rich Text with each ``query`` occurrence bolded."""
    if not query:
        return Text(text)
    out = Text()
    lowered = text.lower()
    q_lower = query.lower()
    cursor = 0
    while True:
        idx = lowered.find(q_lower, cursor)
        if idx < 0:
            out.append(text[cursor:])
            break
        out.append(text[cursor:idx])
        out.append(text[idx : idx + len(query)], style="bold yellow")
        cursor = idx + len(query)
    return out


def render_palette(
    specs: list,
    *,
    query: Optional[str] = None,
    max_height: int = 12,
) -> Text:
    """Render the palette for the matched specs.

    Layout (one category at a time):

    ::

        ── session ──
          /mode  [plan|build|run|explore|retro] — show or switch mode
          /model [name] — show or set the active model name

    Truncated to ``max_height`` *entries* (not lines — headers are free).
    A ``…`` line is appended when truncation kicked in so the user knows
    to refine the query.
    """
    if not specs:
        return Text("(no matches)\n", style="dim italic")

    out = Text()
    grouped: dict[str, list] = {}
    for spec in specs:
        grouped.setdefault(spec.category, []).append(spec)

    shown = 0
    truncated = False
    for cat in sorted(grouped, key=_category_rank):
        if shown >= max_height:
            truncated = True
            break
        out.append(f"── {cat} ──\n", style="bold cyan")
        for spec in grouped[cat]:
            if shown >= max_height:
                truncated = True
                break
            line = Text("  /")
            line.append_text(_highlight(spec.name, query or ""))
            if spec.args_hint:
                line.append(f" {spec.args_hint}", style="dim")
            line.append(" — ", style="dim")
            line.append_text(_highlight(spec.description, query or ""))
            line.append("\n")
            out.append_text(line)
            shown += 1

    if truncated:
        out.append("  …\n", style="dim")
    return out
