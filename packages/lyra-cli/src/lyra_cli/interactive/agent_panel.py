"""Sub-agent panel renderer — Claude Code style.

Renders one display line per sub-agent record:

    ⏺ main / general-purpose  running deep analysis  3m 4s · ↓ 63.6k tokens
    ◯ main / executor         done                   12s · ↓ 1.2k tokens
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .status_source import SubAgentRecord

_ICON_ACTIVE = "⏺"
_ICON_IDLE = "◯"


def _fmt_elapsed(seconds: float) -> str:
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    return f"{s // 60}m {s % 60}s"


def _fmt_tokens(n: int) -> str:
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


def render_agent_panel(
    records: list[SubAgentRecord], now: float | None = None
) -> list[str]:
    """Return one display line per sub-agent record.

    Args:
        records: List of SubAgentRecord instances (active or completed).
        now: Reference monotonic time for elapsed calculation. Defaults to
            ``time.monotonic()`` so callers can pin it for deterministic tests.

    Returns:
        List of plain-text strings, one per agent, with no trailing newlines.
        Returns ``[]`` when *records* is empty.
    """
    if now is None:
        now = time.monotonic()
    lines = []
    for r in records:
        icon = _ICON_ACTIVE if r.state == "running" else _ICON_IDLE
        elapsed = _fmt_elapsed(now - r.started_at)
        toks = _fmt_tokens(r.tokens_down)
        desc = r.description[:40]
        line = f"{icon} main / {r.role}  {desc}  {elapsed} · ↓ {toks} tokens"
        lines.append(line)
    return lines


__all__ = ["_fmt_elapsed", "_fmt_tokens", "render_agent_panel"]
