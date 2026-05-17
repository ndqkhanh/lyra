"""Expandable tool output with ctrl+o hints."""
from typing import Optional


class ExpandableToolOutput:
    """Tool output that can be expanded/collapsed.

    Example (collapsed):
    ⎿  Searching for 1 pattern, reading 1 file… (ctrl+o to expand)

    Example (expanded):
    ⎿  $ grep -r "tool_use" packages/
       packages/lyra-cli/src/lyra_cli/cli/agent_integration.py:    tool_use
       packages/lyra-cli/src/lyra_cli/eager_tools/executor.py:    tool_use
    """

    def __init__(self, tool_name: str, output: str, block_id: Optional[str] = None):
        self.tool_name = tool_name
        self.output = output
        self.expanded = False
        self.block_id = block_id or f"tool_{id(self)}"

    def toggle(self) -> None:
        """Toggle expansion state."""
        self.expanded = not self.expanded

    def render(self, max_lines: int = 20) -> str:
        """Render tool output (collapsed or expanded).

        Args:
            max_lines: Maximum lines to show when expanded

        Returns:
            Formatted tool output string
        """
        if not self.expanded:
            return self.render_collapsed()
        return self.render_expanded(max_lines)

    def render_collapsed(self) -> str:
        """Render collapsed view with hint."""
        summary = self._summarize_output()
        return f"⎿  {summary} (ctrl+o to expand)"

    def render_expanded(self, max_lines: int = 20) -> str:
        """Render full output.

        Args:
            max_lines: Maximum lines to display

        Returns:
            Formatted expanded output
        """
        lines = self.output.split("\n")

        # Truncate if too long
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines.append("... (truncated)")

        # Indent each line
        formatted_lines = [f"   {line}" for line in lines]

        # Add header
        header = f"⎿  {self.tool_name} output (ctrl+o to collapse):"
        return header + "\n" + "\n".join(formatted_lines)

    def _summarize_output(self) -> str:
        """Create one-line summary of tool output."""
        lines = self.output.split("\n")

        # Single line output - show it directly
        if len(lines) == 1:
            text = lines[0].strip()
            if len(text) <= 80:
                return text
            return text[:77] + "..."

        # Multi-line output - show summary
        non_empty_lines = [l for l in lines if l.strip()]
        return f"{self.tool_name} ({len(non_empty_lines)} lines)"


class ExpandableBlockManager:
    """Manages expandable blocks with ctrl+o toggle."""

    def __init__(self):
        self.blocks: dict[str, ExpandableToolOutput] = {}
        self.current_block_id: Optional[str] = None

    def add_block(self, block: ExpandableToolOutput) -> None:
        """Register an expandable block."""
        self.blocks[block.block_id] = block

    def toggle_current(self) -> None:
        """Toggle the current block."""
        if self.current_block_id and self.current_block_id in self.blocks:
            self.blocks[self.current_block_id].toggle()

    def toggle_block(self, block_id: str) -> None:
        """Toggle a specific block."""
        if block_id in self.blocks:
            self.blocks[block_id].toggle()

    def set_current(self, block_id: str) -> None:
        """Set the current block for ctrl+o toggle."""
        self.current_block_id = block_id

    def render_all(self) -> str:
        """Render all blocks."""
        if not self.blocks:
            return ""

        lines = []
        for block in self.blocks.values():
            lines.append(block.render())

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all blocks."""
        self.blocks.clear()
        self.current_block_id = None
