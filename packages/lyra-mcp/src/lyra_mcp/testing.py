"""In-process fake MCP server for tests.

This module lives in the ``lyra_mcp`` package (not ``tests/``) so that
multiple test files can import the same ``FakeMCPServer`` without duplicating
setup code.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

Handler = Callable[[str, dict[str, Any]], dict[str, Any]]


@dataclass
class FakeMCPServer:
    """Minimal transport shim that looks like an MCP adapter would to the
    real protocol layer.
    """
    tools: list[dict[str, Any]] = field(default_factory=list)
    handler: Handler | None = None
    simulated_latency_ms: int = 0
    force_malformed: bool = False

    # ----- MCPAdapter Transport protocol -----
    def list_tools(self) -> list[dict[str, Any]]:
        return [dict(t) for t in self.tools]

    def call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if self.simulated_latency_ms:
            time.sleep(self.simulated_latency_ms / 1000.0)
        if self.force_malformed:
            return {"unexpected": "shape"}
        if self.handler is None:
            return {"ok": True, "content": None}
        return self.handler(name, args)
