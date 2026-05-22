"""Notification Drawer — toast notification history.

Keeps a running log of notification events (compaction, tool errors,
background task completion) in a slide-out drawer. Mirrors the
NotificationSystem from lyra-ui within the TUI v2 shell.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, Label, ListItem, ListView, Static


@dataclass
class NotificationEntry:
    """A single notification."""
    level: str  # info, success, warning, error
    title: str
    message: str = ""
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    read: bool = False

    @property
    def glyph(self) -> str:
        return {
            "info": "ℹ",
            "success": "✓",
            "warning": "⚠",
            "error": "✗",
        }.get(self.level, "ℹ")

    @property
    def style(self) -> str:
        return {
            "info": "bold cyan",
            "success": "bold green",
            "warning": "bold yellow",
            "error": "bold red",
        }.get(self.level, "bold cyan")

    @property
    def summary(self) -> str:
        ts = datetime.fromtimestamp(self.timestamp).strftime("%H:%M")
        return f"[{self.style}]{self.glyph}[/] [dim]{ts}[/]  {self.title}"


class NotificationDrawer(ModalScreen[None]):
    """Slide-out notification history drawer."""

    DEFAULT_CSS = """
    NotificationDrawer {
        align: right top;
    }

    NotificationDrawer > Vertical {
        width: 50;
        height: 80%;
        min-height: 20;
        margin: 1;
        background: $surface;
        border: thick $accent;
        padding: 1;
    }

    NotificationDrawer #notif-header {
        height: 3;
        content-align: center middle;
        text-style: bold;
        border-bottom: solid $border;
        margin-bottom: 1;
    }

    NotificationDrawer #notif-list {
        height: 1fr;
        border: solid $border;
    }

    NotificationDrawer #notif-list ListItem {
        padding: 0 1;
        height: 2;
    }

    NotificationDrawer #notif-list ListItem:hover {
        background: $accent 15%;
    }

    NotificationDrawer #notif-footer {
        dock: bottom;
        height: 3;
        content-align: center middle;
    }
    """

    _notifications: list[NotificationEntry] = []
    _unread_count: reactive[int] = reactive(0)

    BINDINGS = [
        Binding("escape", "dismiss(None)", "Close", show=False),
        Binding("c", "clear_all", "Clear All", show=True),
    ]

    def __init__(self, notifications: Optional[list[NotificationEntry]] = None):
        super().__init__()
        self._notifications = notifications or []
        self._unread_count = sum(1 for n in self._notifications if not n.read)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(
                f"[bold]Notifications[/]  [dim]({self._unread_count} unread)[/]",
                id="notif-header",
            )
            yield ListView(id="notif-list")
            yield Label("[dim]c=clear all · esc=close[/]", id="notif-footer")

    def on_mount(self) -> None:
        self._rebuild()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx is not None and 0 <= idx < len(self._notifications):
            self._notifications[idx].read = True
            self._rebuild()

    def action_clear_all(self) -> None:
        self._notifications.clear()
        self._unread_count = 0
        self._rebuild()

    def _rebuild(self) -> None:
        list_view = self.query_one("#notif-list", ListView)
        list_view.clear()
        if not self._notifications:
            list_view.append(ListItem(Static("[dim]  No notifications[/]")))
            return
        for notif in reversed(self._notifications):
            item = ListItem(
                Static(notif.summary),
            )
            list_view.append(item)

    @staticmethod
    def add_notification(level: str, title: str, message: str = "") -> NotificationEntry:
        n = NotificationEntry(level=level, title=title, message=message)
        return n
