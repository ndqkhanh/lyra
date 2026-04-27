"""Multi-channel gateway adapter layer — hermes parity.

Exposes an :class:`~.adapter.ChannelAdapter` protocol that Telegram /
Slack / Discord / Mattermost / Matrix / SMS / Email / Feishu / WeCom
adapters implement. The gateway daemon owns the event loop and ticks
adapters on every poll; adapters declare a normalized
:class:`~.adapter.InboundMessage` and return a
:class:`~.adapter.OutboundMessage` to route replies.

Only the protocol + a :class:`~.adapters.telegram.TelegramAdapter`
stub ship in this scaffold.
"""
from __future__ import annotations

from .adapter import (
    ChannelAdapter,
    GatewayError,
    InboundMessage,
    OutboundMessage,
)

__all__ = [
    "ChannelAdapter",
    "GatewayError",
    "InboundMessage",
    "OutboundMessage",
]
