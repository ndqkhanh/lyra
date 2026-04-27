"""Red tests for progressive disclosure of MCP tools via an umbrella tool."""
from __future__ import annotations

from lyra_mcp.client.progressive import ProgressiveMCP
from lyra_mcp.testing import FakeMCPServer


def test_cold_discovery_via_umbrella_tool() -> None:
    server = FakeMCPServer(
        tools=[
            {"name": "filesystem.read", "description": "read a file from FS"},
            {"name": "filesystem.write", "description": "write to the FS"},
            {"name": "jira.get_issue", "description": "fetch a Jira issue"},
        ]
    )
    mcp = ProgressiveMCP(adapter=server)
    # Initially no tools surfaced
    assert mcp.surfaced_tool_names() == []
    # User query routed via umbrella tool
    response = mcp.umbrella_call("find the jira issue named OC-42")
    assert "jira.get_issue" in response.candidate_tools
    assert "filesystem.read" not in response.candidate_tools


def test_filesystem_query_surfaces_fs_tools() -> None:
    server = FakeMCPServer(
        tools=[
            {"name": "filesystem.read", "description": "read a file from FS"},
            {"name": "jira.get_issue", "description": "fetch a Jira issue"},
        ]
    )
    mcp = ProgressiveMCP(adapter=server)
    resp = mcp.umbrella_call("read the README file")
    assert "filesystem.read" in resp.candidate_tools
