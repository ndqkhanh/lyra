"""Enhanced spinner states for Lyra TUI v2.

Provides Claude Code-style spinner states with fun names, timing,
token tracking, and thinking time display.
"""
from __future__ import annotations

import random
import time
from typing import Final

# Fun spinner state names matching Claude Code's style
SPINNER_STATES: Final[list[str]] = [
    "Blanching", "Roosting", "Pollinating", "Galloping",
    "Puttering", "Brewing", "Percolating", "Simmering",
    "Steeping", "Marinating", "Fermenting", "Distilling",
]

# Spinner glyphs matching Claude Code
SPINNER_GLYPHS: Final[list[str]] = ["⏺", "✳", "✻", "✶", "✽", "❋", "✺", "✹"]


def _humanize_tokens(n: int) -> str:
    """Format token count in compact form (1.2K, 45.8K, etc.)."""
    if n < 1_000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1_000:.1f}K"
    return f"{n / 1_000_000:.1f}M"


def _format_duration(seconds: float) -> str:
    """Format duration as Xs, Xm Ys, or Xh Ym."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s" if secs > 0 else f"{mins}m"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m" if mins > 0 else f"{hours}h"


def format_spinner_status(
    elapsed_s: float,
    tokens_in: int = 0,
    tokens_out: int = 0,
    thinking_s: float = 0,
    state_name: str | None = None,
) -> str:
    """Format spinner status line matching Claude Code style.

    Example outputs:
        ✶ Brewing… (45s · ↑ 1.2K tokens · thought for 5s)
        ✳ Blanching… (10m 50s · ↓ 62.1K tokens · thought for 28s)
        ✽ Pollinating… (1m 0s · ↓ 2.6K tokens · thought for 4s)

    Args:
        elapsed_s: Elapsed time in seconds
        tokens_in: Input tokens (shown with ↑)
        tokens_out: Output tokens (shown with ↓)
        thinking_s: Extended thinking time in seconds
        state_name: Optional state name (random if not provided)

    Returns:
        Formatted spinner status string with Rich markup
    """
    # Pick random spinner glyph and state name
    glyph = random.choice(SPINNER_GLYPHS)
    state = state_name or random.choice(SPINNER_STATES)

    # Format elapsed time
    elapsed = _format_duration(elapsed_s)

    # Build status parts
    parts = [f"{glyph} {state}… ({elapsed}"]

    if tokens_in > 0:
        parts.append(f" · ↑ {_humanize_tokens(tokens_in)} tokens")
    if tokens_out > 0:
        parts.append(f" · ↓ {_humanize_tokens(tokens_out)} tokens")
    if thinking_s > 0:
        parts.append(f" · thought for {thinking_s:.0f}s")

    parts.append(")")

    return "".join(parts)


def get_random_spinner_state() -> str:
    """Get a random spinner state name."""
    return random.choice(SPINNER_STATES)


def get_random_spinner_glyph() -> str:
    """Get a random spinner glyph."""
    return random.choice(SPINNER_GLYPHS)


__all__ = [
    "SPINNER_STATES",
    "SPINNER_GLYPHS",
    "format_spinner_status",
    "get_random_spinner_state",
    "get_random_spinner_glyph",
]
