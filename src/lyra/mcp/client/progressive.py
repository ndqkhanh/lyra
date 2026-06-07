"""Progressive-disclosure wrapper: one umbrella ``MCP`` tool.

Only surfaces specific tool names after the user query mentions concepts
relevant to that tool's description. This keeps cold-start context small.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol


class _AdapterLike(Protocol):
    def list_tools(self) -> list[dict[str, Any]]: ...


@dataclass
class UmbrellaResponse:
    candidate_tools: list[str] = field(default_factory=list)


_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]+")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text)}


@dataclass
class ProgressiveMCP:
    adapter: _AdapterLike
    _surfaced: set[str] = field(default_factory=set)

    def surfaced_tool_names(self) -> list[str]:
        return sorted(self._surfaced)

    def umbrella_call(self, query: str) -> UmbrellaResponse:
        query_tokens = _tokens(query)
        tools = self.adapter.list_tools()
        candidates: list[str] = []
        for t in tools:
            name = str(t.get("name", ""))
            desc = str(t.get("description", ""))
            name_tokens = _tokens(name.replace(".", " "))
            desc_tokens = _tokens(desc)
            # Match if any non-stopword query token appears in name or desc.
            overlap = (name_tokens | desc_tokens) & query_tokens
            if overlap:
                candidates.append(name)
        for name in candidates:
            self._surfaced.add(name)
        return UmbrellaResponse(candidate_tools=candidates)
