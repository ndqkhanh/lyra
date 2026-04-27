"""JSON-RPC 2.0 dispatcher for the ACP bridge.

The surface is deliberately tiny — just enough to say "yes this is a
valid ACP server" without yet binding real turn execution. That keeps
the protocol handshake testable in isolation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

__all__ = [
    "ACP_ERROR_METHOD_NOT_FOUND",
    "ACP_ERROR_PARSE",
    "AcpError",
    "AcpMethod",
    "AcpServer",
]

ACP_ERROR_PARSE = -32700
ACP_ERROR_METHOD_NOT_FOUND = -32601

AcpMethod = Callable[[dict[str, Any]], Any]


class AcpError(Exception):
    """Wraps a JSON-RPC error response so handlers can raise naturally."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data

    def as_response(self, req_id: Any) -> dict[str, Any]:
        err: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.data is not None:
            err["data"] = self.data
        return {"jsonrpc": "2.0", "id": req_id, "error": err}


@dataclass
class AcpServer:
    """JSON-RPC 2.0 dispatcher routing by method name."""

    methods: dict[str, AcpMethod] = field(default_factory=dict)

    def register(self, method: str, handler: AcpMethod) -> None:
        self.methods[method] = handler

    def handle_request(self, raw: str) -> str | None:
        try:
            req = json.loads(raw)
        except json.JSONDecodeError as exc:
            return json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": ACP_ERROR_PARSE,
                        "message": f"parse error: {exc}",
                    },
                }
            )

        req_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params") or {}

        handler = self.methods.get(method)
        if handler is None:
            if req_id is None:
                return None
            return json.dumps(
                AcpError(
                    ACP_ERROR_METHOD_NOT_FOUND,
                    f"method not found: {method}",
                ).as_response(req_id)
            )

        try:
            result = handler(params)
        except AcpError as exc:
            return json.dumps(exc.as_response(req_id))

        if req_id is None:
            return None
        return json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result})

    def serve(self, lines: Iterable[str]) -> Iterable[str]:
        """Consume newline-delimited JSON-RPC input and yield responses.

        Notifications (``id`` absent) produce no output so the stream
        stays aligned with the ACP / LSP convention of silent acks.
        """
        for raw in lines:
            raw = raw.strip()
            if not raw:
                continue
            out = self.handle_request(raw)
            if out is not None:
                yield out
