"""Reasoning-effort picker shipped with ``/effort``.

Mirrors Claude Code's five-level taxonomy:

    Speed                                Intelligence
    low      medium      high      xhigh      max

The TTY renders the picker as an arrow-key horizontal slider; this
module exposes the *pure* state machine so unit tests can drive it
without prompt_toolkit. The actual interactive ``Application`` lives
in :mod:`.effort_app` (separate to keep this module dependency-free).

Two callers depend on the value:

1. The OpenAI-compat reasoning preset reads ``HARNESS_REASONING_EFFORT``
   when the model is an o-series / reasoning capable LLM.
2. :func:`effort_to_max_completion_tokens` maps the qualitative level
   to a numeric budget the factory cascade can plug into
   ``max_output_tokens`` (mirrors opencode's ``effort.{low,medium,high,max}``).

Levels: ``low``, ``medium``, ``high``, ``xhigh``, ``max``. The legacy
``ultra`` alias from v0.x continues to resolve to ``max`` at the
dispatch layer (see ``_cmd_effort``).
"""
from __future__ import annotations

from typing import List, Tuple


_LEVELS: Tuple[str, ...] = ("low", "medium", "high", "xhigh", "max")


_BLURBS = {
    "low":    "fastest single-turn attempt; cheapest model + smallest budget",
    "medium": "default — Plan + Build with standard verification",
    "high":   "extra review passes (/review, /ultrareview)",
    "xhigh":  "deep reasoning + multi-pass verifier",
    "max":    "full refute-or-promote loop + cross-channel verifier",
}


# Token budget per level. Numbers are conservative — the factory may
# clamp them down further when the model has a smaller window.
_MAX_TOKENS = {
    "low":    2_000,
    "medium": 4_000,
    "high":   8_000,
    "xhigh":  12_000,
    "max":    16_000,
}


class EffortPicker:
    """In-memory model for the arrow-key /effort slider.

    Vertical (``up``/``down``) and horizontal (``left``/``right``)
    navigation are aliases — the slider is logically horizontal in the
    Claude-Code-style UI but the existing TTY hooks bind both axes so
    users with non-standard keyboards still get muscle memory.
    """

    def __init__(self, *, initial: str = "medium") -> None:
        if initial not in _LEVELS:
            initial = "medium"
        self._cursor = _LEVELS.index(initial)

    @property
    def levels(self) -> Tuple[str, ...]:
        return _LEVELS

    @property
    def value(self) -> str:
        return _LEVELS[self._cursor]

    @property
    def cursor(self) -> int:
        return self._cursor

    def up(self) -> None:
        self._cursor = (self._cursor - 1) % len(_LEVELS)

    def down(self) -> None:
        self._cursor = (self._cursor + 1) % len(_LEVELS)

    # Horizontal aliases — the slider is rendered as a left→right bar
    # (Speed → Intelligence), so ←/→ are the natural keys.
    def left(self) -> None:
        self.up()

    def right(self) -> None:
        self.down()

    def confirm(self) -> str:
        return self.value

    # ----- renderers ---------------------------------------------------

    def render(self) -> str:
        """Vertical legacy render. Retained for non-TTY callers and the
        existing test contract (``▸ medium``-style cursor + every level
        appearing in the output).
        """
        lines = ["Pick a reasoning effort:"]
        for i, level in enumerate(_LEVELS):
            cursor = "▸" if i == self._cursor else " "
            lines.append(f"  {cursor} {level:<7} — {_BLURBS[level]}")
        lines.append("")
        lines.append("(↑/↓ or ←/→ to move · Enter to confirm · Esc to cancel)")
        return "\n".join(lines)

    def render_slider_lines(self, *, width: int = 50) -> List[str]:
        """Claude-Code-style horizontal slider as plain text.

        Returns four lines:

        1. ``Speed`` ── ``Intelligence`` axis labels.
        2. The track itself, ``─``\\ s with a ``▲`` at the cursor's
           proportional position.
        3. Level names aligned beneath their track positions.
        4. Help hint (``←/→`` · Enter · Esc).
        """
        if width < 20:
            width = 20
        n = len(_LEVELS)

        # Proportional cursor & level positions (column indexes 0..width-1).
        def _col(i: int) -> int:
            return 0 if n <= 1 else round(i * (width - 1) / (n - 1))

        cursor_col = _col(self._cursor)

        # Track: ── filling, with a ▲ marker at the cursor.
        track = ["─"] * width
        track[cursor_col] = "▲"
        track_str = "".join(track)

        # Level row: place each level name under its column. The
        # leftmost level is left-anchored (start=0), the rightmost
        # right-anchored (end=width); middle levels are centred so
        # their visual position tracks the cursor's track column.
        level_row = [" "] * width
        for i, level in enumerate(_LEVELS):
            col = _col(i)
            if i == 0:
                start = 0
            elif i == n - 1:
                start = width - len(level)
            else:
                start = col - len(level) // 2
            start = max(0, min(start, width - len(level)))
            for j, ch in enumerate(level):
                pos = start + j
                if 0 <= pos < width:
                    level_row[pos] = ch
        level_row_str = "".join(level_row).rstrip()

        # Axis labels: "Speed" left-aligned to col 0, "Intelligence"
        # right-aligned to col width-1.
        left_label = "Speed"
        right_label = "Intelligence"
        gap = width - len(left_label) - len(right_label)
        if gap < 1:
            gap = 1
        axis = left_label + (" " * gap) + right_label

        return [
            axis,
            track_str,
            level_row_str,
            "←/→ to adjust · Enter to confirm · Esc to cancel",
        ]


def effort_to_max_completion_tokens(level: str) -> int:
    """Return the recommended ``max_output_tokens`` for *level*.

    Falls back to the medium budget for unknown labels so a typo at
    the call site never zeroes the budget.
    """
    return _MAX_TOKENS.get(level, _MAX_TOKENS["medium"])


def apply_effort(level: str) -> str:
    """Persist *level* into the env so the factory cascade picks it up.

    Returns the canonical level string (or ``medium`` for an unknown
    input). Environment-variable contract:

    * ``HARNESS_REASONING_EFFORT`` — read by the OpenAI / Anthropic
      reasoning presets.
    * ``HARNESS_MAX_OUTPUT_TOKENS`` — soft hint consumed by the same
      presets when the user hasn't pinned a value via settings.json.
    """
    import os as _os

    canonical = level if level in _LEVELS else "medium"
    _os.environ["HARNESS_REASONING_EFFORT"] = canonical
    _os.environ["HARNESS_MAX_OUTPUT_TOKENS"] = str(
        effort_to_max_completion_tokens(canonical)
    )
    return canonical


__all__ = [
    "EffortPicker",
    "effort_to_max_completion_tokens",
    "apply_effort",
]
