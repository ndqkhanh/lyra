"""Basic MCP (Model Context Protocol) integration."""

from dataclasses import dataclass
from typing import Any


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""

    name: str
    command: str
    args: list[str]
    env: dict[str, str] | None = None
    enabled: bool = True


class MCPClient:
    """Lightweight MCP client for server integration."""

    def __init__(self):
        self.servers: dict[str, MCPServerConfig] = {}
        self.connected: dict[str, bool] = {}

    def register_server(self, config: MCPServerConfig) -> None:
        """Register an MCP server."""
        self.servers[config.name] = config
        self.connected[config.name] = False

    async def connect(self, server_name: str) -> bool:
        """Connect to an MCP server."""
        if server_name not in self.servers:
            return False

        # Simulate connection
        self.connected[server_name] = True
        return True

    async def call_tool(
        self, server: str, tool: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Call a tool on an MCP server."""
        if server not in self.connected or not self.connected[server]:
            raise ConnectionError(f"Server {server} not connected")

        # Simulate tool call
        return {
            "server": server,
            "tool": tool,
            "arguments": arguments,
            "result": f"Executed {tool} on {server}",
        }

    def list_servers(self) -> list[MCPServerConfig]:
        """List all registered servers."""
        return list(self.servers.values())

    def is_connected(self, server_name: str) -> bool:
        """Check if server is connected."""
        return self.connected.get(server_name, False)


class MCPServers:
    """Pre-configured MCP servers."""

    @staticmethod
    def github() -> MCPServerConfig:
        """GitHub MCP server configuration."""
        return MCPServerConfig(
            name="github",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_TOKEN": "${GITHUB_TOKEN}"},
        )

    @staticmethod
    def memory() -> MCPServerConfig:
        """Memory (claude-mem) MCP server configuration."""
        return MCPServerConfig(
            name="memory",
            command="npx",
            args=["-y", "@anthropic-ai/mcp-server-memory"],
        )

    @staticmethod
    def exa() -> MCPServerConfig:
        """Exa search MCP server configuration."""
        return MCPServerConfig(
            name="exa",
            command="npx",
            args=["-y", "@exa/mcp-server"],
            env={"EXA_API_KEY": "${EXA_API_KEY}"},
        )

    @staticmethod
    def get_all() -> list[MCPServerConfig]:
        """Get all pre-configured servers."""
        return [
            MCPServers.github(),
            MCPServers.memory(),
            MCPServers.exa(),
        ]
