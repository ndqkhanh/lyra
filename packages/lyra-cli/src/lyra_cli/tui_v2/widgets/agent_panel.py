"""Display parallel agent execution like Claude Code."""
from typing import Dict, Optional
from dataclasses import dataclass, field
import time


@dataclass
class AgentStatus:
    """Status of a running agent."""
    description: str
    tool_uses: int = 0
    tokens: int = 0
    status: str = "running"  # running, done, error
    last_action: str = ""
    start_time: float = field(default_factory=time.time)


class AgentExecutionPanel:
    """Shows running agents with live status.

    Example output:
    ⏺ Running 4 agents… (ctrl+o to expand)
       ├ oh-my-claudecode:executor (Wave A) · 12 tool uses · 46.8k tokens
       │ ⎿  Done
       ├ oh-my-claudecode:executor (Wave C) · 26 tool uses · 54.3k tokens
       │ ⎿  Read agent output: b62lxay8a
       ├ oh-my-claudecode:executor (Wave D+E) · 13 tool uses · 42.2k tokens
       │ ⎿  Write: src/lyra_cli/interactive/skills_lifecycle.py
       └ oh-my-claudecode:executor (Wave F+G) · 16 tool uses · 61.6k tokens
          ⎿  Searching for 1 pattern, reading 13 files…
    """

    def __init__(self):
        self.agents: Dict[str, AgentStatus] = {}

    def add_agent(self, agent_id: str, description: str) -> None:
        """Register new agent."""
        self.agents[agent_id] = AgentStatus(description=description)

    def update_agent(
        self,
        agent_id: str,
        tool_uses: Optional[int] = None,
        tokens: Optional[int] = None,
        status: Optional[str] = None,
        last_action: Optional[str] = None,
    ) -> None:
        """Update agent status."""
        if agent_id not in self.agents:
            return

        agent = self.agents[agent_id]
        if tool_uses is not None:
            agent.tool_uses = tool_uses
        if tokens is not None:
            agent.tokens = tokens
        if status is not None:
            agent.status = status
        if last_action is not None:
            agent.last_action = last_action

    def remove_agent(self, agent_id: str) -> None:
        """Remove completed agent."""
        self.agents.pop(agent_id, None)

    def render(self, expanded: bool = False) -> str:
        """Render agent panel.

        Args:
            expanded: If True, show full details. If False, show collapsed view.

        Returns:
            Formatted agent panel string
        """
        if not self.agents:
            return ""

        lines = []
        agent_count = len(self.agents)

        # Header
        if expanded:
            lines.append(f"⏺ Running {agent_count} agents… (ctrl+o to collapse)")
        else:
            lines.append(f"⏺ Running {agent_count} agents… (ctrl+o to expand)")

        if not expanded:
            return "\n".join(lines)

        # Agent list
        agent_items = list(self.agents.items())
        for i, (agent_id, status) in enumerate(agent_items):
            is_last = i == len(agent_items) - 1
            prefix = "└" if is_last else "├"

            # Status icon
            if status.status == "done":
                status_icon = "✓"
            elif status.status == "error":
                status_icon = "✗"
            else:
                status_icon = "⏺"

            # Main line
            line = f"   {prefix} {status_icon} {status.description} · "
            line += f"{status.tool_uses} tool uses · "
            line += f"{status.tokens/1000:.1f}k tokens"

            # Duration
            elapsed = time.time() - status.start_time
            if elapsed < 60:
                duration_str = f"{int(elapsed)}s"
            else:
                minutes = int(elapsed // 60)
                seconds = int(elapsed % 60)
                duration_str = f"{minutes}m {seconds}s"
            line += f" · {duration_str}"

            lines.append(line)

            # Last action (if any)
            if status.last_action:
                continuation = "│" if not is_last else " "
                lines.append(f"   {continuation} ⎿  {status.last_action}")

        return "\n".join(lines)

    def get_summary(self) -> str:
        """Get one-line summary of agent activity."""
        if not self.agents:
            return ""

        total_tools = sum(a.tool_uses for a in self.agents.values())
        total_tokens = sum(a.tokens for a in self.agents.values())

        return f"{len(self.agents)} agents · {total_tools} tool uses · {total_tokens/1000:.1f}k tokens"
