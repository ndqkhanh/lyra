"""Lyra context engine.

v1 surfaces:
- :class:`ContextAssembler` / :class:`ContextItem` / :class:`ContextLayer`
  — the 5-layer pipeline.
- :func:`compact` — item-level compaction for the pipeline.

v1.7.3 surfaces:
- :func:`compact_messages` + :class:`CompactResult` — transcript-level
  LLM-driven compaction used by the ``/compact`` slash command and
  by :class:`lyra_core.agent.loop.AgentLoop` when a turn approaches a
  context-window cap.
"""
from __future__ import annotations

from .compactor import CompactResult, compact, compact_messages
from .grid import render_context_grid
from .ngc import (
    NGCCompactor,
    NGCDecision,
    NGCItem,
    NGCOutcomeLogger,
    NGCResult,
)
from .pipeline import ContextAssembler, ContextItem, ContextLayer

__all__ = [
    "CompactResult",
    "ContextAssembler",
    "ContextItem",
    "ContextLayer",
    "NGCCompactor",
    "NGCDecision",
    "NGCItem",
    "NGCOutcomeLogger",
    "NGCResult",
    "compact",
    "compact_messages",
    "render_context_grid",
]
