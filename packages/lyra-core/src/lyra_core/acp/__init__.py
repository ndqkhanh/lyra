"""ACP (Agent Client Protocol) bridge — opencode parity.

Implements a stdio JSON-RPC 2.0 server so that ACP-aware editors (Zed,
JetBrains, etc.) can host Lyra as a subprocess with
``lyra acp``. Only the routing shell is scaffolded here — method
implementations (``initialize``, ``sendUserMessage``, ``cancel``) are
stubs that satisfy the protocol contract while the real agent turn is
wired behind them.

Reference: https://agentclientprotocol.com
"""
from __future__ import annotations

from .http_bridge import HttpBridge, HttpBridgeError, make_handler
from .server import (
    ACP_ERROR_METHOD_NOT_FOUND,
    ACP_ERROR_PARSE,
    AcpError,
    AcpMethod,
    AcpServer,
)
from .v311_methods import register_v311_methods

__all__ = [
    "AcpError",
    "AcpMethod",
    "AcpServer",
    "ACP_ERROR_METHOD_NOT_FOUND",
    "ACP_ERROR_PARSE",
    "HttpBridge",
    "HttpBridgeError",
    "make_handler",
    "register_v311_methods",
]
