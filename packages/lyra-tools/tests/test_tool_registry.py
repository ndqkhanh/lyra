"""Tests for lyra-tools centralized tool registry."""

from __future__ import annotations

import pytest
from lyra_tools import (
    ToolCategory,
    ToolDisclosureLevel,
    ToolManifest,
    Toolset,
    tool_registry,
)


class TestToolManifest:
    def test_create_manifest(self):
        m = ToolManifest(
            name="test_tool",
            category=ToolCategory.CODE,
            description="A test tool",
        )
        assert m.name == "test_tool"
        assert m.category == ToolCategory.CODE
        assert not m.is_destructive

    def test_manifest_is_frozen(self):
        m = ToolManifest(
            name="test_tool",
            category=ToolCategory.CODE,
            description="A test tool",
        )
        with pytest.raises(Exception):
            m.name = "changed"


class TestToolset:
    def test_create_toolset(self):
        tools = (
            ToolManifest(name="a", category=ToolCategory.CODE, description="A"),
            ToolManifest(name="b", category=ToolCategory.CODE, description="B"),
        )
        ts = Toolset(name="Test", category=ToolCategory.CODE, description="Testing", tools=tools)
        assert ts.tool_count == 2
        assert ts.tool_names == ("a", "b")


class TestToolRegistry:
    def test_20_categories(self):
        assert len(tool_registry.list_categories()) >= 19

    def test_total_tools_exceeds_200(self):
        assert tool_registry.total_tools >= 200

    def test_get_tool_by_name(self):
        tool = tool_registry.get("file_read")
        assert tool is not None
        assert tool.name == "file_read"
        assert tool.category == ToolCategory.FILESYSTEM

    def test_get_nonexistent_tool(self):
        assert tool_registry.get("nonexistent_tool") is None

    def test_search_finds_tools(self):
        results = tool_registry.search("git")
        assert len(results) > 0
        assert all("git" in r.name.lower() or "git" in r.description.lower() for r in results)

    def test_search_finds_by_description(self):
        results = tool_registry.search("database")
        assert len(results) > 0

    def test_search_case_insensitive(self):
        results_lower = tool_registry.search("git")
        results_upper = tool_registry.search("GIT")
        assert len(results_lower) == len(results_upper)

    def test_list_tools_by_category(self):
        fs_tools = tool_registry.list_tools(ToolCategory.FILESYSTEM)
        assert len(fs_tools) >= 10

    def test_is_destructive(self):
        assert tool_registry.is_destructive("file_delete")
        assert not tool_registry.is_destructive("file_read")

    def test_list_destructive(self):
        destructive = tool_registry.list_destructive()
        assert len(destructive) > 0
        assert all(d.is_destructive for d in destructive)

    def test_get_toolset(self):
        ts = tool_registry.get_toolset(ToolCategory.CODE)
        assert ts is not None
        assert ts.category == ToolCategory.CODE

    def test_resolve_dependencies_simple(self):
        # File read has no dependencies
        deps = tool_registry.resolve_dependencies("file_read")
        assert len(deps) == 1
        assert deps[0].name == "file_read"

    def test_stats(self):
        stats = tool_registry.stats()
        assert stats["total_tools"] >= 200
        assert stats["total_toolsets"] >= 19
        assert isinstance(stats["tools_per_category"], dict)

    def test_empty_search(self):
        results = tool_registry.search("xyznonexistentpattern12345")
        assert len(results) == 0

    def test_disclosure_filter(self):
        tool = tool_registry.get_disclosure("file_read", ToolDisclosureLevel.L1)
        assert tool is not None

    def test_all_categories_have_tools(self):
        for cat in tool_registry.list_categories():
            tools = tool_registry.list_tools(cat)
            assert len(tools) > 0, f"Category {cat} has no tools"


class TestToolCategories:
    def test_all_plan9_categories_present(self):
        expected = {
            "filesystem", "code", "search", "shell", "git",
            "web_browser", "database", "document", "media", "network",
            "security", "agent", "memory", "skill", "observability",
            "automation", "communication", "mcp", "voice", "ui",
        }
        actual = {c.value for c in tool_registry.list_categories()}
        assert actual >= expected
