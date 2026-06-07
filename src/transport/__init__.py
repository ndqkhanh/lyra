"""
Transport bridge — WebSocket-based Python↔TypeScript communication layer.
"""

from src.transport.bridge import (
    BridgeMessage,
    BridgeMessageType,
    HeartbeatMessage,
    TransportBridge,
)

__version__ = "0.1.0"

__all__ = [
    "TransportBridge",
    "BridgeMessage",
    "BridgeMessageType",
    "HeartbeatMessage",
]
