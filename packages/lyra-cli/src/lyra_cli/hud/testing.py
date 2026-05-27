"""Sample HUD state factory for ``lyra hud preview``.

Generates a realistic HudState so users and tests can preview
HUD layouts without a live session.
"""
from __future__ import annotations

import re

from . import HudState


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from *text*."""
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)


def sample_state() -> HudState:
    """Return a realistic HudState for preview/testing."""
    return HudState(
        model="deepseek-chat",
        provider="deepseek",
        mode="edit_automatically",
        tokens_used=45_678,
        tokens_max=200_000,
        turn=12,
        agent_count=4,
        agent_running=2,
        duration_s=842.0,
        cost_usd=0.0421,
        tasks=[
            {"label": "Research: transformer architecture", "status": "done"},
            {"label": "Design: agent pipeline", "status": "running"},
            {"label": "Implement: data layer", "status": "pending"},
            {"label": "Test: integration suite", "status": "pending"},
            {"label": "Review: code quality", "status": "pending"},
            {"label": "Docs: update README", "status": "pending"},
        ],
        memory_mb=142.3,
        compaction_count=3,
        bg_tasks=1,
    )
