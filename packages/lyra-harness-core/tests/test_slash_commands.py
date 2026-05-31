"""Tests for Custom User-Defined Slash Commands (P1-B4)."""
from __future__ import annotations

import os
import tempfile

import pytest

from lyra_harness_core.slash_commands import (
    CommandArgument,
    CommandConfig,
    CommandDefinition,
    CommandFlag,
    SlashCommandRegistry,
    fuzzy_match,
    fuzzy_match_commands,
    load_commands_from_directories,
    load_commands_from_yaml,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_YAML = """\
commands:
  research:
    description: "Start a deep research task"
    usage: "/research <topic> [--depth 1-5]"
    handler: "lyra.research.deep_research"
    arguments:
      - name: topic
        type: string
        required: true
      - name: depth
        type: int
        default: 3
        choices: [1, 2, 3, 4, 5]
    flags:
      - name: verbose
        type: bool
        description: "Enable verbose output"

  review:
    description: "Review current changes"
    usage: "/review [--security] [--performance]"
    handler: "lyra.review.code_review"
    flags:
      - name: security
        type: bool
      - name: performance
        type: bool
"""


# ---------------------------------------------------------------------------
# CommandArgument
# ---------------------------------------------------------------------------


class TestCommandArgument:
    def test_defaults(self):
        a = CommandArgument(name="topic")
        assert a.name == "topic"
        assert a.type == "string"
        assert not a.required
        assert a.default is None
        assert a.choices is None
        assert a.description == ""

    def test_required_with_choices(self):
        a = CommandArgument(name="mode", type="string", required=True, choices=["a", "b"])
        assert a.required
        assert a.choices == ["a", "b"]

    def test_with_default(self):
        a = CommandArgument(name="depth", type="int", default=3)
        assert a.default == 3

    def test_frozen(self):
        a = CommandArgument(name="x")
        with pytest.raises(Exception):
            a.name = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CommandFlag
# ---------------------------------------------------------------------------


class TestCommandFlag:
    def test_defaults(self):
        f = CommandFlag(name="verbose")
        assert f.name == "verbose"
        assert f.type == "bool"
        assert f.description == ""

    def test_with_description(self):
        f = CommandFlag(name="security", description="Run security checks")
        assert f.description == "Run security checks"

    def test_frozen(self):
        f = CommandFlag(name="x")
        with pytest.raises(Exception):
            f.name = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CommandDefinition
# ---------------------------------------------------------------------------


class TestCommandDefinition:
    def test_minimal(self):
        d = CommandDefinition(name="test")
        assert d.name == "test"
        assert d.description == ""
        assert d.arguments == []
        assert d.flags == []

    def test_full(self):
        args = [CommandArgument(name="topic")]
        flags = [CommandFlag(name="verbose")]
        d = CommandDefinition(
            name="research",
            description="Deep research",
            usage="/research <topic>",
            handler="lyra.research",
            arguments=args,
            flags=flags,
            source="commands.yaml",
        )
        assert len(d.arguments) == 1
        assert len(d.flags) == 1
        assert d.source == "commands.yaml"

    def test_frozen(self):
        d = CommandDefinition(name="x")
        with pytest.raises(Exception):
            d.name = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# CommandConfig
# ---------------------------------------------------------------------------


class TestCommandConfig:
    def test_defaults(self):
        c = CommandConfig()
        assert c.commands == []
        assert c.source == ""

    def test_with_commands(self):
        cmds = [CommandDefinition(name="a"), CommandDefinition(name="b")]
        c = CommandConfig(commands=cmds, source="test.yaml")
        assert len(c.commands) == 2
        assert c.source == "test.yaml"

    def test_frozen(self):
        c = CommandConfig()
        with pytest.raises(Exception):
            c.commands = []  # type: ignore[misc]


# ---------------------------------------------------------------------------
# fuzzy_match
# ---------------------------------------------------------------------------


class TestFuzzyMatch:
    def test_exact_match(self):
        assert fuzzy_match("research", ["research", "review", "deploy"]) == "research"

    def test_close_match(self):
        result = fuzzy_match("reserch", ["research", "review", "deploy"])
        assert result == "research"  # 1-char typo

    def test_no_match(self):
        assert fuzzy_match("xyz", ["research", "review"], cutoff=0.6) is None

    def test_empty_candidates(self):
        assert fuzzy_match("test", []) is None

    def test_single_candidate_perfect(self):
        assert fuzzy_match("research", ["research"]) == "research"

    def test_single_candidate_close(self):
        result = fuzzy_match("reserch", ["research"])
        assert result == "research"

    def test_custom_cutoff_strict(self):
        assert fuzzy_match("reserch", ["research", "review"], cutoff=0.95) is None

    def test_case_insensitive(self):
        assert fuzzy_match("RESEARCH", ["research", "review"]) == "research"


# ---------------------------------------------------------------------------
# fuzzy_match_commands
# ---------------------------------------------------------------------------


class TestFuzzyMatchCommands:
    @pytest.fixture
    def cmds(self):
        return [
            CommandDefinition(name="research", description="Deep research"),
            CommandDefinition(name="review", description="Code review"),
            CommandDefinition(name="deploy", description="Deploy to production"),
        ]

    def test_exact(self, cmds):
        result = fuzzy_match_commands("review", cmds)
        assert result is not None
        assert result.name == "review"

    def test_fuzzy(self, cmds):
        result = fuzzy_match_commands("reveiw", cmds)
        assert result is not None
        assert result.name == "review"

    def test_no_match(self, cmds):
        assert fuzzy_match_commands("xyz", cmds) is None

    def test_empty_list(self):
        assert fuzzy_match_commands("test", []) is None


# ---------------------------------------------------------------------------
# load_commands_from_yaml
# ---------------------------------------------------------------------------


class TestLoadCommandsFromYaml:
    def test_loads_two_commands(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(VALID_YAML)
            f.flush()
            path = f.name

        try:
            cfg = load_commands_from_yaml(path)
            assert len(cfg.commands) == 2
            assert cfg.source == path
        finally:
            os.unlink(path)

    def test_command_has_arguments(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(VALID_YAML)
            f.flush()
            path = f.name

        try:
            cfg = load_commands_from_yaml(path)
            research = cfg.commands[0]
            assert research.name == "research"
            assert len(research.arguments) == 2
            assert research.arguments[0].name == "topic"
            assert research.arguments[0].required
            assert research.arguments[1].name == "depth"
            assert research.arguments[1].default == 3
        finally:
            os.unlink(path)

    def test_command_has_flags(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(VALID_YAML)
            f.flush()
            path = f.name

        try:
            cfg = load_commands_from_yaml(path)
            review = cfg.commands[1]
            assert review.name == "review"
            assert len(review.flags) == 2
            flag_names = {f.name for f in review.flags}
            assert flag_names == {"security", "performance"}
        finally:
            os.unlink(path)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_commands_from_yaml("/nonexistent/path/commands.yaml")

    def test_empty_commands(self):
        yaml_text = "commands: {}\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_text)
            f.flush()
            path = f.name

        try:
            cfg = load_commands_from_yaml(path)
            assert len(cfg.commands) == 0
        finally:
            os.unlink(path)

    def test_minimal_command(self):
        yaml_text = """\
commands:
  hello:
    description: "Say hello"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_text)
            f.flush()
            path = f.name

        try:
            cfg = load_commands_from_yaml(path)
            assert len(cfg.commands) == 1
            cmd = cfg.commands[0]
            assert cmd.name == "hello"
            assert cmd.description == "Say hello"
            assert cmd.arguments == []
            assert cmd.flags == []
        finally:
            os.unlink(path)

    def test_invalid_root_not_dict(self):
        yaml_text = "- not a mapping\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_text)
            f.flush()
            path = f.name

        try:
            with pytest.raises(ValueError, match="mapping"):
                load_commands_from_yaml(path)
        finally:
            os.unlink(path)

    def test_commands_not_dict(self):
        yaml_text = "commands: [1, 2, 3]\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_text)
            f.flush()
            path = f.name

        try:
            with pytest.raises(ValueError, match="mapping"):
                load_commands_from_yaml(path)
        finally:
            os.unlink(path)

    def test_command_spec_not_dict(self):
        yaml_text = """\
commands:
  bad: [1, 2, 3]
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_text)
            f.flush()
            path = f.name

        try:
            with pytest.raises(ValueError, match="mapping"):
                load_commands_from_yaml(path)
        finally:
            os.unlink(path)

    def test_arguments_with_choices(self):
        yaml_text = """\
commands:
  build:
    arguments:
      - name: target
        choices: [linux, macos, windows]
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_text)
            f.flush()
            path = f.name

        try:
            cfg = load_commands_from_yaml(path)
            assert cfg.commands[0].arguments[0].choices == ["linux", "macos", "windows"]
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# load_commands_from_directories
# ---------------------------------------------------------------------------


class TestLoadCommandsFromDirectories:
    def test_loads_from_env_var(self, monkeypatch, tmp_path):
        d = tmp_path / "env_cmds"
        d.mkdir()
        cmd_file = d / "commands.yaml"
        cmd_file.write_text(VALID_YAML)

        monkeypatch.setenv("LYRA_COMMANDS_PATH", str(d))

        cfg = load_commands_from_directories()
        assert len(cfg.commands) == 2

    def test_loads_from_explicit_directory(self, tmp_path):
        d = tmp_path / "explicit_cmds"
        d.mkdir()
        cmd_file = d / "commands.yaml"
        cmd_file.write_text(VALID_YAML)

        cfg = load_commands_from_directories(directories=[str(d)])
        assert len(cfg.commands) == 2

    def test_duplicate_skip(self, tmp_path, monkeypatch):
        d = tmp_path / "dup_cmds"
        d.mkdir()
        cmd_file = d / "commands.yaml"
        cmd_file.write_text(VALID_YAML)

        monkeypatch.setenv("LYRA_COMMANDS_PATH", str(d))
        # Same directory via both env and explicit — should not duplicate
        cfg = load_commands_from_directories(directories=[str(d)])
        assert len(cfg.commands) == 2  # not 4

    def test_no_files_found(self, tmp_path, monkeypatch):
        monkeypatch.delenv("LYRA_COMMANDS_PATH", raising=False)
        cfg = load_commands_from_directories(directories=[str(tmp_path)])
        assert len(cfg.commands) == 0

    def test_invalid_yaml_skipped(self, tmp_path):
        d = tmp_path / "bad_cmds"
        d.mkdir()
        cmd_file = d / "commands.yaml"
        cmd_file.write_text("not: [valid: yaml")

        cfg = load_commands_from_directories(directories=[str(d)])
        assert len(cfg.commands) == 0


# ---------------------------------------------------------------------------
# SlashCommandRegistry
# ---------------------------------------------------------------------------


class TestSlashCommandRegistry:
    @pytest.fixture
    def registry(self):
        return SlashCommandRegistry()

    @pytest.fixture
    def research_cmd(self):
        return CommandDefinition(
            name="research",
            description="Deep research",
            handler="lyra.research",
            arguments=[CommandArgument(name="topic")],
        )

    @pytest.fixture
    def review_cmd(self):
        return CommandDefinition(
            name="review",
            description="Code review",
            handler="lyra.review",
        )

    # --- register -------------------------------------------------------------

    def test_register_single(self, registry, research_cmd):
        registry.register(research_cmd)
        assert "research" in registry
        assert len(registry) == 1

    def test_register_with_handler(self, registry, research_cmd):
        called = []

        def handler(**kw):
            called.append(kw)

        registry.register(research_cmd, handler)
        registry.dispatch("research", args={"topic": "AI"})
        assert len(called) == 1

    def test_register_many(self, registry, research_cmd, review_cmd):
        cfg = CommandConfig(commands=[research_cmd, review_cmd])
        registry.register_many(cfg)
        assert len(registry) == 2

    def test_register_duplicate_overwrites(self, registry, research_cmd):
        registry.register(research_cmd)
        updated = CommandDefinition(name="research", description="Updated")
        registry.register(updated)
        assert registry.get("research").description == "Updated"

    def test_unregister(self, registry, research_cmd):
        registry.register(research_cmd)
        assert registry.unregister("research")
        assert "research" not in registry

    def test_unregister_nonexistent(self, registry):
        assert not registry.unregister("nope")

    def test_unregister_also_removes_handler(self, registry, research_cmd):
        called = []

        def handler(**kw):
            called.append(kw)

        registry.register(research_cmd, handler)
        registry.unregister("research")
        with pytest.raises(KeyError):
            registry.dispatch("research")

    # --- lookup ---------------------------------------------------------------

    def test_get_exact(self, registry, research_cmd):
        registry.register(research_cmd)
        assert registry.get("research") is research_cmd

    def test_get_missing(self, registry):
        assert registry.get("nope") is None

    def test_find_exact(self, registry, research_cmd):
        registry.register(research_cmd)
        assert registry.find("research") is research_cmd

    def test_find_fuzzy(self, registry, research_cmd, review_cmd):
        registry.register(research_cmd)
        registry.register(review_cmd)
        result = registry.find("reveiw")
        assert result is not None
        assert result.name == "review"

    def test_find_none(self, registry):
        assert registry.find("xyz") is None

    def test_find_empty_registry(self, registry):
        assert registry.find("anything") is None

    # --- suggest --------------------------------------------------------------

    def test_suggest_prefix(self, registry):
        registry.register(CommandDefinition(name="research"))
        registry.register(CommandDefinition(name="review"))
        registry.register(CommandDefinition(name="reset"))
        suggestions = registry.suggest("re")
        assert len(suggestions) >= 2
        assert suggestions[0].startswith("re")

    def test_suggest_empty(self, registry):
        assert registry.suggest("test") == []

    def test_suggest_limit(self, registry):
        for i in range(10):
            registry.register(CommandDefinition(name=f"cmd{i:02d}"))
        assert len(registry.suggest("cmd")) == 5  # default limit

    # --- dispatch -------------------------------------------------------------

    def test_dispatch_exact_name(self, registry, research_cmd):
        called = []

        def handler(args, flags, definition):
            called.append((args, flags, definition))

        registry.register(research_cmd, handler)
        _result = registry.dispatch("research", args={"topic": "AI"})
        assert len(called) == 1
        assert called[0][0] == {"topic": "AI"}

    def test_dispatch_fuzzy_name(self, registry, review_cmd):
        called = []

        def handler(args, flags, definition):
            called.append(definition.name)

        registry.register(review_cmd, handler)
        registry.dispatch("reveiw")
        assert called == ["review"]

    def test_dispatch_unknown_command(self, registry):
        with pytest.raises(KeyError, match="unknown"):
            registry.dispatch("nope")

    def test_dispatch_no_handler(self, registry, research_cmd):
        registry.register(research_cmd)
        with pytest.raises(RuntimeError, match="no handler"):
            registry.dispatch("research")

    def test_dispatch_passes_flags(self, registry, research_cmd):
        called = []

        def handler(args, flags, definition):  # noqa: ARG001
            called.append(flags)

        registry.register(research_cmd, handler)
        registry.dispatch("research", flags={"verbose": True})
        assert called[0] == {"verbose": True}

    def test_dispatch_passes_definition(self, registry, research_cmd):
        called = []

        def handler(args, flags, definition):  # noqa: ARG001
            called.append(definition)

        registry.register(research_cmd, handler)
        registry.dispatch("research")
        assert called[0] is research_cmd

    # --- introspection --------------------------------------------------------

    def test_command_names_sorted(self, registry):
        registry.register(CommandDefinition(name="ccc"))
        registry.register(CommandDefinition(name="aaa"))
        registry.register(CommandDefinition(name="bbb"))
        assert registry.command_names == ["aaa", "bbb", "ccc"]

    def test_command_names_empty(self, registry):
        assert registry.command_names == []

    def test_len(self, registry):
        assert len(registry) == 0
        registry.register(CommandDefinition(name="a"))
        assert len(registry) == 1

    def test_contains(self, registry, research_cmd):
        assert "research" not in registry
        registry.register(research_cmd)
        assert "research" in registry

    # --- fuzzy threshold ------------------------------------------------------

    def test_custom_fuzzy_threshold_strict(self, research_cmd):
        registry = SlashCommandRegistry(fuzzy_threshold=0.95)
        registry.register(research_cmd)
        assert registry.find("reserch") is None  # typo won't match at 0.95

    def test_custom_fuzzy_threshold_lenient(self, research_cmd):
        registry = SlashCommandRegistry(fuzzy_threshold=0.4)
        registry.register(research_cmd)
        result = registry.find("xyz")
        # At 0.4, even short words might match — just check it doesn't crash
        assert result is None or result.name == "research"


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------


class TestSlashCommandIntegration:
    def test_full_pipeline(self):
        # 1. Write YAML
        yaml_text = """\
commands:
  deploy:
    description: "Deploy to environment"
    usage: "/deploy <env> [--force]"
    handler: "lyra.deploy.run"
    arguments:
      - name: env
        type: string
        required: true
        choices: [staging, production]
    flags:
      - name: force
        type: bool
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_text)
            f.flush()
            path = f.name

        try:
            # 2. Load config from YAML
            cfg = load_commands_from_yaml(path)
            assert len(cfg.commands) == 1

            # 3. Register with handler
            dispatched = []

            def deploy_handler(args, flags, definition):
                dispatched.append((args, flags, definition))

            registry = SlashCommandRegistry()
            registry.register(cfg.commands[0], deploy_handler)

            # 4. Dispatch
            registry.dispatch("deploy", args={"env": "staging"}, flags={"force": True})

            assert len(dispatched) == 1
            call_args, call_flags, call_def = dispatched[0]
            assert call_args == {"env": "staging"}
            assert call_flags == {"force": True}
            assert call_def.name == "deploy"

            # 5. Fuzzy lookup works
            result = registry.find("deply")  # typo
            assert result is not None
            assert result.name == "deploy"

            # 6. Suggest works
            suggestions = registry.suggest("dep")
            assert "deploy" in suggestions
        finally:
            os.unlink(path)
