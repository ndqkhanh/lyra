"""Test helpers for the HUD — strip_ansi, sample_state."""

from __future__ import annotations

import re

from .pipeline import HudState

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes for plain-text comparison in tests."""
    return _ANSI_RE.sub("", text)


def sample_state(**overrides) -> HudState:
    """Build a representative HudState for examples / preview / tests."""
    defaults = dict(
        session_id="sess-20260501-abcd",
        mode="edit_automatically",
        model="anthropic:claude-3-5-sonnet",
        context_used=24512,
        context_max=200000,
        cost_usd=0.123,
        burn_usd_per_hour=0.05,
        tools_active=["bash", "edit"],
        agents_active=["planner"],
        todos=[
            ("split session.py", "in_progress"),
            ("wire HUD", "pending"),
            ("fix DAG tests", "completed"),
        ],
        git_branch="main",
        git_dirty_count=3,
        cache_ttl_seconds=252,
        tracer_active=True,
    )
    defaults.update(overrides)
    return HudState(**defaults)


__all__ = ["sample_state", "strip_ansi"]
