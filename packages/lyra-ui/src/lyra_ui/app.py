"""
Textual App - Main Textual application with dual-pane layout.

Features:
- Split-pane layout
- Conversation pane
- Status panel
- Keyboard navigation
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Static


class ConversationPane(Static):
    """
    Conversation pane widget.

    Features:
    - Message history
    - Scrollable content
    - Syntax highlighting
    """

    def __init__(self):
        """Initialize conversation pane."""
        super().__init__()
        self.messages = []

    def compose(self) -> ComposeResult:
        """Compose conversation pane."""
        yield Static("Conversation Pane", id="conversation-title")

    def add_message(self, role: str, content: str):
        """
        Add message to conversation.

        Args:
            role: Message role (user/assistant)
            content: Message content
        """
        self.messages.append({"role": role, "content": content})
        self.refresh()


class StatusPanel(Static):
    """
    Status panel widget.

    Features:
    - Agent status
    - Token usage
    - Progress indicators
    """

    def compose(self) -> ComposeResult:
        """Compose status panel."""
        yield Static("Status Panel", id="status-title")
        yield Static("Agent: Idle", id="agent-status")
        yield Static("Tokens: 0 / 200k", id="token-usage")
        yield Static("Context: 0%", id="context-usage")


class DualPaneLayout(Container):
    """
    Dual-pane layout container.

    Features:
    - Resizable panes
    - Conversation + status
    - Keyboard navigation
    """

    def compose(self) -> ComposeResult:
        """Compose dual-pane layout."""
        with Horizontal():
            yield ConversationPane()
            yield StatusPanel()


class LyraApp(App):
    """
    Main Lyra Textual application.

    Features:
    - Dual-pane interface
    - Keyboard shortcuts
    - Theme support
    """

    CSS = """
    Screen {
        background: $surface;
    }

    ConversationPane {
        width: 70%;
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    StatusPanel {
        width: 30%;
        height: 100%;
        border: solid $secondary;
        padding: 1;
    }

    #conversation-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    #status-title {
        text-style: bold;
        color: $secondary;
        margin-bottom: 1;
    }

    #agent-status {
        margin-bottom: 1;
    }

    #token-usage {
        margin-bottom: 1;
    }

    #context-usage {
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+w", "switch_pane", "Switch Pane"),
        ("ctrl+n", "new_chat", "New Chat"),
    ]

    def compose(self) -> ComposeResult:
        """Compose application."""
        yield Header()
        yield DualPaneLayout()
        yield Footer()

    def action_switch_pane(self):
        """Switch between panes."""
        # TODO: Implement pane switching
        pass

    def action_new_chat(self):
        """Start new chat."""
        # TODO: Implement new chat
        pass


def run_app():
    """Run Lyra Textual app."""
    app = LyraApp()
    app.run()


if __name__ == "__main__":
    run_app()
