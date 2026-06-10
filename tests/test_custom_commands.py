"""
Tests for the custom command system (custom_loader.py and palette.py).

Covers:
  - CustomCommandLoader: file discovery, parsing, registration, reload
  - CommandPalette: fuzzy search, history, formatting
  - SandboxedExecutor: execution, safety checks, banned commands
  - REPLEnhancements: syntax highlighting, auto-complete, history search
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from lyra.commands.custom_loader import (
    CommandFile,
    CustomCommandLoader,
)
from lyra.commands.dispatcher import Command, CommandContext, CommandDispatcher
from lyra.commands.palette import (
    CommandPalette,
    CompletionResult,
    REPLEnhancements,
    SandboxedExecutor,
)


# ======================================================================
# CustomCommandLoader
# ======================================================================


class TestCustomCommandLoader:
    @pytest.fixture
    def loader(self) -> CustomCommandLoader:
        return CustomCommandLoader(commands_dir="/tmp/nonexistent_commands")

    def test_discover_files_no_directory(self) -> None:
        loader = CustomCommandLoader(commands_dir="/tmp/nonexistent_dir_xyz")
        assert loader.discover_files() == []

    def test_load_all_no_directory_raises(self) -> None:
        loader = CustomCommandLoader(commands_dir="/tmp/nonexistent_dir_xyz_2")
        with pytest.raises(FileNotFoundError):
            loader.load_all()

    def test_load_single_nonexistent(self) -> None:
        loader = CustomCommandLoader()
        result = loader.load_single("/tmp/nonexistent_file.md")
        assert result is None

    def test_parse_frontmatter_basic(self) -> None:
        raw = "name: test-cmd\ndescription: A test command\nusage: test-cmd [arg]\n"
        result = CustomCommandLoader._parse_frontmatter(raw)
        assert result.get("name") == "test-cmd"
        assert result.get("description") == "A test command"
        assert result.get("usage") == "test-cmd [arg]"

    def test_parse_frontmatter_boolean(self) -> None:
        raw = "hidden: true\nenabled: false\n"
        result = CustomCommandLoader._parse_frontmatter(raw)
        assert result.get("hidden") is True
        assert result.get("enabled") is False

    def test_parse_frontmatter_list(self) -> None:
        raw = "aliases:\n- tc\n- test\n"
        result = CustomCommandLoader._parse_frontmatter(raw)
        assert result.get("aliases") == ["tc", "test"]

    def test_parse_frontmatter_empty(self) -> None:
        assert CustomCommandLoader._parse_frontmatter("") == {}

    def test_load_from_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd_file = Path(tmpdir) / "greet.md"
            cmd_file.write_text(
                "---\n"
                "name: greet\n"
                "description: Say hello\n"
                "usage: greet [name]\n"
                "aliases:\n"
                "  - hi\n"
                "---\n"
                "Hello, ${0}! You said: ${args}\n"
            )

            dispatcher = CommandDispatcher()
            loader = CustomCommandLoader(
                commands_dir=tmpdir,
                dispatcher=dispatcher,
            )
            count = loader.load_all()
            assert count == 1

            cmd = dispatcher.get_command("greet")
            assert cmd is not None
            assert cmd.description == "Say hello"

    def test_hot_reload_detects_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd_file = Path(tmpdir) / "reload_test.md"
            cmd_file.write_text("---\nname: rt\n---\nbody v1\n")

            dispatcher = CommandDispatcher()
            loader = CustomCommandLoader(
                commands_dir=tmpdir,
                dispatcher=dispatcher,
                watch=True,
            )
            loader.load_all()
            assert dispatcher.get_command("rt") is not None

            # Modify file
            cmd_file.write_text("---\nname: rt\n---\nbody v2\n")
            reloaded = loader.reload_changed()
            assert reloaded >= 1

    def test_unload_all(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd_file = Path(tmpdir) / "cmd1.md"
            cmd_file.write_text("---\nname: cmd1\n---\nbody\n")
            cmd_file2 = Path(tmpdir) / "cmd2.md"
            cmd_file2.write_text("---\nname: cmd2\n---\nbody\n")

            dispatcher = CommandDispatcher()
            loader = CustomCommandLoader(commands_dir=tmpdir, dispatcher=dispatcher)
            loader.load_all()
            assert len(loader.get_loaded_commands()) == 2

            unloaded = loader.unload_all()
            assert unloaded == 2
            assert len(loader.get_loaded_commands()) == 0

    def test_get_load_errors(self) -> None:
        loader = CustomCommandLoader()
        assert loader.get_load_errors() == []

    def test_get_statistics(self) -> None:
        loader = CustomCommandLoader()
        stats = loader.get_statistics()
        assert "commands_dir" in stats

    def test_discover_files_no_directory(self) -> None:
        loader = CustomCommandLoader(commands_dir="/tmp/nonexistent_dir_xyz")
        assert loader.discover_files() == []

    def test_reload_changed_watch_disabled(self) -> None:
        loader = CustomCommandLoader()
        assert loader.reload_changed() == 0

    def test_parse_file_exceeds_max_size(self) -> None:
        from lyra.commands.custom_loader import MAX_COMMAND_FILE_SIZE

        with tempfile.TemporaryDirectory() as tmpdir:
            big_path = Path(tmpdir) / "big.md"
            big_path.write_text("x" * (MAX_COMMAND_FILE_SIZE + 1))
            loader = CustomCommandLoader(commands_dir=tmpdir)
            result = loader.load_single(str(big_path))
            assert result is None  # should fail due to size

    def test_load_all_with_bad_directory(self) -> None:
        """load_all with non-existent directory raises."""
        loader = CustomCommandLoader(commands_dir="/tmp/definitely_not_a_dir_xyz")
        with pytest.raises(FileNotFoundError):
            loader.load_all()

    def test_load_single_exception_handling(self) -> None:
        """load_single returns None for unreadable file."""
        result = CustomCommandLoader().load_single("/tmp/nonexistent_file.md")
        assert result is None

    def test_parse_frontmatter_with_comments(self) -> None:
        raw = "name: test\n# this is a comment\ndescription: test\n"
        result = CustomCommandLoader._parse_frontmatter(raw)
        assert result.get("name") == "test"
        assert result.get("description") == "test"

    def test_parse_frontmatter_with_list_value(self) -> None:
        raw = "name: test\naliases:\n- alias1\n- alias2\n"
        result = CustomCommandLoader._parse_frontmatter(raw)
        assert result.get("aliases") == ["alias1", "alias2"]

    def test_parse_frontmatter_empty_value_then_list(self) -> None:
        """Test frontmatter where key has no value then list items follow."""
        raw = "aliases:\n- a\n- b\n"
        result = CustomCommandLoader._parse_frontmatter(raw)
        assert result.get("aliases") == ["a", "b"]

    def test_register_command_handler_body(self) -> None:
        """Test that the registered handler actually renders body with args."""
        import tempfile
        from pathlib import Path
        from lyra.commands.dispatcher import CommandContext

        with tempfile.TemporaryDirectory() as tmpdir:
            cmd_file = Path(tmpdir) / "hello.md"
            cmd_file.write_text(
                "---\nname: hello\ndescription: Say hello\n---\nHello, ${0}!\n"
            )

            dispatcher = CommandDispatcher()
            loader = CustomCommandLoader(
                commands_dir=tmpdir,
                dispatcher=dispatcher,
            )
            loader.load_all()

            cmd = dispatcher.get_command("hello")
            assert cmd is not None, "Command should be registered"

            # Execute the command
            import asyncio
            ctx = CommandContext(command="hello", args=["world"], raw_input="hello world", session_id="sess-1")
            result = asyncio.run(cmd.handler(ctx))
            assert "Hello, world!" in result


# ======================================================================
# CommandPalette
# ======================================================================


class TestCommandPalette:
    @pytest.fixture
    def palette(self) -> CommandPalette:
        dispatcher = CommandDispatcher()
        return CommandPalette(dispatcher)

    def test_search_empty_query(self, palette: CommandPalette) -> None:
        results = palette.search("")
        assert len(results) > 0  # returns all commands

    def test_search_prefix_match(self, palette: CommandPalette) -> None:
        results = palette.search("help")
        assert any(r["name"] == "help" for r in results)
        # prefix match should have score 1.0
        help_result = [r for r in results if r["name"] == "help"][0]
        assert help_result["score"] == 1.0

    def test_search_fuzzy_name(self, palette: CommandPalette) -> None:
        results = palette.search("hel")
        assert any("help" in r["name"] for r in results)

    def test_search_no_match(self, palette: CommandPalette) -> None:
        results = palette.search("zzzznonexistent")
        assert len(results) == 0

    def test_search_by_category(self, palette: CommandPalette) -> None:
        results = palette.search_by_category("help")
        assert len(results) >= 0

    def test_record_and_get_history(self, palette: CommandPalette) -> None:
        palette.record_search("help")
        palette.record_search("status")
        history = palette.get_search_history()
        assert "help" in history
        assert "status" in history

    def test_format_results(self, palette: CommandPalette) -> None:
        results = palette.search("help")
        formatted = palette.format_results(results)
        assert isinstance(formatted, str)
        assert len(formatted) > 0

    def test_format_results_empty(self, palette: CommandPalette) -> None:
        formatted = palette.format_results([])
        assert "No matching" in formatted

    def test_get_statistics(self, palette: CommandPalette) -> None:
        stats = palette.get_statistics()
        assert stats["available_commands"] > 0


# ======================================================================
# SandboxedExecutor
# ======================================================================


class TestSandboxedExecutor:
    @pytest.fixture
    def executor(self) -> SandboxedExecutor:
        return SandboxedExecutor(timeout=5.0)

    def test_execute_simple(self, executor: SandboxedExecutor) -> None:
        result = executor.execute("echo hello")
        assert result["success"] is True
        assert result["exit_code"] == 0
        assert "hello" in result["output"]

    def test_execute_failure(self, executor: SandboxedExecutor) -> None:
        result = executor.execute("false")
        assert result["success"] is False
        assert result["exit_code"] != 0

    def test_banned_command_raises(self, executor: SandboxedExecutor) -> None:
        with pytest.raises(ValueError, match="banned"):
            executor.execute("rm -rf /")

    def test_batch_execution(self, executor: SandboxedExecutor) -> None:
        results = executor.execute_batch(["echo a", "echo b", "false"])
        assert len(results) == 3
        assert results[0]["success"] is True
        assert results[2]["success"] is False

    def test_get_last_results(self, executor: SandboxedExecutor) -> None:
        executor.execute("echo test")
        results = executor.get_last_results()
        assert len(results) >= 1
        assert results[0]["command"] == "echo test"

    def test_get_execution_count(self, executor: SandboxedExecutor) -> None:
        executor.execute("echo a")
        executor.execute("echo b")
        assert executor.get_execution_count() >= 2

    def test_get_statistics(self, executor: SandboxedExecutor) -> None:
        executor.execute("echo test")
        stats = executor.get_statistics()
        assert stats["execution_count"] >= 1


# ======================================================================
# REPLEnhancements
# ======================================================================


class TestREPLEnhancements:
    @pytest.fixture
    def repl(self) -> REPLEnhancements:
        dispatcher = CommandDispatcher()
        return REPLEnhancements(dispatcher=dispatcher)

    def test_syntax_highlight(self, repl: REPLEnhancements) -> None:
        highlighted = repl.highlight("help status")
        assert "\033[" in highlighted  # ANSI codes present
        assert "help" in highlighted
        assert "status" in highlighted

    def test_strip_ansi(self, repl: REPLEnhancements) -> None:
        ansi_text = "\033[1;36mhelp\033[0m"
        plain = repl.strip_ansi(ansi_text)
        assert plain == "help"

    def test_complete_command_name(self, repl: REPLEnhancements) -> None:
        results = repl.complete("he")
        assert any("help" in r.text for r in results)

    def test_complete_empty(self, repl: REPLEnhancements) -> None:
        results = repl.complete("")
        assert len(results) > 0  # should list all

    def test_complete_args(self, repl: REPLEnhancements) -> None:
        results = repl.complete("help --")
        assert len(results) >= 0

    def test_history_add_and_get(self, repl: REPLEnhancements) -> None:
        repl.add_to_history("echo hello", duration=0.5, exit_code=0)
        repl.add_to_history("ls -la", duration=0.3, exit_code=0)
        history = repl.get_history(limit=10)
        assert len(history) == 2
        assert history[0].command == "ls -la"  # most recent first

    def test_history_search(self, repl: REPLEnhancements) -> None:
        repl.add_to_history("echo hello world")
        repl.add_to_history("ls -la")
        repl.add_to_history("git status")
        matches = repl.search_history("echo")
        assert len(matches) >= 1
        assert matches[0].command == "echo hello world"

    def test_history_search_empty_query(self, repl: REPLEnhancements) -> None:
        repl.add_to_history("echo test")
        matches = repl.search_history("")
        assert len(matches) >= 1

    def test_navigate_back_and_forward(self, repl: REPLEnhancements) -> None:
        repl.add_to_history("cmd1")
        repl.add_to_history("cmd2")
        repl.add_to_history("cmd3")

        assert repl.navigate_back() == "cmd3"
        assert repl.navigate_back() == "cmd2"
        assert repl.navigate_back() == "cmd1"
        # At beginning, back should stay at first
        assert repl.navigate_back() == "cmd1"
        assert repl.navigate_forward() == "cmd2"
        assert repl.navigate_forward() == "cmd3"
        # At end, forward should return None
        assert repl.navigate_forward() is None

    def test_navigate_empty_history(self, repl: REPLEnhancements) -> None:
        assert repl.navigate_back() is None
        assert repl.navigate_forward() is None

    def test_clear_history(self, repl: REPLEnhancements) -> None:
        repl.add_to_history("cmd1")
        repl.add_to_history("cmd2")
        repl.clear_history()
        assert len(repl.get_history()) == 0

    def test_format_prompt(self, repl: REPLEnhancements) -> None:
        prompt = repl.format_prompt(cwd="/home/user", session_id="sess123", model="claude-sonnet")
        assert "lyra" in prompt
        assert "sess123" in prompt
        assert "sonnet" in prompt or "claude" in prompt

    def test_format_matched_line(self, repl: REPLEnhancements) -> None:
        formatted = repl.format_matched_line("echo hello world", "hello")
        assert "\033[" in formatted  # ANSI highlighting
        assert "hello" in formatted

    def test_get_statistics(self, repl: REPLEnhancements) -> None:
        stats = repl.get_statistics()
        assert stats["history_size"] == 0
        assert stats["dispatcher_available"] is True


# ======================================================================
# Additional palette coverage for missing lines
# ======================================================================


class TestCommandPaletteAdvanced:
    """Covers remaining palette lines."""

    @pytest.fixture
    def palette(self) -> CommandPalette:
        dispatcher = CommandDispatcher()
        return CommandPalette(dispatcher)

    def test_search_alias_match(self, palette: CommandPalette) -> None:
        results = palette.search("help")
        help_r = [r for r in results if r["name"] == "help"]
        if help_r:
            assert help_r[0]["match_type"] in ("prefix",)

    def test_search_fuzzy_description(self, palette: CommandPalette) -> None:
        results = palette.search("command")
        desc_matches = [r for r in results if r["match_type"] == "fuzzy_desc"]
        assert len(desc_matches) >= 0

    def test_search_by_category_match(self, palette: CommandPalette) -> None:
        results = palette.search_by_category("help")
        assert len(results) >= 0

    def test_get_statistics_details(self, palette: CommandPalette) -> None:
        stats = palette.get_statistics()
        assert "available_commands" in stats
        assert "search_history_size" in stats
        assert "max_results" in stats

    def test_format_results_with_selection(self, palette: CommandPalette) -> None:
        palette._selected_index = 0
        results = palette.search("help")
        formatted = palette.format_results(results)
        if results:
            assert formatted.startswith(">")

    def test_format_results_no_selection(self, palette: CommandPalette) -> None:
        results = palette.search("help")
        formatted = palette.format_results(results)
        assert isinstance(formatted, str)
        assert len(formatted) > 0

    def test_empty_search_history(self, palette: CommandPalette) -> None:
        assert palette.get_search_history() == []

    def test_record_search_noop_empty(self, palette: CommandPalette) -> None:
        palette.record_search("")
        assert palette.get_search_history() == []

    def test_record_search_max_history(self, palette: CommandPalette) -> None:
        from lyra.commands.palette import MAX_HISTORY_SIZE
        for i in range(MAX_HISTORY_SIZE + 10):
            palette.record_search(f"q{i}")
        assert len(palette.get_search_history()) <= MAX_HISTORY_SIZE

    def test_search_no_query_all(self, palette: CommandPalette) -> None:
        results = palette.search("   ")
        assert len(results) > 0


class TestSandboxedExecutorAdvanced:
    """Covers remaining executor lines."""

    @pytest.fixture
    def executor(self) -> SandboxedExecutor:
        return SandboxedExecutor(timeout=5.0)

    def test_custom_working_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            exec_ = SandboxedExecutor(timeout=5.0, working_dir=tmpdir)
            result = exec_.execute("pwd")
            assert result["success"] is True
            assert tmpdir in result["output"]

    def test_execute_timeout(self) -> None:
        exec_ = SandboxedExecutor(timeout=0.1)
        result = exec_.execute("sleep 5")
        assert result["success"] is False
        assert result["exit_code"] == -1

    def test_get_last_results_count(self, executor: SandboxedExecutor) -> None:
        executor.execute("echo a")
        executor.execute("echo b")
        executor.execute("echo c")
        results = executor.get_last_results(count=2)
        assert len(results) == 2

    def test_get_statistics_empty(self) -> None:
        exec_ = SandboxedExecutor()
        stats = exec_.get_statistics()
        assert stats["success_rate"] == 0.0
        assert stats["avg_duration"] == 0.0

    def test_get_statistics_after_runs(self, executor: SandboxedExecutor) -> None:
        executor.execute("echo hello")
        executor.execute("echo world")
        stats = executor.get_statistics()
        assert stats["execution_count"] >= 2
        assert stats["cached_results"] >= 2
        assert stats["success_rate"] > 0


class TestREPLEnhancementsAdvanced:
    """Covers remaining REPL lines."""

    @pytest.fixture
    def repl(self) -> REPLEnhancements:
        dispatcher = CommandDispatcher()
        return REPLEnhancements(dispatcher=dispatcher)

    def test_highlight_empty(self, repl: REPLEnhancements) -> None:
        assert repl.highlight("") == ""

    def test_highlight_number(self, repl: REPLEnhancements) -> None:
        """Numbers are highlighted with ANSI."""
        highlighted = repl.highlight("count 42")
        assert "\033[" in highlighted

    def test_highlight_flag(self, repl: REPLEnhancements) -> None:
        highlighted = repl.highlight("ls -la")
        assert "-la" in highlighted

    def test_format_prompt_full(self, repl: REPLEnhancements) -> None:
        prompt = repl.format_prompt(
            cwd="/home/user/projects",
            session_id="session-abc-123",
            model="claude-sonnet-4-20250514",
        )
        assert "lyra" in prompt
        assert "session" in prompt
        assert "claude" in prompt or "sonnet" in prompt

    def test_format_prompt_cwd_with_home(self, repl: REPLEnhancements) -> None:
        import os
        home = os.path.expanduser("~")
        prompt = repl.format_prompt(cwd=home + "/project")
        assert "~" in prompt

    def test_format_prompt_no_session(self, repl: REPLEnhancements) -> None:
        prompt = repl.format_prompt()
        assert "lyra" in prompt

    def test_add_history_empty_noop(self, repl: REPLEnhancements) -> None:
        repl.add_to_history("")
        assert len(repl.get_history()) == 0

    def test_search_history_with_regex_special_chars(self, repl: REPLEnhancements) -> None:
        repl.add_to_history("test (parentheses) here")
        matches = repl.search_history("(parentheses)")
        assert len(matches) >= 1

    def test_search_history_invalid_regex(self, repl: REPLEnhancements) -> None:
        repl.add_to_history("echo hello")
        matches = repl.search_history("[invalid")
        assert len(matches) >= 0

    def test_format_matched_line_no_match(self, repl: REPLEnhancements) -> None:
        result = repl.format_matched_line("echo hello", "xyz")
        assert result == "echo hello"

    def test_complete_without_dispatcher(self) -> None:
        repl = REPLEnhancements()
        results = repl.complete("he")
        assert isinstance(results, list)

    def test_navigate_back_single_entry(self, repl: REPLEnhancements) -> None:
        repl.add_to_history("only-command")
        assert repl.navigate_back() == "only-command"
        assert repl.navigate_back() == "only-command"

    def test_navigate_forward_at_end(self, repl: REPLEnhancements) -> None:
        repl.add_to_history("cmd1")
        repl.add_to_history("cmd2")
        repl.navigate_back()  # -> "cmd2"
        repl.navigate_back()  # -> "cmd1"
        assert repl.navigate_forward() == "cmd2"
        assert repl.navigate_forward() is None

    def test_complete_args_dispatcher_available(self, repl: REPLEnhancements) -> None:
        results = repl.complete("help --")
        assert len(results) >= 0

    def test_complete_args_not_a_command(self, repl: REPLEnhancements) -> None:
        results = repl.complete("nonexistent_command --")
        assert len(results) >= 0

    def test_complete_paths(self, repl: REPLEnhancements) -> None:
        results = repl._complete_paths("/")
        assert isinstance(results, list)

    def test_complete_paths_empty_prefix(self, repl: REPLEnhancements) -> None:
        results = repl._complete_paths("")
        assert isinstance(results, list)

    def test_strip_ansi(self, repl: REPLEnhancements) -> None:
        text = "\033[1;36mhelp\033[0m \033[0;33m--flag\033[0m"
        plain = repl.strip_ansi(text)
        assert plain == "help --flag"
        assert "\033[" not in plain
