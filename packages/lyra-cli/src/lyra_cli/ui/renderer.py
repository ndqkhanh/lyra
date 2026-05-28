"""Unified rendering system for Claude Code-style UI patterns"""

from dataclasses import dataclass

from .colors import ColorEngine
from .layout import LayoutConfig, LayoutEngine
from .symbols import SymbolRegistry


@dataclass(frozen=True)
class ResponseSection:
    """Immutable response section for hierarchical display"""
    title: str
    content: str
    level: int = 0
    expandable: bool = False
    line_numbers: bool = False
    language: str | None = None


class LyraUIRenderer:
    """Claude Code-style response formatter for Lyra"""

    def __init__(
        self,
        use_colors: bool = True,
        use_unicode: bool = True,
        config: LayoutConfig | None = None
    ):
        self.symbols = SymbolRegistry(use_unicode=use_unicode)
        self.colors = ColorEngine(use_colors=use_colors)
        self.layout = LayoutEngine(config=config)

    def render_box(
        self,
        content: str,
        title: str = "",
        width: int = 80,
        two_column: bool = False
    ) -> str:
        """Render box-drawn panel (welcome screen, dialogs)"""
        lines = []

        # Top border
        top_left = self.symbols.box("top_left")
        top_right = self.symbols.box("top_right")
        horizontal = self.symbols.box("horizontal")

        if title:
            title_text = f" {title} "
            title_width = self.layout.measure_visual_width(title_text)
            remaining = width - title_width - 2
            left_border = horizontal * 3
            right_border = horizontal * remaining
            top_line = f"{top_left}{left_border}{title_text}{right_border}{top_right}"
        else:
            top_line = f"{top_left}{horizontal * (width - 2)}{top_right}"

        lines.append(self.colors.dim(top_line))

        # Content
        vertical = self.symbols.box("vertical")
        content_lines = content.split("\n")

        for line in content_lines:
            # Pad line to width
            padded = self.layout.pad_to_width(line, width - 4, align="left")
            lines.append(f"{self.colors.dim(vertical)} {padded} {self.colors.dim(vertical)}")

        # Bottom border
        bottom_left = self.symbols.box("bottom_left")
        bottom_right = self.symbols.box("bottom_right")
        bottom_line = f"{bottom_left}{horizontal * (width - 2)}{bottom_right}"
        lines.append(self.colors.dim(bottom_line))

        return "\n".join(lines)

    def render_status(
        self,
        message: str,
        elapsed_seconds: int | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        phase: str | None = None
    ) -> str:
        """Render status line with time/tokens/phase"""
        symbol = self.symbols.status("thinking")
        parts = [f"{self.colors.yellow(symbol)} {message}"]

        metrics = []
        if elapsed_seconds is not None:
            time_str = self.layout.format_time(elapsed_seconds)
            metrics.append(time_str)

        if tokens_in is not None:
            upload = self.symbols.get("↑")
            token_str = self.layout.format_token_count(tokens_in)
            metrics.append(f"{upload} {token_str}")

        if tokens_out is not None:
            download = self.symbols.get("↓")
            token_str = self.layout.format_token_count(tokens_out)
            metrics.append(f"{download} {token_str}")

        if phase:
            metrics.append(phase)

        if metrics:
            metrics_str = " · ".join(metrics)
            parts.append(f"({self.colors.dim(metrics_str)})")

        return " ".join(parts)

    def render_tree_node(
        self,
        content: str,
        is_last: bool = False,
        indent_level: int = 0,
        has_children: bool = False
    ) -> str:
        """Render a single tree node with proper connectors"""
        indent = "  " * indent_level

        if indent_level == 0:
            # Root node
            symbol = self.symbols.status("running")
            return f"{self.colors.yellow(symbol)} {content}"

        # Child node
        connector = self.symbols.get("└" if is_last else "├")
        line = self.symbols.get("─")

        return f"{indent}{self.colors.dim(connector)}{self.colors.dim(line)} {content}"

    def render_tool_result(self, content: str, indent_level: int = 1) -> str:
        """Render tool result with connector"""
        indent = "  " * indent_level
        connector = self.symbols.get("⎿")
        return f"{indent}{self.colors.dim(connector)}  {content}"

    def render_file_update(
        self,
        file_path: str,
        added_lines: int,
        removed_lines: int
    ) -> str:
        """Render file update summary"""
        symbol = self.symbols.status("running")
        summary = f"Added {added_lines} lines, removed {removed_lines} lines"

        lines = [
            f"{self.colors.yellow(symbol)} {self.colors.bold(f'Update({file_path})')}",
            f"  {self.colors.dim(self.symbols.get('⎿'))}  {self.colors.dim(summary)}"
        ]

        return "\n".join(lines)

    def render_diff_line(
        self,
        line_num: int,
        content: str,
        change_type: str = "context"
    ) -> str:
        """Render a single diff line with line number"""
        # Right-align line number in 6-char column
        line_num_str = self.layout.align_right(str(line_num), 6)

        if change_type == "add":
            prefix = "+"
            styled_content = self.colors.green(f"{prefix}{content}")
        elif change_type == "remove":
            prefix = "-"
            styled_content = self.colors.red(f"{prefix}{content}")
        else:
            prefix = " "
            styled_content = self.colors.dim(f"{prefix}{content}")

        return f"     {self.colors.dim(self.colors.cyan(line_num_str))} {styled_content}"

    def render_diagnostic_summary(
        self,
        error_count: int,
        file_count: int,
        collapsed: bool = True
    ) -> str:
        """Render diagnostic issues summary"""
        connector = self.symbols.get("⎿")
        expand_hint = "(ctrl+o to expand)" if collapsed else ""

        summary = f"Found {self.colors.red(str(error_count))} new diagnostic issues in {file_count} file(s)"

        if expand_hint:
            summary += f" {self.colors.dim(expand_hint)}"

        return f"  {self.colors.dim(connector)}  {self.colors.yellow(summary)}"

    def render_separator(self, width: int = 80) -> str:
        """Render horizontal separator"""
        return self.colors.dim(self.layout.create_separator(width))

    def render_agent_status(
        self,
        agent_type: str,
        task: str,
        elapsed_seconds: int,
        is_main: bool = False
    ) -> str:
        """Render agent status line"""
        symbol = self.symbols.status("running" if is_main else "idle")
        time_str = self.layout.format_time(elapsed_seconds)

        # Truncate task if too long
        max_task_width = 60
        truncated_task = self.layout.truncate_text(task, max_task_width)

        if is_main:
            return f"  {self.colors.yellow(symbol)} {self.colors.bold(agent_type)}"
        else:
            # Pad task to align time on right
            padded_task = self.layout.pad_to_width(truncated_task, max_task_width)
            return f"  {self.colors.dim(symbol)} {self.colors.dim(agent_type)}  {padded_task}  {self.colors.dim(self.colors.cyan(time_str))}"
