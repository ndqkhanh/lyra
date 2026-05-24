"""Channel system — external event routing into running sessions.

Claude Code's channel system lets MCP servers push external events
(webhooks, CI alerts, chat messages) into running sessions via
``notifications/claude/channel``. Channels are two-way: they can
carry a reply tool so the model can respond to the external source.

This module provides the core datatypes and manager. Integration
with the REPL session happens through :meth:`ChannelManager.route`
which wraps incoming events as ``<channel>`` tags in the message
stream.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelSpec:
    """Declarative config for one channel endpoint.

    Attributes:
        name: Human-readable name (e.g. ``"ci-webhook"``).
        command: Shell command or MCP server entry point.
        args: Positional args for the channel process.
        capabilities: The set of capabilities this channel advertises
            (``"claude/channel"``, ``"claude/channel/permission"``).
        instructions: System-prompt snippet injected when the channel
            delivers an event — tells the model how to interpret it.
    """

    name: str
    command: str
    args: tuple[str, ...] = ()
    capabilities: frozenset[str] = frozenset({"claude/channel"})
    instructions: str = ""


@dataclass(frozen=True)
class ChannelEvent:
    """One event arriving through a channel.

    Attributes:
        channel_name: Which channel emitted the event.
        source: Free-form source identifier (e.g. ``"GitHub/webhook"``).
        body: The event payload as a string — typically JSON from a
            webhook or a chat message body.
        timestamp: ISO-8601 timestamp set by the channel manager.
        reply_available: True when the model can reply through this
            channel (the channel registered a reply MCP tool).
    """

    channel_name: str
    source: str
    body: str
    timestamp: str = ""
    reply_available: bool = False

    def as_context_tag(self) -> str:
        """Render this event as a ``<channel>`` XML tag for the LLM."""
        reply = " reply" if self.reply_available else ""
        ts = f' ts="{self.timestamp}"' if self.timestamp else ""
        return (
            f'<channel source="{self.channel_name} / {self.source}"'
            f'{reply}{ts}>\n{self.body}\n</channel>'
        )


class ChannelManager:
    """Registry + event router for external channels.

    Channels are registered at session boot and persist for the
    session lifetime. Incoming events are buffered per-channel and
    flushed into the prompt stream each turn so the model always
    sees the latest external context without polling.

    Usage::

        mgr = ChannelManager()
        mgr.register(ChannelSpec(
            name="gh-webhook",
            command="lyra-channel-github",
            instructions="These are GitHub webhook events.",
        ))
        # On webhook POST:
        mgr.push("gh-webhook", ChannelEvent(
            channel_name="gh-webhook",
            source="GitHub/push",
            body='{"ref": "refs/heads/main", ...}',
        ))
        # Each turn, inject pending events:
        block = mgr.flush_context_block()
    """

    def __init__(self) -> None:
        self._specs: dict[str, ChannelSpec] = {}
        self._pending: dict[str, list[ChannelEvent]] = {}
        self._on_event: Callable[[ChannelEvent], None] | None = None

    # ---- registration -------------------------------------------------- #

    def register(self, spec: ChannelSpec) -> None:
        """Add or replace a channel spec."""
        self._specs[spec.name] = spec
        if spec.name not in self._pending:
            self._pending[spec.name] = []

    def unregister(self, name: str) -> bool:
        """Remove a channel; returns False if it didn't exist."""
        self._specs.pop(name, None)
        self._pending.pop(name, None)
        return True

    @property
    def registered_names(self) -> list[str]:
        return sorted(self._specs.keys())

    def get(self, name: str) -> ChannelSpec | None:
        return self._specs.get(name)

    # ---- event routing ------------------------------------------------- #

    def push(self, name: str, event: ChannelEvent) -> None:
        """Enqueue an event for the next turn's context block.

        Events are queued per-channel and drained on
        :meth:`flush_context_block`.
        """
        if name not in self._pending:
            self._pending[name] = []
        self._pending[name].append(event)
        if self._on_event is not None:
            try:
                self._on_event(event)
            except Exception:
                pass

    def on_event(self, callback: Callable[[ChannelEvent], None]) -> None:
        """Register a callback fired on every pushed event.

        Useful for desktop notifications, logging, or triggering
        permission re-check flows.
        """
        self._on_event = callback

    def drain(self, name: str | None = None) -> list[ChannelEvent]:
        """Drain and return pending events.

        When *name* is None, drains all channels.
        """
        if name is not None:
            return self._pending.pop(name, [])
        drained: list[ChannelEvent] = []
        for ch in list(self._pending):
            drained.extend(self._pending.pop(ch, []))
        return drained

    def pending_count(self) -> int:
        """Total number of undrained events across all channels."""
        return sum(len(q) for q in self._pending.values())

    # ---- context injection --------------------------------------------- #

    def flush_context_block(self) -> str:
        """Drain all pending events and return a context-block string.

        The returned block is prepended as ``<channel>`` tags so the
        LLM sees external events as structured context. Returns the
        empty string when no events are pending.
        """
        events = self.drain()
        if not events:
            return ""
        lines: list[str] = []
        for evt in events:
            specs = self._specs.get(evt.channel_name)
            if specs and specs.instructions:
                lines.append(f"<!-- {specs.instructions} -->")
            lines.append(evt.as_context_tag())
        return "\n".join(lines).strip()


__all__ = [
    "ChannelEvent",
    "ChannelManager",
    "ChannelSpec",
]
