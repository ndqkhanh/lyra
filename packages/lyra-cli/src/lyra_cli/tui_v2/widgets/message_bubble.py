"""MessageBubbleWidget — polished message display with syntax highlighting, timestamps, and roles.

Ports lyra-ui's widgets.py (MessageBubble, TokenUsageIndicator) into Textual.
Shows:
  • Role-styled message bubbles (user = yellow, assistant = cyan, system = dim)
  • Syntax-highlighted code blocks via Rich
  • Timestamp badges
  • Collapsible long messages
  • Token counts per message

ECC reference: ECC's identity.json emphasizes minimal + legible output — this
makes every message visually scannable at a glance.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static, RichLog


# ── Color mapping ───────────────────────────────────────────────────────

ROLE_STYLE = {
    "user": "bold yellow",
    "assistant": "bold cyan",
    "system": "dim",
    "tool": "dim magenta",
    "error": "bold red",
}

ROLE_GLYPH = {
    "user": "👤",
    "assistant": "✦",
    "system": "⚙",
    "tool": "🔧",
    "error": "✗",
}


# ── Data models ─────────────────────────────────────────────────────────

@dataclass
class Message:
    """One message in the conversation."""
    role: str  # user, assistant, system, tool, error
    content: str
    token_count: int = 0
    timestamp: float = field(default_factory=time.time)
    message_id: str = ""

    @property
    def time_str(self) -> str:
        return time.strftime("%H:%M:%S", time.localtime(self.timestamp))

    @property
    def header(self) -> str:
        glyph = ROLE_GLYPH.get(self.role, "•")
        style = ROLE_STYLE.get(self.role, "white")
        tok = f"  [dim]{self.token_count}t[/]" if self.token_count > 0 else ""
        return f"[{style}]{glyph} {self.role.title()}[/]  [dim]{self.time_str}[/]{tok}"

    def render_content(self, max_chars: int = 4000) -> str:
        """Render message content with syntax highlighting for code blocks."""
        content = self.content

        # Truncate very long messages
        if len(content) > max_chars:
            content = content[:max_chars] + "\n[dim]… (truncated)[/]"

        # Highlight code blocks (simple detection)
        lines = content.split("\n")
        result = []
        in_code = False
        for line in lines:
            if line.strip().startswith("```"):
                in_code = not in_code
                if in_code:
                    lang = line.strip()[3:].strip()
                    if lang:
                        result.append(f"[bold magenta]```{lang}[/]")
                    else:
                        result.append("[bold magenta]```[/]")
                else:
                    result.append("[bold magenta]```[/]")
                continue
            if in_code:
                result.append(f"[cyan]{line}[/]")
            else:
                result.append(line)

        return "\n".join(result)


# ── Widget ──────────────────────────────────────────────────────────────

class MessageBubbleWidget(Widget):
    """Message display with roles, timestamps, syntax highlight, and collapse."""

    DEFAULT_CSS = """
    MessageBubbleWidget {
        height: auto;
        margin: 0;
        padding: 0;
    }

    MessageBubbleWidget .msg-header {
        height: 1;
        margin: 1 0 0 0;
    }

    MessageBubbleWidget .msg-body {
        height: auto;
        margin: 0 0 0 1;
        padding: 0 1;
        border-left: solid $border;
    }

    MessageBubbleWidget .msg-body.collapsed {
        height: 1;
        overflow-y: hidden;
    }

    MessageBubbleWidget .msg-body-tool {
        border-left: solid magenta 30%;
    }

    MessageBubbleWidget .msg-body-error {
        border-left: solid red;
        background: red 10%;
    }

    MessageBubbleWidget .msg-token-badge {
        color: $text-muted;
        height: 1;
        text-align: right;
    }
    """

    # Reactive for auto-scroll
    message_count: reactive[int] = reactive(0)

    def __init__(self):
        super().__init__()
        self._messages: list[Message] = []
        self._max_visible = 100

    def compose(self) -> ComposeResult:
        yield RichLog(id="msg-log", highlight=True, markup=True, max_lines=1000)

    def on_mount(self) -> None:
        pass

    # ── Public API ─────────────────────────────────────────────────────

    def append(self, role: str, content: str, token_count: int = 0, message_id: str = "") -> Message:
        """Add a message to the display."""
        msg = Message(
            role=role,
            content=content,
            token_count=token_count,
            message_id=message_id or f"msg_{len(self._messages)}",
        )
        self._messages.append(msg)
        self.message_count = len(self._messages)

        # Trim old messages
        if len(self._messages) > self._max_visible:
            self._messages = self._messages[-self._max_visible:]

        self._render_message(msg)
        return msg

    def clear(self) -> None:
        """Clear all messages."""
        self._messages.clear()
        try:
            self.query_one("#msg-log", RichLog).clear()
        except Exception:
            pass

    def get_messages(self) -> list[Message]:
        return list(self._messages)

    def last_n(self, n: int = 5) -> list[Message]:
        return self._messages[-n:] if self._messages else []

    def total_tokens(self) -> int:
        return sum(m.token_count for m in self._messages)

    # ── Internal ───────────────────────────────────────────────────────

    def _render_message(self, msg: Message) -> None:
        try:
            log = self.query_one("#msg-log", RichLog)
            log.write(msg.header)
            log.write(msg.render_content())
        except Exception:
            pass
