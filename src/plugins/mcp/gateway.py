"""
MCP Gateway — connect to MCP servers, discover tools, translate schemas.

Uses ``lyra_mcp.client.stdio.StdioMCPTransport`` for real server connections
and ``lyra_mcp.testing.FakeMCPServer`` for tests. Exposes discovered tools as
Lyra ``ToolDef`` instances suitable for registration in ``ToolRegistry``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from src.tools.registry import ToolDef

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MCPServerInfo:
    """Metadata about a connected MCP server."""

    name: str
    command: str
    tool_count: int
    status: str = "connected"


@dataclass(frozen=True)
class MCPToolSchema:
    """A tool advertised by an MCP server, in Lyra-neutral form."""

    server: str
    original_name: str
    description: str
    input_schema: Dict[str, Any]
    raw: Dict[str, Any]

    @property
    def lyra_name(self) -> str:
        """Fully-qualified Lyra tool name, e.g. ``mcp__filesystem__read``."""
        return f"mcp__{self.server}__{self.original_name}"


# ---------------------------------------------------------------------------
# Gateway
# ---------------------------------------------------------------------------


class MCPGateway:
    """Manages connections to MCP servers and translates their tools.

    Accepts any transport object with ``list_tools()`` and ``call_tool()``
    methods. Real deployments wire ``StdioMCPTransport.start(...)`` via
    :meth:`connect`; the test suite injects a ``FakeMCPServer`` via
    :meth:`connect_transport`.

    Typical usage::

        gateway = MCPGateway()
        info = await gateway.connect(
            "filesystem",
            command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        )
        schemas = await gateway.discover_tools("filesystem")
        tooldefs = [gateway.to_tool_def(s) for s in schemas]
        result = await gateway.call_tool("filesystem", "read", {"path": "/tmp/x"})
        await gateway.disconnect("filesystem")
        await gateway.close()
    """

    def __init__(self) -> None:
        self._servers: Dict[str, MCPServerInfo] = {}
        self._transports: Dict[str, Any] = {}
        self._discovered_tools: Dict[str, List[MCPToolSchema]] = {}
        self._closed: bool = False

    # ---- connection lifecycle -----------------------------------------------

    async def connect(
        self,
        server_name: str,
        *,
        command: Sequence[str],
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        init_timeout: float = 10.0,
    ) -> MCPServerInfo:
        """Spawn an MCP server subprocess and complete the JSON-RPC handshake.

        Args:
            server_name: A unique identifier for this server connection.
            command: Full argv (e.g. ``["npx", "-y",
                "@modelcontextprotocol/server-filesystem", "/tmp"]``).
            env: Extra environment variables merged onto the parent env.
            cwd: Working directory for the subprocess.
            init_timeout: Max seconds to wait for the ``initialize`` response.

        Returns:
            MCPServerInfo describing the connected server.

        Raises:
            RuntimeError: If the gateway is already closed or the server
                name is already registered.
            ConnectionError: If the handshake fails.
        """
        if self._closed:
            raise RuntimeError("MCPGateway is closed")
        if server_name in self._servers:
            raise RuntimeError(
                f"MCP server {server_name!r} is already connected"
            )

        try:
            from lyra_mcp.client.stdio import StdioMCPTransport as Transport
        except ImportError as exc:
            raise RuntimeError(
                "lyra_mcp package is required for connect()"
            ) from exc

        try:
            transport = Transport.start(
                command=list(command),
                env=env,
                cwd=cwd,
                server_name=server_name,
                init_timeout_s=init_timeout,
            )
        except Exception as exc:
            raise ConnectionError(
                f"Failed to connect to MCP server {server_name!r}: {exc}"
            ) from exc

        return self._register(server_name, transport, command[0])

    def connect_transport(
        self,
        server_name: str,
        transport: Any,
    ) -> MCPServerInfo:
        """Register a pre-built transport (used for testing with ``FakeMCPServer``).

        The transport must expose ``list_tools()`` and ``call_tool()``.

        Raises:
            RuntimeError: If the gateway is already closed.
        """
        if self._closed:
            raise RuntimeError("MCPGateway is closed")
        self._servers.pop(server_name, None)
        self._transports.pop(server_name, None)
        self._discovered_tools.pop(server_name, None)
        return self._register(server_name, transport, "test-transport")

    def _register(
        self,
        server_name: str,
        transport: Any,
        command_label: str,
    ) -> MCPServerInfo:
        """Common registration logic after a transport is ready."""
        # Synchronous list_tools call (the transport is already connected)
        try:
            raw_tools = transport.list_tools()
        except Exception as exc:
            raise ConnectionError(
                f"Failed to list tools from {server_name!r}: {exc}"
            ) from exc

        tools_list = raw_tools if isinstance(raw_tools, list) else []
        normalized = _normalise_mcp_tools(server_name, tools_list)
        self._discovered_tools[server_name] = normalized

        info = MCPServerInfo(
            name=server_name,
            command=command_label,
            tool_count=len(normalized),
            status="connected",
        )
        self._servers[server_name] = info
        self._transports[server_name] = transport

        logger.info(
            "MCP server %r connected (%d tools)",
            server_name,
            len(normalized),
        )
        return info

    async def disconnect(self, server_name: str) -> None:
        """Disconnect a single MCP server and close its transport."""
        if server_name not in self._servers:
            logger.warning("MCP server %r is not connected", server_name)
            return
        transport = self._transports.pop(server_name, None)
        if transport is not None and hasattr(transport, "close"):
            transport.close()
        self._servers.pop(server_name, None)
        self._discovered_tools.pop(server_name, None)
        logger.info("MCP server %r disconnected", server_name)

    async def close(self) -> None:
        """Disconnect all MCP servers and mark the gateway as closed."""
        for name in list(self._servers):
            await self.disconnect(name)
        self._closed = True

    async def __aenter__(self) -> "MCPGateway":
        return self

    async def __aexit__(
        self,
        _exc_type: Any,
        _exc_val: Any,
        _exc_tb: Any,
    ) -> None:
        await self.close()

    # ---- tool discovery ----------------------------------------------------

    async def discover_tools(
        self, server_name: str
    ) -> List[MCPToolSchema]:
        """Return the tools advertised by a connected server.

        Raises:
            KeyError: When *server_name* is not connected.
        """
        if server_name not in self._servers:
            raise KeyError(f"MCP server {server_name!r} is not connected")
        return list(self._discovered_tools.get(server_name, []))

    def discover_all_tools(self) -> Dict[str, List[MCPToolSchema]]:
        """Return all discovered tools, keyed by server name."""
        return {
            name: list(schemas)
            for name, schemas in self._discovered_tools.items()
        }

    # ---- schema translation ------------------------------------------------

    def to_tool_def(self, schema: MCPToolSchema) -> ToolDef:
        """Translate an ``MCPToolSchema`` into a Lyra ``ToolDef``.

        The resulting ``ToolDef`` has *no handler* -- the caller must wire
        a handler that delegates to the corresponding MCP transport when
        the tool is invoked.
        """
        return ToolDef(
            name=schema.lyra_name,
            description=schema.description,
            parameters=schema.input_schema,
            capabilities=["mcp", f"mcp:{schema.server}"],
            sandbox_requirements={
                "allowed_domains": [],
                "timeout_seconds": 30,
            },
        )

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
        *,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Invoke a tool on a connected MCP server.

        Args:
            server_name: The connected server identifier.
            tool_name: The original tool name (not the prefixed Lyra name).
            arguments: Tool arguments.
            timeout: Timeout in seconds.

        Returns:
            The raw result dict from the MCP server.

        Raises:
            KeyError: When the server is not connected.
            RuntimeError: When the call fails.
        """
        if server_name not in self._servers:
            raise KeyError(f"MCP server {server_name!r} is not connected")
        transport = self._transports.get(server_name)
        if transport is None:
            raise RuntimeError(
                f"No transport found for server {server_name!r}"
            )

        try:
            result = transport.call_tool(tool_name, arguments)
        except Exception as exc:
            raise RuntimeError(
                f"MCP call to {server_name}.{tool_name} failed: {exc}"
            ) from exc

        if not isinstance(result, dict):
            return {"ok": True, "content": str(result)}
        return result

    # ---- query -------------------------------------------------------------

    def list_servers(self) -> List[MCPServerInfo]:
        """Return metadata for all connected servers."""
        return list(self._servers.values())

    def get_server(self, name: str) -> Optional[MCPServerInfo]:
        """Get server info by name."""
        return self._servers.get(name)

    def is_connected(self, name: str) -> bool:
        """Check whether a server is currently connected."""
        return name in self._servers


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalise_mcp_tools(
    server_name: str,
    tools: List[Dict[str, Any]],
) -> List[MCPToolSchema]:
    """Convert raw MCP tool records (from ``tools/list``) into schemas.

    Each MCP tool record has at minimum ``name`` and optionally
    ``description``, ``inputSchema`` / ``input_schema``.
    """
    result: List[MCPToolSchema] = []
    for t in tools:
        if not isinstance(t, dict):
            continue
        name = t.get("name", "")
        if not isinstance(name, str) or not name:
            continue
        description = (t.get("description") or "").strip()
        raw_schema = t.get("inputSchema") or t.get("input_schema")
        if not isinstance(raw_schema, dict):
            raw_schema = {"type": "object", "properties": {}}
        result.append(
            MCPToolSchema(
                server=server_name,
                original_name=name,
                description=description,
                input_schema=raw_schema,
                raw=dict(t),
            )
        )
    return result


__all__ = [
    "MCPGateway",
    "MCPServerInfo",
    "MCPToolSchema",
]
