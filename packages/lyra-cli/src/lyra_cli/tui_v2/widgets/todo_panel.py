"""To-do panel widget (FR-015)."""

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Static, Widget
from textual.containers import Vertical


class TodoPanel(Widget):
    """Live to-do list with checkboxes."""

    DEFAULT_CSS = """
    TodoPanel {
        height: auto;
        border: solid $accent;
        padding: 1;
    }

    TodoPanel .todo-item {
        height: 1;
    }

    TodoPanel .todo-item.transition {
        background: $accent 50%;
    }
    """

    GLYPH_MAP = {
        "pending": "◻",
        "done": "◼",
        "blocked": "⚠",
    }

    todos: reactive[list[dict]] = reactive([])

    def compose(self) -> ComposeResult:
        visible = self.todos[:5]
        overflow = len(self.todos) - 5

        items = []
        for todo in visible:
            items.append(
                Static(
                    self._render_item(todo),
                    classes="todo-item",
                    id=f"todo-{todo['id']}",
                )
            )

        if overflow > 0:
            items.append(Static(f"… +{overflow} pending"))

        yield Vertical(*items)

    def _render_item(self, todo: dict) -> str:
        glyph = self.GLYPH_MAP.get(todo["status"], "?")
        return f"{glyph} {todo['label']}"

    def watch_todos(self, old_todos: list, new_todos: list) -> None:
        old_ids = {t["id"]: t for t in old_todos}
        new_ids = {t["id"]: t for t in new_todos}

        for todo_id, new_todo in new_ids.items():
            old_todo = old_ids.get(todo_id)
            if old_todo and old_todo["status"] != new_todo["status"]:
                self._animate_transition(todo_id)

        self.refresh(layout=True)

    def _animate_transition(self, todo_id: str) -> None:
        try:
            item = self.query_one(f"#todo-{todo_id}")
            item.add_class("transition")
            self.set_timer(0.3, lambda: item.remove_class("transition"))
        except Exception:
            pass
