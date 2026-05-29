"""Tests for lyra-command-registry."""

from lyra_command_registry import Command, CommandRegistry


class TestCommandRegistry:
    def test_register_and_get(self):
        r = CommandRegistry()
        r.register(Command(name="lint", description="Lint the codebase", pattern="run linter"))
        cmd = r.get_command("lint")
        assert cmd is not None
        assert cmd.name == "lint"

    def test_evolve_from_instinct(self):
        r = CommandRegistry()
        cmd = r.evolve_from_instinct("always_lint", "Always run linter before commit")
        assert cmd.name == "always_lint"
        assert cmd.source_instinct_id is None  # auto-evolved

    def test_execute_with_handler(self):
        r = CommandRegistry()
        r.register(
            Command(name="hello", description="Say hello", pattern="greet"),
            handler=lambda: "hello!",
        )
        result = r.execute("hello")
        assert result == "hello!"

    def test_execute_missing(self):
        r = CommandRegistry()
        try:
            r.execute("nonexistent")
            raise AssertionError()
        except ValueError:
            assert True

    def test_stats(self):
        r = CommandRegistry()
        assert r.stats["total"] == 0
        r.register(Command(name="test", description="t", pattern="t"))
        assert r.stats["total"] == 1
