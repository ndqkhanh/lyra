"""Contract tests for the ACP JSON-RPC server."""
from __future__ import annotations

import json

from lyra_core.acp import (
    ACP_ERROR_METHOD_NOT_FOUND,
    ACP_ERROR_PARSE,
    AcpError,
    AcpServer,
)


def _req(method: str, params=None, req_id: int | None = 1) -> str:
    body: dict = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        body["params"] = params
    if req_id is not None:
        body["id"] = req_id
    return json.dumps(body)


def test_unknown_method_returns_jsonrpc_error() -> None:
    s = AcpServer()
    out = json.loads(s.handle_request(_req("bogus")))
    assert out["error"]["code"] == ACP_ERROR_METHOD_NOT_FOUND


def test_known_method_returns_result() -> None:
    s = AcpServer()
    s.register("ping", lambda params: {"ok": True, **(params or {})})
    out = json.loads(s.handle_request(_req("ping", {"n": 1})))
    assert out["result"] == {"ok": True, "n": 1}
    assert out["jsonrpc"] == "2.0"
    assert out["id"] == 1


def test_handler_raising_AcpError_surfaces_code() -> None:
    s = AcpServer()
    s.register(
        "boom",
        lambda _: (_ for _ in ()).throw(AcpError(-32000, "boom", {"why": "test"})),
    )
    out = json.loads(s.handle_request(_req("boom")))
    assert out["error"]["code"] == -32000
    assert out["error"]["data"] == {"why": "test"}


def test_notification_without_id_returns_none() -> None:
    s = AcpServer()
    s.register("notify", lambda _: "ignored")
    out = s.handle_request(
        json.dumps({"jsonrpc": "2.0", "method": "notify", "params": {}})
    )
    assert out is None


def test_parse_error_yields_jsonrpc_envelope() -> None:
    out = json.loads(AcpServer().handle_request("not json {{"))
    assert out["error"]["code"] == ACP_ERROR_PARSE


def test_serve_stream_preserves_order_and_skips_notifications() -> None:
    s = AcpServer()
    s.register("echo", lambda p: p)
    lines = [
        _req("echo", {"i": 1}, req_id=1),
        json.dumps({"jsonrpc": "2.0", "method": "echo", "params": {}}),  # notif
        _req("echo", {"i": 2}, req_id=2),
    ]
    out = [json.loads(x) for x in s.serve(lines)]
    assert [r["id"] for r in out] == [1, 2]
    assert [r["result"]["i"] for r in out] == [1, 2]
