"""Background task switcher modal (FR-012)."""

from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import ListView, ListItem, Label
from textual.binding import Binding


class BackgroundSwitcherModal(ModalScreen[str | None]):
    """Modal for switching between background tasks."""

    BINDINGS = [
        Binding("escape", "dismiss(None)", "Cancel"),
        Binding("enter", "select", "Select"),
    ]

    DEFAULT_CSS = """
    BackgroundSwitcherModal {
        align: center middle;
    }

    BackgroundSwitcherModal > ListView {
        width: 80;
        height: 20;
        border: solid $accent;
    }
    """

    def __init__(self, background_tasks: dict):
        super().__init__()
        self.background_tasks = background_tasks

    def compose(self) -> ComposeResult:
        items = []
        for task_id, task in self.background_tasks.items():
            label = self._render_task(task)
            items.append(ListItem(Label(label), id=task_id))

        yield ListView(*items)

    def _render_task(self, task: dict) -> str:
        status_glyph = {
            "running": "⏵",
            "done": "✓",
            "failed": "✗",
            "cancelled": "⊗",
        }.get(task["status"], "?")

        elapsed = self._format_elapsed(task["started_at"])
        tokens = task.get("last_token_delta", 0)

        return f"{status_glyph} {task['label']} • {elapsed} • ↓ {tokens} tokens"

    def _format_elapsed(self, started_at: float) -> str:
        import time
        elapsed = time.time() - started_at

        if elapsed < 60:
            return f"{int(elapsed)}s"
        elif elapsed < 3600:
            return f"{int(elapsed / 60)}m {int(elapsed % 60)}s"
        else:
            return f"{int(elapsed / 3600)}h {int((elapsed % 3600) / 60)}m"

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        task_id = event.item.id
        self.dismiss(task_id)

    def action_select(self) -> None:
        list_view = self.query_one(ListView)
        if list_view.highlighted_child:
            self.dismiss(list_view.highlighted_child.id)
