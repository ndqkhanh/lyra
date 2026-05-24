"""Claude Code-style live turn-progress display with nyan-bar animation.

Shown above the streaming panel during an LLM turn so the user can see
which phases completed (skills injection, memory loading) and how long
the current turn has been running — mirrors the layered spinner +
checklist display in Claude Code.

Public API::

    from .live_progress import nyan_bar, TurnProgressHeader, make_turn_phases

    phases = make_turn_phases(skills=True, memory=False)
    header = TurnProgressHeader(phases, tick=0, elapsed=2.5, verb="Thinking")

    # During streaming:
    from rich.console import Group
    live.update(Group(header, chat_panel))
"""
from __future__ import annotations

from typing import Literal

from rich.text import Text


# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

_NYAN_PALETTE: list[str] = [
    "#FF0000",  # red
    "#FF7F00",  # orange
    "#FFFF00",  # yellow
    "#00CC00",  # green
    "#0088FF",  # blue
    "#8B00FF",  # violet
]

_PHASE_GLYPH: dict[str, str] = {
    "done":    "✓",
    "running": "◼",
    "pending": "◻",
    "error":   "✗",
}

_PHASE_COLOR: dict[str, str] = {
    "done":    "#7CFFB2",
    "running": "#00E5FF",
    "pending": "#6B7280",
    "error":   "#FF5370",
}

PhaseState = Literal["done", "running", "pending", "error"]

_INDENT_FIRST = "  ⎿  "
_INDENT_REST  = "     "
_FLOW_GLYPH = "✳"  # Claude Code's progress glyph


# ---------------------------------------------------------------------------
# nyan_bar
# ---------------------------------------------------------------------------


def nyan_bar(width: int = 6, tick: int = 0) -> Text:
    """Return a rainbow-coloured progress bar (nyan-cat style).

    ``tick`` rotates the colour offset so successive renders animate.
    Each character is one ``━`` block in a cycling palette.

    >>> bar = nyan_bar(width=3, tick=0)
    >>> len(bar._spans)
    3
    """
    out = Text()
    for i in range(width):
        color = _NYAN_PALETTE[(i + tick) % len(_NYAN_PALETTE)]
        out.append("━", style=f"bold {color}")
    return out


# ---------------------------------------------------------------------------
# Phase list helpers
# ---------------------------------------------------------------------------


def make_turn_phases(
    *,
    skills: bool = False,
    memory: bool = False,
    extra: list[tuple[str, PhaseState]] | None = None,
) -> list[tuple[str, PhaseState]]:
    """Build a phase list for :class:`TurnProgressHeader`.

    Only includes phases that actually ran this turn so the checklist
    doesn't show "skills loaded" on a bare no-skill session.
    """
    phases: list[tuple[str, PhaseState]] = []
    if skills:
        phases.append(("Skills loaded", "done"))
    if memory:
        phases.append(("Memory loaded", "done"))
    if extra:
        phases.extend(extra)
    return phases


# ---------------------------------------------------------------------------
# TurnProgressHeader
# ---------------------------------------------------------------------------


def _humanise_tokens(n: int) -> str:
    if n < 1_000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1_000:.1f}k"
    return f"{n / 1_000_000:.1f}M"


def _fmt_elapsed(secs: float) -> str:
    m, s = divmod(int(secs), 60)
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


class TurnProgressHeader:
    """Claude Code-style progress header with optional phase checklist.

    Designed to sit above the streaming ``chat_renderable`` panel inside
    a ``rich.console.Group`` so it scrolls away naturally when the Live
    context exits (``transient=False`` on the outer Live keeps the
    panel; this header is the *last* thing updated so it too remains).

    Attributes rendered::

        ✳ Thinking… (3s · ↑ 1.2k tokens)
          ⎿  ✓ Skills loaded
          ⎿  ✓ Memory loaded
          ⎿  ◼ Streaming reply

    Pass ``phases=[]`` and ``streaming=False`` to get just the glyph + verb.
    """

    def __init__(
        self,
        phases: list[tuple[str, PhaseState]],
        *,
        tick: int = 0,
        elapsed: float = 0.0,
        verb: str = "Thinking",
        streaming: bool = True,
        nyan_width: int = 6,
        tokens: int = 0,
        tokens_down: bool = True,
    ) -> None:
        self.phases = phases
        self.tick = tick
        self.elapsed = elapsed
        self.verb = verb
        self.streaming = streaming
        self.nyan_width = nyan_width
        self.tokens = tokens
        self.tokens_down = tokens_down

    def __rich__(self) -> Text:
        return self.render()

    def render(self) -> Text:
        """Return the full Text renderable for this header."""
        out = Text()
        # ✳ Verb… (elapsed · ↑/↓ tokens)
        elapsed_str = _fmt_elapsed(self.elapsed)
        out.append(f"{_FLOW_GLYPH} ", style="bold #00E5FF")
        out.append(f"{self.verb}…", style="bold bright_white")
        out.append(f" ({elapsed_str}", style="#6B7280")
        if self.tokens > 0:
            arrow = "↓" if self.tokens_down else "↑"
            out.append(f" · {arrow} {_humanise_tokens(self.tokens)}", style="#6B7280")
        out.append(")", style="#6B7280")
        # Phase checklist
        all_phases = list(self.phases)
        if self.streaming:
            all_phases.append(("Streaming reply", "running"))
        for i, (label, state) in enumerate(all_phases):
            glyph = _PHASE_GLYPH.get(state, "◻")
            glyph_color = _PHASE_COLOR.get(state, "#6B7280")
            label_style = "bright_white" if state == "running" else "#A1A7B3"
            prefix = _INDENT_FIRST if i == 0 else _INDENT_REST
            out.append("\n")
            out.append(prefix, style="#6B7280")
            out.append(glyph + " ", style=f"bold {glyph_color}")
            out.append(label, style=label_style)
        return out


__all__ = [
    "nyan_bar",
    "make_turn_phases",
    "TurnProgressHeader",
    "PhaseState",
]
