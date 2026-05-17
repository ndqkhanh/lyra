"""Hierarchical output formatter for Lyra TUI v2.

Provides Claude Code-style hierarchical tree display with proper indentation,
tree glyphs (├ │ └ ⎿), and nested structure for operations, agents, and tasks.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class HierarchicalNode:
    """Represents a node in the hierarchical tree.

    Attributes:
        content: The text content to display
        level: Indentation level (0 = root)
        is_last: Whether this is the last child at this level
        node_type: Type of node (operation, agent, tool, task, tip)
        children: Child nodes
        metadata: Optional metadata (tokens, time, status, etc.)
    """
    content: str
    level: int = 0
    is_last: bool = False
    node_type: Literal["operation", "agent", "tool", "task", "tip", "detail"] = "detail"
    children: list[HierarchicalNode] | None = None
    metadata: dict | None = None

    def render(self, parent_pipes: list[bool] | None = None) -> str:
        """Render this node and its children with proper tree glyphs.

        Args:
            parent_pipes: List of booleans indicating which levels need pipes

        Returns:
            Formatted string with tree structure
        """
        if parent_pipes is None:
            parent_pipes = []

        lines = []

        # Build prefix with tree glyphs
        prefix = self._build_prefix(parent_pipes)

        # Format content based on node type
        formatted_content = self._format_content()

        lines.append(f"{prefix}{formatted_content}")

        # Render children
        if self.children:
            for i, child in enumerate(self.children):
                child_is_last = i == len(self.children) - 1
                child.is_last = child_is_last

                # Update parent_pipes for children
                new_pipes = parent_pipes + [not self.is_last]
                lines.append(child.render(new_pipes))

        return "\n".join(lines)

    def _build_prefix(self, parent_pipes: list[bool]) -> str:
        """Build the prefix with tree glyphs."""
        if self.level == 0:
            return ""

        prefix_parts = []

        # Add pipes for parent levels
        for needs_pipe in parent_pipes[:-1]:
            if needs_pipe:
                prefix_parts.append("│ ")
            else:
                prefix_parts.append("  ")

        # Add branch glyph for this level
        if self.level > 0:
            if self.is_last:
                prefix_parts.append("└ ")
            else:
                prefix_parts.append("├ ")

        return "".join(prefix_parts)

    def _format_content(self) -> str:
        """Format content based on node type and metadata."""
        if self.node_type == "operation":
            # Format: ⏺ Operation name
            return f"[green]⏺[/] {self.content}"

        elif self.node_type == "agent":
            # Format: agent-type · N tool uses · X tokens
            meta = self.metadata or {}
            tool_uses = meta.get("tool_uses", 0)
            tokens = meta.get("tokens", 0)
            elapsed = meta.get("elapsed", "")

            parts = [self.content]
            if tool_uses:
                parts.append(f"{tool_uses} tool uses")
            if tokens:
                parts.append(f"{self._humanize_tokens(tokens)} tokens")
            if elapsed:
                parts.append(elapsed)

            return " · ".join(parts)

        elif self.node_type == "tool":
            # Format: ⎿  Tool: description
            return f"[dim]⎿[/]  {self.content}"

        elif self.node_type == "task":
            # Format: ⎿  ◻ Task name
            meta = self.metadata or {}
            status = meta.get("status", "pending")
            checkbox = {"pending": "◻", "in_progress": "◼", "completed": "✓"}[status]
            color = {"pending": "dim", "in_progress": "yellow", "completed": "green"}[status]

            return f"[dim]⎿[/]  [{color}]{checkbox} {self.content}[/]"

        elif self.node_type == "tip":
            # Format: ⎿  Tip: content
            return f"[dim]⎿[/]  Tip: {self.content}"

        else:
            # Default: just content
            return self.content

    @staticmethod
    def _humanize_tokens(n: int) -> str:
        """Humanize token count."""
        if n < 1_000:
            return str(n)
        if n < 1_000_000:
            return f"{n / 1_000:.1f}k"
        return f"{n / 1_000_000:.1f}M"


def create_operation_tree(
    operation_name: str,
    agents: list[dict],
    expandable: bool = True,
) -> HierarchicalNode:
    """Create a hierarchical tree for an operation with agents.

    Example output:
        ⏺ Running 4 agents… (ctrl+o to expand)
           ├ executor · 12 tool uses · 46.8k tokens
           │ ⎿  Done
           ├ researcher · 26 tool uses · 54.3k tokens
           │ ⎿  Web Search: topic…
           └ planner · 13 tool uses · 42.2k tokens
             ⎿  Write: file.py

    Args:
        operation_name: Name of the operation
        agents: List of agent dicts with name, tool_uses, tokens, current_op
        expandable: Whether to show (ctrl+o to expand)

    Returns:
        HierarchicalNode representing the tree
    """
    # Root operation node
    content = f"Running {len(agents)} agents…"
    if expandable:
        content += " [dim](ctrl+o to expand)[/]"

    root = HierarchicalNode(
        content=content,
        level=0,
        node_type="operation",
    )

    # Add agent children
    root.children = []
    for agent in agents:
        agent_node = HierarchicalNode(
            content=agent.get("name", "agent"),
            level=1,
            node_type="agent",
            metadata={
                "tool_uses": agent.get("tool_uses", 0),
                "tokens": agent.get("tokens", 0),
                "elapsed": agent.get("elapsed", ""),
            },
        )

        # Add current operation as child
        current_op = agent.get("current_op")
        if current_op:
            op_node = HierarchicalNode(
                content=current_op,
                level=2,
                node_type="tool",
            )
            agent_node.children = [op_node]

        root.children.append(agent_node)

    return root


def create_task_tree(tasks: list[dict], max_visible: int = 5) -> HierarchicalNode:
    """Create a hierarchical tree for tasks.

    Example output:
        ⎿  ◻ Phase 9: Production Readiness
           ◻ Phase 3: Implement Research Pipeline
           ◼ Phase 6: Interactive UI & Themes
           ✓ Phase 5: Memory Systems
           ✓ Phase 2: Integrate Real Agent Loop
            … +3 pending

    Args:
        tasks: List of task dicts with name, status, depth
        max_visible: Maximum tasks to show

    Returns:
        HierarchicalNode representing the tree
    """
    root = HierarchicalNode(content="", level=0)
    root.children = []

    for i, task in enumerate(tasks[:max_visible]):
        task_node = HierarchicalNode(
            content=task.get("name", "Task"),
            level=task.get("depth", 0),
            node_type="task",
            metadata={"status": task.get("status", "pending")},
        )
        root.children.append(task_node)

    # Add remaining count
    remaining = len(tasks) - max_visible
    if remaining > 0:
        remaining_node = HierarchicalNode(
            content=f"[dim]… +{remaining} pending[/]",
            level=0,
        )
        root.children.append(remaining_node)

    return root


def create_tool_output_tree(
    tool_name: str,
    summary: str,
    details: list[str] | None = None,
) -> HierarchicalNode:
    """Create a hierarchical tree for tool output.

    Example output:
        ⎿  Searched for 2 patterns, read 1 file (ctrl+o to expand)

    Or expanded:
        ⎿  Searched for 2 patterns, read 1 file
           Pattern 1: found in file.py
           Pattern 2: found in test.py
           Read: config.json (150 lines)

    Args:
        tool_name: Name of the tool
        summary: Brief summary
        details: Optional list of detail lines

    Returns:
        HierarchicalNode representing the tree
    """
    content = f"{tool_name}: {summary}"
    if details:
        content += " [dim](ctrl+o to expand)[/]"

    root = HierarchicalNode(
        content=content,
        level=0,
        node_type="tool",
    )

    if details:
        root.children = [
            HierarchicalNode(content=detail, level=1)
            for detail in details
        ]

    return root


__all__ = [
    "HierarchicalNode",
    "create_operation_tree",
    "create_task_tree",
    "create_tool_output_tree",
]
