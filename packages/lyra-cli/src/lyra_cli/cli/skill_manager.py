"""Skill Manager for Lyra — Phases 1-4: Complete Skill System.

Manages skill installation, loading, execution, configuration, templates, analytics, and composition.
Integrates 179+ skills from research.

Phase 1 Features:
- Auto-discovery from ~/.lyra/skills/ and .lyra/skills/
- JSON skill format with rich metadata
- Auto-registration as slash commands
- Autocomplete integration
- /skill list command

Phase 4 Features:
- Skill composition and chaining
- Skill templates and scaffolding
- Usage analytics and tracking
- Advanced configuration system
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from lyra_cli.cli.composition_engine import CompositionEngine
from lyra_cli.cli.skill_analytics import SkillAnalytics, SkillInvocation
from lyra_cli.cli.skill_config import SkillConfigManager
from lyra_cli.cli.skill_templates import SkillTemplateEngine


class SkillManager:
    """Manages skills for Lyra with auto-discovery and slash command registration."""

    def __init__(self):
        # Global skills directory
        self.global_skills_dir = Path.home() / ".lyra" / "skills"
        self.global_skills_dir.mkdir(parents=True, exist_ok=True)

        # Project-local skills directory (relative to cwd)
        self.local_skills_dir = Path.cwd() / ".lyra" / "skills"

        # Phase 4: Initialize advanced features
        self.config_manager = SkillConfigManager(
            Path.home() / ".lyra" / "skill_config.json"
        )
        self.template_engine = SkillTemplateEngine(
            Path.home() / ".lyra" / "templates"
        )
        self.analytics = SkillAnalytics(Path.home() / ".lyra" / "analytics")
        self.composition_engine = CompositionEngine(self)

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

    # Phase 4: Composition Methods
    def execute_composition(self, skill_name: str, user_input: str) -> dict:
        """Execute a composition skill.

        Args:
            skill_name: Name of composition skill
            user_input: User-provided arguments

        Returns:
            Execution result with output and success status
        """
        skill = self.skills.get(skill_name)
        if not skill:
            return {"success": False, "error": f"Skill '{skill_name}' not found"}

        execution = skill.get("execution", {})
        if execution.get("type") != "composition":
            return {
                "success": False,
                "error": f"Skill '{skill_name}' is not a composition",
            }

        start_time = datetime.now()
        try:
            result = self.composition_engine.execute(execution, user_input)
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            # Track analytics
            self.analytics.record_invocation(
                SkillInvocation(
                    skill_name=skill_name,
                    timestamp=start_time,
                    duration_ms=duration_ms,
                    success=result.success,
                    error=result.error,
                    args_length=len(user_input),
                    output_length=len(str(result.output)) if result.output else 0,
                )
            )

            return {
                "success": result.success,
                "output": result.output,
                "error": result.error,
            }
        except Exception as e:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self.analytics.record_invocation(
                SkillInvocation(
                    skill_name=skill_name,
                    timestamp=start_time,
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e),
                    args_length=len(user_input),
                )
            )
            return {"success": False, "error": str(e)}

    # Phase 4: Template Methods
    def create_from_template(
        self, template_name: str, variables: dict[str, str], save_path: Optional[Path] = None
    ) -> dict:
        """Create a new skill from a template.

        Args:
            template_name: Name of template to use
            variables: Template variables
            save_path: Optional path to save skill (defaults to global skills dir)

        Returns:
            Result with skill data and save path
        """
        try:
            skill_data = self.template_engine.render(template_name, variables)

            # Save to file
            if save_path is None:
                skill_name = skill_data["name"]
                save_path = self.global_skills_dir / f"{skill_name}.json"

            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "w") as f:
                json.dump(skill_data, f, indent=2)

            # Reload skills
            self.reload()

            return {
                "success": True,
                "skill_name": skill_data["name"],
                "path": str(save_path),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_templates(self) -> list[dict]:
        """List available skill templates."""
        return self.template_engine.list_templates()

    # Phase 4: Configuration Methods
    def get_skill_config(self, skill_name: str) -> dict:
        """Get configuration for a skill."""
        return self.config_manager.get_skill_config(skill_name)

    def set_skill_config(self, skill_name: str, config: dict):
        """Set configuration for a skill."""
        self.config_manager.set_skill_config(skill_name, config)

    def get_global_config(self) -> dict:
        """Get global skill configuration."""
        return self.config_manager.config.get("global", {})

    # Phase 4: Analytics Methods
    def get_skill_stats(self, skill_name: Optional[str] = None) -> dict:
        """Get usage statistics for skills."""
        stats = self.analytics.get_stats(skill_name)
        return {
            name: {
                "total_invocations": s.total_invocations,
                "successful_invocations": s.successful_invocations,
                "failed_invocations": s.failed_invocations,
                "avg_duration_ms": s.avg_duration_ms,
                "success_rate": s.success_rate,
                "first_used": s.first_used.isoformat(),
                "last_used": s.last_used.isoformat(),
            }
            for name, s in stats.items()
        }

    def get_top_skills(
        self, limit: int = 10, sort_by: str = "invocations"
    ) -> list[dict]:
        """Get top skills by usage or performance."""
        top_stats = self.analytics.get_top_skills(limit, sort_by)
        return [
            {
                "skill_name": s.skill_name,
                "total_invocations": s.total_invocations,
                "success_rate": s.success_rate,
                "avg_duration_ms": s.avg_duration_ms,
            }
            for s in top_stats
        ]

    def record_skill_execution(
        self,
        skill_name: str,
        duration_ms: int,
        success: bool,
        error: Optional[str] = None,
        args_length: int = 0,
        output_length: int = 0,
    ):
        """Record a skill execution for analytics."""
        self.analytics.record_invocation(
            SkillInvocation(
                skill_name=skill_name,
                timestamp=datetime.now(),
                duration_ms=duration_ms,
                success=success,
                error=error,
                args_length=args_length,
                output_length=output_length,
            )
        )


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
