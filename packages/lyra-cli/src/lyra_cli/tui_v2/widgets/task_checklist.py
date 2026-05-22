"""TaskChecklistWidget — renders sub-task checklist in TUI.

Ports task_list.py's sub-task checklist renderer into a TUI widget.
Shows pending/running/done tasks with overflow collapse.
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

_STATE_GLYPH = {"pending": "◻", "running": "◼", "done": "✓"}
_MAX_VISIBLE = 8


class TaskChecklistWidget(Widget):
    """Sub-task checklist — Ctrl+Shift+T to toggle."""

    DEFAULT_CSS = """
    TaskChecklistWidget {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }
    TaskChecklistWidget.collapsed { height: 1; border: none; }
    TaskChecklistWidget #tcl-header { height: 1; color: $text-muted; }
    TaskChecklistWidget #tcl-items { height: auto; margin: 0 0 0 1; }
    """

    BINDINGS = [Binding("ctrl+shift+t", "toggle_tasklist", "Tasks")]

    expanded: reactive[bool] = reactive(False)
    items: reactive[list] = reactive([])

    def compose(self) -> ComposeResult:
        yield Static("", id="tcl-header")
        yield Static("", id="tcl-items")

    def on_mount(self) -> None:
        self._render()

    def set_tasks(self, tasks: list[dict]) -> None:
        self.items = tasks
        self._render()

    def action_toggle_tasklist(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._render()

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            tasks = list(self.items)
            total = len(tasks)
            done = sum(1 for t in tasks if t.get("state", t.get("status", "")) == "done")
            hint = "[dim](ctrl+shift+t)[/]"
            if self.expanded:
                self.query_one("#tcl-header", Static).update(
                    f"[bold]Tasks[/]  [green]{done}[/]/{total}  {hint}"
                )
                lines = []
                for t in tasks[:_MAX_VISIBLE]:
                    state = t.get("state", t.get("status", "pending"))
                    desc = t.get("description", t.get("name", "?"))[:50]
                    glyph = _STATE_GLYPH.get(state, "○")
                    color = {"done": "green", "running": "yellow", "pending": "dim"}.get(state, "dim")
                    lines.append(f"  [{color}]{glyph}[/] {desc}")
                if total > _MAX_VISIBLE:
                    lines.append(f"  [dim]… +{total - _MAX_VISIBLE} more[/]")
                self.query_one("#tcl-items", Static).update("\n".join(lines))
            else:
                self.query_one("#tcl-header", Static).update(
                    f"[bold]Tasks[/]  [green]{done}[/]/{total}  {hint}"
                )
                self.query_one("#tcl-items", Static).update("")
        except Exception:
            pass


__all__ = ["TaskChecklistWidget"]
