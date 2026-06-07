"""MCP consumer adapter.

The adapter is transport-agnostic: it accepts any object with ``list_tools``
and ``call_tool`` methods. Real deployments wire this to a stdio or HTTP
JSON-RPC transport; the test suite uses ``lyra_mcp.testing.FakeMCPServer``.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Protocol


class MCPProtocolError(Exception):
    pass


class MCPTimeoutError(Exception):
    pass


class Transport(Protocol):
    def list_tools(self) -> list[dict[str, Any]]: ...
    def call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]: ...


def _expected_shape(obj: Any) -> bool:
    return isinstance(obj, dict) and ("ok" in obj or "content" in obj or "result" in obj)


@dataclass
class MCPAdapter:
    transport: Transport
    timeout_ms: int = 5000

    # -------------------------------------------------------------- list_tools
    def list_tools(self) -> list[dict[str, Any]]:
        try:
            tools = self.transport.list_tools()
        except Exception as e:
            raise MCPProtocolError(f"list_tools failed: {e}") from e
        if not isinstance(tools, list):
            raise MCPProtocolError(f"list_tools returned non-list: {type(tools).__name__}")
        return tools

    # -------------------------------------------------------------- call_tool
    def call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        result_box: dict[str, Any] = {}

        def worker() -> None:
            try:
                result_box["value"] = self.transport.call_tool(name, args)
            except Exception as e:
                result_box["error"] = e

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        t.join(self.timeout_ms / 1000.0)
        if t.is_alive():
            raise MCPTimeoutError(
                f"call_tool {name!r} exceeded timeout of {self.timeout_ms}ms"
            )
        if "error" in result_box:
            raise MCPProtocolError(str(result_box["error"]))
        value = result_box.get("value")
        if not _expected_shape(value):
            raise MCPProtocolError(
                f"call_tool {name!r} returned unexpected shape: {value!r}"
            )
        return value  # type: ignore[return-value]
