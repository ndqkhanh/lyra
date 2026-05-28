"""Tests for command loader — Lyra + ECC unified registry."""


from lyra_cli.commands.command_loader import CommandLoader
from lyra_cli.commands.command_registry import Command, CommandRegistry, get_registry


class TestCommandRegistry:
    def test_register_and_get(self):
        reg = CommandRegistry()
        cmd = Command(name="test-cmd", description="Test", handler=lambda: None)
        reg.register(cmd)
        assert reg.get("test-cmd") is cmd

    def test_get_by_alias(self):
        reg = CommandRegistry()
        cmd = Command(name="main", description="Main", handler=lambda: None, aliases=["m"])
        reg.register(cmd)
        assert reg.get("m") is cmd

    def test_exists(self):
        reg = CommandRegistry()
        reg.register(Command(name="exists", description="", handler=lambda: None))
        assert reg.exists("exists") is True
        assert reg.exists("missing") is False

    def test_exists_alias(self):
        reg = CommandRegistry()
        reg.register(Command(name="real", description="", handler=lambda: None, aliases=["r"]))
        assert reg.exists("r") is True

    def test_list_all(self):
        reg = CommandRegistry()
        reg.register(Command(name="a", description="", handler=lambda: None, category="cat1"))
        reg.register(Command(name="b", description="", handler=lambda: None, category="cat2"))
        assert len(reg.list()) == 2

    def test_list_by_category(self):
        reg = CommandRegistry()
        reg.register(Command(name="a", description="", handler=lambda: None, category="planning"))
        reg.register(Command(name="b", description="", handler=lambda: None, category="review"))
        assert len(reg.list(category="planning")) == 1

    def test_list_by_source(self):
        reg = CommandRegistry()
        reg.register(Command(name="a", description="", handler=lambda: None, source="lyra"))
        reg.register(Command(name="b", description="", handler=lambda: None, source="ecc"))
        assert len(reg.list(source="ecc")) == 1

    def test_list_categories(self):
        reg = CommandRegistry()
        reg.register(Command(name="a", description="", handler=lambda: None, category="z"))
        reg.register(Command(name="b", description="", handler=lambda: None, category="a"))
        assert reg.list_categories() == ["a", "z"]

    def test_merge_duplicate(self):
        reg = CommandRegistry()
        cmd1 = Command(name="shared", description="v1", handler=lambda: None, aliases=["s1"])
        cmd2 = Command(name="shared", description="v2", handler=lambda: None, aliases=["s2"])
        reg.register(cmd1)
        assert reg.merge_duplicate(cmd2) is True
        assert reg.get("s1") is cmd1
        assert reg.get("s2") is cmd1

    def test_merge_duplicate_no_existing(self):
        reg = CommandRegistry()
        cmd = Command(name="unique", description="u", handler=lambda: None)
        assert reg.merge_duplicate(cmd) is False

    def test_multiple_aliases(self):
        reg = CommandRegistry()
        cmd = Command(name="multi", description="", handler=lambda: None, aliases=["m1", "m2", "m3"])
        reg.register(cmd)
        assert reg.get("m1") is cmd
        assert reg.get("m2") is cmd
        assert reg.get("m3") is cmd


class TestCommandLoader:
    def test_load_lyra_commands(self):
        cmds = CommandLoader.load_lyra_commands()
        assert len(cmds) > 100
        names = {c.name for c in cmds}
        assert "help" in names
        assert "model" in names
        assert "research" in names

    def test_register_all(self):
        registry = CommandLoader.register_all()
        assert registry is not None
        assert CommandLoader.total_count() > 150

    def test_count_by_source(self):
        CommandLoader.register_all()
        counts = CommandLoader.count_by_source()
        assert "lyra" in counts
        assert "ecc" in counts
        assert counts["lyra"] > 100
        assert counts["ecc"] >= 70

    def test_all_commands_have_description(self):
        cmds = CommandLoader.load_lyra_commands()
        for cmd in cmds:
            assert cmd.description, f"{cmd.name} has no description"

    def test_all_commands_have_valid_names(self):
        cmds = CommandLoader.load_lyra_commands()
        for cmd in cmds:
            assert not cmd.name.startswith("/"), f"{cmd.name} starts with /"
            assert " " not in cmd.name, f"{cmd.name} contains space"

    def test_no_duplicate_names(self):
        cmds = CommandLoader.load_lyra_commands()
        names = [c.name for c in cmds]
        assert len(names) == len(set(names)), f"Duplicates: {[n for n in names if names.count(n) > 1]}"


class TestGlobalRegistry:
    def test_singleton(self):
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2
