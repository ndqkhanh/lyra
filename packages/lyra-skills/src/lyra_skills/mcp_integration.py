"""MCP (Model Context Protocol) server integration for Lyra.

Provides integration with MCP servers for extended capabilities.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MCPServerManager:
    """Manage MCP servers for Lyra."""

    def __init__(self, config_dir: Path | None = None):
        """Initialize MCP server manager.

        Args:
            config_dir: Configuration directory (default: ~/.lyra)
        """
        if config_dir is None:
            config_dir = Path.home() / ".lyra"
        self.config_dir = config_dir
        self.config_file = config_dir / "mcp_servers.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self) -> dict[str, Any]:
        """Load MCP server configuration.

        Returns:
            Configuration dictionary
        """
        if not self.config_file.exists():
            return {"mcpServers": {}}

        try:
            with open(self.config_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")
            return {"mcpServers": {}}

    def save_config(self, config: dict[str, Any]) -> bool:
        """Save MCP server configuration.

        Args:
            config: Configuration dictionary

        Returns:
            True if successful
        """
        try:
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save MCP config: {e}")
            return False

    def add_server(
        self,
        name: str,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> bool:
        """Add an MCP server to configuration.

        Args:
            name: Server name
            command: Command to run server
            args: Command arguments
            env: Environment variables

        Returns:
            True if successful
        """
        config = self.load_config()

        config["mcpServers"][name] = {
            "command": command,
            "args": args or [],
        }

        if env:
            config["mcpServers"][name]["env"] = env

        return self.save_config(config)

    def remove_server(self, name: str) -> bool:
        """Remove an MCP server from configuration.

        Args:
            name: Server name

        Returns:
            True if successful
        """
        config = self.load_config()

        if name in config["mcpServers"]:
            del config["mcpServers"][name]
            return self.save_config(config)

        return False

    def list_servers(self) -> dict[str, Any]:
        """List all configured MCP servers.

        Returns:
            Dictionary of server configurations
        """
        config = self.load_config()
        return config.get("mcpServers", {})

    def install_mcp_package(self, package: str) -> bool:
        """Install an MCP server package via npm.

        Args:
            package: NPM package name

        Returns:
            True if successful
        """
        try:
            subprocess.run(
                ["npm", "install", "-g", package],
                check=True,
                capture_output=True,
            )
            logger.info(f"Installed MCP package: {package}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install {package}: {e.stderr.decode()}")
            return False
        except FileNotFoundError:
            logger.error("npm not found. Please install Node.js")
            return False


# Production-ready MCP servers
PRODUCTION_MCP_SERVERS = {
    "filesystem": {
        "name": "Filesystem MCP",
        "package": "@modelcontextprotocol/server-filesystem",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        "description": "File system operations",
    },
    "github": {
        "name": "GitHub MCP",
        "package": "@modelcontextprotocol/server-github",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"},
        "description": "GitHub API integration",
    },
    "postgres": {
        "name": "PostgreSQL MCP",
        "package": "@modelcontextprotocol/server-postgres",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-postgres"],
        "env": {"DATABASE_URL": "${DATABASE_URL}"},
        "description": "PostgreSQL database operations",
    },
}


def install_production_mcp_servers(
    servers: list[str] | None = None,
    config_dir: Path | None = None,
) -> dict[str, bool]:
    """Install production-ready MCP servers.

    Args:
        servers: List of server names to install (None = all)
        config_dir: Configuration directory

    Returns:
        Dict mapping server names to installation success
    """
    manager = MCPServerManager(config_dir)
    results = {}

    if servers is None:
        servers = list(PRODUCTION_MCP_SERVERS.keys())

    for server_name in servers:
        if server_name not in PRODUCTION_MCP_SERVERS:
            logger.warning(f"Unknown MCP server: {server_name}")
            results[server_name] = False
            continue

        server_info = PRODUCTION_MCP_SERVERS[server_name]

        # Install package
        package_installed = manager.install_mcp_package(server_info["package"])
        if not package_installed:
            results[server_name] = False
            continue

        # Add to configuration
        config_added = manager.add_server(
            server_name,
            server_info["command"],
            server_info["args"],
            server_info.get("env"),
        )

        results[server_name] = config_added

    return results


__all__ = [
    "MCPServerManager",
    "PRODUCTION_MCP_SERVERS",
    "install_production_mcp_servers",
]
