"""Session Manager Modal — browse, search & resume sessions.

ECC-inspired session history surface. Lets users:
  - Browse recent sessions with metadata
  - Search by keyword across session content
  - Resume / delete sessions
  - See token usage & duration

Uses the same filter+list pattern as LyraPickerModal (base.py).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, Input, ListItem, ListView, Static, Label


class SessionEntry:
    """A session history entry."""
    def __init__(
        self,
        session_id: str,
        title: str,
        model: str = "",
        turns: int = 0,
        tokens: int = 0,
        duration_s: float = 0.0,
        timestamp: str = "",
    ):
        self.session_id = session_id
        self.title = title
        self.model = model
        self.turns = turns
        self.tokens = tokens
        self.duration_s = duration_s
        self.timestamp = timestamp

    @property
    def summary(self) -> str:
        """One-line summary for the list."""
        parts = [f"[bold]{self.title}[/]"]
        if self.model:
            parts.append(f"[dim]{self.model}[/]")
        if self.turns:
            parts.append(f"[dim]{self.turns} turns[/]")
        if self.tokens:
            parts.append(f"[dim]{self._human_tokens()}[/]")
        if self.timestamp:
            parts.append(f"[dim]{self.timestamp}[/]")
        return "  ·  ".join(parts)

    def _human_tokens(self) -> str:
        if self.tokens < 1_000:
            return f"{self.tokens} tok"
        return f"{self.tokens / 1_000:.1f}K tok"


class SessionManagerModal(ModalScreen[Optional[SessionEntry]]):
    """Modal for browsing & searching session history."""

    DEFAULT_CSS = """
    SessionManagerModal {
        align: center middle;
    }

    SessionManagerModal > Vertical {
        width: 80;
        height: 70%;
        min-height: 20;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }

    SessionManagerModal #search-input {
        dock: top;
        margin: 0 0 1 0;
    }

    SessionManagerModal #session-list {
        height: 1fr;
        border: solid $border;
        margin: 1 0;
    }

    SessionManagerModal #session-list ListItem {
        padding: 0 1;
    }

    SessionManagerModal #session-list ListItem:hover {
        background: $accent 20%;
    }

    SessionManagerModal #session-list ListItem:focus {
        background: $accent 30%;
    }

    SessionManagerModal #modal-footer {
        dock: bottom;
        height: 3;
        content-align: center middle;
    }

    SessionManagerModal Button {
        margin: 0 1;
    }

    SessionManagerModal .stats-line {
        color: $text-muted;
        height: 1;
    }
    """

    search_query: reactive[str] = reactive("")
    _sessions: list[SessionEntry] = []
    _filtered: list[SessionEntry] = []

    BINDINGS = [
        Binding("escape", "dismiss(None)", "Cancel", show=False),
        Binding("enter", "select_session", "Resume", show=True),
        Binding("/", "focus_search", "Search", show=False),
        Binding("r", "refresh_list", "Refresh", show=True),
        Binding("delete", "delete_session", "Delete", show=True),
    ]

    def __init__(self, sessions: Optional[list[SessionEntry]] = None):
        super().__init__()
        self._sessions = sessions or self._load_mock_sessions()
        self._filtered = list(self._sessions)

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[bold]Session Manager[/]  [dim]r=refresh · / =search · del=delete · enter=resume[/]")
            yield Input(
                placeholder="Search sessions…",
                id="search-input",
            )
            yield ListView(id="session-list")
            with Horizontal(id="modal-footer"):
                yield Button("Resume", variant="primary", id="resume-btn")
                yield Button("Close", variant="default", id="close-btn")

    def on_mount(self) -> None:
        self._rebuild_list()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self.search_query = event.value

    def watch_search_query(self, query: str) -> None:
        q = query.lower().strip()
        if not q:
            self._filtered = list(self._sessions)
        else:
            self._filtered = [
                s for s in self._sessions
                if q in s.title.lower()
                or q in s.session_id.lower()
                or q in s.model.lower()
            ]
        self._rebuild_list()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.action_select_session()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "resume-btn":
            self.action_select_session()
        elif event.button.id == "close-btn":
            self.dismiss(None)

    # ── Actions ────────────────────────────────────────────────────

    def action_select_session(self) -> None:
        list_view = self.query_one("#session-list", ListView)
        if list_view.index is not None and 0 <= list_view.index < len(self._filtered):
            self.dismiss(self._filtered[list_view.index])

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    def action_refresh_list(self) -> None:
        self._rebuild_list()

    def action_delete_session(self) -> None:
        list_view = self.query_one("#session-list", ListView)
        if list_view.index is not None and 0 <= list_view.index < len(self._filtered):
            removed = self._filtered.pop(list_view.index)
            self._sessions = [s for s in self._sessions if s.session_id != removed.session_id]
            self._rebuild_list()

    # ── Internals ──────────────────────────────────────────────────

    def _rebuild_list(self) -> None:
        list_view = self.query_one("#session-list", ListView)
        list_view.clear()

        if not self._filtered:
            list_view.append(ListItem(Static("[dim]  No sessions found[/]")))
            return

        for session in self._filtered:
            item = ListItem(
                Static(session.summary),
            )
            list_view.append(item)

    @staticmethod
    def _load_mock_sessions() -> list[SessionEntry]:
        """Load placeholder sessions (in production, reads from session_history)."""
        return [
            SessionEntry("s1", "Feature dev: auth system", "deepseek-chat", 12, 45600, 342, "2h ago"),
            SessionEntry("s2", "Bug fix: memory leak in task allocator", "claude-sonnet-4-6", 8, 28400, 195, "4h ago"),
            SessionEntry("s3", "Research: transformer architecture", "deepseek-reasoner", 5, 89200, 612, "6h ago"),
            SessionEntry("s4", "Refactor: skill importer", "claude-sonnet-4-6", 15, 52300, 410, "Yesterday"),
            SessionEntry("s5", "UI: welcome card redesign", "claude-sonnet-4-6", 6, 18200, 130, "Yesterday"),
            SessionEntry("s6", "Docs: architecture update", "gpt-4o", 3, 9800, 72, "2d ago"),
            SessionEntry("s7", "Security: agent shield audit", "deepseek-chat", 20, 124000, 890, "3d ago"),
        ]
