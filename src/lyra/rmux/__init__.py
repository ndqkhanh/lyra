"""
rmux — Terminal multiplexing integration for session management.

Provides:
- RmuxIntegration: stub / interface for tmux-style sessions
- PTYHost: pseudo-terminal hosting for multiplexed sessions
- IPCProtocol: message-passing between PTY sessions
- TUIRenderer: terminal UI rendering for multiplexed view
- SessionMultiplexer: manage multiple PTY sessions concurrently
"""

from lyra.rmux.integration import RmuxIntegration, TerminalSession, TerminalSessionStatus
from lyra.rmux.pty_host import (
    IPCProtocol,
    IPCMessage,
    IPCMessageType,
    PTYConfig,
    PTYHost,
    PTYOutput,
    PTYSize,
    PTYStatus,
    SessionMultiplexer,
    TUIPanel,
    TUIRenderer,
)

__all__ = [
    "RmuxIntegration",
    "TerminalSession",
    "TerminalSessionStatus",
    "PTYHost",
    "PTYConfig",
    "PTYSize",
    "PTYOutput",
    "PTYStatus",
    "IPCProtocol",
    "IPCMessage",
    "IPCMessageType",
    "TUIRenderer",
    "TUIPanel",
    "SessionMultiplexer",
]
