"""Tests for MCP integration."""

import pytest

from lyra_cli.mcp_integration import MCPClient, MCPServers


def test_register_server():
    """Servers can be registered."""
    client = MCPClient()
    config = MCPServers.github()

    client.register_server(config)

    assert "github" in client.servers
    assert client.servers["github"].name == "github"


@pytest.mark.anyio
async def test_connect_server():
    """Can connect to registered server."""
    client = MCPClient()
    client.register_server(MCPServers.github())

    result = await client.connect("github")

    assert result is True
    assert client.is_connected("github")


@pytest.mark.anyio
async def test_call_tool():
    """Can call tool on connected server."""
    client = MCPClient()
    client.register_server(MCPServers.github())
    await client.connect("github")

    result = await client.call_tool(
        "github", "search_code", {"query": "test"}
    )

    assert result["server"] == "github"
    assert result["tool"] == "search_code"


@pytest.mark.anyio
async def test_call_tool_not_connected():
    """Calling tool on disconnected server raises error."""
    client = MCPClient()
    client.register_server(MCPServers.github())

    with pytest.raises(ConnectionError):
        await client.call_tool("github", "search_code", {})


def test_list_servers():
    """Can list all registered servers."""
    client = MCPClient()
    client.register_server(MCPServers.github())
    client.register_server(MCPServers.memory())

    servers = client.list_servers()

    assert len(servers) == 2


def test_preconfigured_servers():
    """All preconfigured servers are available."""
    servers = MCPServers.get_all()

    assert len(servers) == 3
    assert any(s.name == "github" for s in servers)
    assert any(s.name == "memory" for s in servers)
    assert any(s.name == "exa" for s in servers)
