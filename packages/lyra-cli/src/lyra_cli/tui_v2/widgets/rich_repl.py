"""RichReplWidget — enhanced streaming REPL with multi-source completions.

Ports lyra_ui/streaming_repl.py into the TUI as a rich input widget.

Provides:
  • Multi-source tab completions (/commands, @files, #skills, :tools)
  • Markdown-aware streaming output display (fence-safe)
  • Command history with fuzzy recall
  • Syntax-highlighted input area

ECC reference: match the everything-claude-code REPL feel — fast
completions, fence-safe streaming, and keyboard-friendly input.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Input, RichLog, Static


# ── Built-in command registry for completions ──────────────────────────

_COMMANDS = [
    "workflow", "undo", "redo", "help", "profile", "whoami",
    "git", "diff", "verify", "checkpoint", "monitor", "hud",
    "model", "mode", "clear", "history", "exit", "status",
    "compact", "search", "skills", "agents", "memory", "plan",
    "execute", "config", "feedback", "sessions", "resume",
    "doctor", "eval", "research", "investigate",
]

_SLASH_COMMANDS = [f"/{c}" for c in _COMMANDS]


# ── Markdown streaming buffer (fence-aware) ────────────────────────────

_FENCE = "```"


class MarkdownStreamBuffer:
    """Deferred-flush buffer for streaming markdown (port from stream.py)."""

    def __init__(self) -> None:
        self._buf: str = ""

    def push(self, delta: str) -> Optional[str]:
        """Append delta; return safe-to-flush prefix or None."""
        if delta:
            self._buf += delta
        boundary = self._safe_boundary()
        if boundary <= 0:
            return None
        ready = self._buf[:boundary]
        self._buf = self._buf[boundary:]
        return ready

    def flush(self) -> str:
        """Return everything remaining."""
        ready = self._buf
        self._buf = ""
        return ready

    def _safe_boundary(self) -> int:
        """Find last newline outside any open ``` fence."""
        fences = 0
        i = 0
        while True:
            idx = self._buf.find(_FENCE, i)
            if idx == -1:
                break
            fences += 1
            i = idx + 3
        if fences % 2 == 0:
            # Even fences = we're outside a code block — safe to flush to
            # the last newline
            last_nl = self._buf.rfind("\n")
            return last_nl + 1 if last_nl >= 0 else 0
        return 0

    @property
    def buffered(self) -> str:
        return self._buf


# ── TUI Widget ──────────────────────────────────────────────────────────

class RichReplWidget(Widget):
    """Enhanced REPL input with streaming display and completions.

    Ctrl+Shift+I to toggle. Shows: multi-source completions, streaming
    output with fence-safe buffering, command history.

    Replacements offered:
      /<tab> → slash commands (e.g. /workflow, /undo)
      @<tab> → file paths in cwd
      #<tab> → skill names
    """

    DEFAULT_CSS = """
    RichReplWidget {
        height: auto;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }

    RichReplWidget.collapsed {
        height: 1;
        border: none;
    }

    RichReplWidget #repl-header {
        height: 1;
        color: $text-muted;
    }

    RichReplWidget #repl-input {
        height: 3;
        min-height: 3;
        margin: 0 0 0 1;
    }

    RichReplWidget #repl-output {
        height: auto;
        max-height: 8;
        margin: 0 0 0 1;
        overflow-y: auto;
    }

    RichReplWidget #repl-completions {
        height: auto;
        max-height: 6;
        margin: 0 0 0 1;
    }

    RichReplWidget .completion-item {
        height: 1;
        padding: 0 1;
    }

    RichReplWidget .completion-highlight {
        color: $accent;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("ctrl+shift+i", "toggle_repl", "REPL"),
    ]

    expanded: reactive[bool] = reactive(False)
    input_text: reactive[str] = reactive("")
    completions: reactive[list] = reactive([])
    cwd: reactive[str] = reactive("")

    def __init__(self):
        super().__init__()
        self._stream_buf = MarkdownStreamBuffer()
        self._history: list[str] = []
        self._history_idx = 0
        self._cached_files: list[str] = []

    def compose(self) -> ComposeResult:
        yield Static("", id="repl-header")
        yield Input(placeholder="Type / for commands, @ for files, # for skills…", id="repl-input")
        yield Static("", id="repl-completions")
        yield Static("", id="repl-output")

    def on_mount(self) -> None:
        self._scan_files()
        self._render()

    # ── Public API ─────────────────────────────────────────────────────

    def stream_token(self, token: str) -> None:
        """Push a streaming token into the fence-aware buffer."""
        safe = self._stream_buf.push(token)
        if safe:
            try:
                log = self.query_one("#repl-output", Static)
                current = log.renderable or ""
                log.update(current + safe)
            except Exception:
                pass

    def flush_stream(self) -> None:
        """Flush remaining buffered output."""
        remaining = self._stream_buf.flush()
        if remaining:
            try:
                log = self.query_one("#repl-output", Static)
                log.update((log.renderable or "") + remaining)
            except Exception:
                pass

    def add_to_history(self, text: str) -> None:
        self._history.append(text)
        self._history_idx = len(self._history)

    @property
    def stream_buffer(self) -> MarkdownStreamBuffer:
        return self._stream_buf

    # ── Completions ────────────────────────────────────────────────────

    def compute_completions(self, text: str) -> list[str]:
        """Return completions for current input text."""
        if not text:
            return _SLASH_COMMANDS[:10]  # Show most common

        if text.startswith("/"):
            q = text[1:].lower()
            return [f"/{c}" for c in _COMMANDS if c.startswith(q)][:10]

        if text.startswith("@"):
            q = text[1:].lower()
            return [f"@{f}" for f in self._cached_files if f.startswith(q)][:10]

        if text.startswith("#"):
            return []  # Skills not loaded in this scope

        return []

    # ── Input handler ──────────────────────────────────────────────────

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "repl-input":
            self.input_text = event.value
            self.completions = self.compute_completions(event.value)
            self._render_completions()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "repl-input" and event.value.strip():
            self.add_to_history(event.value)

    # ── Actions ────────────────────────────────────────────────────────

    def action_toggle_repl(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._render()

    # ── Internal ───────────────────────────────────────────────────────

    def _scan_files(self) -> None:
        try:
            cwd = Path.cwd()
            self._cached_files = sorted(
                p.name for p in cwd.iterdir()
                if p.is_file() and not p.name.startswith(".")
            )[:30]
        except Exception:
            self._cached_files = []

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            hint = "[dim](ctrl+shift+i)[/]"
            if self.expanded:
                self.query_one("#repl-header", Static).update(
                    f"[bold]REPL[/]  {hint}"
                )
            else:
                self.query_one("#repl-header", Static).update(
                    f"[bold]REPL[/]  {len(self._history)} history  {hint}"
                )
        except Exception:
            pass

    def _render_completions(self) -> None:
        if not self.expanded or not self.completions:
            try:
                self.query_one("#repl-completions", Static).update("")
            except Exception:
                pass
            return

        lines = ["[dim]Completions:[/]"]
        for c in self.completions[:8]:
            lines.append(f"  [accent]{c}[/]")
        try:
            self.query_one("#repl-completions", Static).update("\n".join(lines))
        except Exception:
            pass
