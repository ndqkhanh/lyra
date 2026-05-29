"""Expandable content system with collapse/expand functionality"""

from dataclasses import dataclass, field

from .colors import ColorEngine
from .layout import LayoutEngine
from .symbols import SymbolRegistry


@dataclass
class ExpandableSection:
    """Expandable content section"""

    id: str
    title: str
    content: str
    collapsed: bool = True
    truncate_at: int = 20
    preserve_first: int = 5
    preserve_last: int = 3


@dataclass
class CollapseState:
    """State manager for collapsed/expanded sections"""

    states: dict[str, bool] = field(default_factory=dict)

    def is_expanded(self, section_id: str) -> bool:
        """Check if section is expanded"""
        return self.states.get(section_id, False)

    def toggle(self, section_id: str) -> bool:
        """Toggle section state, return new state"""
        current = self.is_expanded(section_id)
        self.states[section_id] = not current
        return not current

    def expand(self, section_id: str):
        """Expand section"""
        self.states[section_id] = True

    def collapse(self, section_id: str):
        """Collapse section"""
        self.states[section_id] = False

    def expand_all(self):
        """Expand all sections"""
        for section_id in self.states:
            self.states[section_id] = True

    def collapse_all(self):
        """Collapse all sections"""
        for section_id in self.states:
            self.states[section_id] = False


class TruncationEngine:
    """Engine for truncating and expanding content"""

    def __init__(self, use_colors: bool = True):
        self.colors = ColorEngine(use_colors=use_colors)
        self.layout = LayoutEngine()

    def truncate_lines(
        self, lines: list[str], max_lines: int, preserve_first: int = 5, preserve_last: int = 3
    ) -> tuple[list[str], int]:
        """
        Truncate lines with smart preservation.
        Returns (truncated_lines, hidden_count)
        """
        if len(lines) <= max_lines:
            return lines, 0

        # Calculate how many lines to hide
        hidden_count = len(lines) - max_lines

        # If we can show first + last within max_lines
        if preserve_first + preserve_last <= max_lines:
            result = []
            result.extend(lines[:preserve_first])
            result.extend(lines[-preserve_last:])
            return result, hidden_count

        # Otherwise just show first max_lines
        return lines[:max_lines], hidden_count

    def create_truncation_indicator(self, hidden_count: int, indent: int = 0) -> str:
        """Create '… +N lines' indicator"""
        indent_str = " " * indent
        indicator = f"… +{hidden_count} lines"
        return f"{indent_str}{self.colors.dim(indicator)}"

    def create_expand_hint(self, indent: int = 0) -> str:
        """Create 'ctrl+o to expand' hint"""
        indent_str = " " * indent
        hint = "(ctrl+o to expand)"
        return f"{indent_str}{self.colors.dim(hint)}"


class ExpandableRenderer:
    """Renderer for expandable content sections"""

    def __init__(self, use_colors: bool = True, use_unicode: bool = True):
        self.symbols = SymbolRegistry(use_unicode=use_unicode)
        self.colors = ColorEngine(use_colors=use_colors)
        self.truncation = TruncationEngine(use_colors=use_colors)
        self.collapse_state = CollapseState()

    def render_section(self, section: ExpandableSection, indent: int = 0) -> list[str]:
        """Render expandable section"""
        lines = []
        indent_str = " " * indent

        # Title
        title_line = f"{indent_str}{section.title}"
        lines.append(title_line)

        # Check if expanded
        is_expanded = self.collapse_state.is_expanded(section.id)

        if is_expanded:
            # Show full content
            content_lines = section.content.split("\n")
            for line in content_lines:
                lines.append(f"{indent_str}  {line}")
        else:
            # Show truncated content
            content_lines = section.content.split("\n")

            if len(content_lines) > section.truncate_at:
                # Truncate
                truncated, hidden = self.truncation.truncate_lines(
                    content_lines,
                    section.truncate_at,
                    section.preserve_first,
                    section.preserve_last,
                )

                for line in truncated:
                    lines.append(f"{indent_str}  {line}")

                # Add truncation indicator
                lines.append(self.truncation.create_truncation_indicator(hidden, indent + 2))
                lines.append(self.truncation.create_expand_hint(indent + 2))
            else:
                # Show all lines
                for line in content_lines:
                    lines.append(f"{indent_str}  {line}")

        return lines

    def render_diagnostic_summary(
        self,
        section_id: str,
        error_count: int,
        warning_count: int,
        file_count: int,
        diagnostics: list[dict] | None = None,
        indent: int = 0,
    ) -> list[str]:
        """Render diagnostic issues with collapse/expand"""
        lines = []
        indent_str = " " * indent
        connector = self.symbols.get("⎿")

        # Summary line
        is_expanded = self.collapse_state.is_expanded(section_id)
        expand_hint = "" if is_expanded else " (ctrl+o to expand)"

        summary =(
            f"Found {self.colors.red(str(error_count))} errors, "
            f"{self.colors.yellow(str(warning_count))} warnings in {file_count} file(s)"
            f"{self.colors.dim(expand_hint)}"
        )
        lines.append(f"{indent_str}{self.colors.dim(connector)}  {summary}")

        # If expanded, show diagnostics
        if is_expanded and diagnostics:
            for diag in diagnostics:
                severity = diag.get("severity", "error")
                file_path = diag.get("file", "")
                line_num = diag.get("line", 0)
                message = diag.get("message", "")

                # Color by severity
                if severity == "error":
                    severity_icon = self.colors.red("✗")
                elif severity == "warning":
                    severity_icon = self.colors.yellow("⚠")
                else:
                    severity_icon = self.colors.cyan("ℹ")

                location = f"{file_path}:{line_num}"
                diag_line = (
                    f"{indent_str}  {severity_icon} {self.colors.cyan(location)} - {message}"
                )
                lines.append(diag_line)

        return lines

    def render_compaction_event(
        self,
        section_id: str,
        files_read: list[tuple[str, int]],
        files_referenced: list[str],
        skills_restored: list[str],
        indent: int = 0,
    ) -> list[str]:
        """Render conversation compaction event"""
        lines = []
        indent_str = " " * indent
        connector = self.symbols.get("⎿")

        # Header
        symbol = self.symbols.get("✻")
        is_expanded = self.collapse_state.is_expanded(section_id)
        expand_hint = " (ctrl+o for history)" if not is_expanded else ""

        header = (
            f"{self.colors.yellow(symbol)} Conversation compacted{self.colors.dim(expand_hint)}"
        )
        lines.append(f"{indent_str}{header}")

        # Always show summary items
        for file_path, line_count in files_read:
            item = f"Read {self.colors.cyan(file_path)} ({line_count} lines)"
            lines.append(f"{indent_str}{self.colors.dim(connector)}  {item}")

        for file_path in files_referenced:
            item = f"Referenced file {self.colors.cyan(file_path)}"
            lines.append(f"{indent_str}{self.colors.dim(connector)}  {item}")

        if skills_restored:
            skills_str = ", ".join(skills_restored)
            item = f"Skills restored ({self.colors.green(skills_str)})"
            lines.append(f"{indent_str}{self.colors.dim(connector)}  {item}")

        # If expanded, show additional details
        if is_expanded:
            lines.append(

                    f"{indent_str}{self.colors.dim(connector)}  "
                    f"{self.colors.dim('Full compaction history:')}"

            )
            lines.append(f"{indent_str}    {self.colors.dim('- Original size: 150,000 tokens')}")
            lines.append(f"{indent_str}    {self.colors.dim('- Compacted size: 45,000 tokens')}")
            lines.append(f"{indent_str}    {self.colors.dim('- Savings: 70%')}")

        return lines
