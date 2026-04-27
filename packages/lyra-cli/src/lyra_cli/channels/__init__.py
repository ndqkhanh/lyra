"""Wave-E (v1.9.0): channel adapters and the gateway daemon.

Per-channel adapters (Slack, Discord, Matrix, Email, SMS, etc.) plug
into a single :class:`Gateway` that routes inbound messages to a
per-thread agent-loop session and pushes outbound replies back.

The base protocol + gateway live here; concrete adapters land in
sibling modules (``slack.py``, ``discord.py``, …) so missing optional
deps stay isolated to one file each.
"""
from __future__ import annotations

from .base import (
    ChannelAdapter,
    Gateway,
    GatewayHandler,
    Inbound,
    Outbound,
)

__all__ = [
    "ChannelAdapter",
    "Gateway",
    "GatewayHandler",
    "Inbound",
    "Outbound",
]
