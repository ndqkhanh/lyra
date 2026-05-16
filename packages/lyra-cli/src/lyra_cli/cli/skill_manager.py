"""Skill Manager for Lyra — Phase 1: Auto-discovery & Slash Command Registration.

Manages skill installation, loading, and execution.
Integrates 179+ skills from research.

Phase 1 Features:
- Auto-discovery from ~/.lyra/skills/ and .lyra/skills/
- JSON skill format with rich metadata
- Auto-registration as slash commands
- Autocomplete integration
- /skill list command
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional


class SkillManager:
    """Manages skills for Lyra with auto-discovery and slash command registration."""

    def __init__(self):
        # Global skills directory
        self.global_skills_dir = Path.home() / ".lyra" / "skills"
        self.global_skills_dir.mkdir(parents=True, exist_ok=True)

        # Project-local skills directory (relative to cwd)
        self.local_skills_dir = Path.cwd() / ".lyra" / "skills"

        # Load skills from both locations
        self.skills = self._load_skills()

    def _load_skills(self) -> dict:
        """Load installed skills from global and local directories.

        Local skills override global skills with the same name.
        """
        skills = {}

        # Load global skills first
        for skill_file in self.global_skills_dir.glob("*.json"):
            try:
                with open(skill_file) as f:
                    skill_data = json.load(f)
                    if self._validate_skill(skill_data):
                        skills[skill_data["name"]] = skill_data
            except Exception:
                pass

        # Load local skills (override global)
        if self.local_skills_dir.exists():
            for skill_file in self.local_skills_dir.glob("*.json"):
                try:
                    with open(skill_file) as f:
                        skill_data = json.load(f)
                        if self._validate_skill(skill_data):
                            skills[skill_data["name"]] = skill_data
                except Exception:
                    pass

        return skills

    def _validate_skill(self, skill_data: dict) -> bool:
        """Validate skill JSON structure.

        Required fields:
        - name: str
        - version: str
        - description: str
        - category: str
        - execution: dict with 'type' field

        Returns:
            True if valid, False otherwise
        """
        required_fields = ["name", "version", "description", "category", "execution"]
        if not all(field in skill_data for field in required_fields):
            return False

        if not isinstance(skill_data["execution"], dict):
            return False

        if "type" not in skill_data["execution"]:
            return False

        return True

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
                target_dir = self.global_skills_dir / skill_name

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
                target_dir = self.global_skills_dir / skill_name
                shutil.copytree(source_path, target_dir)

            # Reload skill metadata
            self.skills = self._load_skills()
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
            "global_skills_dir": str(self.global_skills_dir),
            "local_skills_dir": str(self.local_skills_dir),
        }

    def get_command_specs(self):
        """Generate CommandSpec entries for all skills.

        Returns a list of CommandSpec objects that can be registered
        as slash commands. Each skill becomes a command like /auto-research.

        Returns:
            list[CommandSpec]: List of command specifications
        """
        from lyra_cli.commands.registry import CommandSpec

        specs = []
        for name, skill in self.skills.items():
            # Create handler function for this skill
            def make_handler(skill_name: str):
                def handler(session, args: str):
                    return session._execute_skill(skill_name, args)
                return handler

            # Extract metadata
            description = skill.get("description", f"Execute {name} skill")
            category = skill.get("category", "skill")
            aliases = tuple(skill.get("aliases", []) or [])
            args_data = skill.get("args") or {}
            args_hint = args_data.get("hint", "") if isinstance(args_data, dict) else ""

            # Create CommandSpec
            spec = CommandSpec(
                name=name,
                handler=make_handler(name),
                description=description,
                category=category,
                aliases=aliases,
                args_hint=args_hint,
            )
            specs.append(spec)

        return specs

    def reload(self):
        """Reload skills from disk."""
        self.skills = self._load_skills()


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

    def add_server(self, name: str, command: str, args: Optional[list[str]] = None, env: Optional[dict] = None):
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
