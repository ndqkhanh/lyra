"""MCP consumer: adapter, trust bridge, progressive-disclosure wrapper."""
from __future__ import annotations

from .adapter import MCPAdapter, MCPProtocolError, MCPTimeoutError
from .bridge import TrustBanner, guard_third_party_content, wrap_with_trust_banner
from .config import (
    MCPLoadIssue,
    MCPLoadResult,
    MCPServerConfig,
    add_user_mcp_server,
    default_config_paths,
    load_mcp_config,
    load_mcp_config_from,
    remove_user_mcp_server,
)
from .progressive import ProgressiveMCP
from .stdio import (
    MCPHandshakeError,
    MCPTransportError,
    StdioMCPTransport,
    stdio_transport_from_command,
)
from .toolspec import (
    MCPToolDispatcher,
    MCPToolEntry,
    normalise_mcp_tools,
    parse_lyra_mcp_name,
    render_mcp_result_for_chat,
)

__all__ = [
    "MCPAdapter",
    "MCPHandshakeError",
    "MCPLoadIssue",
    "MCPLoadResult",
    "MCPProtocolError",
    "MCPServerConfig",
    "MCPTimeoutError",
    "MCPToolDispatcher",
    "MCPToolEntry",
    "MCPTransportError",
    "ProgressiveMCP",
    "StdioMCPTransport",
    "TrustBanner",
    "add_user_mcp_server",
    "default_config_paths",
    "guard_third_party_content",
    "load_mcp_config",
    "load_mcp_config_from",
    "normalise_mcp_tools",
    "parse_lyra_mcp_name",
    "remove_user_mcp_server",
    "render_mcp_result_for_chat",
    "stdio_transport_from_command",
    "wrap_with_trust_banner",
]
