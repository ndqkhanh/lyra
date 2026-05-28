"""Tests for Meta MCP."""
from __future__ import annotations

from lyra_cli.mcp.meta_mcp import MetaMcp, ToolCategory


class TestMetaMcp:
    def test_initial_empty_registry(self):
        meta = MetaMcp()
        assert meta.server_count == 0
        assert meta.total_tools == 0
        assert meta.total_resources == 0

    def test_register_server(self):
        meta = MetaMcp()
        info = meta.register_server("srv-1", "Test Server", "1.0", "http://localhost")
        assert meta.server_count == 1
        assert info.name == "Test Server"

    def test_deregister_server(self):
        meta = MetaMcp()
        meta.register_server("srv-1", "Test", "1.0", "http://a")
        meta.deregister_server("srv-1")
        assert meta.server_count == 0

    def test_register_tool(self):
        meta = MetaMcp()
        meta.register_server("srv-1", "Test", "1.0", "http://a")
        tool = meta.register_tool("srv-1", "read_file", "Read a file", ToolCategory.FILE)
        assert tool is not None
        assert meta.total_tools == 1
        assert tool.name == "read_file"

    def test_register_tool_unknown_server(self):
        meta = MetaMcp()
        assert meta.register_tool("unknown", "tool", "desc") is None

    def test_find_tool(self):
        meta = MetaMcp()
        meta.register_server("srv-1", "S", "1", "x")
        meta.register_tool("srv-1", "search", "Search code")
        found = meta.find_tool("search")
        assert found is not None
        assert found.name == "search"

    def test_find_tool_not_found(self):
        meta = MetaMcp()
        assert meta.find_tool("nonexistent") is None

    def test_search_tools(self):
        meta = MetaMcp()
        meta.register_server("srv-1", "S", "1", "x")
        meta.register_tool("srv-1", "search_code", "Search source code")
        meta.register_tool("srv-1", "read_file", "Read a file")
        results = meta.search_tools("search")
        assert len(results) == 1
        assert results[0].name == "search_code"

    def test_search_tools_no_match(self):
        meta = MetaMcp()
        meta.register_server("srv-1", "S", "1", "x")
        meta.register_tool("srv-1", "read", "Read content")
        assert meta.search_tools("xyzzy_nonexistent") == []

    def test_list_tools_by_category(self):
        meta = MetaMcp()
        meta.register_server("srv-1", "S", "1", "x")
        meta.register_tool("srv-1", "read", "Read", ToolCategory.FILE)
        meta.register_tool("srv-1", "fetch", "Fetch", ToolCategory.NETWORK)
        assert len(meta.list_tools_by_category(ToolCategory.FILE)) == 1
        assert len(meta.list_tools_by_category(ToolCategory.NETWORK)) == 1

    def test_register_resource(self):
        meta = MetaMcp()
        meta.register_server("srv-1", "S", "1", "x")
        res = meta.register_resource("srv-1", "file:///doc", "Doc", "Documentation")
        assert res is not None
        assert meta.total_resources == 1

    def test_find_resource(self):
        meta = MetaMcp()
        meta.register_server("srv-1", "S", "1", "x")
        meta.register_resource("srv-1", "file:///doc", "Doc", "Documentation")
        found = meta.find_resource("file:///doc")
        assert found is not None
        assert found.name == "Doc"

    def test_get_meta_manifest(self):
        meta = MetaMcp()
        meta.register_server("srv-1", "Server1", "1.0", "http://a")
        meta.register_tool("srv-1", "tool_a", "Tool A", ToolCategory.FILE)
        manifest = meta.get_meta_manifest()
        assert manifest["total_tools"] == 1
        assert "tools_by_server" in manifest
        assert "categories" in manifest

    def test_prune_stale_servers(self):
        meta = MetaMcp()
        meta.register_server("srv-1", "S", "1", "x")
        meta._servers["srv-1"].last_seen = 0  # ancient
        pruned = meta.prune_stale_servers(max_age_sec=1)
        assert pruned == 1
        assert meta.server_count == 0

    def test_deregister_cleans_up_indices(self):
        meta = MetaMcp()
        meta.register_server("srv-1", "S", "1", "x")
        meta.register_tool("srv-1", "tool_x", "X")
        assert meta.total_tools == 1
        meta.deregister_server("srv-1")
        assert meta.total_tools == 0
