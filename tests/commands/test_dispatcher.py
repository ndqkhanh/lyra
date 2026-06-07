"""
Tests for the command dispatcher module.
"""

import pytest

from src.commands.dispatcher import Command, CommandContext, CommandDispatcher


@pytest.fixture
def dispatcher() -> CommandDispatcher:
    """Provide a fresh CommandDispatcher for each test."""
    return CommandDispatcher()


class TestCommandDispatcher:
    """Tests for basic dispatcher behavior."""

    def test_initializes_with_builtins(self, dispatcher: CommandDispatcher):
        """Dispatcher should register built-in commands at init."""
        names = {cmd.name for cmd in dispatcher.list_commands()}
        assert names == {"help", "model", "clear", "status", "export", "skills"}

    def test_register_custom_command(self, dispatcher: CommandDispatcher):
        """A custom command should be registered and dispatchable."""

        async def my_handler(ctx: CommandContext) -> str:
            return f"Hello, {ctx.args[0] if ctx.args else 'world'}"

        cmd = Command(
            name="greet",
            handler=my_handler,
            description="Greet someone.",
            usage="greet [name]",
        )
        dispatcher.register(cmd)

        assert dispatcher.get_command("greet") is cmd

    def test_register_duplicate_raises(self, dispatcher: CommandDispatcher):
        """Registering a duplicate command name should raise."""

        async def handler(ctx: CommandContext) -> str:
            return ""

        dispatcher.register(Command(name="dup", handler=handler))
        with pytest.raises(ValueError, match="already registered"):
            dispatcher.register(Command(name="dup", handler=handler))

    def test_register_with_aliases(self, dispatcher: CommandDispatcher):
        """Commands with aliases should be dispatchable by alias."""

        async def handler(ctx: CommandContext) -> str:
            return "handled"

        dispatcher.register(Command(
            name="longname",
            handler=handler,
            aliases=["ln", "l"],
        ))
        assert dispatcher.get_command("ln") is not None
        assert dispatcher.get_command("l") is not None
        assert dispatcher.get_command("longname") is not None

    def test_register_conflicting_alias_raises(self, dispatcher: CommandDispatcher):
        """Registering a command with a conflicting alias should raise."""

        async def h1(ctx: CommandContext) -> str:
            return ""

        async def h2(ctx: CommandContext) -> str:
            return ""

        dispatcher.register(Command(name="first", handler=h1, aliases=["shared"]))
        with pytest.raises(ValueError, match="already mapped"):
            dispatcher.register(Command(name="second", handler=h2, aliases=["shared"]))

    def test_unregister_by_name(self, dispatcher: CommandDispatcher):
        """Unregistering a command by name should remove it."""
        dispatcher.unregister("status")
        assert dispatcher.get_command("status") is None

    def test_unregister_by_alias(self, dispatcher: CommandDispatcher):
        """Unregistering by alias should also remove the command."""

        async def handler(ctx: CommandContext) -> str:
            return ""

        dispatcher.register(Command(name="custom", handler=handler, aliases=["c"]))
        assert dispatcher.unregister("c") is True
        assert dispatcher.get_command("custom") is None

    def test_unregister_nonexistent(self, dispatcher: CommandDispatcher):
        """Unregistering a nonexistent command should return False."""
        assert dispatcher.unregister("ghost") is False

    def test_get_command_returns_none_for_unknown(
        self, dispatcher: CommandDispatcher
    ):
        """get_command for an unknown name should return None."""
        assert dispatcher.get_command("nonexistent") is None


class TestCommandDispatch:
    """Tests for command parsing and dispatch."""

    @pytest.mark.asyncio
    async def test_help_command(self, dispatcher: CommandDispatcher):
        """/help should return available commands."""
        result = await dispatcher.dispatch("/help")
        assert "help" in result
        assert "model" in result
        assert "clear" in result
        assert "status" in result
        assert "export" in result
        assert "skills" in result

    @pytest.mark.asyncio
    async def test_help_with_command_name(self, dispatcher: CommandDispatcher):
        """/help model should show model-specific help."""
        result = await dispatcher.dispatch("/help model")
        assert "model" in result
        assert "Switch" in result

    @pytest.mark.asyncio
    async def test_model_without_args(self, dispatcher: CommandDispatcher):
        """/model without args should show current model."""
        result = await dispatcher.dispatch("/model")
        assert "model" in result.lower()

    @pytest.mark.asyncio
    async def test_model_with_args(self, dispatcher: CommandDispatcher):
        """/model <name> should switch the model."""
        result = await dispatcher.dispatch("/model claude-opus-4")
        assert "claude-opus-4" in result

    @pytest.mark.asyncio
    async def test_clear_command(self, dispatcher: CommandDispatcher):
        """/clear should return a confirmation."""
        result = await dispatcher.dispatch("/clear")
        assert "cleared" in result.lower()

    @pytest.mark.asyncio
    async def test_status_command(self, dispatcher: CommandDispatcher):
        """/status should return session info."""
        ctx = CommandContext(
            command="status",
            args=[],
            raw_input="/status",
            session_id="test-session",
            state={"model": "custom-model"},
        )
        result = await dispatcher.dispatch("/status", context=ctx)
        assert "test-session" in result
        assert "custom-model" in result

    @pytest.mark.asyncio
    async def test_export_command(self, dispatcher: CommandDispatcher):
        """/export should return a confirmation with format."""
        result = await dispatcher.dispatch("/export json")
        assert "json" in result

    @pytest.mark.asyncio
    async def test_skills_command(self, dispatcher: CommandDispatcher):
        """/skills should list available skills."""
        result = await dispatcher.dispatch("/skills")
        assert "skills" in result.lower()

    @pytest.mark.asyncio
    async def test_dispatch_without_prefix_raises(
        self, dispatcher: CommandDispatcher
    ):
        """Dispatching without the prefix should raise ValueError."""
        with pytest.raises(ValueError, match="prefix"):
            await dispatcher.dispatch("help")

    @pytest.mark.asyncio
    async def test_dispatch_unknown_command(self, dispatcher: CommandDispatcher):
        """Dispatching an unknown command should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown command"):
            await dispatcher.dispatch("/nonexistent")

    @pytest.mark.asyncio
    async def test_dispatch_with_arguments(self, dispatcher: CommandDispatcher):
        """Arguments should be parsed and passed to the handler."""

        async def custom_handler(ctx: CommandContext) -> str:
            return f"args={ctx.args}"

        dispatcher.register(Command(
            name="testargs",
            handler=custom_handler,
        ))
        result = await dispatcher.dispatch("/testargs foo bar baz")
        assert "args=['foo', 'bar', 'baz']" in result

    @pytest.mark.asyncio
    async def test_route_using_aliases(self, dispatcher: CommandDispatcher):
        """Commands should be dispatchable by alias."""
        result = await dispatcher.dispatch("/?")
        assert "help" in result or "Available" in result

        result2 = await dispatcher.dispatch("/h")
        assert "help" in result2 or "Available" in result2


class TestCommandHelpers:
    """Tests for format_help and list_commands."""

    def test_format_help_all(self, dispatcher: CommandDispatcher):
        """format_help without a command should list all commands."""
        help_text = dispatcher.format_help()
        assert help_text.startswith("Available commands:")
        for name in ("help", "model", "clear", "status", "export", "skills"):
            assert name in help_text

    def test_format_help_specific(self, dispatcher: CommandDispatcher):
        """format_help for a specific command should show details."""
        help_text = dispatcher.format_help("help")
        assert "/help" in help_text
        assert "Show help" in help_text

    def test_format_help_unknown(self, dispatcher: CommandDispatcher):
        """format_help for an unknown command should return an error."""
        result = dispatcher.format_help("ghost")
        assert "Unknown" in result

    def test_hidden_commands_excluded(self, dispatcher: CommandDispatcher):
        """Hidden commands should not appear in list_commands()."""

        async def handler(ctx: CommandContext) -> str:
            return ""

        dispatcher.register(Command(
            name="secret",
            handler=handler,
            hidden=True,
        ))
        visible = dispatcher.list_commands(include_hidden=False)
        assert not any(c.name == "secret" for c in visible)

        all_cmds = dispatcher.list_commands(include_hidden=True)
        assert any(c.name == "secret" for c in all_cmds)
