"""SpecDrawer widget for Auto-Spec-Kit TUI integration."""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Static, Markdown
from textual.binding import Binding
from textual.message import Message


class SpecDrawer(Container):
    """Right-side drawer for spec-kit flow."""

    BINDINGS = [
        Binding("enter", "approve", "Approve", show=True),
        Binding("e", "edit", "Edit", show=True),
        Binding("r", "redraft", "Redraft", show=True),
        Binding("escape", "cancel", "Cancel", show=True),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.phase = "idle"
        self.current_draft = ""

    def compose(self) -> ComposeResult:
        """Compose the drawer layout."""
        with Vertical():
            yield Static("", id="spec-phase-title")
            yield Markdown("", id="spec-draft-content")
            yield Static("", id="spec-approval-bar")

    def update_phase(self, phase: str) -> None:
        """Update current phase."""
        self.phase = phase
        if phase == "idle":
            self.display = False
        else:
            self.display = True
            title = self.query_one("#spec-phase-title", Static)
            title.update(f"Phase: {phase}")

    def update_draft(self, content: str) -> None:
        """Update draft content."""
        self.current_draft = content
        markdown = self.query_one("#spec-draft-content", Markdown)
        markdown.update(content)

    def action_approve(self) -> None:
        """Approve current artifact."""
        self.post_message(self.Approved())

    def action_edit(self) -> None:
        """Edit current artifact."""
        self.post_message(self.EditRequested())

    def action_redraft(self) -> None:
        """Request redraft."""
        self.post_message(self.RedraftRequested())

    def action_cancel(self) -> None:
        """Cancel spec-kit flow."""
        self.post_message(self.Cancelled())

    class Approved(Message):
        """User approved the artifact."""

    class EditRequested(Message):
        """User wants to edit."""

    class RedraftRequested(Message):
        """User wants to redraft."""

    class Cancelled(Message):
        """User cancelled the flow."""
