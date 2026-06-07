"""
Tests for ProviderNormalizer, ToolSearch, ToolIndex.

Covers:
- ProviderNormalizer format detection (Anthropic, OpenAI, DeepSeek, Lyra)
- Conversion between provider formats
- Batch normalization and conversion
- ToolSearch keyword search, capability filtering, tag filtering
- ToolIndex cross-provider tool discovery
"""

from __future__ import annotations

import pytest

from lyra.tools.provider_normalizer import (
    ProviderNormalizer,
    ProviderToolDef,
    ProviderType,
    ToolFormat,
    ToolFormatError,
)
from lyra.tools.registry import ToolDef
from lyra.tools.tool_search import ToolIndex, ToolSearch, ToolSearchResult


# ======================================================================
# Sample tool definitions
# ======================================================================

ANTHROPIC_TOOL = {
    "name": "read_file",
    "description": "Read a file from disk",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path"},
        },
        "required": ["path"],
    },
}

OPENAI_TOOL = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read a file from disk",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
            },
            "required": ["path"],
        },
        "strict": True,
    },
}

LYRA_TOOL_DEF = ToolDef(
    name="list_dir",
    description="List directory contents",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string"},
        },
    },
    capabilities=["file"],
)

# ======================================================================
# ProviderNormalizer - format detection
# ======================================================================


class TestProviderNormalizerDetection:
    """ProviderNormalizer.detect_format() and detect_and_normalize()."""

    def test_detect_anthropic(self) -> None:
        """Anthropic format has 'name' and 'input_schema'."""
        normalizer = ProviderNormalizer()
        fmt = normalizer.detect_format(ANTHROPIC_TOOL)
        assert fmt == ToolFormat.ANTHROPIC

    def test_detect_openai(self) -> None:
        """OpenAI format has 'type': 'function' and 'function' key."""
        normalizer = ProviderNormalizer()
        fmt = normalizer.detect_format(OPENAI_TOOL)
        assert fmt == ToolFormat.OPENAI

    def test_detect_unknown_format(self) -> None:
        """Unknown format raises ToolFormatError."""
        normalizer = ProviderNormalizer()
        with pytest.raises(ToolFormatError):
            normalizer.detect_format({"unknown": "structure"})

    def test_normalize_anthropic(self) -> None:
        """detect_and_normalize extracts fields from Anthropic format."""
        normalizer = ProviderNormalizer()
        tool = normalizer.detect_and_normalize(ANTHROPIC_TOOL)
        assert tool.name == "read_file"
        assert tool.description == "Read a file from disk"
        assert "path" in tool.parameters.get("properties", {})
        assert tool.provider == ProviderType.ANTHROPIC

    def test_normalize_openai(self) -> None:
        """detect_and_normalize extracts fields from OpenAI format."""
        normalizer = ProviderNormalizer()
        tool = normalizer.detect_and_normalize(OPENAI_TOOL)
        assert tool.name == "read_file"
        assert tool.provider == ProviderType.OPENAI

    def test_normalize_batch(self) -> None:
        """normalize_batch handles mixed formats."""
        normalizer = ProviderNormalizer()
        tools = normalizer.normalize_batch([ANTHROPIC_TOOL, OPENAI_TOOL])
        assert len(tools) == 2
        assert tools[0].provider == ProviderType.ANTHROPIC
        assert tools[1].provider == ProviderType.OPENAI


# ======================================================================
# ProviderNormalizer - conversion
# ======================================================================


class TestProviderNormalizerConversion:
    """ProviderNormalizer.to_provider() — cross-format conversion."""

    def setup_method(self) -> None:
        self.normalizer = ProviderNormalizer()
        self.tool = ProviderToolDef(
            name="search",
            description="Search the web",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
            provider=ProviderType.ANTHROPIC,
        )

    def test_to_anthropic(self) -> None:
        """Convert to Anthropic format."""
        result = self.normalizer.to_anthropic(self.tool)
        assert result["name"] == "search"
        assert "input_schema" in result
        assert result["input_schema"]["required"] == ["query"]

    def test_to_openai(self) -> None:
        """Convert to OpenAI format."""
        result = self.normalizer.to_openai(self.tool)
        assert result["type"] == "function"
        assert result["function"]["name"] == "search"
        assert result["function"]["strict"] is True

    def test_to_deepseek(self) -> None:
        """Convert to DeepSeek format (same as OpenAI)."""
        result = self.normalizer.to_deepseek(self.tool)
        assert result["type"] == "function"
        assert result["function"]["name"] == "search"

    def test_to_google(self) -> None:
        """Convert to Google AI format."""
        result = self.normalizer.to_google(self.tool)
        assert result["name"] == "search"
        assert "parameters" in result

    def test_convert_batch(self) -> None:
        """convert_batch converts multiple tools."""
        tools = [
            self.tool,
            ProviderToolDef(
                name="read",
                description="Read",
                parameters={},
                provider=ProviderType.ANTHROPIC,
            ),
        ]
        results = self.normalizer.convert_batch(tools, ProviderType.OPENAI)
        assert len(results) == 2
        assert results[0]["function"]["name"] == "search"
        assert results[1]["function"]["name"] == "read"

    def test_unsupported_provider(self) -> None:
        """All valid provider types are supported."""
        for provider in ProviderType:
            result = self.normalizer.to_provider(self.tool, provider)
            assert isinstance(result, dict)

    def test_same_provider_returns_raw(self) -> None:
        """When source and target match, raw is returned."""
        tool_with_raw = ProviderToolDef(
            name="x",
            description="x",
            parameters={},
            provider=ProviderType.ANTHROPIC,
            raw={"original": True},
        )
        result = self.normalizer.to_provider(tool_with_raw, ProviderType.ANTHROPIC)
        assert result["original"] is True


# ======================================================================
# ProviderNormalizer — edge cases
# ======================================================================


class TestProviderNormalizerEdgeCases:
    """Edge cases and parameter normalization."""

    def test_detect_and_normalize_lyra_tool_def(self) -> None:
        """A ToolDef-dict without provider key is detected as LYRA."""
        normalizer = ProviderNormalizer()
        raw = {"name": "test", "description": "desc", "parameters": {}, "handler": "fn"}
        tool = normalizer.detect_and_normalize(raw)
        assert tool.name == "test"
        assert tool.provider == ProviderType.ANTHROPIC  # canonical

    def test_normalize_non_dict_parameters(self) -> None:
        """Parameters that are not structured are wrapped."""
        normalizer = ProviderNormalizer()
        raw = {"name": "t", "description": "d", "parameters": {"p": {"type": "string"}}}
        tool = normalizer.detect_and_normalize(raw)
        assert "properties" in tool.parameters

    def test_empty_description(self) -> None:
        """Tool with empty description is handled."""
        normalizer = ProviderNormalizer()
        raw = {"name": "t", "description": "", "input_schema": {}}
        tool = normalizer.detect_and_normalize(raw)
        assert tool.description == ""


# ======================================================================
# ToolSearch
# ======================================================================


class TestToolSearch:
    """ToolSearch — dynamic tool discovery."""

    def test_index_and_search_by_name(self) -> None:
        """search finds tools by name keyword."""
        search = ToolSearch()
        search.index_tool(LYRA_TOOL_DEF)
        results = search.search("list_dir")
        assert len(results) >= 1
        assert results[0].tool_name == "list_dir"

    def test_search_by_description(self) -> None:
        """search finds tools by description keyword."""
        search = ToolSearch()
        search.index_tool(LYRA_TOOL_DEF)
        results = search.search("directory")
        assert len(results) >= 1

    def test_search_empty_query(self) -> None:
        """Empty query returns empty results."""
        search = ToolSearch()
        search.index_tool(LYRA_TOOL_DEF)
        assert search.search("") == []

    def test_find_by_name_exact(self) -> None:
        """find_by_name returns None for unknown tool."""
        search = ToolSearch()
        search.index_tool(LYRA_TOOL_DEF)
        tool = search.find_by_name("list_dir")
        assert tool is not None
        assert tool.name == "list_dir"
        assert search.find_by_name("nonexistent") is None

    def test_find_by_capability(self) -> None:
        """find_by_capability returns tools with matching capability."""
        search = ToolSearch()
        search.index_tool(LYRA_TOOL_DEF)
        tools = search.find_by_capability("file")
        assert len(tools) == 1
        assert tools[0].name == "list_dir"

    def test_find_by_capability_no_match(self) -> None:
        """find_by_capability returns empty list for no match."""
        search = ToolSearch()
        search.index_tool(LYRA_TOOL_DEF)
        assert search.find_by_capability("network") == []

    def test_find_by_tag(self) -> None:
        """find_by_tag returns tools with matching capability (as tag)."""
        search = ToolSearch()
        search.index_tool(LYRA_TOOL_DEF)
        tools = search.find_by_tag("file")
        assert len(tools) == 1

    def test_find_by_tag_no_match(self) -> None:
        """find_by_tag returns empty list when tag not found."""
        search = ToolSearch()
        search.index_tool(LYRA_TOOL_DEF)
        assert search.find_by_tag("database") == []

    def test_find_by_parameter(self) -> None:
        """find_by_parameter returns tools that accept a parameter."""
        search = ToolSearch()
        search.index_tool(LYRA_TOOL_DEF)
        tools = search.find_by_parameter("path")
        assert len(tools) == 1
        assert "list_dir" in tools

    def test_remove_tool(self) -> None:
        """remove_tool removes from index."""
        search = ToolSearch()
        search.index_tool(LYRA_TOOL_DEF)
        assert search.count == 1
        assert search.remove_tool("list_dir")
        assert search.count == 0

    def test_remove_unknown_tool(self) -> None:
        """remove_tool on unknown returns False."""
        search = ToolSearch()
        assert not search.remove_tool("nonexistent")

    def test_clear(self) -> None:
        """clear empties the index."""
        search = ToolSearch()
        search.index_tool(LYRA_TOOL_DEF)
        search.clear()
        assert search.count == 0

    def test_list_all_tools(self) -> None:
        """list_all_tools returns all indexed tools."""
        search = ToolSearch()
        search.index_tool(LYRA_TOOL_DEF)
        tools = search.list_all_tools()
        assert len(tools) == 1

    def test_index_multiple_tools(self) -> None:
        """index_tools adds multiple tools."""
        search = ToolSearch()
        tool2 = ToolDef(
            name="write_file",
            description="Write to file",
            capabilities=["file"],
        )
        search.index_tools([LYRA_TOOL_DEF, tool2])
        assert search.count == 2

    def test_search_relevance_ranking(self) -> None:
        """Name matches rank higher than description matches."""
        search = ToolSearch()
        search.index_tool(LYRA_TOOL_DEF)
        results = search.search("list_dir")
        assert results[0].matched_field == "name"


# ======================================================================
# ToolIndex
# ======================================================================


class TestToolIndex:
    """ToolIndex — searchable cross-provider index."""

    def test_add_and_get_tool(self) -> None:
        """add_tool makes a tool discoverable by get_tool."""
        index = ToolIndex()
        index.add_tool(LYRA_TOOL_DEF, provider="lyra", category="filesystem")
        tool = index.get_tool("list_dir")
        assert tool is not None
        assert tool.name == "list_dir"

    def test_query(self) -> None:
        """query returns ranked results for a keyword."""
        index = ToolIndex()
        index.add_tool(LYRA_TOOL_DEF, provider="lyra", category="filesystem")
        results = index.query("list_dir")
        assert len(results) >= 1
        assert results[0].tool_name == "list_dir"

    def test_query_with_provider_filter(self) -> None:
        """query filters by provider."""
        index = ToolIndex()
        index.add_tool(LYRA_TOOL_DEF, provider="anthropic", category="filesystem")
        results = index.query("list_dir", provider="anthropic")
        assert len(results) >= 1
        results = index.query("list_dir", provider="openai")
        assert len(results) == 0

    def test_query_with_category_filter(self) -> None:
        """query filters by category."""
        index = ToolIndex()
        index.add_tool(LYRA_TOOL_DEF, provider="lyra", category="filesystem")
        results = index.query("list_dir", category="filesystem")
        assert len(results) >= 1
        results = index.query("list_dir", category="network")
        assert len(results) == 0

    def test_query_with_capability_filter(self) -> None:
        """query filters by capability."""
        index = ToolIndex()
        index.add_tool(LYRA_TOOL_DEF, provider="lyra", category="filesystem")
        results = index.query("list_dir", capability="file")
        assert len(results) >= 1
        results = index.query("list_dir", capability="network")
        assert len(results) == 0

    def test_query_empty(self) -> None:
        """query returns empty list when no match."""
        index = ToolIndex()
        assert index.query("nonexistent") == []

    def test_remove_tool(self) -> None:
        """remove_tool removes from provider and category maps."""
        index = ToolIndex()
        index.add_tool(LYRA_TOOL_DEF, provider="lyra", category="fs")
        index.remove_tool("list_dir")
        assert index.get_tool("list_dir") is None
        assert "lyra" not in index.list_providers() or index.list_tools_by_provider("lyra") == []

    def test_clear(self) -> None:
        """clear empties the entire index."""
        index = ToolIndex()
        index.add_tool(LYRA_TOOL_DEF, provider="lyra", category="fs")
        index.clear()
        assert index.count == 0

    def test_list_providers(self) -> None:
        """list_providers returns unique provider names."""
        index = ToolIndex()
        index.add_tool(LYRA_TOOL_DEF, provider="anthropic", category="fs")
        index.add_tool(
            ToolDef(name="web_search", description="Search"),
            provider="openai",
            category="network",
        )
        providers = index.list_providers()
        assert sorted(providers) == ["anthropic", "openai"]

    def test_list_categories(self) -> None:
        """list_categories returns unique category names."""
        index = ToolIndex()
        index.add_tool(LYRA_TOOL_DEF, provider="lyra", category="filesystem")
        index.add_tool(
            ToolDef(name="search", description="Search"),
            provider="lyra",
            category="network",
        )
        cats = index.list_categories()
        assert sorted(cats) == ["filesystem", "network"]

    def test_list_tools_by_provider(self) -> None:
        """list_tools_by_provider filters by provider."""
        index = ToolIndex()
        index.add_tool(LYRA_TOOL_DEF, provider="anthropic", category="fs")
        tools = index.list_tools_by_provider("anthropic")
        assert len(tools) == 1

    def test_list_tools_by_category(self) -> None:
        """list_tools_by_category filters by category."""
        index = ToolIndex()
        index.add_tool(LYRA_TOOL_DEF, provider="lyra", category="filesystem")
        tools = index.list_tools_by_category("filesystem")
        assert len(tools) == 1
