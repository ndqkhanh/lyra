"""Tool call formatting system for displaying tool invocations and results"""

from dataclasses import dataclass
from typing import Any
from .symbols import SymbolRegistry
from .colors import ColorEngine
from .layout import LayoutEngine


@dataclass
class ToolCall:
    """Tool call data structure"""
    id: str
    name: str
    parameters: dict[str, Any]
    result: "ToolResult | None" = None
    status: str = "pending"  # pending, running, success, error
    start_time: float = 0.0
    end_time: float | None = None


@dataclass
class ToolResult:
    """Tool result data structure"""
    success: bool
    data: Any = None
    error: dict[str, Any] | None = None
    diagnostics: list["Diagnostic"] | None = None


@dataclass
class Diagnostic:
    """Diagnostic message"""
    severity: str  # error, warning, info, hint
    message: str
    file: str | None = None
    line: int | None = None
    column: int | None = None
    snippet: str | None = None


@dataclass
class DiffHunk:
    """Diff hunk for file updates"""
    start_line: int
    context_before: list[tuple[int, str]]
    removed: list[tuple[int, str]]
    added: list[tuple[int, str]]
    context_after: list[tuple[int, str]]


class ToolCallFormatter:
    """Formatter for tool calls and results"""

    def __init__(self, use_colors: bool = True, use_unicode: bool = True):
        self.symbols = SymbolRegistry(use_unicode=use_unicode)
        self.colors = ColorEngine(use_colors=use_colors)
        self.layout = LayoutEngine()

    def render_tool_call(
        self,
        tool_call: ToolCall,
        indent: int = 0,
        show_parameters: bool = True
    ) -> list[str]:
        """Render tool call with parameters"""
        lines = []
        indent_str = " " * indent

        # Status symbol
        if tool_call.status == "running":
            symbol = self.symbols.status("running")
            symbol_styled = self.colors.yellow(symbol)
        elif tool_call.status == "success":
            symbol = self.symbols.status("completed")
            symbol_styled = self.colors.green(symbol)
        elif tool_call.status == "error":
            symbol = self.symbols.status("failed")
            symbol_styled = self.colors.red(symbol)
        else:
            symbol = self.symbols.status("idle")
            symbol_styled = self.colors.dim(symbol)

        # Tool name
        tool_name = f"{self.colors.bold(self.colors.cyan(tool_call.name))}"
        header = f"{indent_str}{symbol_styled} Tool Call: {tool_name}"
        lines.append(header)

        # Parameters
        if show_parameters and tool_call.parameters:
            for key, value in tool_call.parameters.items():
                param_line = self._format_parameter(key, value, indent + 2)
                lines.append(param_line)

        return lines

    def _format_parameter(self, key: str, value: Any, indent: int) -> str:
        """Format a single parameter"""
        indent_str = " " * indent

        # Format value based on type
        if isinstance(value, str):
            # Truncate long strings
            if len(value) > 60:
                value_str = self.layout.truncate_text(value, 60)
            else:
                value_str = value
        elif isinstance(value, (int, float, bool)):
            value_str = str(value)
        elif value is None:
            value_str = "null"
        elif isinstance(value, (list, dict)):
            # For complex types, show type and length
            if isinstance(value, list):
                value_str = f"[{len(value)} items]"
            else:
                value_str = f"{{{len(value)} keys}}"
        else:
            value_str = str(value)

        return f"{indent_str}{self.colors.dim(key)}: {value_str}"

    def render_tool_result(
        self,
        tool_result: ToolResult,
        indent: int = 2,
        show_data: bool = True
    ) -> list[str]:
        """Render tool result"""
        lines = []
        indent_str = " " * indent
        connector = self.symbols.get("⎿")

        # Result header
        if tool_result.success:
            status_text = self.colors.green("(success)")
        else:
            status_text = self.colors.red("(error)")

        header = f"{indent_str}{self.colors.dim(connector)}  Result {status_text}"
        lines.append(header)

        # Data or error
        if tool_result.success and show_data and tool_result.data:
            data_str = self._format_result_data(tool_result.data)
            for line in data_str.split("\n"):
                lines.append(f"{indent_str}  {line}")
        elif not tool_result.success and tool_result.error:
            error_msg = tool_result.error.get("message", "Unknown error")
            lines.append(f"{indent_str}  {self.colors.red(error_msg)}")

            # Stack trace if available
            if "stack" in tool_result.error:
                stack_lines = tool_result.error["stack"].split("\n")[:5]  # First 5 lines
                for stack_line in stack_lines:
                    lines.append(f"{indent_str}    {self.colors.dim(stack_line)}")

        # Diagnostics
        if tool_result.diagnostics:
            lines.extend(self.render_diagnostics(tool_result.diagnostics, indent + 2))

        return lines

    def _format_result_data(self, data: Any) -> str:
        """Format result data"""
        if isinstance(data, str):
            return data
        elif isinstance(data, (int, float, bool)):
            return str(data)
        elif data is None:
            return "null"
        else:
            # For complex types, show summary
            return f"{type(data).__name__}: {str(data)[:100]}"

    def render_diagnostics(
        self,
        diagnostics: list[Diagnostic],
        indent: int = 0
    ) -> list[str]:
        """Render diagnostic messages"""
        lines = []
        indent_str = " " * indent

        for diag in diagnostics:
            # Severity icon
            if diag.severity == "error":
                icon = self.colors.red("✗")
            elif diag.severity == "warning":
                icon = self.colors.yellow("⚠")
            elif diag.severity == "info":
                icon = self.colors.cyan("ℹ")
            else:
                icon = self.colors.dim("·")

            # Location
            if diag.file and diag.line:
                location = f"{diag.file}:{diag.line}"
                if diag.column:
                    location += f":{diag.column}"
                location_str = self.colors.cyan(location)
            else:
                location_str = ""

            # Message
            if location_str:
                line = f"{indent_str}{icon} {location_str} - {diag.message}"
            else:
                line = f"{indent_str}{icon} {diag.message}"

            lines.append(line)

            # Code snippet if available
            if diag.snippet:
                snippet_lines = diag.snippet.split("\n")
                for snippet_line in snippet_lines:
                    lines.append(f"{indent_str}  {self.colors.dim(snippet_line)}")

        return lines

    def render_file_update(
        self,
        file_path: str,
        added_lines: int,
        removed_lines: int,
        hunks: list[DiffHunk] | None = None,
        indent: int = 0
    ) -> list[str]:
        """Render file update with diff"""
        lines = []
        indent_str = " " * indent

        # Header
        symbol = self.symbols.status("running")
        header = f"{indent_str}{self.colors.yellow(symbol)} {self.colors.bold(f'Update({file_path})')}"
        lines.append(header)

        # Summary
        connector = self.symbols.get("⎿")
        summary = f"Added {added_lines} lines, removed {removed_lines} lines"
        lines.append(f"{indent_str}  {self.colors.dim(connector)}  {self.colors.dim(summary)}")

        # Diff hunks
        if hunks:
            for hunk in hunks:
                lines.extend(self._render_diff_hunk(hunk, indent + 4))

        return lines

    def _render_diff_hunk(self, hunk: DiffHunk, indent: int) -> list[str]:
        """Render a single diff hunk"""
        lines = []
        indent_str = " " * indent

        # Context before
        for line_num, content in hunk.context_before:
            lines.append(self._render_diff_line(line_num, content, "context", indent))

        # Removed lines
        for line_num, content in hunk.removed:
            lines.append(self._render_diff_line(line_num, content, "remove", indent))

        # Added lines
        for line_num, content in hunk.added:
            lines.append(self._render_diff_line(line_num, content, "add", indent))

        # Context after
        for line_num, content in hunk.context_after:
            lines.append(self._render_diff_line(line_num, content, "context", indent))

        return lines

    def _render_diff_line(
        self,
        line_num: int,
        content: str,
        change_type: str,
        indent: int
    ) -> str:
        """Render a single diff line"""
        indent_str = " " * indent

        # Line number (right-aligned in 6 chars)
        line_num_str = self.layout.align_right(str(line_num), 6)
        line_num_styled = self.colors.dim(self.colors.cyan(line_num_str))

        # Content with prefix
        if change_type == "add":
            prefix = "+"
            content_styled = self.colors.green(f"{prefix}{content}")
        elif change_type == "remove":
            prefix = "-"
            content_styled = self.colors.red(f"{prefix}{content}")
        else:
            prefix = " "
            content_styled = self.colors.dim(f"{prefix}{content}")

        return f"{indent_str}{line_num_styled} {content_styled}"
