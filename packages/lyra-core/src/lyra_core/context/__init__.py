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

from .clear import (
    FORGET_TOOL_DESCRIPTION,
    FORGET_TOOL_NAME,
    clear_stale_tool_results,
    clear_tool_result,
    collect_cited_span_ids,
    forget_tool_handler,
)
from .compact_validate import (
    Invariant,
    ValidatedCompactResult,
    ValidationReport,
    compact_messages_validated,
    extract_default_invariants,
    validate_compaction,
)
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
from .profile import (
    MINIMAL,
    STANDARD,
    STRICT,
    ContextProfile,
    list_profiles,
    resolve_profile,
)

__all__ = [
    "CompactResult",
    "ContextAssembler",
    "ContextItem",
    "ContextLayer",
    "ContextProfile",
    "FORGET_TOOL_DESCRIPTION",
    "FORGET_TOOL_NAME",
    "Invariant",
    "MINIMAL",
    "NGCCompactor",
    "NGCDecision",
    "NGCItem",
    "NGCOutcomeLogger",
    "NGCResult",
    "STANDARD",
    "STRICT",
    "ValidatedCompactResult",
    "ValidationReport",
    "clear_stale_tool_results",
    "clear_tool_result",
    "collect_cited_span_ids",
    "compact",
    "compact_messages",
    "compact_messages_validated",
    "extract_default_invariants",
    "forget_tool_handler",
    "list_profiles",
    "render_context_grid",
    "resolve_profile",
    "validate_compaction",
]
