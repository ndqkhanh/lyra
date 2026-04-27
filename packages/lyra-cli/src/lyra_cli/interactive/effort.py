"""Reasoning-effort picker shipped with ``/effort``.

The TTY uses an arrow-key slider; this module exposes the *pure*
state machine so unit tests can drive it without prompt_toolkit.

Two callers depend on the value:

1. The OpenAI-compat reasoning preset reads ``HARNESS_REASONING_EFFORT``
   when the model is an o-series / reasoning capable LLM.
2. :func:`effort_to_max_completion_tokens` maps the qualitative level
   to a numeric budget the factory cascade can plug into
   ``max_output_tokens`` (mirrors opencode's ``effort.{low,medium,high,max}``).

Levels: ``low``, ``medium``, ``high``, ``max``.
"""
from __future__ import annotations

from typing import Tuple


_LEVELS: Tuple[str, ...] = ("low", "medium", "high", "max")


_BLURBS = {
    "low":    "single quick attempt; cheapest model + smallest budget",
    "medium": "default — Plan + Build with standard verification",
    "high":   "extra review passes (/review, /ultrareview)",
    "max":    "full refute-or-promote loop + cross-channel verifier",
}


# Token budget per level. Numbers are conservative — the factory may
# clamp them down further when the model has a smaller window.
_MAX_TOKENS = {
    "low":    2_000,
    "medium": 4_000,
    "high":   8_000,
    "max":    16_000,
}


class EffortPicker:
    """In-memory model for the arrow-key /effort slider."""

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

    def up(self) -> None:
        self._cursor = (self._cursor - 1) % len(_LEVELS)

    def down(self) -> None:
        self._cursor = (self._cursor + 1) % len(_LEVELS)

    def confirm(self) -> str:
        return self.value

    def render(self) -> str:
        lines = ["Pick a reasoning effort:"]
        for i, level in enumerate(_LEVELS):
            cursor = "▸" if i == self._cursor else " "
            lines.append(f"  {cursor} {level:<7} — {_BLURBS[level]}")
        lines.append("")
        lines.append("(↑/↓ to move · Enter to confirm)")
        return "\n".join(lines)


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
