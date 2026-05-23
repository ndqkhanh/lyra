"""Server registry - Registry of MCP servers"""

from typing import Dict, List
from .mcp_manager import MCPServer


class ServerRegistry:
    """Registry of MCP servers"""

    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}

    def register(self, server: MCPServer):
        """Register a server"""
        self.servers[server.name] = server

    def get(self, name: str) -> MCPServer:
        """Get server by name"""
        return self.servers.get(name)

    def list(self, category: str = None) -> List[MCPServer]:
        """List servers"""
        servers = list(self.servers.values())
        
        if category:
            servers = [s for s in servers if s.category == category]
        
        return sorted(servers, key=lambda s: s.name)


# Global registry
_registry = ServerRegistry()


def get_registry() -> ServerRegistry:
    """Get global server registry"""
    return _registry
