"""Lyra HUD — claude-hud-inspired live status pane (Phase 6i).

A terminal status pane that renders Lyra's session state — identity
banner, context window usage, token burn, active tools / agents /
todos, git status, prompt-cache TTL, tracer activity — in a single
declarative layout that can be embedded in `prompt_toolkit`'s
toolbar OR rendered standalone via ``lyra hud preview``.

Inspirations
------------
- :repo:`jarrodwatts/claude-hud` — visual + UX inspiration. We
  re-implemented natively in Python because the upstream couples
  deeply to Claude Code's stdin / transcript JSONL contract; Lyra
  has its own session state model so we wire the widgets to that
  directly.
- ``prompt_toolkit``'s toolbar API for inline embedding.
- Rich's renderables for standalone preview.

Public API
----------
- :class:`HudState` — pure dataclass; what the renderer consumes.
- :func:`render` — turn a :class:`HudState` into ANSI-coloured text.
- :func:`load_preset` — built-in presets (``"compact"``, ``"full"``,
  ``"minimal"``); operators can override via ``~/.lyra/hud.yaml``.
"""

from __future__ import annotations

from .config import HudConfig, available_presets, load_preset
from .pipeline import HudState, render, render_inline

__all__ = [
    "HudConfig",
    "HudState",
    "available_presets",
    "load_preset",
    "render",
    "render_inline",
]
