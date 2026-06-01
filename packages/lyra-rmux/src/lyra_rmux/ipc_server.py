"""Unix-socket JSON-RPC IPC server — dispatches to SessionManager."""

from __future__ import annotations

import enum
import json
import os
import select
import socket
import threading
import traceback
from typing import Any, Callable

from lyra_rmux.models import IpcMessage, IpcResponse


_ROUTES: dict[str, Callable[..., Any]] = {}


def _rpc(method: str) -> Callable[[Any], Any]:
    """Decorator to register an RPC method handler."""

    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        _ROUTES[method] = fn
        return fn

    return deco


class IpcServer:
    """Unix-domain socket JSON-RPC server.

    Listens on a path (default ``/tmp/lyra-rmux.sock``).  Each connected
    client sends one JSON line: ``{"method": "...", "params": {...}}``.
    The server dispatches to a registered handler and writes a JSON
    response line back.

    Thread-per-connection for simplicity (low user count expected).
    """

    def __init__(self, socket_path: str = "/tmp/lyra-rmux.sock") -> None:
        self.socket_path = socket_path
        self._server: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._handlers: dict[str, Callable[..., Any]] = {}

    def register(self, method: str, handler: Callable[..., Any]) -> None:
        """Register an RPC handler."""
        self._handlers[method] = handler

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the IPC server in a daemon thread."""
        self._cleanup_stale_socket()
        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server.bind(self.socket_path)
        self._server.listen(5)
        self._server.settimeout(1.0)
        self._running = True
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signal the server to stop and clean up."""
        self._running = False
        if self._server:
            try:
                self._server.close()
            except OSError:
                pass
            self._server = None
        self._cleanup_stale_socket()

    # ------------------------------------------------------------------
    # accept loop
    # ------------------------------------------------------------------

    def _accept_loop(self) -> None:
        assert self._server is not None
        while self._running:
            try:
                conn, _addr = self._server.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            t = threading.Thread(target=self._handle_connection, args=(conn,), daemon=True)
            t.start()

    def _handle_connection(self, conn: socket.socket) -> None:
        with conn:
            fp = conn.makefile("rb")
            while self._running:
                line = fp.readline()
                if not line:
                    break
                try:
                    msg = json.loads(line.decode("utf-8"))
                    resp = self._dispatch(IpcMessage(**msg))
                except Exception as exc:
                    resp = IpcResponse(
                        msg_id="unknown",
                        success=False,
                        error=str(exc),
                    )
                raw = json.dumps({
                    "msg_id": resp.msg_id,
                    "success": resp.success,
                    "result": resp.result,
                    "error": resp.error,
                }).encode("utf-8") + b"\n"
                conn.sendall(raw)

    def _dispatch(self, msg: IpcMessage) -> IpcResponse:
        handler = self._handlers.get(msg.method)
        if handler is None:
            return IpcResponse(
                msg_id=msg.msg_id,
                success=False,
                error=f"Unknown method: {msg.method}",
            )
        try:
            result = handler(**msg.params)
            return IpcResponse(msg_id=msg.msg_id, success=True, result=_serialize(result))
        except Exception as exc:
            traceback.print_exc()
            return IpcResponse(
                msg_id=msg.msg_id,
                success=False,
                error=f"{type(exc).__name__}: {exc}",
            )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _cleanup_stale_socket(self) -> None:
        try:
            os.unlink(self.socket_path)
        except FileNotFoundError:
            pass
        except OSError:
            pass


def _serialize(obj: Any) -> Any:
    """Convert dataclass/enum instances to plain dicts for JSON."""
    if hasattr(obj, "_asdict"):
        return obj._asdict()
    if hasattr(obj, "__dataclass_fields__"):
        return {f: _serialize(getattr(obj, f)) for f in obj.__dataclass_fields__}
    if isinstance(obj, (list, tuple)):
        return [_serialize(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, enum.Enum):
        return obj.value
    return obj
