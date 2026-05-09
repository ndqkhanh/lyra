"""End-to-end tests for the v3.11 HTTP bridge over the ACP method pack.

Spins up the bridge on an OS-assigned port, fires real HTTP POSTs at
it, and verifies the JSON-RPC responses.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from lyra_core.acp import AcpServer, HttpBridge, register_v311_methods


@pytest.fixture
def bridge(tmp_path):
    server = AcpServer()
    register_v311_methods(server, team_dir_root=tmp_path / "teams")
    b = HttpBridge(acp_server=server)
    addr = b.start()
    yield (b, addr)
    b.stop()


def _post(addr: tuple[str, int], path: str, body: dict, *, headers: dict | None = None) -> dict:
    url = f"http://{addr[0]}:{addr[1]}{path}"
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return {
                "status": resp.status,
                "body": json.loads(resp.read().decode() or "{}"),
            }
    except urllib.error.HTTPError as e:
        body_bytes = e.read()
        try:
            payload = json.loads(body_bytes.decode())
        except Exception:
            payload = {"raw": body_bytes.decode(errors="replace")}
        return {"status": e.code, "body": payload}


def _get(addr: tuple[str, int], path: str, *, headers: dict | None = None) -> dict:
    url = f"http://{addr[0]}:{addr[1]}{path}"
    req = urllib.request.Request(url, method="GET", headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return {
                "status": resp.status,
                "body": json.loads(resp.read().decode() or "{}"),
            }
    except urllib.error.HTTPError as e:
        return {"status": e.code, "body": json.loads(e.read().decode() or "{}")}


# ---- liveness + introspection -----------------------------------


def test_healthz(bridge):
    _, addr = bridge
    r = _get(addr, "/healthz")
    assert r["status"] == 200
    assert r["body"]["ok"] is True
    assert r["body"]["method_count"] >= 10


def test_methods_lists_v311(bridge):
    _, addr = bridge
    r = _get(addr, "/methods")
    assert r["status"] == 200
    methods = set(r["body"]["methods"])
    assert {"v311.bundle.info", "v311.scaling.snapshot"} <= methods


def test_unknown_path_404(bridge):
    _, addr = bridge
    r = _get(addr, "/nope")
    assert r["status"] == 404


# ---- jsonrpc happy path ------------------------------------------


def test_post_jsonrpc_scaling_snapshot(bridge):
    _, addr = bridge
    r = _post(addr, "/jsonrpc", {
        "jsonrpc": "2.0", "id": 1,
        "method": "v311.scaling.snapshot", "params": {},
    })
    assert r["status"] == 200
    assert "result" in r["body"]
    assert "best_lever" in r["body"]["result"]


def test_post_jsonrpc_unknown_method(bridge):
    _, addr = bridge
    r = _post(addr, "/jsonrpc", {
        "jsonrpc": "2.0", "id": 1,
        "method": "v311.does_not_exist", "params": {},
    })
    assert r["status"] == 200
    assert "error" in r["body"]
    assert r["body"]["error"]["code"] == -32601


def test_post_jsonrpc_notification_returns_204(bridge):
    """JSON-RPC notification (no id) returns 204 No Content."""
    _, addr = bridge
    r = _post(addr, "/jsonrpc", {
        "jsonrpc": "2.0",
        "method": "v311.scaling.snapshot", "params": {},
    })
    assert r["status"] == 204


def test_post_jsonrpc_invalid_path(bridge):
    _, addr = bridge
    r = _post(addr, "/wrong", {"jsonrpc": "2.0", "id": 1, "method": "v311.scaling.snapshot"})
    assert r["status"] == 404


# ---- bundle install over HTTP -----------------------------------


def test_post_jsonrpc_bundle_info_real_bundle(bridge):
    _, addr = bridge
    here = Path(__file__).resolve().parents[5]
    bundle_path = here / "projects" / "argus" / "bundle"
    r = _post(addr, "/jsonrpc", {
        "jsonrpc": "2.0", "id": 1,
        "method": "v311.bundle.info",
        "params": {"path": str(bundle_path)},
    })
    assert r["status"] == 200
    assert r["body"]["result"]["name"] == "argus-skill-router"


# ---- LBL-HTTP-AUTH ----------------------------------------------


def test_auth_required_when_token_set(tmp_path):
    server = AcpServer()
    register_v311_methods(server, team_dir_root=tmp_path / "teams")
    b = HttpBridge(acp_server=server, auth_token="s3cret")
    addr = b.start()
    try:
        # No auth header → 401.
        r = _get(addr, "/healthz")
        assert r["status"] == 401
        # Wrong token → 401.
        r = _get(addr, "/healthz", headers={"Authorization": "Bearer wrong"})
        assert r["status"] == 401
        # Right token → 200.
        r = _get(addr, "/healthz", headers={"Authorization": "Bearer s3cret"})
        assert r["status"] == 200
    finally:
        b.stop()


def test_auth_constant_time_compare(tmp_path):
    """Compare uses hmac.compare_digest — wrong-length tokens still
    produce 401 without leaking timing info."""
    server = AcpServer()
    register_v311_methods(server, team_dir_root=tmp_path / "teams")
    b = HttpBridge(acp_server=server, auth_token="s3cret")
    addr = b.start()
    try:
        r = _get(addr, "/healthz", headers={"Authorization": "Bearer x"})
        assert r["status"] == 401
    finally:
        b.stop()


# ---- LBL-HTTP-LIMIT ---------------------------------------------


def test_body_size_limit(tmp_path):
    server = AcpServer()
    register_v311_methods(server, team_dir_root=tmp_path / "teams")
    b = HttpBridge(acp_server=server, max_body_bytes=128)
    addr = b.start()
    try:
        # Build an oversize body.
        big = {"jsonrpc": "2.0", "id": 1, "method": "v311.scaling.snapshot",
               "params": {"junk": "x" * 256}}
        r = _post(addr, "/jsonrpc", big)
        assert r["status"] == 413
        assert "LBL-HTTP-LIMIT" in r["body"]["error"]
    finally:
        b.stop()


# ---- lifecycle ---------------------------------------------------


def test_start_twice_raises(tmp_path):
    server = AcpServer()
    register_v311_methods(server, team_dir_root=tmp_path / "teams")
    b = HttpBridge(acp_server=server)
    b.start()
    try:
        from lyra_core.acp import HttpBridgeError
        with pytest.raises(HttpBridgeError):
            b.start()
    finally:
        b.stop()


def test_stop_is_idempotent(tmp_path):
    server = AcpServer()
    register_v311_methods(server, team_dir_root=tmp_path / "teams")
    b = HttpBridge(acp_server=server)
    b.start()
    b.stop()
    b.stop()  # second stop is safe


def test_context_manager(tmp_path):
    server = AcpServer()
    register_v311_methods(server, team_dir_root=tmp_path / "teams")
    with HttpBridge(acp_server=server) as addr:
        r = _get(addr, "/healthz")
        assert r["status"] == 200


def test_loopback_default(tmp_path):
    """Bridge defaults to 127.0.0.1 binding (LBL-HTTP-LOOPBACK)."""
    server = AcpServer()
    register_v311_methods(server, team_dir_root=tmp_path / "teams")
    b = HttpBridge(acp_server=server)
    addr = b.start()
    try:
        assert addr[0] in ("127.0.0.1", "::1")
    finally:
        b.stop()
