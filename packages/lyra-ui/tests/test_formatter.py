"""
Tests for RichFormatter

Comprehensive test suite for the Rich formatter.
"""

import pytest
from io import StringIO
from rich.console import Console

from lyra_ui.formatter import RichFormatter, FormatterColors


class TestFormatterColors:
    """Test FormatterColors dataclass."""

    def test_formatter_colors_init(self):
        """Test FormatterColors initialization."""
        colors = FormatterColors(
            primary="#7C3AED",
            secondary="#06B6D4",
            accent="#F59E0B",
            success="#10B981",
            warning="#F59E0B",
            error="#EF4444",
            info="#3B82F6",
            text_dim="#BAC2DE",
            surface="#313244",
        )

        assert colors.primary == "#7C3AED"
        assert colors.secondary == "#06B6D4"
        assert colors.accent == "#F59E0B"
        assert colors.success == "#10B981"
        assert colors.warning == "#F59E0B"
        assert colors.error == "#EF4444"
        assert colors.info == "#3B82F6"
        assert colors.text_dim == "#BAC2DE"
        assert colors.surface == "#313244"


class TestRichFormatter:
    """Test RichFormatter class."""

    def test_formatter_init(self):
        """Test formatter initialization."""
        formatter = RichFormatter()

        assert formatter.console is not None
        assert formatter.theme_manager is not None
        assert formatter.colors is not None
        assert isinstance(formatter.colors, FormatterColors)

    def test_print_message_user(self):
        """Test printing user message."""
        formatter = RichFormatter()

        # Capture output
        output = StringIO()
        formatter.console = Console(file=output, force_terminal=True)

        formatter.print_message("Hello", role="user")

        result = output.getvalue()
        assert "Hello" in result
        assert "You" in result or "👤" in result

    def test_print_message_assistant(self):
        """Test printing assistant message."""
        formatter = RichFormatter()

        output = StringIO()
        formatter.console = Console(file=output, force_terminal=True)

        formatter.print_message("Hi there", role="assistant")

        result = output.getvalue()
        assert "Hi there" in result
        assert "Assistant" in result or "🤖" in result

    def test_print_message_system(self):
        """Test printing system message."""
        formatter = RichFormatter()

        output = StringIO()
        formatter.console = Console(file=output, force_terminal=True)

        formatter.print_message("System message", role="system")

        result = output.getvalue()
        assert "System message" in result
        assert "System" in result or "⚙️" in result

    def test_print_message_custom_title(self):
        """Test printing message with custom title."""
        formatter = RichFormatter()

        output = StringIO()
        formatter.console = Console(file=output, force_terminal=True)

        formatter.print_message("Custom", role="user", title="Custom Title")

        result = output.getvalue()
        assert "Custom" in result
        assert "Custom Title" in result

    def test_print_code_python(self):
        """Test printing Python code."""
        formatter = RichFormatter()

        output = StringIO()
        formatter.console = Console(file=output, force_terminal=True)

        code = "def hello():\n    print('Hello')"
        formatter.print_code(code, language="python")

        result = output.getvalue()
        # Check for key parts (ANSI codes will be present)
        assert "hello" in result
        assert "print" in result

    def test_print_code_with_title(self):
        """Test printing code with title."""
        formatter = RichFormatter()

        output = StringIO()
        formatter.console = Console(file=output, force_terminal=True)

        code = "const x = 1;"
        formatter.print_code(code, language="javascript", title="Example")

        result = output.getvalue()
        # Check for key parts
        assert "const" in result
        assert "Example" in result or "📝" in result

    def test_print_table_empty(self):
        """Test printing empty table."""
        formatter = RichFormatter()

        output = StringIO()
        formatter.console = Console(file=output, force_terminal=True)

        formatter.print_table([])

        result = output.getvalue()
        assert result == ""  # Empty table prints nothing

    def test_print_table_with_data(self):
        """Test printing table with data."""
        formatter = RichFormatter()

        output = StringIO()
        formatter.console = Console(file=output, force_terminal=True)

        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        formatter.print_table(data)

        result = output.getvalue()
        assert "Alice" in result
        assert "Bob" in result
        assert "30" in result
        assert "25" in result

    def test_print_table_with_title(self):
        """Test printing table with title."""
        formatter = RichFormatter()

        output = StringIO()
        formatter.console = Console(file=output, force_terminal=True)

        data = [{"id": 1}]
        formatter.print_table(data, title="Test Table")

        result = output.getvalue()
        # Check that output contains the title and data
        assert "Test Table" in result or "Test" in result
        assert "1" in result

    def test_print_status_success(self):
        """Test printing success status."""
        formatter = RichFormatter()

        output = StringIO()
        formatter.console = Console(file=output, force_terminal=True)

        formatter.print_status("Success!", status="success")

        result = output.getvalue()
        assert "Success!" in result
        assert "✅" in result

    def test_print_status_warning(self):
        """Test printing warning status."""
        formatter = RichFormatter()

        output = StringIO()
        formatter.console = Console(file=output, force_terminal=True)

        formatter.print_status("Warning!", status="warning")

        result = output.getvalue()
        assert "Warning!" in result
        assert "⚠️" in result

    def test_print_status_error(self):
        """Test printing error status."""
        formatter = RichFormatter()

        output = StringIO()
        formatter.console = Console(file=output, force_terminal=True)

        formatter.print_status("Error!", status="error")

        result = output.getvalue()
        assert "Error!" in result
        assert "❌" in result

    def test_print_status_info(self):
        """Test printing info status."""
        formatter = RichFormatter()

        output = StringIO()
        formatter.console = Console(file=output, force_terminal=True)

        formatter.print_status("Info", status="info")

        result = output.getvalue()
        assert "Info" in result
        assert "ℹ️" in result

    def test_print_markdown(self):
        """Test printing markdown."""
        formatter = RichFormatter()

        output = StringIO()
        formatter.console = Console(file=output, force_terminal=True)

        markdown = "# Heading\n\nParagraph with **bold** text."
        formatter.print_markdown(markdown)

        result = output.getvalue()
        assert "Heading" in result
        assert "Paragraph" in result

    def test_create_progress(self):
        """Test creating progress indicator."""
        formatter = RichFormatter()

        progress = formatter.create_progress("Loading...")

        assert progress is not None
        assert len(progress.tasks) == 1
        assert progress.tasks[0].description == "Loading..."

    def test_create_progress_default(self):
        """Test creating progress with default description."""
        formatter = RichFormatter()

        progress = formatter.create_progress()

        assert progress is not None
        assert len(progress.tasks) == 1
        assert progress.tasks[0].description == "Processing..."

    def test_print_header(self):
        """Test printing header."""
        formatter = RichFormatter()

        output = StringIO()
        formatter.console = Console(file=output, force_terminal=True)

        formatter.print_header("Main Title")

        result = output.getvalue()
        assert "Main Title" in result
        assert "🌟" in result

    def test_print_header_with_subtitle(self):
        """Test printing header with subtitle."""
        formatter = RichFormatter()

        output = StringIO()
        formatter.console = Console(file=output, force_terminal=True)

        formatter.print_header("Main Title", subtitle="Subtitle text")

        result = output.getvalue()
        assert "Main Title" in result
        assert "Subtitle text" in result

    def test_print_divider(self):
        """Test printing divider."""
        formatter = RichFormatter()

        output = StringIO()
        formatter.console = Console(file=output, force_terminal=True, width=80)

        formatter.print_divider()

        result = output.getvalue()
        assert "─" in result

    def test_print_divider_custom_char(self):
        """Test printing divider with custom character."""
        formatter = RichFormatter()

        output = StringIO()
        formatter.console = Console(file=output, force_terminal=True, width=80)

        formatter.print_divider(char="=")

        result = output.getvalue()
        assert "=" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
