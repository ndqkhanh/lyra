"""
Dynamic tool discovery at runtime and searchable index of available tools.

Provides ``ToolSearch`` for finding tools by name, description, tag, or
capability at runtime, and ``ToolIndex`` for maintaining a searchable
inverted index of all registered tools.

Classes
-------
ToolSearchResult:
    A single search result.
ToolSearch:
    Dynamic tool discovery at runtime.
ToolIndex:
    Searchable inverted index of available tools.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from lyra.tools.registry import ToolDef

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolSearchResult:
    """A single search result.

    Attributes
    ----------
    tool_name:
        Canonical tool name.
    score:
        Relevance score (higher = more relevant).
    matched_field:
        Which field produced the match (``"name"``, ``"description"``,
        ``"tag"``, ``"capability"``, or ``"parameter"``).
    matched_text:
        The text that matched.
    """

    tool_name: str
    score: float
    matched_field: str = ""
    matched_text: str = ""


# ---------------------------------------------------------------------------
# ToolSearch
# ---------------------------------------------------------------------------


class ToolSearch:
    """Dynamic tool discovery at runtime.

    Searches registered tools by keyword, tag, capability, or parameter
    name.  Maintains a scored relevance ranking.

    Usage::

        search = ToolSearch()
        search.index_tool(tool_def)  # add a single tool
        search.index_tools(tool_defs)  # add multiple tools

        results = search.search("read file")
        for r in results:
            print(r.tool_name, r.score)

        # Find tools with a specific capability
        file_tools = search.find_by_capability("file")
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDef] = {}
        self._index: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
        # ^ term -> [(tool_name, field, value)]

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def index_tool(self, tool: ToolDef) -> None:
        """Add a single tool to the search index.

        Args:
            tool: The tool definition to index.
        """
        self._tools[tool.name] = tool
        self._index_tool_fields(tool)

    def index_tools(self, tools: list[ToolDef]) -> None:
        """Add multiple tools to the search index.

        Args:
            tools: List of tool definitions to index.
        """
        for tool in tools:
            self.index_tool(tool)

    def remove_tool(self, name: str) -> bool:
        """Remove a tool from the index.

        Args:
            name: Tool name to remove.

        Returns:
            True if the tool was found and removed.
        """
        if name not in self._tools:
            return False
        del self._tools[name]
        # Clean up index
        keys_to_delete: list[str] = []
        for term, entries in self._index.items():
            self._index[term] = [e for e in entries if e[0] != name]
            if not self._index[term]:
                keys_to_delete.append(term)
        for k in keys_to_delete:
            del self._index[k]
        return True

    def clear(self) -> None:
        """Clear the search index."""
        self._tools.clear()
        self._index.clear()

    # ------------------------------------------------------------------
    # Search methods
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        max_results: int = 10,
        min_score: float = 0.1,
    ) -> list[ToolSearchResult]:
        """Search for tools by keyword.

        Matches against tool name, description, tags, capabilities, and
        parameter names.

        Args:
            query: Free-text search query.
            max_results: Maximum results to return.
            min_score: Minimum relevance score threshold.

        Returns:
            Ranked list of ``ToolSearchResult``.
        """
        if not query.strip():
            return []

        tokens = self._tokenize(query)
        scores: dict[str, float] = defaultdict(float)
        match_details: dict[str, tuple[str, str]] = {}

        for token in tokens:
            if token in self._index:
                for tool_name, field, value in self._index[token]:
                    weight = self._field_weight(field)
                    scores[tool_name] += weight
                    if tool_name not in match_details:
                        match_details[tool_name] = (field, value)

        # Filter and sort
        results = [
            ToolSearchResult(
                tool_name=name,
                score=score,
                matched_field=match_details.get(name, ("", ""))[0],
                matched_text=match_details.get(name, ("", ""))[1],
            )
            for name, score in scores.items()
            if score >= min_score
        ]
        results.sort(key=lambda r: r.score, reverse=True)

        return results[:max_results]

    def find_by_name(self, name: str) -> ToolDef | None:
        """Find a tool by exact name.

        Args:
            name: Exact tool name.

        Returns:
            The ``ToolDef`` or ``None``.
        """
        return self._tools.get(name)

    def find_by_capability(self, capability: str) -> list[ToolDef]:
        """Find all tools that have a specific capability.

        Args:
            capability: Capability identifier (``"file"``, ``"shell"``,
                ``"network"``, etc.).

        Returns:
            List of matching ToolDef instances.
        """
        return [
            tool
            for tool in self._tools.values()
            if capability in tool.capabilities
        ]

    def find_by_tag(self, tag: str) -> list[ToolDef]:
        """Find all tools with a specific tag.

        Tags are matched against tool capabilities and categories.

        Args:
            tag: Tag to search for.

        Returns:
            List of matching ToolDef instances.
        """
        tag_lower = tag.lower()
        return [
            tool for tool in self._tools.values()
            if any(c.lower() == tag_lower for c in tool.capabilities)
        ]

    def find_by_parameter(self, param_name: str) -> list[str]:
        """Find tools that accept a specific parameter.

        Args:
            param_name: Parameter name to search for.

        Returns:
            List of matching tool names.
        """
        matching: list[str] = []
        for name, tool in self._tools.items():
            if tool.parameters and "properties" in tool.parameters:
                if param_name in tool.parameters["properties"]:
                    matching.append(name)
        return matching

    def list_all_tools(self) -> list[ToolDef]:
        """Return all indexed tools."""
        return list(self._tools.values())

    @property
    def count(self) -> int:
        """Number of indexed tools."""
        return len(self._tools)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _index_tool_fields(self, tool: ToolDef) -> None:
        """Tokenize and index all searchable fields of a tool."""
        # Name
        for token in self._tokenize(tool.name):
            self._index[token].append((tool.name, "name", tool.name))

        # Description
        for token in self._tokenize(tool.description):
            self._index[token].append((tool.name, "description", token))

        # Capabilities (treated as tags for search purposes)
        for cap in tool.capabilities:
            cap_lower = cap.lower()
            self._index[cap_lower].append((tool.name, "capability", cap))
            for token in self._tokenize(cap):
                self._index[token].append((tool.name, "capability", cap))

        # Parameter names
        if tool.parameters and "properties" in tool.parameters:
            for param_name in tool.parameters["properties"]:
                for token in self._tokenize(param_name):
                    self._index[token].append((tool.name, "parameter", param_name))

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Tokenize text into lowercase search tokens."""
        text = text.lower()
        # Split on non-alphanumeric
        tokens = re.findall(r"[a-z0-9_]+", text)
        result: set[str] = set()
        for token in tokens:
            result.add(token)
            # Add single-character tokens only if alphanumeric
            if len(token) > 1:
                result.add(token)
        return result

    @staticmethod
    def _field_weight(field: str) -> float:
        """Return the relevance weight for a matched field."""
        weights = {
            "name": 10.0,
            "tag": 5.0,
            "capability": 4.0,
            "parameter": 2.0,
            "description": 1.0,
        }
        return weights.get(field, 1.0)


# ---------------------------------------------------------------------------
# ToolIndex
# ---------------------------------------------------------------------------


class ToolIndex:
    """Searchable index of available tools.

    Maintains an inverted index of tool attributes with support for
    filtering by provider, category, and capability.  Designed for
    use with ``ProviderNormalizer`` to provide cross-provider tool
    discovery.

    Usage::

        index = ToolIndex()
        index.add_tool(
            tool_def,
            provider="anthropic",
            category="file_operations",
        )

        results = index.query("read", provider="anthropic")
        print([r.tool_name for r in results])

        capability_results = index.find_by_capability("shell")
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDef] = {}
        self._search = ToolSearch()
        self._provider_map: dict[str, set[str]] = defaultdict(set)
        # ^ provider -> set of tool names
        self._category_map: dict[str, set[str]] = defaultdict(set)
        # ^ category -> set of tool names

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def add_tool(
        self,
        tool: ToolDef,
        provider: str = "",
        category: str = "",
    ) -> None:
        """Add a tool to the index.

        Args:
            tool: Tool definition to index.
            provider: Optional provider name (e.g. ``"anthropic"``).
            category: Optional category (e.g. ``"file_operations"``).
        """
        self._tools[tool.name] = tool
        self._search.index_tool(tool)

        if provider:
            self._provider_map[provider].add(tool.name)
        if category:
            self._category_map[category].add(tool.name)

    def add_tools(
        self,
        tools: list[tuple[ToolDef, str, str]],
    ) -> None:
        """Add multiple tools with their provider and category metadata.

        Args:
            tools: List of ``(tool_def, provider, category)`` tuples.
        """
        for tool, provider, category in tools:
            self.add_tool(tool, provider, category)

    def remove_tool(self, name: str) -> bool:
        """Remove a tool from the index.

        Args:
            name: Tool name to remove.

        Returns:
            True if the tool was found and removed.
        """
        if name not in self._tools:
            return False
        del self._tools[name]
        self._search.remove_tool(name)

        # Clean up provider/category maps
        for provider_map in [self._provider_map, self._category_map]:
            keys_to_delete: list[str] = []
            for key, names in provider_map.items():
                names.discard(name)
                if not names:
                    keys_to_delete.append(key)
            for k in keys_to_delete:
                del provider_map[k]

        return True

    def clear(self) -> None:
        """Clear the entire index."""
        self._tools.clear()
        self._search.clear()
        self._provider_map.clear()
        self._category_map.clear()

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query(
        self,
        query: str,
        provider: str | None = None,
        category: str | None = None,
        capability: str | None = None,
        max_results: int = 20,
    ) -> list[ToolSearchResult]:
        """Search for tools with optional filters.

        Args:
            query: Free-text search query.
            provider: Optional provider filter.
            category: Optional category filter.
            capability: Optional capability filter.
            max_results: Maximum results.

        Returns:
            Ranked list of matching tools.
        """
        results = self._search.search(query, max_results=1000)

        if not results:
            return []

        if provider:
            matching_names = self._provider_map.get(provider, set())
            results = [r for r in results if r.tool_name in matching_names]

        if category:
            matching_names = self._category_map.get(category, set())
            results = [r for r in results if r.tool_name in matching_names]

        if capability:
            matching = self._search.find_by_capability(capability)
            matching_names = {t.name for t in matching}
            results = [r for r in results if r.tool_name in matching_names]

        return results[:max_results]

    def get_tool(self, name: str) -> ToolDef | None:
        """Get a tool by exact name.

        Args:
            name: Tool name.

        Returns:
            The ``ToolDef`` or ``None``.
        """
        return self._tools.get(name)

    def list_providers(self) -> list[str]:
        """List all providers that have tools in the index."""
        return list(self._provider_map.keys())

    def list_categories(self) -> list[str]:
        """List all categories in the index."""
        return list(self._category_map.keys())

    def list_tools_by_provider(self, provider: str) -> list[ToolDef]:
        """List all tools for a given provider.

        Args:
            provider: Provider name.

        Returns:
            List of ToolDef instances.
        """
        names = self._provider_map.get(provider, set())
        return [self._tools[n] for n in names if n in self._tools]

    def list_tools_by_category(self, category: str) -> list[ToolDef]:
        """List all tools in a given category.

        Args:
            category: Category name.

        Returns:
            List of ToolDef instances.
        """
        names = self._category_map.get(category, set())
        return [self._tools[n] for n in names if n in self._tools]

    @property
    def count(self) -> int:
        """Number of tools in the index."""
        return len(self._tools)
