"""Widget renderers for the Lyra HUD (Phase 6i).

Each widget is a function ``(state: HudState, *, max_width: int) ->
str``. It returns the rendered ANSI-coloured line, or ``""`` if it
has nothing to show (e.g. ``git_line`` returns empty when not in a
git repo).

Widgets registered in :data:`WIDGET_REGISTRY` are looked up by the
pipeline; new widgets just register a new entry there.

Coloring uses raw ANSI escapes (no Rich dependency) so the same
rendered text can flow into prompt_toolkit's toolbar (which speaks
ANSI directly) and into stdout for ``lyra hud preview``. Tests use
:func:`strip_ansi` from :mod:`lyra_cli.hud.testing` to compare
against plain text.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from .width import truncate_to_columns

if TYPE_CHECKING:  # avoid circular import at runtime
    from .pipeline import HudState


# ---------------------------------------------------------------------------
# ANSI escape helpers — no rich dependency.
# ---------------------------------------------------------------------------

_ESC = "\x1b["
_RESET = f"{_ESC}0m"

_DIM = f"{_ESC}2m"
_BOLD = f"{_ESC}1m"
_FG_GREEN = f"{_ESC}32m"
_FG_CYAN = f"{_ESC}36m"
_FG_YELLOW = f"{_ESC}33m"
_FG_RED = f"{_ESC}31m"
_FG_MAGENTA = f"{_ESC}35m"
_FG_BLUE = f"{_ESC}34m"
_FG_GREY = f"{_ESC}90m"


def _color(text: str, code: str) -> str:
    return f"{code}{text}{_RESET}"


def _bar(used: int, total: int, *, width: int = 20) -> str:
    """Render a [████──────] usage bar, ``used/total`` filled."""
    if total <= 0:
        return _color("[" + "─" * width + "]", _FG_GREY)
    fill = max(0, min(width, round(width * used / total)))
    bar = "█" * fill + "─" * (width - fill)
    pct = used / total
    code = _FG_GREEN if pct < 0.7 else (_FG_YELLOW if pct < 0.9 else _FG_RED)
    return _color(f"[{bar}]", code)


# ---------------------------------------------------------------------------
# Widget implementations
# ---------------------------------------------------------------------------


def _identity_line(state: HudState, *, max_width: int) -> str:
    """``● lyra session=<id> mode=<mode> model=<model>``."""
    parts: list[str] = [_color("●", _FG_GREEN), _color("lyra", _BOLD)]
    if state.session_id:
        parts.append(_color(f"session={state.session_id}", _FG_GREY))
    parts.append(_color(f"mode={state.mode}", _FG_CYAN))
    if state.model:
        parts.append(_color(f"model={state.model}", _FG_MAGENTA))
    return truncate_to_columns(" ".join(parts), max_width)


def _context_bar(state: HudState, *, max_width: int) -> str:
    """``ctx [████──] 24,512 / 200,000 (12%)``."""
    if state.context_max <= 0:
        return ""
    pct = state.context_used / state.context_max * 100
    bar = _bar(state.context_used, state.context_max, width=24)
    line = (
        f"{_color('ctx', _FG_GREY)} {bar} "
        f"{state.context_used:,} / {state.context_max:,} "
        f"({pct:.0f}%)"
    )
    return truncate_to_columns(line, max_width)


def _usage_line(state: HudState, *, max_width: int) -> str:
    """``$ 0.123 USD  ·  burn 0.05 USD/h``."""
    if state.cost_usd == 0.0 and state.burn_usd_per_hour == 0.0:
        return ""
    cost = _color(f"${state.cost_usd:.3f} USD", _FG_YELLOW)
    parts: list[str] = [cost]
    if state.burn_usd_per_hour > 0:
        burn = _color(
            f"burn {state.burn_usd_per_hour:.2f} USD/h", _FG_GREY
        )
        parts.append("·")
        parts.append(burn)
    return truncate_to_columns("  ".join(parts), max_width)


def _tools_line(state: HudState, *, max_width: int) -> str:
    """``tools: bash, edit, test`` — empty if no active tools."""
    if not state.tools_active:
        return ""
    body = ", ".join(state.tools_active)
    return truncate_to_columns(
        f"{_color('tools:', _FG_GREY)} {_color(body, _FG_CYAN)}",
        max_width,
    )


def _agents_line(state: HudState, *, max_width: int) -> str:
    """``agents: planner, executor`` — empty if no active subagents."""
    if not state.agents_active:
        return ""
    body = ", ".join(state.agents_active)
    return truncate_to_columns(
        f"{_color('agents:', _FG_GREY)} {_color(body, _FG_BLUE)}",
        max_width,
    )


_TODO_GLYPH: dict[str, str] = {
    "pending": "○",
    "in_progress": "◐",
    "completed": "●",
    "cancelled": "✕",
}


def _todos_line(state: HudState, *, max_width: int) -> str:
    """``todos: ◐ split session.py · ○ wire HUD · ● fix tests``."""
    if not state.todos:
        return ""
    rendered: list[str] = []
    for text, status in state.todos:
        glyph = _TODO_GLYPH.get(status, "?")
        if status == "completed":
            rendered.append(_color(f"{glyph} {text}", _FG_GREEN))
        elif status == "in_progress":
            rendered.append(_color(f"{glyph} {text}", _FG_YELLOW))
        elif status == "cancelled":
            rendered.append(_color(f"{glyph} {text}", _FG_GREY))
        else:
            rendered.append(_color(f"{glyph} {text}", _FG_CYAN))
    body = " · ".join(rendered)
    return truncate_to_columns(f"{_color('todos:', _FG_GREY)} {body}", max_width)


def _git_line(state: HudState, *, max_width: int) -> str:
    """``git: main · 3 modified``  ·  empty when not a git repo."""
    if state.git_dirty_count < 0 or not state.git_branch:
        return ""
    branch = _color(state.git_branch, _FG_CYAN)
    if state.git_dirty_count == 0:
        return truncate_to_columns(
            f"{_color('git:', _FG_GREY)} {branch} · clean", max_width
        )
    dirty = _color(f"{state.git_dirty_count} modified", _FG_YELLOW)
    return truncate_to_columns(f"{_color('git:', _FG_GREY)} {branch} · {dirty}", max_width)


def _cache_line(state: HudState, *, max_width: int) -> str:
    """``cache: 4m 12s remaining`` — empty when no cache active."""
    if state.cache_ttl_seconds < 0:
        return ""
    secs = state.cache_ttl_seconds
    mins, secs = divmod(secs, 60)
    if mins >= 60:
        hrs, mins = divmod(mins, 60)
        ttl = f"{hrs}h {mins}m"
    elif mins > 0:
        ttl = f"{mins}m {secs}s"
    else:
        ttl = f"{secs}s"
    return truncate_to_columns(
        f"{_color('cache:', _FG_GREY)} {_color(ttl, _FG_GREEN)} remaining",
        max_width,
    )


def _tracer_line(state: HudState, *, max_width: int) -> str:
    """``tracer: ON``  ·  empty when off."""
    if not state.tracer_active:
        return ""
    return truncate_to_columns(
        f"{_color('tracer:', _FG_GREY)} {_color('ON', _FG_GREEN)}",
        max_width,
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


WIDGET_REGISTRY: dict[str, Callable[..., str]] = {
    "identity_line": _identity_line,
    "context_bar": _context_bar,
    "usage_line": _usage_line,
    "tools_line": _tools_line,
    "agents_line": _agents_line,
    "todos_line": _todos_line,
    "git_line": _git_line,
    "cache_line": _cache_line,
    "tracer_line": _tracer_line,
}


# Re-export for tests / external consumers that want to count widgets.
def widget_names() -> list[str]:
    """All registered widget names, in registration order."""
    return list(WIDGET_REGISTRY.keys())


__all__ = ["WIDGET_REGISTRY", "widget_names"]
