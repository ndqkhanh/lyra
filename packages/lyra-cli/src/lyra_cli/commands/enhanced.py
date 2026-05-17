"""Enhanced command utilities for Claude Code integration."""

from typing import Any

from lyra_cli.commands.registry import CommandSpec, register_command


class CommandEnhancer:
    """Enhances Lyra's command system with Claude Code patterns."""

    @staticmethod
    def create_model_command() -> CommandSpec:
        """Create /model command for model switching."""

        async def handler(args: str, context: dict[str, Any]) -> str:
            """Switch between models (haiku, sonnet, opus)."""
            model = args.strip().lower()
            valid_models = ["haiku", "sonnet", "opus"]

            if not model:
                current = context.get("model", "sonnet")
                return f"Current model: {current}\nAvailable: {', '.join(valid_models)}"

            if model not in valid_models:
                return f"Invalid model. Choose from: {', '.join(valid_models)}"

            context["model"] = model
            return f"Switched to {model}"

        return CommandSpec(
            name="model",
            handler=handler,
            description="Switch between AI models",
            category="config-theme",
            args_hint="[haiku|sonnet|opus]",
        )

    @staticmethod
    def create_skills_command() -> CommandSpec:
        """Create /skills command for skill management."""

        async def handler(args: str, context: dict[str, Any]) -> str:
            """List or activate skills."""
            if not args:
                # List available skills
                skills = context.get("skills_registry", {})
                if not skills:
                    return "No skills registered"
                return "Available skills:\n" + "\n".join(
                    f"  - {name}: {meta.get('description', 'No description')}"
                    for name, meta in skills.items()
                )

            # Activate specific skill
            skill_name = args.strip()
            return f"Activating skill: {skill_name}"

        return CommandSpec(
            name="skills",
            handler=handler,
            description="Manage and activate skills",
            category="tools-agents",
            args_hint="[skill-name]",
        )

    @staticmethod
    def create_mcp_command() -> CommandSpec:
        """Create /mcp command for MCP server management."""

        async def handler(args: str, context: dict[str, Any]) -> str:
            """Manage MCP servers."""
            if not args:
                # List connected servers
                servers = context.get("mcp_servers", {})
                if not servers:
                    return "No MCP servers connected"
                return "Connected MCP servers:\n" + "\n".join(
                    f"  - {name}: {status}"
                    for name, status in servers.items()
                )

            # Connect to server
            server_name = args.strip()
            return f"Connecting to MCP server: {server_name}"

        return CommandSpec(
            name="mcp",
            handler=handler,
            description="Manage MCP servers",
            category="mcp",
            args_hint="[server-name]",
        )

    @staticmethod
    def register_enhanced_commands() -> None:
        """Register all enhanced commands."""
        commands = [
            CommandEnhancer.create_model_command(),
            CommandEnhancer.create_skills_command(),
            CommandEnhancer.create_mcp_command(),
        ]

        for cmd in commands:
            try:
                register_command(cmd)
            except ValueError:
                # Command already registered
                pass
