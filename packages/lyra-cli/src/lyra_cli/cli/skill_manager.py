"""Skill Manager for Lyra.

Manages skill installation, loading, and execution.
Integrates 179+ skills from research.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional


class SkillManager:
    """Manages skills for Lyra."""

    def __init__(self):
        self.skills_dir = Path.home() / ".lyra" / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.skills = self._load_skills()

    def _load_skills(self) -> dict:
        """Load installed skills."""
        skills = {}

        # Load from skills directory
        for skill_file in self.skills_dir.glob("*.json"):
            try:
                with open(skill_file) as f:
                    skill_data = json.load(f)
                    skills[skill_data["name"]] = skill_data
            except Exception:
                pass

        return skills

    def install_skill(self, source: str) -> bool:
        """Install a skill from git or local path.

        Args:
            source: Git URL or local path

        Returns:
            True if successful
        """
        try:
            if source.startswith("http") or source.startswith("git"):
                # Clone from git
                skill_name = source.split("/")[-1].replace(".git", "")
                target_dir = self.skills_dir / skill_name

                subprocess.run(
                    ["git", "clone", source, str(target_dir)],
                    check=True,
                    capture_output=True
                )
            else:
                # Copy from local path
                import shutil
                source_path = Path(source).expanduser()
                skill_name = source_path.name
                target_dir = self.skills_dir / skill_name
                shutil.copytree(source_path, target_dir)

            # Load skill metadata
            self._load_skills()
            return True

        except Exception:
            return False

    def list_skills(self) -> list[str]:
        """List installed skills."""
        return list(self.skills.keys())

    def get_skill(self, name: str) -> Optional[dict]:
        """Get skill by name."""
        return self.skills.get(name)

    def search_skills(self, query: str) -> list[str]:
        """Search skills by name or description."""
        results = []
        query_lower = query.lower()

        for name, skill in self.skills.items():
            if query_lower in name.lower():
                results.append(name)
            elif "description" in skill and query_lower in skill["description"].lower():
                results.append(name)

        return results

    def get_stats(self) -> dict:
        """Get skill statistics."""
        return {
            "total_skills": len(self.skills),
            "skills_dir": str(self.skills_dir),
        }


class MCPManager:
    """Manages MCP (Model Context Protocol) servers."""

    def __init__(self):
        self.mcp_config = Path.home() / ".lyra" / "mcp_servers.json"
        self.servers = self._load_servers()

    def _load_servers(self) -> dict:
        """Load MCP server configuration."""
        if self.mcp_config.exists():
            try:
                with open(self.mcp_config) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_servers(self):
        """Save MCP server configuration."""
        self.mcp_config.parent.mkdir(parents=True, exist_ok=True)
        with open(self.mcp_config, "w") as f:
            json.dump(self.servers, f, indent=2)

    def add_server(self, name: str, command: str, args: list[str] = None, env: dict = None):
        """Add an MCP server.

        Args:
            name: Server name
            command: Command to run (e.g., "npx")
            args: Command arguments
            env: Environment variables
        """
        self.servers[name] = {
            "command": command,
            "args": args or [],
            "env": env or {},
        }
        self._save_servers()

    def remove_server(self, name: str):
        """Remove an MCP server."""
        if name in self.servers:
            del self.servers[name]
            self._save_servers()

    def list_servers(self) -> list[str]:
        """List configured MCP servers."""
        return list(self.servers.keys())

    def get_server(self, name: str) -> Optional[dict]:
        """Get MCP server configuration."""
        return self.servers.get(name)

    def get_stats(self) -> dict:
        """Get MCP statistics."""
        return {
            "total_servers": len(self.servers),
            "config_file": str(self.mcp_config),
        }
