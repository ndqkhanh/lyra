"""StreamHandlerWidget — stream controls with cancel/resume/pause + live progress.

Ports lyra-ui's streaming.py into a Textual widget showing:
  • Live token-by-token streaming display
  • Cancel / Pause / Resume controls via keyboard
  • Progress bar with streaming throughput
  • Buffer indicator showing accumulated content
  • ECC-style "⎿" prefix for streamed output

ECC reference: mirrors the real-time streaming UX in Claude Code and Hermes.
"""
from __future__ import annotations

import time
from typing import Callable, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static, Button, RichLog


class StreamHandlerWidget(Widget):
    """Live streaming display with cancel/pause/resume controls.

    Composes with LyraTransport to show real-time text deltas,
    tool call output, and agent thinking in an incrementally-
    updating RichLog.

    Keyboard controls:
      Ctrl+Shift+C  — Cancel current stream
      Ctrl+Shift+P  — Pause / Resume stream
      Ctrl+Shift+O  — Toggle output panel
    """

    DEFAULT_CSS = """
    StreamHandlerWidget {
        height: auto;
        max-height: 12;
        border: solid $border;
        padding: 0 1;
        margin: 0 1;
    }

    StreamHandlerWidget.collapsed {
        height: 1;
        border: none;
    }

    StreamHandlerWidget #stream-header {
        height: 1;
        color: $text-muted;
    }

    StreamHandlerWidget #stream-content {
        height: 1fr;
        max-height: 8;
        overflow-y: auto;
    }

    StreamHandlerWidget #stream-progress {
        height: 1;
    }

    StreamHandlerWidget #stream-status {
        height: 1;
        color: $text-muted;
    }

    StreamHandlerWidget .stream-token {
        color: $text;
    }

    StreamHandlerWidget .stream-agent-label {
        color: $accent;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("ctrl+shift+c", "cancel_stream", "Cancel Stream", show=False),
        Binding("ctrl+shift+p", "pause_stream", "Pause/Resume", show=False),
        Binding("ctrl+shift+o", "toggle_visibility", "Stream Panel", show=False),
    ]

    # Reactive state
    is_streaming: reactive[bool] = reactive(False)
    is_paused: reactive[bool] = reactive(False)
    expanded: reactive[bool] = reactive(False)
    char_count: reactive[int] = reactive(0)
    token_count: reactive[int] = reactive(0)
    bytes_per_sec: reactive[float] = reactive(0.0)
    duration_sec: reactive[float] = reactive(0.0)

    def __init__(self):
        super().__init__()
        self._buffer: list[str] = []
        self._start_time: Optional[float] = None
        self._on_cancel: Optional[Callable] = None
        self._on_pause: Optional[Callable[[bool], None]] = None
        self._last_byte_count = 0
        self._last_sample_time = 0.0

    def compose(self) -> ComposeResult:
        yield Static("", id="stream-header")
        yield RichLog(id="stream-content", highlight=True, markup=True)
        yield Static("", id="stream-progress")
        yield Static("", id="stream-status")

    def on_mount(self) -> None:
        self._render()

    # ── Public API ─────────────────────────────────────────────────────

    def start_stream(self, label: str = "Assistant") -> None:
        """Begin a new streaming session."""
        self._buffer = []
        self._start_time = time.time()
        self.char_count = 0
        self.token_count = 0
        self.bytes_per_sec = 0.0
        self.is_streaming = True
        self.is_paused = False
        self._last_byte_count = 0
        self._last_sample_time = time.time()
        self._update_header(f"[bold cyan]⏺[/] Streaming from {label}…")
        self._render()

    def push_token(self, token: str, agent_label: str = "") -> None:
        """Push a token into the streaming display."""
        if not self.is_streaming or self.is_paused:
            return

        self._buffer.append(token)
        self.char_count += len(token)
        self.token_count += 1

        # Calculate throughput every 0.5s
        now = time.time()
        if now - self._last_sample_time >= 0.5:
            elapsed = now - self._last_sample_time
            delta_bytes = self.char_count - self._last_byte_count
            self.bytes_per_sec = delta_bytes / elapsed if elapsed > 0 else 0.0
            self._last_byte_count = self.char_count
            self._last_sample_time = now

        self._render_stream_content(agent_label)
        self._render_progress()

    def end_stream(self, reason: str = "complete") -> None:
        """End the streaming session."""
        self.is_streaming = False
        if self._start_time:
            self.duration_sec = time.time() - self._start_time
        status = {
            "complete": "[green]✓ Complete[/]",
            "cancelled": "[yellow]⚠ Cancelled[/]",
            "error": "[red]✗ Error[/]",
        }.get(reason, reason)
        self._update_header(f"{status}  [dim]{self.char_count:,} chars · {self.token_count} tokens · {self.duration_sec:.1f}s[/]")
        self._render()

    def set_on_cancel(self, fn: Callable) -> None:
        self._on_cancel = fn

    def set_on_pause(self, fn: Callable[[bool], None]) -> None:
        self._on_pause = fn

    # ── Actions ────────────────────────────────────────────────────────

    def action_cancel_stream(self) -> None:
        if self.is_streaming:
            self.end_stream("cancelled")
            if self._on_cancel:
                self._on_cancel()

    def action_pause_stream(self) -> None:
        self.is_paused = not self.is_paused
        if self._on_pause:
            self._on_pause(self.is_paused)
        state = "paused" if self.is_paused else "resumed"
        self._update_header(f"[yellow]⏸[/] {state}")

    def action_toggle_visibility(self) -> None:
        self.expanded = not self.expanded
        self.toggle_class("collapsed", not self.expanded)
        self._render()

    # ── Internal ───────────────────────────────────────────────────────

    def _update_header(self, text: str) -> None:
        try:
            self.query_one("#stream-header", Static).update(text)
        except Exception:
            pass

    def _render(self) -> None:
        if not self.is_mounted:
            return
        try:
            self._render_stream_content()
            self._render_progress()
            self._render_status()
        except Exception:
            pass

    def _render_stream_content(self, agent_label: str = "") -> None:
        if not self.expanded:
            return
        try:
            log = self.query_one("#stream-content", RichLog)
            if agent_label:
                log.write(f"[dim]{agent_label}:[/] {self._buffer[-1] if self._buffer else ''}")
        except Exception:
            pass

    def _render_progress(self) -> None:
        if not self.expanded:
            try:
                self.query_one("#stream-progress", Static).update("")
            except Exception:
                pass
            return

        throughput = self.bytes_per_sec
        if throughput > 0:
            unit = "KB/s" if throughput > 1024 else "B/s"
            rate = throughput / 1024 if throughput > 1024 else throughput
            rate_str = f"{rate:.1f} {unit}"
        else:
            rate_str = "—"

        progress = (
            f"[dim]{self.char_count:,}[/] chars · "
            f"[dim]{self.token_count}[/] tokens · "
            f"[dim]{rate_str}[/]"
        )
        try:
            self.query_one("#stream-progress", Static).update(progress)
        except Exception:
            pass

    def _render_status(self) -> None:
        if not self.expanded:
            try:
                self.query_one("#stream-status", Static).update("")
            except Exception:
                pass
            return

        if self.is_streaming:
            controls = "[dim]Ctrl+Shift+C[/] cancel · [dim]Ctrl+Shift+P[/] pause"
            if self.is_paused:
                controls = f"[yellow]⏸ PAUSED[/]  {controls}"
        else:
            controls = ""

        if self.duration_sec > 0:
            dur = f"[dim]{self.duration_sec:.1f}s[/]"
        else:
            dur = ""

        text = "  ".join(p for p in [dur, controls] if p)
        try:
            self.query_one("#stream-status", Static).update(text)
        except Exception:
            pass
