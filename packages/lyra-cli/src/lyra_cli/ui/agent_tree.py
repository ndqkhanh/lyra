"""Agent tree display - Hierarchical agent status with collapse/expand"""

from dataclasses import dataclass

from .colors import ColorEngine
from .symbols import SymbolRegistry


@dataclass
class AgentNode:
    """Agent node in tree"""
    agent_id: str
    name: str
    status: str  # running, completed, failed
    tool_count: int = 0
    tokens: int = 0
    latest_tool: str | None = None
    parent_id: str | None = None


class AgentTree:
    """Hierarchical agent display with collapse/expand

    Implements Claude Code-style agent tree:
    - Collapsed: ⏺ Running 4 agents… (ctrl+o to expand)
    - Expanded: Tree with box-drawing characters
    """

    def __init__(self):
        self.agents: dict[str, AgentNode] = {}
        self.expanded = False
        self.symbols = SymbolRegistry()
        self.colors = ColorEngine()

    def add_agent(
        self,
        agent_id: str,
        name: str,
        parent_id: str | None = None
    ) -> None:
        """Add agent to tree

        Args:
            agent_id: Unique agent ID
            name: Agent name/description
            parent_id: Parent agent ID (for nested agents)
        """
        self.agents[agent_id] = AgentNode(
            agent_id=agent_id,
            name=name,
            status="running",
            parent_id=parent_id
        )

    def update_agent(
        self,
        agent_id: str,
        status: str | None = None,
        tool_count: int | None = None,
        tokens: int | None = None,
        latest_tool: str | None = None
    ) -> None:
        """Update agent status

        Args:
            agent_id: Agent ID
            status: New status
            tool_count: Tool count
            tokens: Token count
            latest_tool: Latest tool call
        """
        if agent_id not in self.agents:
            return

        agent = self.agents[agent_id]
        if status is not None:
            agent.status = status
        if tool_count is not None:
            agent.tool_count = tool_count
        if tokens is not None:
            agent.tokens = tokens
        if latest_tool is not None:
            agent.latest_tool = latest_tool

    def toggle_expand(self) -> None:
        """Toggle expand/collapse state"""
        self.expanded = not self.expanded

    def render(self) -> str:
        """Render agent tree

        Returns:
            Formatted tree string
        """
        if not self.agents:
            return ""

        if not self.expanded:
            return self._render_collapsed()

        return self._render_expanded()

    def _render_collapsed(self) -> str:
        """Render collapsed state"""
        running_count = sum(
            1 for agent in self.agents.values()
            if agent.status == "running"
        )

        symbol = self.symbols.status("running")
        hint = self.colors.dim("(ctrl+o to expand)")

        if running_count == 0:
            return ""

        return f"{self.colors.yellow(symbol)} Running {running_count} agents… {hint}"

    def _render_expanded(self) -> str:
        """Render expanded state"""
        lines = []

        # Header
        symbol = self.symbols.status("running")
        hint = self.colors.dim("(ctrl+o to collapse)")
        lines.append(f"{self.colors.yellow(symbol)} Running agents… {hint}")

        # Get root agents (no parent)
        root_agents = [
            agent for agent in self.agents.values()
            if agent.parent_id is None
        ]

        # Render each agent
        for i, agent in enumerate(root_agents):
            is_last = (i == len(root_agents) - 1)
            lines.extend(self._render_agent_node(agent, is_last, 0))

        return "\n".join(lines)

    def _render_agent_node(
        self,
        agent: AgentNode,
        is_last: bool,
        depth: int
    ) -> list[str]:
        """Render single agent node

        Args:
            agent: Agent node
            is_last: Whether this is the last sibling
            depth: Tree depth

        Returns:
            List of formatted lines
        """
        lines = []

        # Indent
        indent = "   " * depth

        # Connector
        if depth == 0:
            connector = ""
        else:
            connector = self.colors.dim("└" if is_last else "├")

        # Status symbol
        if agent.status == "running":
            self.symbols.status("running")
        elif agent.status == "completed":
            self.symbols.get("✓")
        else:
            self.symbols.get("✗")

        # Agent line
        line = f"{indent}{connector} {agent.name} · "
        line += f"{agent.tool_count} tool uses · "
        line += f"{agent.tokens:,} tokens"

        lines.append(line)

        # Latest tool
        if agent.latest_tool:
            tool_indent = "   " * (depth + 1)
            if not is_last and depth > 0:
                tool_indent = "   " * depth + self.colors.dim("│") + "  "

            tool_symbol = self.colors.dim(self.symbols.get("⎿"))
            tool_line = f"{tool_indent}{tool_symbol}  {agent.latest_tool}"
            lines.append(tool_line)

        return lines

    def get_running_count(self) -> int:
        """Get count of running agents"""
        return sum(
            1 for agent in self.agents.values()
            if agent.status == "running"
        )

    def clear(self) -> None:
        """Clear all agents"""
        self.agents.clear()
