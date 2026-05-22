"""
Tests for streaming REPL.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lyra_ui.streaming_repl import (
    LyraCompleter,
    REPLConfig,
    REPLMode,
    StatusBar,
    StreamingREPL,
    ToolProgressDisplay,
)


class TestREPLConfig:
    """Tests for REPLConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = REPLConfig()

        assert config.mode == REPLMode.AGENT
        assert config.model == "sonnet"
        assert config.streaming is True
        assert config.multiline is True
        assert config.show_status_bar is True
        assert config.show_progress is True
        assert config.vim_mode is False
        assert config.theme == "default"

    def test_custom_config(self):
        """Test custom configuration."""
        config = REPLConfig(
            mode=REPLMode.PLAN,
            model="opus",
            streaming=False,
            vim_mode=True,
        )

        assert config.mode == REPLMode.PLAN
        assert config.model == "opus"
        assert config.streaming is False
        assert config.vim_mode is True


class TestLyraCompleter:
    """Tests for LyraCompleter."""

    def test_completer_creation(self):
        """Test creating completer."""
        completer = LyraCompleter()

        assert len(completer.commands) > 0
        assert "help" in completer.commands
        assert "model" in completer.commands

    def test_slash_command_completion(self):
        """Test slash command completion."""
        completer = LyraCompleter()

        # Mock document
        document = MagicMock()
        document.text_before_cursor = "/he"
        document.get_word_before_cursor.return_value = "/he"

        completions = list(completer.get_completions(document, None))

        assert len(completions) > 0
        assert any(c.text == "help" for c in completions)

    def test_file_mention_completion(self):
        """Test file mention completion."""
        completer = LyraCompleter()
        completer.set_files(["test.py", "main.py", "config.yaml"])

        # Mock document
        document = MagicMock()
        document.text_before_cursor = "@te"
        document.get_word_before_cursor.return_value = "@te"

        completions = list(completer.get_completions(document, None))

        assert len(completions) > 0
        assert any(c.text == "test.py" for c in completions)

    def test_skill_mention_completion(self):
        """Test skill mention completion."""
        completer = LyraCompleter()
        completer.set_skills(["python-patterns", "testing", "security"])

        # Mock document
        document = MagicMock()
        document.text_before_cursor = "#py"
        document.get_word_before_cursor.return_value = "#py"

        completions = list(completer.get_completions(document, None))

        assert len(completions) > 0
        assert any(c.text == "python-patterns" for c in completions)

    def test_set_files(self):
        """Test setting files."""
        completer = LyraCompleter()
        files = ["file1.py", "file2.py"]

        completer.set_files(files)

        assert completer.files == files

    def test_set_skills(self):
        """Test setting skills."""
        completer = LyraCompleter()
        skills = ["skill1", "skill2"]

        completer.set_skills(skills)

        assert completer.skills == skills


class TestStreamingREPL:
    """Tests for StreamingREPL."""

    def test_repl_creation(self):
        """Test creating REPL."""
        repl = StreamingREPL()

        assert repl.config is not None
        assert repl.console is not None
        assert repl.formatter is not None
        assert repl.completer is not None
        assert repl.running is False

    def test_repl_with_config(self):
        """Test creating REPL with config."""
        config = REPLConfig(mode=REPLMode.PLAN, model="opus")
        repl = StreamingREPL(config)

        assert repl.config.mode == REPLMode.PLAN
        assert repl.config.model == "opus"

    def test_get_mode_badge(self):
        """Test getting mode badge."""
        repl = StreamingREPL()

        # Test different modes
        repl.config.mode = REPLMode.AGENT
        assert repl._get_mode_badge() == "[agent]"

        repl.config.mode = REPLMode.PLAN
        assert repl._get_mode_badge() == "[plan]"

        repl.config.mode = REPLMode.ASK
        assert repl._get_mode_badge() == "[ask]"

        repl.config.mode = REPLMode.AUTO
        assert repl._get_mode_badge() == "[auto]"

    def test_cmd_help(self):
        """Test help command."""
        repl = StreamingREPL()
        result = repl._cmd_help()

        assert "Commands:" in result
        assert "/help" in result
        assert "/model" in result

    def test_cmd_clear(self):
        """Test clear command."""
        repl = StreamingREPL()
        repl._cmd_clear()  # Should not raise

    def test_cmd_exit(self):
        """Test exit command."""
        repl = StreamingREPL()
        repl.running = True

        repl._cmd_exit()

        assert repl.running is False

    def test_cmd_model(self):
        """Test model command."""
        repl = StreamingREPL()

        # Get current model
        result = repl._cmd_model()
        assert "sonnet" in result

        # Change model
        result = repl._cmd_model("opus")
        assert "opus" in result
        assert repl.config.model == "opus"

    def test_cmd_mode(self):
        """Test mode command."""
        repl = StreamingREPL()

        # Get current mode
        result = repl._cmd_mode()
        assert "agent" in result

        # Change mode
        result = repl._cmd_mode("plan")
        assert "plan" in result
        assert repl.config.mode == REPLMode.PLAN

        # Invalid mode
        result = repl._cmd_mode("invalid")
        assert "Invalid" in result

    @pytest.mark.asyncio
    async def test_mock_agent_stream(self):
        """Test mock agent stream."""
        repl = StreamingREPL()

        chunks = []
        async for chunk in repl._mock_agent_stream("test input"):
            chunks.append(chunk)

        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert "test input" in full_response

    def test_update_stats(self):
        """Test updating stats."""
        repl = StreamingREPL()

        repl.update_stats(tokens_used=100, total_cost=0.5)

        assert repl.stats.tokens_used == 100
        assert repl.stats.total_cost == 0.5

    def test_set_agent(self):
        """Test setting agent."""
        repl = StreamingREPL()
        agent = MagicMock()

        repl.set_agent(agent)  # Should not raise

    def test_history_tracking(self):
        """Test command history tracking."""
        repl = StreamingREPL()

        assert len(repl.history) == 0

        repl.history.append("command1")
        repl.history.append("command2")

        assert len(repl.history) == 2
        assert repl.history[0] == "command1"


class TestToolProgressDisplay:
    """Tests for ToolProgressDisplay."""

    def test_progress_creation(self):
        """Test creating progress display."""
        progress = ToolProgressDisplay()

        assert progress.console is not None
        assert progress.progress is None
        assert len(progress.tasks) == 0

    def test_start_stop(self):
        """Test starting and stopping progress."""
        progress = ToolProgressDisplay()

        progress.start()
        assert progress.progress is not None

        progress.stop()
        assert progress.progress is None

    def test_add_tool(self):
        """Test adding tool."""
        progress = ToolProgressDisplay()
        progress.start()

        task_id = progress.add_tool("test_tool", "Testing")

        assert task_id >= 0
        assert "test_tool" in progress.tasks

        progress.stop()

    def test_update_tool(self):
        """Test updating tool progress."""
        progress = ToolProgressDisplay()
        progress.start()

        progress.add_tool("test_tool", "Testing")
        progress.update_tool("test_tool", 50.0)  # Should not raise

        progress.stop()

    def test_complete_tool(self):
        """Test completing tool."""
        progress = ToolProgressDisplay()
        progress.start()

        progress.add_tool("test_tool", "Testing")
        progress.complete_tool("test_tool")  # Should not raise

        progress.stop()

    def test_update_nonexistent_tool(self):
        """Test updating nonexistent tool."""
        progress = ToolProgressDisplay()
        progress.start()

        # Should not raise
        progress.update_tool("nonexistent", 50.0)

        progress.stop()


class TestStatusBar:
    """Tests for StatusBar."""

    def test_status_bar_creation(self):
        """Test creating status bar."""
        status_bar = StatusBar()

        assert status_bar.console is not None
        assert status_bar.mode == "agent"
        assert status_bar.model == "sonnet"
        assert status_bar.tokens == 0
        assert status_bar.cost == 0.0
        assert status_bar.elapsed == 0.0

    def test_render(self):
        """Test rendering status bar."""
        status_bar = StatusBar()
        panel = status_bar.render()

        assert panel is not None

    def test_update(self):
        """Test updating status bar."""
        status_bar = StatusBar()

        status_bar.update(
            mode="plan",
            model="opus",
            tokens=1000,
            cost=0.5,
            elapsed=10.0,
        )

        assert status_bar.mode == "plan"
        assert status_bar.model == "opus"
        assert status_bar.tokens == 1000
        assert status_bar.cost == 0.5
        assert status_bar.elapsed == 10.0

    def test_update_invalid_field(self):
        """Test updating invalid field."""
        status_bar = StatusBar()

        # Should not raise, just ignore invalid field
        status_bar.update(invalid_field="value")

    def test_display(self):
        """Test displaying status bar."""
        status_bar = StatusBar()
        status_bar.display()  # Should not raise


class TestREPLIntegration:
    """Integration tests for REPL."""

    def test_repl_components_integration(self):
        """Test REPL components work together."""
        repl = StreamingREPL()

        # Test completer integration
        assert repl.completer is not None
        repl.completer.set_files(["test.py"])

        # Test command palette integration
        assert repl.command_palette is not None
        result = repl.command_palette.execute_command("help")
        assert result is not None

        # Test stats integration
        repl.update_stats(tokens_used=100)
        assert repl.stats.tokens_used == 100

    def test_repl_mode_switching(self):
        """Test switching between modes."""
        repl = StreamingREPL()

        # Switch to plan mode
        repl._cmd_mode("plan")
        assert repl.config.mode == REPLMode.PLAN
        assert "[plan]" in repl._get_mode_badge()

        # Switch to ask mode
        repl._cmd_mode("ask")
        assert repl.config.mode == REPLMode.ASK
        assert "[ask]" in repl._get_mode_badge()

    def test_repl_model_switching(self):
        """Test switching between models."""
        repl = StreamingREPL()

        # Switch to opus
        repl._cmd_model("opus")
        assert repl.config.model == "opus"

        # Switch to haiku
        repl._cmd_model("haiku")
        assert repl.config.model == "haiku"

    @pytest.mark.asyncio
    async def test_stream_cancellation(self):
        """Test stream cancellation."""
        repl = StreamingREPL()

        # Start streaming
        stream = repl._mock_agent_stream("test")

        # Cancel after first chunk
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)
            repl.stream_handler.cancel()
            if repl.stream_handler.is_cancelled:
                break

        assert len(chunks) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
