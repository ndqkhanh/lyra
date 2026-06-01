"""RmuxClient — connect to the daemon via Unix socket JSON-RPC."""

from __future__ import annotations

import json
import socket
import uuid

from lyra_rmux.models import IpcMessage, IpcResponse


class RmuxClient:
    """Typed client for the lyra-rmuxd Unix-socket IPC daemon.

    Usage::

        client = RmuxClient("/tmp/lyra-rmux.sock")
        sess = client.create_session(name="my-session")
    """

    def __init__(self, socket_path: str = "/tmp/lyra-rmux.sock", connect_timeout: float = 5.0) -> None:
        self.socket_path = socket_path
        self._connect_timeout = connect_timeout

    def _call(self, method: str, **params: object) -> dict:
        msg = IpcMessage(method=method, params=params, msg_id=uuid.uuid4().hex)
        payload = json.dumps({
            "method": msg.method,
            "params": msg.params,
            "msg_id": msg.msg_id,
        }).encode("utf-8") + b"\n"

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self._connect_timeout)
        try:
            sock.connect(self.socket_path)
            sock.sendall(payload)
            fp = sock.makefile("rb")
            line = fp.readline()
            if not line:
                raise ConnectionError("Empty response from daemon")
            resp = json.loads(line.decode("utf-8"))
            if not resp.get("success", False):
                raise RuntimeError(resp.get("error", "Unknown RPC error"))
            return resp.get("result")
        finally:
            sock.close()

    # ------------------------------------------------------------------
    # typed RPC methods
    # ------------------------------------------------------------------

    def create_session(
        self,
        name: str = "",
        command: tuple[str, ...] | None = None,
        cwd: str | None = None,
        rows: int = 24,
        cols: int = 80,
    ) -> dict:
        """Create a new session. Returns the session dict."""
        return self._call(
            "create_session",
            name=name,
            command=tuple(command) if command else ("/bin/sh", "-i"),
            cwd=cwd,
            rows=rows,
            cols=cols,
        )

    def attach_session(self, session_id: str) -> dict | None:
        """Attach to a session."""
        return self._call("attach_session", session_id=session_id)

    def detach_session(self, session_id: str) -> dict:
        """Detach from a session."""
        return self._call("detach_session", session_id=session_id)

    def kill_session(self, session_id: str) -> None:
        """Kill a session."""
        self._call("kill_session", session_id=session_id)

    def list_sessions(self) -> list:
        """List all sessions."""
        return self._call("list_sessions")

    def split_pane(
        self,
        session_id: str,
        window_id: str = "win-1",
        vertical: bool = True,
        command: tuple[str, ...] | None = None,
    ) -> dict | None:
        """Split a pane."""
        return self._call(
            "split_pane",
            session_id=session_id,
            window_id=window_id,
            vertical=vertical,
            command=tuple(command) if command else ("/bin/sh", "-i"),
        )

    def send_keys(self, session_id: str, data: str, pane_id: str | None = None) -> dict:
        """Send text to a pane."""
        return self._call("send_keys", session_id=session_id, data=data, pane_id=pane_id)

    def get_snapshot(self, session_id: str, pane_id: str | None = None) -> dict | None:
        """Get a snapshot of pane content."""
        return self._call("get_snapshot", session_id=session_id, pane_id=pane_id)

    def resize_pane(self, session_id: str, rows: int, cols: int, pane_id: str | None = None) -> dict:
        """Resize a pane."""
        return self._call("resize_pane", session_id=session_id, rows=rows, cols=cols, pane_id=pane_id)

    def kill_pane(self, session_id: str, pane_id: str | None = None) -> dict:
        """Kill a pane."""
        return self._call("kill_pane", session_id=session_id, pane_id=pane_id)

    def daemon_status(self) -> dict:
        """Check daemon status."""
        return self._call("daemon_status")

    def daemon_shutdown(self) -> None:
        """Request daemon shutdown."""
        self._call("daemon_shutdown")
