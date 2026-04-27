"""Red tests for MCP consumer adapter."""
from __future__ import annotations

import pytest

from lyra_mcp.client.adapter import (
    MCPAdapter,
    MCPProtocolError,
    MCPTimeoutError,
)
from lyra_mcp.testing import FakeMCPServer


def test_list_tools_rpc() -> None:
    server = FakeMCPServer(
        tools=[
            {"name": "fs.read", "description": "read a file"},
            {"name": "fs.write", "description": "write a file"},
        ]
    )
    adapter = MCPAdapter(transport=server)
    tools = adapter.list_tools()
    assert {t["name"] for t in tools} == {"fs.read", "fs.write"}


def test_call_tool_rpc() -> None:
    server = FakeMCPServer(
        tools=[{"name": "echo", "description": "echo"}],
        handler=lambda name, args: {"ok": True, "content": args.get("message", "")},
    )
    adapter = MCPAdapter(transport=server)
    result = adapter.call_tool("echo", {"message": "hi"})
    assert result["content"] == "hi"


def test_timeout_raised() -> None:
    server = FakeMCPServer(
        tools=[{"name": "slow", "description": "slow"}],
        handler=lambda n, a: {"ok": True},
        simulated_latency_ms=500,
    )
    adapter = MCPAdapter(transport=server, timeout_ms=100)
    with pytest.raises(MCPTimeoutError):
        adapter.call_tool("slow", {})


def test_malformed_response_raises() -> None:
    server = FakeMCPServer(
        tools=[{"name": "broken", "description": "broken"}],
        handler=lambda n, a: {"this is": "not the expected shape"},
        force_malformed=True,
    )
    adapter = MCPAdapter(transport=server)
    with pytest.raises(MCPProtocolError):
        adapter.call_tool("broken", {})
