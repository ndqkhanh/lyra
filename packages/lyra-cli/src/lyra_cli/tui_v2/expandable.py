"""Expandable content blocks for Lyra TUI v2.

Provides Claude Code-style expandable/collapsible content with ctrl+o keybinding.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class ExpandableBlock:
    """Represents a collapsible content block.

    Attributes:
        id: Unique identifier for this block
        summary: Brief summary shown when collapsed
        details: Full content shown when expanded
        expanded: Current expansion state
        block_type: Type of content (tool, agent, search, etc.)
    """
    id: str
    summary: str
    details: str
    expanded: bool = False
    block_type: Literal["tool", "agent", "search", "file", "general"] = "general"

    def toggle(self) -> None:
        """Toggle expansion state."""
        self.expanded = not self.expanded

    def render(self) -> str:
        """Render the block based on current state.

        Returns:
            Formatted string with Rich markup
        """
        if self.expanded:
            return self.details
        else:
            return f"{self.summary} [dim](ctrl+o to expand)[/]"


class ExpandableBlockManager:
    """Manages expandable blocks in the TUI."""

    def __init__(self):
        self._blocks: dict[str, ExpandableBlock] = {}
        self._block_order: list[str] = []
        self._current_index: int = -1

    def add_block(self, block: ExpandableBlock) -> None:
        """Add a new expandable block."""
        self._blocks[block.id] = block
        self._block_order.append(block.id)
        self._current_index = len(self._block_order) - 1

    def toggle_current(self) -> ExpandableBlock | None:
        """Toggle the most recent block."""
        if self._current_index >= 0 and self._current_index < len(self._block_order):
            block_id = self._block_order[self._current_index]
            block = self._blocks.get(block_id)
            if block:
                block.toggle()
                return block
        return None

    def toggle_by_id(self, block_id: str) -> ExpandableBlock | None:
        """Toggle a specific block by ID."""
        block = self._blocks.get(block_id)
        if block:
            block.toggle()
            return block
        return None

    def get_block(self, block_id: str) -> ExpandableBlock | None:
        """Get a block by ID."""
        return self._blocks.get(block_id)

    def get_all_blocks(self) -> list[ExpandableBlock]:
        """Get all blocks in order."""
        return [self._blocks[bid] for bid in self._block_order if bid in self._blocks]

    def clear(self) -> None:
        """Clear all blocks."""
        self._blocks.clear()
        self._block_order.clear()
        self._current_index = -1


def create_tool_block(tool_name: str, summary: str, full_output: str) -> ExpandableBlock:
    """Create an expandable block for tool output.

    Example:
        Searched for 2 patterns, read 1 file (ctrl+o to expand)
        [Press Ctrl+O]
        → Full details appear

    Args:
        tool_name: Name of the tool (e.g., "Bash", "Read", "Web Search")
        summary: Brief summary of what the tool did
        full_output: Complete tool output

    Returns:
        ExpandableBlock configured for tool output
    """
    block_id = f"tool_{tool_name}_{id(full_output)}"
    return ExpandableBlock(
        id=block_id,
        summary=f"⎿  {tool_name}: {summary}",
        details=f"⎿  {tool_name}: {summary}\n{full_output}",
        block_type="tool",
    )


def create_agent_block(agent_count: int, agent_details: str) -> ExpandableBlock:
    """Create an expandable block for parallel agents.

    Example:
        Running 4 agents… (ctrl+o to expand)
        [Press Ctrl+O]
        → Shows tree with all agents

    Args:
        agent_count: Number of agents running
        agent_details: Full agent tree display

    Returns:
        ExpandableBlock configured for agent display
    """
    block_id = f"agents_{agent_count}_{id(agent_details)}"
    return ExpandableBlock(
        id=block_id,
        summary=f"⏺ Running {agent_count} agents…",
        details=agent_details,
        block_type="agent",
    )


def create_search_block(query_count: int, results_summary: str, full_results: str) -> ExpandableBlock:
    """Create an expandable block for search results.

    Args:
        query_count: Number of search queries
        results_summary: Brief summary of results
        full_results: Complete search results

    Returns:
        ExpandableBlock configured for search results
    """
    block_id = f"search_{query_count}_{id(full_results)}"
    return ExpandableBlock(
        id=block_id,
        summary=f"⎿  Searched {query_count} queries: {results_summary}",
        details=full_results,
        block_type="search",
    )


__all__ = [
    "ExpandableBlock",
    "ExpandableBlockManager",
    "create_tool_block",
    "create_agent_block",
    "create_search_block",
]
