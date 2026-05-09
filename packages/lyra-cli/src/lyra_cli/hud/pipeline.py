"""HUD render pipeline (Phase 6i).

Three layers:

1. :class:`HudState` — pure dataclass; the snapshot of session state
   that gets rendered. Built by the REPL driver from the
   :mod:`lyra_cli.interactive.status_source` plus
   :class:`lyra_core.org.budget.BudgetMeter`.
2. :func:`render` — takes a :class:`HudState` plus a
   :class:`HudConfig` (which widgets, what order, what max width) and
   returns the rendered string. Pure function — no I/O.
3. :func:`render_inline` — convenience wrapper that loads the
   ``"inline"`` preset (single line, suitable for prompt_toolkit's
   bottom-toolbar) and renders.

The split lets the prompt_toolkit toolbar callable be a 1-line
``lambda: render_inline(state())`` while ``lyra hud preview`` reuses
the same widgets at full size.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import HudConfig, load_preset
from .widgets import WIDGET_REGISTRY


@dataclass
class HudState:
    """Snapshot of Lyra's session state for the HUD to render.

    Every field defaults to a "no signal" value so a partially-filled
    state is renderable without raising. Widgets that have nothing to
    show return an empty string.

    Attributes
    ----------
    session_id
        Truncated session id (e.g. ``"sess-20260501-abcd"``).
    mode
        One of ``"edit_automatically"``, ``"ask_before_edits"``,
        ``"plan_mode"``, ``"auto_mode"`` (v3.6.0 taxonomy). Legacy
        v3.2.x values (``"agent"``, ``"plan"``, ``"debug"``,
        ``"ask"``) are accepted at construction and rendered as-is —
        the HUD doesn't remap; that's the session's job.
    model
        Provider:model slug (e.g. ``"anthropic:claude-3-5-sonnet"``).
    context_used
        Number of tokens currently in the context window.
    context_max
        Provider's context window cap. ``0`` → "unknown".
    cost_usd
        Cumulative session cost in USD.
    burn_usd_per_hour
        Optional rolling rate; rendered if non-zero.
    tools_active
        Names of tools currently running in this turn.
    agents_active
        Names of subagents currently spawned.
    todos
        ``(text, status)`` tuples; ``status`` is
        ``"pending" | "in_progress" | "completed" | "cancelled"``.
    git_branch
        Current branch name; empty string when not in a git repo.
    git_dirty_count
        Count of modified files; ``-1`` when not a git repo.
    cache_ttl_seconds
        Seconds remaining on the prompt-cache (Anthropic / OpenAI);
        ``-1`` when no cache active.
    tracer_active
        Whether the OTel tracer is currently exporting.
    """

    session_id: str = ""
    mode: str = "edit_automatically"
    model: str = ""
    context_used: int = 0
    context_max: int = 0
    cost_usd: float = 0.0
    burn_usd_per_hour: float = 0.0
    tools_active: list[str] = field(default_factory=list)
    agents_active: list[str] = field(default_factory=list)
    todos: list[tuple[str, str]] = field(default_factory=list)
    git_branch: str = ""
    git_dirty_count: int = -1
    cache_ttl_seconds: int = -1
    tracer_active: bool = False


def render(state: HudState, *, config: HudConfig | None = None,
           max_width: int | None = None) -> str:
    """Render ``state`` as a multi-line ANSI-coloured string.

    Parameters
    ----------
    state
        The snapshot to render.
    config
        Which widgets, in what order. Defaults to ``load_preset("full")``.
    max_width
        Optional column cap; widgets that exceed this are truncated
        with ``…``. Defaults to ``config.max_width`` (typically 120).
    """
    cfg = config or load_preset("full")
    width_cap = max_width if max_width is not None else cfg.max_width

    lines: list[str] = []
    for widget_name in cfg.widgets:
        renderer = WIDGET_REGISTRY.get(widget_name)
        if renderer is None:
            # Unknown widget name — render a clear error so misconfigured
            # ~/.lyra/hud.yaml entries are visible rather than silent.
            lines.append(f"<unknown widget: {widget_name!r}>")
            continue
        rendered = renderer(state, max_width=width_cap)
        if rendered:
            lines.append(rendered)
    return "\n".join(lines)


def render_inline(state: HudState, *, max_width: int | None = None) -> str:
    """Render ``state`` as a single line for the prompt_toolkit toolbar.

    Uses the ``"inline"`` preset which packs identity + context + cost
    into one row, separated by a ``│`` divider. ANSI-coloured for
    terminals that support it (degrades to plain text otherwise — the
    ANSI codes are ignored by `prompt_toolkit` if the terminal is
    NO_COLOR).
    """
    return render(state, config=load_preset("inline"), max_width=max_width)


__all__ = ["HudState", "render", "render_inline"]
