"""Wave-F Task 15 — IDE bridges (VS Code, JetBrains, Zed, generic LSP).

Provides URL builders and a tiny adapter layer so the REPL can
open a file at a line in whatever IDE the user has configured.
All bridges are pure-Python string builders; the actual process
launch happens in the REPL dispatcher.
"""
from __future__ import annotations

from .bridges import (
    IDEBridge,
    IDEError,
    IDETarget,
    available_bridges,
    bridge_for,
    build_open_command,
)

__all__ = [
    "IDEBridge",
    "IDEError",
    "IDETarget",
    "available_bridges",
    "bridge_for",
    "build_open_command",
]
