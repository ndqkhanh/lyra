"""MCP manager - Manage MCP servers"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
import json


@dataclass
class MCPServer:
    """MCP server configuration"""
    name: str
    description: str
    command: str
    args: List[str]
    env: Dict[str, str]
    category: str  # issue-tracking, database, deployment, memory, web, ai, search, testing, other


class MCPManager:
    """Manages MCP servers"""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.home() / ".lyra" / "mcp"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.servers: Dict[str, MCPServer] = {}

    def register_server(self, server: MCPServer):
        """Register an MCP server"""
        self.servers[server.name] = server

    def get_server(self, name: str) -> Optional[MCPServer]:
        """Get server by name"""
        return self.servers.get(name)

    def list_servers(self, category: Optional[str] = None) -> List[MCPServer]:
        """List servers"""
        servers = list(self.servers.values())
        
        if category:
            servers = [s for s in servers if s.category == category]
        
        return sorted(servers, key=lambda s: s.name)

    def list_categories(self) -> List[str]:
        """List all categories"""
        categories = set(s.category for s in self.servers.values())
        return sorted(categories)

    def save_config(self):
        """Save MCP configuration to file"""
        config_file = self.config_dir / "servers.json"
        
        config = {
            "mcpServers": {}
        }
        
        for name, server in self.servers.items():
            config["mcpServers"][name] = {
                "command": server.command,
                "args": server.args,
                "env": server.env
            }
        
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)

    def load_config(self):
        """Load MCP configuration from file"""
        config_file = self.config_dir / "servers.json"
        
        if not config_file.exists():
            return
        
        with open(config_file) as f:
            config = json.load(f)
        
        # Note: This loads basic config, full server definitions
        # would need to be registered separately
        return config.get("mcpServers", {})


# Global MCP manager
_mcp_manager: Optional[MCPManager] = None


def get_mcp_manager() -> MCPManager:
    """Get or create global MCP manager"""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager
