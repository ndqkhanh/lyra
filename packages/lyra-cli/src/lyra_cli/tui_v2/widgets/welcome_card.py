"""Welcome card widget (FR-001)."""

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static
from textual.containers import Grid


class WelcomeCard(Widget):
    """Collapsible welcome card shown on launch."""

    DEFAULT_CSS = """
    WelcomeCard {
        height: auto;
        margin: 1;
    }

    WelcomeCard.collapsed {
        height: 1;
    }

    WelcomeCard Grid {
        grid-size: 2;
        grid-columns: 1fr 1fr;
    }

    @media (max-width: 80) {
        WelcomeCard Grid {
            grid-size: 1;
            grid-columns: 1fr;
        }
    }
    """

    model: reactive[str] = reactive("claude-sonnet-4-6")
    cwd: reactive[str] = reactive("")
    account: reactive[str] = reactive("")
    expanded: reactive[bool] = reactive(True)

    def compose(self) -> ComposeResult:
        if self.expanded:
            yield Grid(
                Static(self._render_left(), id="welcome-left"),
                Static(self._render_right(), id="welcome-right"),
            )
        else:
            yield Static(self._render_collapsed(), id="welcome-collapsed")

    def _render_left(self) -> str:
        return f"""
    ╭─────────────────╮
    │   🌟 Lyra 🌟   │
    │  Deep Research  │
    │   AI Agent      │
    ╰─────────────────╯

Welcome back, {self.account or 'User'}!
        """.strip()

    def _render_right(self) -> str:
        cwd_display = self._truncate_path(self.cwd, 40)
        return f"""
[bold]Current Session[/bold]
• Model: {self.model}
• Directory: {cwd_display}

[bold]Quick Tips[/bold]
• [cyan]Ctrl+P[/cyan] command palette
• [cyan]/model[/cyan] switch models
• [cyan]Ctrl+O[/cyan] expand output
• [cyan]Esc[/cyan] interrupt
        """.strip()

    def _render_collapsed(self) -> str:
        cwd_display = self._truncate_path(self.cwd, 30)
        return f"🌟 Lyra | {self.model} | {cwd_display}"

    def _truncate_path(self, path: str, max_length: int) -> str:
        if len(path) <= max_length:
            return path
        parts = path.split("/")
        if len(parts) <= 2:
            return path[:max_length - 3] + "..."
        return f"{parts[0]}/.../{parts[-1]}"

    def on_input_submitted(self) -> None:
        if self.expanded:
            self.expanded = False
            self.remove_class("expanded")
            self.add_class("collapsed")

    def watch_expanded(self, expanded: bool) -> None:
        self.refresh(layout=True)
