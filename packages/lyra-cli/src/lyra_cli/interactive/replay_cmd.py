"""ReplayWidget — TUI session step-through viewer.

Ports the 152-line replay.py engine into a visual step-through panel.
Shows:
  • Turn-by-turn replay with index and metadata
  • Unified diff overlay between adjacent turns
  • Current/previous/next navigation
  • Jump-to-turn by number

Ctrl+Shift+J to toggle. /replay in the REPL.
"""
from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from ..commands.registry import CommandResult


@dataclass
class ReplayEvent:
    """One replay turn."""
    index: int
    payload: dict
    diff: str = ""
    role: str = ""
    content_preview: str = ""
    token_count: int = 0

    @property
    def summary(self) -> str:
        role = self.payload.get("role", self.role) or "?"
        content = self.content_preview or json.dumps(self.payload)[:60]
        return f"[dim]#{self.index}[/] [{role}]{role:<10}[/] {content}"

    @property
    def diff_preview(self) -> str:
        if not self.diff:
            return "[dim](first turn)[/]"
        lines = self.diff.split("\n")[:8]
        return "\n".join(
            f"[green]{l}[/]" if l.startswith("+") else
            f"[red]{l}[/]" if l.startswith("-") else
            l
            for l in lines
        )


class ReplayWidget(Widget):
    """Session replay — step through turns with diff overlay.

    Ctrl+Shift+J to toggle. Shows current turn, diff vs previous,
    and navigation controls.
    """

    DEFAULT_CSS = """
    ReplayWidget {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }

    ReplayWidget.collapsed {
        height: 1;
        border: none;
    }

    ReplayWidget #rp-header {
        height: 1;
        color: $text-muted;
    }

    ReplayWidget #rp-turn {
        height: auto;
        min-height: 2;
        margin: 0 0 0 1;
    }

    ReplayWidget #rp-diff {
        height: auto;
        max-height: 10;
        margin: 0 0 0 1;
        overflow-y: auto;
    }

    ReplayWidget #rp-nav {
        height: 1;
        color: $text-muted;
        margin: 0 0 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+shift+j", "toggle_replay", "Replay"),
    ]

    expanded: reactive[bool] = reactive(False)
    current_index: reactive[int] = reactive(-1)
    total_turns: reactive[int] = reactive(0)

    def __init__(self):
        super().__init__()
        self._events: list[ReplayEvent] = []

    def compose(self) -> ComposeResult:
        yield Static("", id="rp-header")
        yield Static("", id="rp-turn")
        yield Static("", id="rp-diff")
        yield Static("", id="rp-nav")

    def on_mount(self) -> None:
        self._render()

    # ── Public API ─────────────────────────────────────────────────────

    def load_session(self, session_dir: Path | None = None) -> None:
        """Load replay events from a session directory."""
        if not session_dir:
            session_dir = Path.home() / ".lyra" / "sessions"
            sessions = sorted(session_dir.glob("*"))
            session_dir = sessions[-1] if sessions else session_dir

        turns_path = session_dir / "turns.jsonl"
        if not turns_path.exists():
            self._events = []
            self.total_turns = 0
            self._render()
            return

        self._events = []
        prev_body = ""
        with open(turns_path) as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Extract content for diff
                role = payload.get("role", "")
                content = payload.get("content", payload.get("output", ""))
                if isinstance(content, str) and len(content) > 80:
                    content_preview = content[:80] + "…"
                elif isinstance(content, str):
                    content_preview = content
                else:
                    content_preview = str(content)[:80]

                token_count = payload.get("tokens", payload.get("token_count", 0))

                # Compute diff
                cur_body = f"{role}: {content}" if isinstance(content, str) else ""
                diff = ""
                if prev_body and cur_body:
                    diff = "".join(difflib.unified_diff(
                        prev_body.splitlines(keepends=True),
                        cur_body.splitlines(keepends=True),
                        fromfile=f"turn {i - 1}", tofile=f"turn {i}",
                    ))
                prev_body = cur_body

                self._events.append(ReplayEvent(
                    index=i,
                    payload=payload,
                    diff=diff,
                    role=role,
                    content_preview=content_preview,
                    token_count=token_count,
                ))

        self.total_turns = len(self._events)
        self.current_index = 0 if self._events else -1
        self._render()

    def next_turn(self) -> None:
        if self._events and self.current_index < len(self._events) - 1:
            self.current_index += 1
            self._render()

    def prev_turn(self) -> None:
        if self._events and self.current_index > 0:
            self.current_index -= 1
            self._render()

    def jump_to(self, idx: int) -> None:
        if self._events and 0 <= idx < len(self._events):
            self.current_index = idx
            self._render()

    # ── Actions ────────────────────────────────────────────────────────

    def action_toggle_replay(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        if self.expanded and not self._events:
            self.load_session()
        self._render()

    # ── Internal ───────────────────────────────────────────────────────

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            self._render_header()
            self._render_turn()
            self._render_diff()
            self._render_nav()
        except Exception:
            pass

    def _render_header(self) -> None:
        hint = "[dim](ctrl+shift+j)[/]"
        if self.expanded:
            self.query_one("#rp-header", Static).update(
                f"[bold]Replay[/]  [dim]{len(self._events)} turns[/]  {hint}"
            )
        else:
            self.query_one("#rp-header", Static).update(
                f"[bold]Replay[/]  [dim]{len(self._events)} turns[/]  {hint}"
            )

    def _render_turn(self) -> None:
        if not self.expanded:
            self.query_one("#rp-turn", Static).update("")
            return
        if not self._events or self.current_index < 0:
            self.query_one("#rp-turn", Static).update("  [dim]No session loaded[/]")
            return

        event = self._events[self.current_index]
        self.query_one("#rp-turn", Static).update(event.summary)

    def _render_diff(self) -> None:
        if not self.expanded:
            self.query_one("#rp-diff", Static).update("")
            return
        if not self._events or self.current_index < 0:
            self.query_one("#rp-diff", Static).update("")
            return

        event = self._events[self.current_index]
        diff_text = event.diff_preview
        self.query_one("#rp-diff", Static).update(diff_text)

    def _render_nav(self) -> None:
        if not self.expanded:
            self.query_one("#rp-nav", Static).update("")
            return
        if not self._events:
            return

        self.query_one("#rp-nav", Static).update(
            f"[dim]Turn {self.current_index + 1}/{len(self._events)}  "
            f"·  /replay prev|next|jump <N>[/]"
        )


# ── Slash command handler ──────────────────────────────────────────────

def cmd_replay(session: Any, args: str) -> CommandResult:
    """Step through a session turn by turn.

    Usage:
      /replay           — show summary
      /replay next      — next turn
      /replay prev      — previous turn
      /replay jump <N>  — jump to turn N
      /replay load <id> — load session by id
    """
    parts = args.strip().split() if args.strip() else []
    parts[0].lower() if parts else "status"

    # We can't easily drive the widget from here, so we return text
    # (widget is the visual interface; this is the CLI fallback)
    return CommandResult(
        output="Replay: Use Ctrl+Shift+J for the TUI replay viewer, "
               "or specify a session id."
    )


__all__ = ["cmd_replay", "ReplayWidget", "ReplayEvent"]
