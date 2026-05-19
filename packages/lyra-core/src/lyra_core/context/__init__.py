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

v2.0 surfaces (Phase 1 Week 1):
- :class:`LayeredContextManager` / :class:`ContextEntry` / :class:`LayerBudget`
  — 8-layer context system inspired by autocontext for O(1) context growth.

v2.0 surfaces (Phase 1 Week 3):
- :class:`ContextBoundary` / :class:`ContextScope` / :class:`IsolationPolicy`
  — Child-task context isolation for multi-agent coordination.
- :class:`MergeStrategy` / :class:`ContextMerger` / :class:`IsolationStats`
  — Merge strategies and statistics for context isolation.
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
from .isolation import (
    ContextBoundary,
    ContextMerger,
    ContextScope,
    IsolationPolicy,
    IsolationStats,
    MergeResult,
    MergeStrategy,
)
from .layered_context import (
    ContextEntry,
    LayerBudget,
    LayeredContextManager,
)
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
    "ContextBoundary",
    "ContextEntry",
    "ContextItem",
    "ContextLayer",
    "ContextMerger",
    "ContextProfile",
    "ContextScope",
    "FORGET_TOOL_DESCRIPTION",
    "FORGET_TOOL_NAME",
    "Invariant",
    "IsolationPolicy",
    "IsolationStats",
    "LayerBudget",
    "LayeredContextManager",
    "MINIMAL",
    "MergeResult",
    "MergeStrategy",
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
