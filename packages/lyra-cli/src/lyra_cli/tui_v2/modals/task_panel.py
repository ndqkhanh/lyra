"""Task panel modal for Lyra TUI.

Displays an interactive list of tasks with their status (pending, in_progress, completed).
Accessible via Ctrl+T keybinding.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Label, Static
from textual.binding import Binding


class TaskPanelModal(Static):
    """Interactive task management panel modal."""

    DEFAULT_CSS = """
    TaskPanelModal {
        align: center middle;
        width: 100%;
        height: 100%;
        background: $surface-darken-1 60%;
    }

    TaskPanelModal > Container {
        width: 70;
        height: auto;
        max-height: 25;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
    }

    TaskPanelModal .modal-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    TaskPanelModal .task-item {
        margin: 0 0 1 0;
    }

    TaskPanelModal .task-completed {
        color: $success;
    }

    TaskPanelModal .task-in-progress {
        color: $warning;
    }

    TaskPanelModal .task-pending {
        color: $text-muted;
    }

    TaskPanelModal .empty-state {
        text-align: center;
        color: $text-muted;
        margin: 2 0;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=True),
        Binding("q", "dismiss", "Close", show=False),
    ]

    def __init__(self, tasks: list[dict]) -> None:
        """Initialize task panel with task list.

        Args:
            tasks: List of task dictionaries with 'description' and 'status' keys
        """
        super().__init__()
        self.tasks = tasks

    def compose(self) -> ComposeResult:
        """Compose the task panel UI."""
        with Container():
            yield Label("Tasks", classes="modal-title")

            if not self.tasks:
                yield Label("No tasks yet", classes="empty-state")
            else:
                with VerticalScroll():
                    for task in self.tasks:
                        yield self._render_task(task)

    def _render_task(self, task: dict) -> Label:
        """Render a single task item.

        Args:
            task: Task dictionary with 'description' and 'status'

        Returns:
            Label widget with formatted task
        """
        status = task.get('status', 'pending')
        description = task.get('description', 'Unknown task')

        # Status icons matching Claude Code style
        status_icon = {
            'completed': '✓',
            'in_progress': '⏺',
            'pending': '◯',
        }.get(status, '◯')

        # CSS class for styling
        css_class = f"task-item task-{status.replace('_', '-')}"

        label_text = f"{status_icon} {description}"
        return Label(label_text, classes=css_class)

    def action_dismiss(self) -> None:
        """Close the modal."""
        self.remove()


__all__ = ["TaskPanelModal"]
