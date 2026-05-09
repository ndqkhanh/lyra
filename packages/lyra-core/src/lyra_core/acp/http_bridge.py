"""HTTP bridge for the ACP method pack.

Wraps an :class:`AcpServer` (with its v3.11 methods registered) in a
stdlib ``http.server`` so real HTTP clients — web UIs, IDE
extensions, Slack bots, ACP-compatible tools — can POST JSON-RPC
requests instead of speaking the stdio protocol.

Endpoints:

* ``POST /jsonrpc`` — single-request JSON-RPC 2.0. Body is the
  JSON-RPC request; response body is the JSON-RPC response (or empty
  for a notification, mirroring the stdio behavior).
* ``GET  /healthz`` — liveness probe; returns ``{"ok": true,
  "method_count": N}``.
* ``GET  /methods`` — sorted list of registered method names.

Bright lines:

* ``LBL-HTTP-AUTH`` — when an ``AUTH_TOKEN`` is configured, requests
  must present a ``Bearer`` header that matches; mismatches return
  401 without invoking any method.
* ``LBL-HTTP-LIMIT`` — request bodies are capped at
  ``max_body_bytes`` (default 1 MiB) to prevent abuse.
* ``LBL-HTTP-LOOPBACK`` — by default the server binds to ``127.0.0.1``
  only. Callers must pass an explicit ``host="0.0.0.0"`` to expose
  beyond loopback.

Stdlib-only — no FastAPI / uvicorn dep. Production callers can drop
this in front of a real ASGI / WSGI stack but the contract stays
identical.
"""
from __future__ import annotations

import http.server
import json
import threading
from dataclasses import dataclass, field
from typing import Any

from .server import AcpServer


_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_MAX_BODY_BYTES = 1 << 20  # 1 MiB


# ---- typed errors ---------------------------------------------------


class HttpBridgeError(RuntimeError):
    """Raised when the bridge cannot be configured."""


# ---- handler factory ------------------------------------------------


def make_handler(server: AcpServer, *, auth_token: str | None, max_body_bytes: int):
    """Return a ``BaseHTTPRequestHandler`` subclass bound to the given ACP
    server. The factory pattern lets us close over instance state
    without subclassing at module-load time."""

    class V311HttpHandler(http.server.BaseHTTPRequestHandler):
        # Silence default request logging — callers wire their own.
        def log_message(self, fmt: str, *args: Any) -> None:  # noqa: D401
            return

        def _send_json(self, code: int, body: dict[str, Any]) -> None:
            payload = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _send_status(self, code: int) -> None:
            self.send_response(code)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _check_auth(self) -> bool:
            """Return False (and respond 401) if auth token mismatches."""
            if auth_token is None:
                return True
            header = self.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                self._send_json(401, {"error": "missing Bearer token (LBL-HTTP-AUTH)"})
                return False
            presented = header[len("Bearer ") :].strip()
            import hmac

            if not hmac.compare_digest(presented, auth_token):
                self._send_json(401, {"error": "Bearer token mismatch (LBL-HTTP-AUTH)"})
                return False
            return True

        def do_GET(self) -> None:  # noqa: N802
            if not self._check_auth():
                return
            if self.path == "/healthz":
                self._send_json(200, {"ok": True, "method_count": len(server.methods)})
                return
            if self.path == "/methods":
                self._send_json(200, {"methods": sorted(server.methods.keys())})
                return
            self._send_json(404, {"error": f"unknown path {self.path!r}"})

        def do_POST(self) -> None:  # noqa: N802
            if not self._check_auth():
                return
            if self.path != "/jsonrpc":
                self._send_json(404, {"error": f"unknown path {self.path!r}"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            if length > max_body_bytes:
                self._send_json(
                    413,
                    {"error": f"body too large (LBL-HTTP-LIMIT, max={max_body_bytes})"},
                )
                return
            try:
                body = self.rfile.read(length).decode("utf-8")
            except Exception as e:
                self._send_json(400, {"error": f"body read failed: {e}"})
                return
            response = server.handle_request(body)
            if response is None:
                # JSON-RPC notification — no body. 204 No Content.
                self._send_status(204)
                return
            try:
                payload = json.loads(response)
            except json.JSONDecodeError:
                # Defensive: server should always emit valid JSON.
                self._send_json(500, {"error": "server emitted invalid JSON"})
                return
            self._send_json(200, payload)

    return V311HttpHandler


# ---- server lifecycle -----------------------------------------------


@dataclass
class HttpBridge:
    """Threaded HTTP bridge for an :class:`AcpServer`.

    Usage::

        from lyra_core.acp import AcpServer, register_v311_methods, HttpBridge

        acp = AcpServer()
        register_v311_methods(acp)
        bridge = HttpBridge(acp_server=acp)
        addr = bridge.start()  # e.g. ('127.0.0.1', 39701)
        # ... clients POST to http://127.0.0.1:39701/jsonrpc ...
        bridge.stop()
    """

    acp_server: AcpServer
    host: str = _DEFAULT_HOST
    port: int = 0  # 0 = pick a free port
    auth_token: str | None = None
    max_body_bytes: int = _DEFAULT_MAX_BODY_BYTES
    _httpd: http.server.HTTPServer | None = field(default=None, init=False)
    _thread: threading.Thread | None = field(default=None, init=False)

    def start(self) -> tuple[str, int]:
        if self._httpd is not None:
            raise HttpBridgeError("bridge already started")
        handler_cls = make_handler(
            self.acp_server,
            auth_token=self.auth_token,
            max_body_bytes=self.max_body_bytes,
        )
        self._httpd = http.server.HTTPServer((self.host, self.port), handler_cls)
        addr = self._httpd.server_address
        self._thread = threading.Thread(
            target=self._httpd.serve_forever, daemon=True, name="acp-http-bridge"
        )
        self._thread.start()
        return addr  # type: ignore[return-value]

    def stop(self) -> None:
        if self._httpd is None:
            return
        try:
            self._httpd.shutdown()
        except Exception:
            pass
        try:
            self._httpd.server_close()
        except Exception:
            pass
        self._httpd = None
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None

    def __enter__(self) -> tuple[str, int]:
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()


__all__ = [
    "HttpBridge",
    "HttpBridgeError",
    "make_handler",
]
