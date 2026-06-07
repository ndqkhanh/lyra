"""
Command system — CommandDispatcher with slash command registration.

Built-in commands: /help, /model, /clear, /status, /export, /skills.
"""

import shlex
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

CommandHandler = Callable[["CommandContext"], Awaitable[str]]


@dataclass
class Command:
    """A registered slash command."""

    name: str
    handler: CommandHandler
    description: str = ""
    usage: str = ""
    aliases: list[str] = field(default_factory=list)
    hidden: bool = False


@dataclass
class CommandContext:
    """
    Context passed to every command handler.

    Contains the parsed command name, its arguments, and any session-level
    state that handlers may need.
    """

    command: str
    args: list[str]
    raw_input: str
    session_id: str = ""
    state: dict[str, Any] = field(default_factory=dict)


class CommandDispatcher:
    """
    Dispatches slash commands to registered handlers.

    Supports:
    - Named commands with aliases
    - Argument parsing (shell-like via shlex)
    - Built-in commands: /help, /model, /clear, /status, /export, /skills
    - User-friendly error messages for unknown or misused commands
    """

    def __init__(self, prefix: str = "/") -> None:
        """
        Initialize the command dispatcher.

        Args:
            prefix: The command prefix character (default '/').
        """
        self._prefix = prefix
        self._commands: dict[str, Command] = {}
        self._aliases: dict[str, str] = {}
        self._register_builtins()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, command: Command) -> None:
        """
        Register a new command.

        Args:
            command: The Command to register.

        Raises:
            ValueError: If the command name or an alias conflicts.
        """
        if command.name in self._commands:
            raise ValueError(f"Command '{command.name}' is already registered")

        self._commands[command.name] = command

        for alias in command.aliases:
            if alias in self._aliases:
                raise ValueError(
                    f"Alias '{alias}' is already mapped to '{self._aliases[alias]}'"
                )
            self._aliases[alias] = command.name

    def unregister(self, name: str) -> bool:
        """
        Unregister a command.

        Args:
            name: The command name or alias.

        Returns:
            True if the command was found and removed.
        """
        resolved = self._resolve_name(name)
        if resolved is None:
            return False

        cmd = self._commands.pop(resolved, None)
        if cmd is None:
            return False

        for alias in cmd.aliases:
            self._aliases.pop(alias, None)

        return True

    def get_command(self, name: str) -> Command | None:
        """
        Get a registered command by name or alias.

        Args:
            name: Command name or alias.

        Returns:
            The Command or None.
        """
        resolved = self._resolve_name(name)
        if resolved is None:
            return None
        return self._commands.get(resolved)

    def list_commands(self, include_hidden: bool = False) -> list[Command]:
        """
        List all registered commands.

        Args:
            include_hidden: If True, include hidden commands.

        Returns:
            List of Command objects sorted by name.
        """
        cmds = [
            cmd for cmd in self._commands.values()
            if include_hidden or not cmd.hidden
        ]
        return sorted(cmds, key=lambda c: c.name)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def dispatch(self, raw_input: str, context: CommandContext | None = None) -> str:
        """
        Parse and dispatch a command from raw input.

        Args:
            raw_input: The raw input string (e.g. "/help model").
            context: Optional pre-built context; if not provided, a new one
                     is constructed from the parsed input.

        Returns:
            The handler's response string.

        Raises:
            ValueError: If the command is not recognized.
        """
        raw_input = raw_input.strip()

        if not raw_input.startswith(self._prefix):
            raise ValueError(f"Input must start with prefix '{self._prefix}'")

        # Parse command name and arguments
        without_prefix = raw_input[len(self._prefix):].strip()

        parts = shlex.split(without_prefix)
        if not parts:
            raise ValueError("No command name provided")

        cmd_name = parts[0].lower()
        cmd_args = parts[1:]

        # Resolve aliases
        resolved = self._resolve_name(cmd_name)
        if resolved is None:
            available = ", ".join(
                f"{self._prefix}{c}" for c in sorted(self._commands.keys())
                if not self._commands[c].hidden
            )
            raise ValueError(
                f"Unknown command '{self._prefix}{cmd_name}'. "
                f"Available commands: {available}"
            )

        command = self._commands[resolved]

        # Build or reuse context
        if context is None:
            context = CommandContext(
                command=resolved,
                args=cmd_args,
                raw_input=raw_input,
            )
        else:
            context.command = resolved
            context.args = cmd_args
            context.raw_input = raw_input

        return await command.handler(context)

    # ------------------------------------------------------------------
    # Help generation
    # ------------------------------------------------------------------

    def format_help(self, command_name: str | None = None) -> str:
        """
        Format help text for a command or all commands.

        Args:
            command_name: Optional specific command name.

        Returns:
            Formatted help string.
        """
        if command_name is not None:
            cmd = self.get_command(command_name)
            if cmd is None:
                return f"Unknown command: {command_name}"

            parts = [f"  {self._prefix}{cmd.name}"]
            if cmd.aliases:
                parts.append(f"  Aliases: {', '.join(cmd.aliases)}")
            if cmd.usage:
                parts.append(f"  Usage: {self._prefix}{cmd.usage}")
            if cmd.description:
                parts.append(f"  {cmd.description}")
            return "\n".join(parts)

        lines = ["Available commands:"]
        for cmd in self.list_commands():
            aliases = f" ({', '.join(cmd.aliases)})" if cmd.aliases else ""
            usage = f" {cmd.usage}" if cmd.usage else ""
            lines.append(
                f"  {self._prefix}{cmd.name}{usage}{aliases} — {cmd.description}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_name(self, name: str) -> str | None:
        """Resolve a command name or alias to the canonical name."""
        if name in self._commands:
            return name
        return self._aliases.get(name)

    def _register_builtins(self) -> None:
        """Register the built-in slash commands."""
        self._commands = {}
        self._aliases = {}

        self.register(Command(
            name="help",
            handler=self._handle_help,
            description="Show help for commands.",
            usage="help [command]",
            aliases=["h", "?"],
        ))
        self.register(Command(
            name="model",
            handler=self._handle_model,
            description="Switch or show the current AI model.",
            usage="model [model_name]",
        ))
        self.register(Command(
            name="clear",
            handler=self._handle_clear,
            description="Clear the conversation context.",
            usage="clear",
        ))
        self.register(Command(
            name="status",
            handler=self._handle_status,
            description="Show session and system status.",
            usage="status",
        ))
        self.register(Command(
            name="export",
            handler=self._handle_export,
            description="Export the current session data.",
            usage="export [format]",
            aliases=["e"],
        ))
        self.register(Command(
            name="skills",
            handler=self._handle_skills,
            description="List available skills.",
            usage="skills [skill_name]",
        ))

    async def _handle_help(self, ctx: CommandContext) -> str:
        """Built-in /help handler."""
        if ctx.args:
            return self.format_help(ctx.args[0])
        return self.format_help()

    async def _handle_model(self, ctx: CommandContext) -> str:
        """Built-in /model handler."""
        if not ctx.args:
            current = ctx.state.get("model", "claude-sonnet-4-20250514")
            return f"Current model: {current}"
        model_name = ctx.args[0]
        ctx.state["model"] = model_name
        return f"Model switched to: {model_name}"

    async def _handle_clear(self, ctx: CommandContext) -> str:
        """Built-in /clear handler."""
        ctx.state.pop("conversation", None)
        return "Conversation context cleared."

    async def _handle_status(self, ctx: CommandContext) -> str:
        """Built-in /status handler."""
        model = ctx.state.get("model", "claude-sonnet-4-20250514")
        session = ctx.session_id or "none"
        return (
            f"Session: {session}\n"
            f"Model: {model}\n"
            f"Commands loaded: {len(self._commands)}\n"
            f"State keys: {list(ctx.state.keys())}"
        )

    async def _handle_export(self, ctx: CommandContext) -> str:
        """Built-in /export handler."""
        fmt = ctx.args[0] if ctx.args else "json"
        return f"Session exported as {fmt}. (stub)"

    async def _handle_skills(self, ctx: CommandContext) -> str:
        """Built-in /skills handler."""
        if ctx.args:
            return f"Details for skill '{ctx.args[0]}': (stub)"
        return "Available skills:\n  - stub (no skills loaded)"
