"""Compaction banner widget (FR-010)."""

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static, RichLog
from textual.containers import Vertical
from textual.binding import Binding


class CompactionBanner(Widget):
    """Banner showing context compaction events."""

    BINDINGS = [
        Binding("ctrl+o", "toggle_expand", "Expand/Collapse"),
    ]

    DEFAULT_CSS = """
    CompactionBanner {
        height: auto;
        border: solid $accent;
        margin: 1;
    }

    CompactionBanner.collapsed {
        height: 1;
    }
    """

    compaction_event: reactive[dict | None] = reactive(None)
    expanded: reactive[bool] = reactive(True)

    def compose(self) -> ComposeResult:
        if not self.compaction_event:
            return

        if self.expanded:
            yield Vertical(
                Static(self._render_header()),
                RichLog(id="compaction-detail"),
            )
        else:
            yield Static(self._render_collapsed())

    def _render_header(self) -> str:
        return "✻ [bold]Conversation compacted[/bold] (ctrl+o for history)"

    def _render_checklist(self) -> str:
        if not self.compaction_event:
            return ""

        items = self.compaction_event.get("restored", [])
        lines = []

        for kind, path, line_count in items:
            if kind == "read":
                text = f"Read {path}"
                if line_count:
                    text += f" ({line_count} lines)"
            elif kind == "loaded":
                text = f"Loaded {path}"
            elif kind == "skill":
                text = f"Skills restored ({path})"
            else:
                text = f"{kind}: {path}"

            lines.append(f"⎿  {text}")

        return "\n".join(lines)

    def _render_collapsed(self) -> str:
        count = len(self.compaction_event.get("restored", []))
        return f"✻ Compacted ({count} items restored) • ctrl+o to expand"

    def action_toggle_expand(self) -> None:
        self.expanded = not self.expanded
        self.refresh(layout=True)

    def watch_compaction_event(self, event: dict | None) -> None:
        if event:
            self.set_timer(30.0, self._auto_collapse)

    def _auto_collapse(self) -> None:
        if self.expanded:
            self.expanded = False

    def on_mount(self) -> None:
        if self.expanded and self.compaction_event:
            log = self.query_one("#compaction-detail", RichLog)
            log.write(self._render_checklist())
