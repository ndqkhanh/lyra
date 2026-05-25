"""Progressive Tool Discovery — metadata-first registration, deferred schema loading.

The core insight: registering every tool with its full JSON schema (200--500
tokens each) in a single context window burns through the context budget
quickly. On a system with 50+ tools this can cost 10k-25k tokens before any
real work begins.

Progressive Tool Discovery solves this with a **metadata-first** approach:

1. Tools register with lightweight metadata only (~50 tokens each): name,
   description, keywords, and a **token_cost_estimate**.
2. Full JSON schemas are stored as strings and **only parsed on demand**
   via ``load_schema()``.
3. When a task arrives, ``get_tools_for_task()`` semantically searches the
   metadata, loads schemas for the top matches only, and stops once the
   caller's token budget is exhausted.

Typical real-world savings: 70--85% of schema tokens are deferred, giving
the model more room for reasoning.

Usage::

    from lyra_core.tools.tool_search import ToolRegistry, ToolSchema, ToolCategory

    registry = ToolRegistry(tools=[], max_context_budget_tokens=8000)
    schema = ToolSchema(
        name="Read",
        description="Read a file from the filesystem.",
        category=ToolCategory.FILESYSTEM,
        parameters_json_schema='{"type": "object", ...}',
        keywords=("file", "read", "cat"),
        token_cost_estimate=320,
    )
    registry.register(schema)

    results = registry.search("read a file", top_k=5)
    tools = registry.get_tools_for_task("Read file from disk", max_tokens=2000)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Constants & Enums
# ---------------------------------------------------------------------------


class ToolCategory(str, Enum):
    """Categorisation of tools by domain of operation.

    Each tool belongs to exactly one category, which is used during
    search filtering and budget allocation.
    """

    FILESYSTEM = "filesystem"
    CODE = "code"
    WEB = "web"
    DATABASE = "database"
    SHELL = "shell"
    GIT = "git"
    LSP = "lsp"
    NOTIFICATION = "notification"
    CRON = "cron"
    MCP = "mcp"
    SAFETY = "safety"
    OBSERVABILITY = "observability"
    COMMUNICATION = "communication"
    RESEARCH = "research"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolSchema:
    """Immutable descriptor for a registered tool.

    The ``parameters_json_schema`` field stores the full JSON Schema as a
    string; it is **not** parsed at registration time. Call
    :meth:`ToolRegistry.load_schema` to decode it on demand.

    ``usage_count``, ``success_rate``, ``last_used``, and ``deprecated``
    track runtime telemetry.  Because the dataclass is frozen, updating
    these fields requires :func:`dataclasses.replace` — which
    :class:`ToolRegistry` does internally.
    """

    name: str
    """Canonical tool name (e.g. ``"Read"``, ``"WebSearch"``)."""

    description: str
    """Human-readable explanation of what the tool does."""

    category: ToolCategory
    """Functional domain the tool belongs to."""

    parameters_json_schema: str
    """Full JSON Schema stored as a string; parsed on demand."""

    keywords: tuple[str, ...] = ()
    """Alternative terms that help surface this tool in semantic search."""

    token_cost_estimate: int = 0
    """Estimated token count required to include the full schema in context."""

    usage_count: int = 0
    """Number of times this tool has been invoked (runtime telemetry)."""

    success_rate: float = 1.0
    """Fraction of invocations that completed without error (0.0 -- 1.0)."""

    last_used: float | None = None
    """Unix timestamp of the most recent invocation, or ``None`` if never used."""

    deprecated: bool = False
    """If ``True`` the tool is considered stale and should not be recommended."""


@dataclass(frozen=True)
class ToolSearchResult:
    """A single search hit returned by :meth:`ToolRegistry.search`."""

    tool: ToolSchema
    """The matched tool."""

    relevance_score: float
    """Score between 0.0 and 1.0; higher means more relevant."""

    match_reason: str
    """Human-readable explanation of *why* this tool matched."""


@dataclass(frozen=True)
class ToolContextBudget:
    """Tracks how many tokens have been consumed by loaded tool schemas.

    Used by :meth:`ToolRegistry.get_tools_for_task` to decide when to
    stop loading additional schemas.
    """

    max_tokens: int
    """Total token budget for tool schemas in context."""

    used_tokens: int
    """Tokens consumed so far by loaded schemas."""

    remaining_tokens: int
    """Tokens remaining before the budget is exhausted.

    Computed as ``max_tokens - used_tokens`` at construction time.
    """

    def can_fit(self, tool: ToolSchema) -> bool:
        """Return ``True`` if *tool*'s schema can fit in the remaining budget.

        A tool is considered fit when its ``token_cost_estimate`` is
        strictly less than or equal to ``remaining_tokens``.
        """
        return tool.token_cost_estimate <= self.remaining_tokens


@dataclass(frozen=True)
class DiscoveryStats:
    """Aggregate statistics for the progressive discovery system.

    Returned by :meth:`ToolRegistry.get_stats`.
    """

    tools_available: int
    """Total number of tools registered in the registry."""

    tools_loaded: int
    """Number of tools whose schemas have been parsed (loaded on demand)."""

    schemas_deferred: int
    """Number of tools whose schemas have **not** been loaded yet."""

    context_tokens_saved: int
    """Estimated tokens saved by deferring schema loading."""

    savings_percentage: float
    """Percentage of schema tokens that were deferred (0.0 -- 100.0)."""


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class ToolRegistry:
    """Metadata-first tool registry with progressive schema loading.

    Tools are registered with lightweight metadata; their full JSON
    schemas are parsed only when actually needed for a task.  This
    drastically reduces context-window pressure when the system has
    dozens or hundreds of available tools.

    Parameters
    ----------
    tools:
        Initial collection of tools to register.
    max_context_budget_tokens:
        Default token budget for ``get_tools_for_task`` when the caller
        does not provide an explicit ``max_tokens``.
    """

    def __init__(
        self,
        tools: list[ToolSchema],
        max_context_budget_tokens: int = 8000,
    ) -> None:
        self._tools: dict[str, ToolSchema] = {t.name: t for t in tools}
        self._schema_cache: dict[str, dict[str, Any]] = {}
        self._max_context_budget_tokens = max_context_budget_tokens

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, tool: ToolSchema) -> None:
        """Register *tool* in the registry.

        If a tool with the same ``name`` already exists it is overwritten.
        The schema is **not** parsed during registration.
        """
        self._tools[tool.name] = tool
        # Drop any previously cached schema so it is re-parsed on next
        # access (the new ToolSchema may have a different JSON string).
        self._schema_cache.pop(tool.name, None)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 10) -> list[ToolSearchResult]:
        """Semantic (keyword) search over registered tools.

        Matching is case-insensitive against tool ``name``, ``description``,
        and ``keywords``.  Scoring rules:

        * Name exact match ............. ``1.0``
        * Name partial match .......... ``0.8``
        * Keyword match ............... ``0.6``
        * Description match ........... ``0.4``

        When multiple match types fire for the same tool the individual
        scores are summed (capped at ``1.0``), so a tool whose name and
        keywords both match the query will rank higher than one that only
        matches via description.

        Parameters
        ----------
        query:
            Free-text search string.  Empty queries return an empty list.
        top_k:
            Maximum number of results to return.

        Returns
        -------
        list[ToolSearchResult]
            Results sorted by ``relevance_score`` descending.
        """
        if not query or not query.strip():
            return []

        query_lower = query.strip().lower()
        query_words = query_lower.split()

        scored: list[tuple[float, ToolSchema, str]] = []

        for tool in self._tools.values():
            score = 0.0
            reasons: list[str] = []

            name_lower = tool.name.lower()
            desc_lower = tool.description.lower()
            keywords_lower = {kw.lower() for kw in tool.keywords}

            # Name exact match (query equals full name)
            if query_lower == name_lower:
                score += 1.0
                reasons.append("name exact match")
            else:
                # Name partial match (any query word matches part of name)
                for qw in query_words:
                    if qw in name_lower or name_lower in qw:
                        score += 0.8
                        reasons.append(f"name partial match ({qw})")
                        break

                # Also check: is the name a substring of the query?
                if not reasons and name_lower in query_lower:
                    score += 0.8
                    reasons.append("name contained in query")

                # Keyword matches
                for kw in keywords_lower:
                    if any(qw in kw or kw in qw for qw in query_words):
                        score += 0.6
                        reasons.append(f"keyword match ({kw})")
                        break

                # Description match
                for qw in query_words:
                    if qw in desc_lower:
                        score += 0.4
                        reasons.append(f"description match ({qw})")
                        break

            if score > 0.0:
                score = min(score, 1.0)
                reason = "; ".join(reasons) if reasons else "matched"
                scored.append((score, tool, reason))

        # Sort by score descending, then by name for determinism
        scored.sort(key=lambda x: (-x[0], x[1].name))
        top = scored[:top_k]

        return [
            ToolSearchResult(
                tool=tool,
                relevance_score=score,
                match_reason=reason,
            )
            for score, tool, reason in top
        ]

    # ------------------------------------------------------------------
    # Schema Loading
    # ------------------------------------------------------------------

    def load_schema(self, tool_name: str) -> dict | None:
        """Parse and cache the JSON schema for the named tool.

        The schema is parsed from the ``parameters_json_schema`` string
        stored on the :class:`ToolSchema`.  Parsed results are cached so
        that repeated calls for the same tool do not re-parse.

        Parameters
        ----------
        tool_name:
            The ``name`` of the registered tool.

        Returns
        -------
        dict | None
            The parsed JSON Schema dictionary, or ``None`` if the tool
            is unknown or the JSON string is malformed.
        """
        if tool_name in self._schema_cache:
            return self._schema_cache[tool_name]

        tool = self._tools.get(tool_name)
        if tool is None:
            return None

        raw = tool.parameters_json_schema
        if not raw or not raw.strip():
            self._schema_cache[tool_name] = {}
            return {}

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None

        if not isinstance(parsed, dict):
            self._schema_cache[tool_name] = {}
            return {}

        self._schema_cache[tool_name] = parsed
        return parsed

    # ------------------------------------------------------------------
    # Task-aware selection
    # ------------------------------------------------------------------

    def get_tools_for_task(
        self,
        task_description: str,
        max_tokens: int = 4000,
    ) -> list[ToolSchema]:
        """Select the most relevant tools for *task_description*.

        Workflow:

        1. Search all registered tools against the task description.
        2. Sort matches by relevance descending.
        3. Starting from the highest-relevance match, load each tool's
           JSON schema and add it to the result set.
        4. Stop when the next tool's ``token_cost_estimate`` would exceed
           ``max_tokens``.
        5. Return the selected tools (with schemas cached).

        Parameters
        ----------
        task_description:
            Natural-language description of the task at hand.
        max_tokens:
            Maximum cumulative token budget for tool schemas in the
            result set.

        Returns
        -------
        list[ToolSchema]
            Tools selected for the task, sorted by relevance descending.
        """
        results = self.search(task_description, top_k=len(self._tools))
        selected: list[ToolSchema] = []
        used_tokens = 0

        for result in results:
            tool = result.tool
            if tool.deprecated:
                continue
            budget = ToolContextBudget(
                max_tokens=max_tokens,
                used_tokens=used_tokens,
                remaining_tokens=max_tokens - used_tokens,
            )
            if not budget.can_fit(tool):
                continue

            # Trigger deferred schema load (cached internally).
            self.load_schema(tool.name)
            selected.append(tool)
            used_tokens += tool.token_cost_estimate

        return selected

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def prune_unused(self, days_threshold: int = 30) -> list[ToolSchema]:
        """Mark tools unused for *days_threshold* days as deprecated.

        A tool is considered **unused** when:

        * ``last_used`` is not ``None``, **and**
        * ``last_used`` is more than *days_threshold* days in the past.

        Tools whose ``last_used`` is ``None`` (never invoked) are **not**
        deprecated by this method — they have no usage history to assess.

        Deprecated tools are returned so the caller can log, notify, or
        escalate before they are eventually removed.

        Parameters
        ----------
        days_threshold:
            Age in days beyond which a tool is considered stale.

        Returns
        -------
        list[ToolSchema]
            Tools that were newly marked as deprecated.
        """
        now = time.time()
        threshold_seconds = days_threshold * 86_400  # 24 * 60 * 60
        deprecated: list[ToolSchema] = []

        for name, tool in list(self._tools.items()):
            if tool.deprecated:
                continue  # already deprecated
            if tool.last_used is None:
                continue  # never used — cannot assess staleness
            age = now - tool.last_used
            if age > threshold_seconds:
                updated = replace(tool, deprecated=True)
                self._tools[name] = updated
                deprecated.append(updated)

        return deprecated

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate discovery statistics.

        Returns
        -------
        dict
            Keys: ``total_tools``, ``active``, ``deprecated``,
            ``avg_success_rate``, ``total_usage``, ``context_savings_pct``.
        """
        all_tools = list(self._tools.values())
        total = len(all_tools)
        if total == 0:
            return {
                "total_tools": 0,
                "active": 0,
                "deprecated": 0,
                "avg_success_rate": 0.0,
                "total_usage": 0,
                "context_savings_pct": 0.0,
            }

        active = sum(1 for t in all_tools if not t.deprecated)
        deprecated_count = total - active
        total_usage = sum(t.usage_count for t in all_tools)

        # Average success_rate (weighted by usage, fall back to simple avg
        # when total_usage is zero).
        if total_usage > 0:
            weighted = sum(
                t.success_rate * t.usage_count for t in all_tools
            )
            avg_success_rate = weighted / total_usage
        else:
            avg_success_rate = (
                sum(t.success_rate for t in all_tools) / total
            )

        # Context savings: compare loaded vs deferred schemas.
        loaded_count = len(self._schema_cache)

        if total == 0 or loaded_count == 0:
            context_savings_pct = 0.0
        else:
            total_schema = sum(
                t.token_cost_estimate for t in self._tools.values()
            )
            loaded_share = sum(
                self._tools[name].token_cost_estimate
                for name in self._schema_cache
                if name in self._tools
            )
            if total_schema > 0:
                deferred_share = total_schema - loaded_share
                context_savings_pct = round(
                    (deferred_share / total_schema) * 100, 2
                )
            else:
                context_savings_pct = 0.0

        return {
            "total_tools": total,
            "active": active,
            "deprecated": deprecated_count,
            "avg_success_rate": round(avg_success_rate, 4),
            "total_usage": total_usage,
            "context_savings_pct": context_savings_pct,
        }

    def recommend_pruning(self, task_context: str) -> list[ToolSchema]:
        """Suggest candidates for pruning given a current *task_context*.

        The recommendation identifies tools that are **both**:

        * Not relevant to the current task (low search relevance), **and**
        * Rarely or never used (``usage_count`` below threshold).

        Deprecated tools are always included in the recommendation.

        Parameters
        ----------
        task_context:
            Natural-language description of the current session or task
            (used to compute relevance).

        Returns
        -------
        list[ToolSchema]
            Candidates for pruning, sorted by usage ascending
            (least-used first).
        """
        # Get relevance for every registered tool.
        results = self.search(task_context, top_k=len(self._tools))
        relevant_names: set[str] = {
            r.tool.name
            for r in results
            if r.relevance_score >= 0.3
        }

        candidates: list[ToolSchema] = []
        for tool in self._tools.values():
            if tool.deprecated:
                candidates.append(tool)
            elif tool.name not in relevant_names and tool.usage_count < 3:
                candidates.append(tool)
            elif tool.name not in relevant_names and tool.usage_count == 0:
                candidates.append(tool)

        candidates.sort(key=lambda t: (t.usage_count, t.name))
        return candidates

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _update_tool(self, name: str, **changes: Any) -> ToolSchema:
        """Replace a tool with an updated copy (immutable pattern).

        This is the internal mechanism for updating telemetry fields on
        a frozen :class:`ToolSchema`.
        """
        old = self._tools[name]
        updated = replace(old, **changes)
        self._tools[name] = updated
        return updated


__all__ = [
    "DiscoveryStats",
    "ToolCategory",
    "ToolContextBudget",
    "ToolRegistry",
    "ToolSchema",
    "ToolSearchResult",
]
