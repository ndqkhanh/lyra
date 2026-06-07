"""
MCP (Model Context Protocol) gateway for Lyra plugin infrastructure.

Provides MCPGateway for connecting to MCP servers, discovering their tools,
translating MCP tool schemas to Lyra ToolDefs, and managing MCP sessions.
"""

from __future__ import annotations

from .gateway import MCPGateway, MCPServerInfo, MCPToolSchema

__all__ = [
    "MCPGateway",
    "MCPToolSchema",
    "MCPServerInfo",
]

__version__ = "1.0.0"
