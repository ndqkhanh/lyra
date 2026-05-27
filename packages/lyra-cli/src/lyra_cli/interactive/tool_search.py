"""Gap 17: Dynamic Tool Search for Lyra CLI.

Provides ``ToolSearchRegistry`` — a lazy-load registry that exposes
tool definitions on demand via keyword search instead of loading all
definitions upfront. Controlled via ``LYRA_ENABLE_TOOL_SEARCH`` env var.
"""
from __future__ import annotations

import os
from typing import Any

_ENVVAR = "LYRA_ENABLE_TOOL_SEARCH"


class ToolSearchRegistry:
    """Lazy-load tool definitions on demand via keyword search.

    Matches Claude Code's ``ENABLE_TOOL_SEARCH`` concept: tools are only
    exposed when the user (or LLM) searches for them, reducing upfront
    context-window pressure. Once matched, a tool stays in
    ``discovered_tools`` until compaction.
    """

    def __init__(self, all_tools: list[dict[str, Any]]) -> None:
        self._all_tools = list(all_tools)
        # Tools already revealed this session — persist until compaction.
        self.discovered_tools: set[str] = set()

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Return up to ``limit`` tools matching ``query`` (name or summary).

        Scoring: exact-name > name-starts-with > name-contains > summary-contains.
        Every matched tool is added to ``discovered_tools`` so subsequent
        lookups find it without re-querying.
        """
        q = query.lower()
        scored: list[tuple[int, dict[str, Any]]] = []
        for tool in self._all_tools:
            name = tool["name"].lower()
            summary = tool["summary"].lower()
            if q == name:
                score = 100
            elif name.startswith(q):
                score = 90
            elif q in name:
                score = 80
            elif q in summary:
                score = 50
            else:
                continue
            scored.append((score, tool))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [t for _, t in scored[:limit]]
        for t in results:
            self.discovered_tools.add(t["name"])
        return results

    @property
    def discovered_count(self) -> int:
        return len(self.discovered_tools)

    @property
    def total_count(self) -> int:
        return len(self._all_tools)

    @staticmethod
    def parse_enabled() -> tuple[bool, float | None]:
        """Parse ``LYRA_ENABLE_TOOL_SEARCH``.

        Returns ``(enabled, threshold_pct)``:

        * ``"true"``       -> ``(True, None)``
        * ``"auto"``       -> ``(True, 10.0)``   (auto-activate when defs > 10 % of context)
        * ``"auto:5"``     -> ``(True, 5.0)``    (custom threshold)
        * ``"false"`` / missing -> ``(False, None)``
        """
        raw = os.environ.get(_ENVVAR, "").strip().lower()
        if not raw or raw == "false":
            return False, None
        if raw == "true":
            return True, None
        if raw == "auto":
            return True, 10.0
        if raw.startswith("auto:"):
            try:
                return True, float(raw.split(":", 1)[1])
            except (ValueError, IndexError):
                return True, 10.0
        return False, None
