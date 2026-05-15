"""AgentsTab — live subagent monitoring sidebar widget."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class AgentsTab(Widget):
    DEFAULT_CSS = """
    AgentsTab {
        height: auto;
        padding: 1;
    }
    AgentsTab .agents-empty {
        color: $fg_muted;
        text-style: italic;
    }
    AgentsTab .agent-row {
        color: $fg;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("No active subagents", classes="agents-empty", id="agents-content")

    def refresh_agents(self, agents: list[dict]) -> None:
        content = self.query_one("#agents-content", Static)
        if not agents:
            content.update("No active subagents")
            return
        lines = []
        for a in agents:
            state = a.get("state", "?")
            name = a.get("name", "agent")
            lines.append(f"· [{state}] {name}")
        content.update("\n".join(lines))
