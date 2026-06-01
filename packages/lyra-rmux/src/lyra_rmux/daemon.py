"""RmuxDaemon — daemon process that hosts IpcServer + SessionManager."""

from __future__ import annotations

import os
import signal
import sys
import time

from lyra_rmux.ipc_server import IpcServer
from lyra_rmux.session_manager import SessionManager


class RmuxDaemon:
    """Long-lived daemon that accepts IPC requests to manage PTY sessions.

    Usage::

        daemon = RmuxDaemon()
        daemon.start()
        # ... in another process ...
        daemon.stop()
    """

    def __init__(
        self,
        socket_path: str = "/tmp/lyra-rmux.sock",
        session_manager: SessionManager | None = None,
    ) -> None:
        self.socket_path = socket_path
        self._session_manager = session_manager or SessionManager()
        self._server = IpcServer(socket_path=socket_path)
        self._running = False
        self._register_routes()

    def _register_routes(self) -> None:
        """Wire SessionManager methods as IPC handlers."""
        sm = self._session_manager

        self._server.register("create_session", sm.create_session)
        self._server.register("list_sessions", sm.list_sessions)
        self._server.register("get_session", sm.get_session)
        self._server.register("kill_session", sm.kill_session)
        self._server.register("attach_session", sm.attach_session)
        self._server.register("detach_session", sm.detach_session)
        self._server.register("split_pane", sm.split_pane)
        self._server.register("send_keys", sm.send_keys)
        self._server.register("get_snapshot", sm.get_snapshot)
        self._server.register("resize_pane", sm.resize_pane)
        self._server.register("kill_pane", sm.kill_pane)

        def _daemon_status() -> dict:
            return {"running": self._running, "sessions": len(self._session_manager.list_sessions())}

        def _daemon_shutdown() -> str:
            self.stop()
            return "shutting down"

        self._server.register("daemon_status", _daemon_status)
        self._server.register("daemon_shutdown", _daemon_shutdown)

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the IPC server (non-blocking)."""
        self._running = True
        self._server.start()

    def stop(self) -> None:
        """Stop the IPC server and clean up all sessions."""
        self._running = False
        self._session_manager._pty.cleanup_all()
        self._server.stop()

    def serve_forever(self) -> None:
        """Start and block forever, handling signals for graceful shutdown."""
        self.start()

        def _handle_sig(signum: int, _frame: object) -> None:
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGTERM, _handle_sig)
        signal.signal(signal.SIGINT, _handle_sig)

        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()


def main() -> None:
    """Entry point for ``lyra-rmuxd`` CLI command."""
    import argparse

    parser = argparse.ArgumentParser(description="lyra-rmux daemon")
    parser.add_argument(
        "--socket",
        default="/tmp/lyra-rmux.sock",
        help="Unix socket path (default: /tmp/lyra-rmux.sock)",
    )
    parser.add_argument(
        "--detach",
        action="store_true",
        help="Fork into background (Unix only)",
    )
    args = parser.parse_args()

    if args.detach:
        pid = os.fork()
        if pid > 0:
            print(f"Daemon started (PID {pid})")
            sys.exit(0)
        os.setsid()
        # second fork to fully detach
        pid2 = os.fork()
        if pid2 > 0:
            sys.exit(0)
        sys.stdin.close()
        sys.stdout.close()
        sys.stderr.close()

    daemon = RmuxDaemon(socket_path=args.socket)
    daemon.serve_forever()


if __name__ == "__main__":
    main()
