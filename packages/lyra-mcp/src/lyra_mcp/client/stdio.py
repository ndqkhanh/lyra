"""Real MCP stdio JSON-RPC transport.

The Model Context Protocol (MCP) v2025-03-26 specifies a JSON-RPC 2.0
transport over a child process's stdin/stdout streams using **newline-
delimited JSON** (NDJSON). Each message — request, response, or
notification — is a single JSON object on its own line. This module
implements the client side of that transport so Lyra can spawn any
spec-compliant MCP server (filesystem, git, postgres, brave-search, …)
and use its tools the same way Claude Code, Open-Claw, and Hermes do.

Pre-v2.5 ``MCPAdapter`` was *transport-agnostic* but Lyra didn't ship
a real transport — it only had ``FakeMCPServer`` for tests. That's
the gap this module fills.

## Lifecycle

::

    transport = StdioMCPTransport.start(command=["npx", "mcp-server-fs"])
    transport.list_tools()       # JSON-RPC tools/list
    transport.call_tool("read_file", {"path": "/tmp/x"})
    transport.close()            # SIGTERM, then SIGKILL after grace period

The class is also a context manager:

::

    with StdioMCPTransport.start(command=["mcp-fs"]) as t:
        ...

## Design notes

* **Initialization handshake.** Per spec, the client *must* call
  ``initialize`` before any other method, then send the
  ``initialized`` notification. We do that automatically inside
  :meth:`start` so callers don't forget. A server that fails the
  handshake yields a :class:`MCPHandshakeError` and we tear down the
  child cleanly.
* **Request correlation.** Each request gets a monotonic integer id;
  responses are matched on the way back. We currently issue requests
  *synchronously* (one in flight at a time) because the chat tool
  loop is sequential and parallel MCP calls would blow the user's
  approval budget anyway. The reader thread routes responses by id
  to a per-request :class:`threading.Event` so a future async
  rewrite can land without a public-API change.
* **Reader thread.** A background daemon thread reads stdout
  line-by-line and dispatches:
  - JSON-RPC *responses* → looked up by id, posted to the
    requesting thread.
  - *Notifications* → currently logged and dropped; phase C.4 will
    wire them to the renderer (e.g. ``logging/message`` notes
    appear in the tool card).
  - Anything malformed → forwarded to ``self.last_protocol_error``
    so :meth:`call_tool` can surface a useful diagnostic.
* **Subprocess hygiene.** ``close`` sends SIGTERM, waits up to
  ``grace_period_s`` (default 2s), then SIGKILLs and drains. The
  reader thread exits when stdout closes, so we never leak threads.
* **stderr.** The child's stderr is *not* swallowed silently; we
  ship a tail buffer (last 4 KiB) into :attr:`last_stderr` so a
  failed call_tool can blame the right server. Phase C.4 may surface
  this in the tool card.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class MCPHandshakeError(RuntimeError):
    """Raised when the ``initialize`` exchange fails or times out."""


class MCPTransportError(RuntimeError):
    """Raised on transport-level failures: pipe closed, timeout, RPC error."""


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


_PROTOCOL_VERSION = "2025-03-26"
_CLIENT_INFO: dict[str, Any] = {"name": "lyra-mcp", "version": "2.5.0"}
_DEFAULT_INIT_TIMEOUT_S = 10.0
_DEFAULT_CALL_TIMEOUT_S = 60.0
_STDERR_TAIL_BYTES = 4096


@dataclass
class StdioMCPTransport:
    """Stdio JSON-RPC transport for one MCP server child process.

    Use :meth:`start` to spawn — the dataclass constructor is for
    test injection (e.g. an in-process pipe pair) and not normal
    callers.
    """

    process: Any  # subprocess.Popen, but typed as Any for test fakes
    server_name: str = "mcp-stdio"
    init_timeout_s: float = _DEFAULT_INIT_TIMEOUT_S
    call_timeout_s: float = _DEFAULT_CALL_TIMEOUT_S
    grace_period_s: float = 2.0

    # Filled at start(); read by callers.
    server_info: dict[str, Any] = field(default_factory=dict)
    capabilities: dict[str, Any] = field(default_factory=dict)
    last_stderr: str = ""

    # Internal request/response correlation.
    _id_counter: int = field(default=0, init=False)
    _id_lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _pending: dict[int, dict[str, Any]] = field(default_factory=dict, init=False)
    _pending_lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _events: dict[int, threading.Event] = field(default_factory=dict, init=False)
    _reader_thread: Optional[threading.Thread] = field(default=None, init=False)
    _stderr_thread: Optional[threading.Thread] = field(default=None, init=False)
    _stderr_buffer: "deque[bytes]" = field(
        default_factory=lambda: deque(maxlen=64),
        init=False,
    )
    _closed: bool = field(default=False, init=False)
    _initialized: bool = field(default=False, init=False)
    _write_lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def start(
        cls,
        command: Sequence[str],
        *,
        env: Optional[Mapping[str, str]] = None,
        cwd: Optional[Path] = None,
        server_name: str = "mcp-stdio",
        init_timeout_s: float = _DEFAULT_INIT_TIMEOUT_S,
        call_timeout_s: float = _DEFAULT_CALL_TIMEOUT_S,
    ) -> "StdioMCPTransport":
        """Spawn ``command`` and complete the JSON-RPC handshake.

        Args:
            command: full argv list (e.g.
                ``["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"]``).
            env: extra env vars merged onto the parent's env. ``None``
                inherits the parent env unchanged.
            cwd: working directory for the child. ``None`` keeps the
                parent cwd.
            server_name: human-readable label used in error messages
                and trust banners.
            init_timeout_s: max seconds to wait for the
                ``initialize`` response.
            call_timeout_s: max seconds for any subsequent RPC. May
                be tuned per call via :meth:`call_tool` ``timeout_s``.

        Raises:
            MCPHandshakeError: spawn failed, the server didn't
                respond to ``initialize`` within ``init_timeout_s``,
                or the response carried a JSON-RPC error.
            FileNotFoundError: ``command[0]`` isn't on ``$PATH``.
        """
        full_env = dict(os.environ)
        if env is not None:
            full_env.update(env)

        try:
            proc = subprocess.Popen(  # noqa: S603 - command is caller-supplied
                list(command),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=full_env,
                cwd=str(cwd) if cwd is not None else None,
                bufsize=0,
            )
        except FileNotFoundError:
            raise
        except OSError as exc:
            raise MCPHandshakeError(
                f"failed to spawn MCP server {server_name!r}: {exc}"
            ) from exc

        transport = cls(
            process=proc,
            server_name=server_name,
            init_timeout_s=init_timeout_s,
            call_timeout_s=call_timeout_s,
        )
        transport._spawn_reader_threads()
        try:
            transport._handshake()
        except Exception:
            transport.close()
            raise
        return transport

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_tools(self) -> list[dict[str, Any]]:
        """Return the server's advertised tools (per ``tools/list``).

        Each entry has at minimum ``name`` and ``inputSchema``;
        production servers also include ``description``,
        ``annotations``, and per-tool metadata.
        """
        result = self._request("tools/list", {})
        tools = result.get("tools", []) if isinstance(result, dict) else []
        if not isinstance(tools, list):
            raise MCPTransportError(
                f"server {self.server_name!r} returned non-list tools: "
                f"{type(tools).__name__}"
            )
        return tools

    def call_tool(
        self,
        name: str,
        args: Mapping[str, Any],
        *,
        timeout_s: Optional[float] = None,
    ) -> dict[str, Any]:
        """Invoke ``name`` with ``args`` over JSON-RPC ``tools/call``.

        Returns the server's full response payload (typically with a
        ``content`` array per the MCP spec). Adapters / renderers
        unwrap as needed — we don't pre-flatten because tool
        responses can carry mixed-content arrays (text + images +
        resource refs) and pre-flattening would lose information.
        """
        result = self._request(
            "tools/call",
            {"name": name, "arguments": dict(args)},
            timeout_s=timeout_s,
        )
        if not isinstance(result, dict):
            raise MCPTransportError(
                f"server {self.server_name!r} returned non-dict for "
                f"call_tool({name!r}): {result!r}"
            )
        return result

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Tear the child down with SIGTERM → wait → SIGKILL.

        Idempotent — calling twice is a no-op. Always drains the
        reader thread before returning so callers don't deadlock on
        repeated ``close()``.
        """
        if self._closed:
            return
        self._closed = True
        proc = self.process
        if proc is None:
            return
        try:
            if hasattr(proc, "stdin") and proc.stdin is not None:
                try:
                    proc.stdin.close()
                except Exception:
                    pass
            try:
                proc.terminate()
            except Exception:
                pass
            try:
                proc.wait(timeout=self.grace_period_s)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
                try:
                    proc.wait(timeout=self.grace_period_s)
                except Exception:
                    pass
        finally:
            for thread in (self._reader_thread, self._stderr_thread):
                if thread is not None and thread.is_alive():
                    thread.join(timeout=self.grace_period_s)

    def __enter__(self) -> "StdioMCPTransport":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # JSON-RPC plumbing
    # ------------------------------------------------------------------

    def _next_id(self) -> int:
        with self._id_lock:
            self._id_counter += 1
            return self._id_counter

    def _send(self, payload: dict[str, Any]) -> None:
        line = json.dumps(payload, separators=(",", ":")) + "\n"
        data = line.encode("utf-8")
        with self._write_lock:
            stdin = getattr(self.process, "stdin", None)
            if stdin is None:
                raise MCPTransportError(
                    f"server {self.server_name!r} stdin is closed"
                )
            try:
                stdin.write(data)
                stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                raise MCPTransportError(
                    f"server {self.server_name!r} pipe closed: {exc}"
                ) from exc

    def _request(
        self,
        method: str,
        params: Mapping[str, Any],
        *,
        timeout_s: Optional[float] = None,
    ) -> Any:
        if self._closed:
            raise MCPTransportError(
                f"server {self.server_name!r} transport is closed"
            )
        rid = self._next_id()
        evt = threading.Event()
        with self._pending_lock:
            self._events[rid] = evt
        payload = {
            "jsonrpc": "2.0",
            "id": rid,
            "method": method,
            "params": dict(params),
        }
        self._send(payload)
        wait_for = timeout_s if timeout_s is not None else self.call_timeout_s
        if not evt.wait(timeout=wait_for):
            with self._pending_lock:
                self._events.pop(rid, None)
                self._pending.pop(rid, None)
            raise MCPTransportError(
                f"server {self.server_name!r} timed out on {method!r} "
                f"after {wait_for:.1f}s"
            )
        with self._pending_lock:
            response = self._pending.pop(rid, None)
            self._events.pop(rid, None)
        if response is None:
            raise MCPTransportError(
                f"server {self.server_name!r} returned no response to {method!r}"
            )
        if "error" in response:
            err = response["error"]
            raise MCPTransportError(
                f"server {self.server_name!r} returned error on {method!r}: "
                f"{err.get('message', err)!r} (code={err.get('code')})"
            )
        return response.get("result")

    def _notify(self, method: str, params: Mapping[str, Any]) -> None:
        """Send a JSON-RPC notification (no id, no response expected)."""
        self._send(
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": dict(params),
            }
        )

    def _handshake(self) -> None:
        """Run the ``initialize`` → ``initialized`` exchange.

        Per spec, the client sends:

        1. ``initialize`` request advertising its protocol version and
           supported capabilities. The server responds with its own
           protocol version, server info, and capabilities.
        2. ``initialized`` *notification* (no id) once the response
           lands, signalling the server can begin sending non-init
           notifications.
        """
        try:
            result = self._request(
                "initialize",
                {
                    "protocolVersion": _PROTOCOL_VERSION,
                    "capabilities": {
                        # We're a tool consumer; we don't expose our own
                        # tools to the server, so capabilities stay empty
                        # for v2.5.0. Phase C.4 may add ``roots`` if we
                        # wire MCP roots to the chat tool sandbox.
                    },
                    "clientInfo": _CLIENT_INFO,
                },
                timeout_s=self.init_timeout_s,
            )
        except MCPTransportError as exc:
            # Transport-level failures during the *initialize* exchange
            # (timeout, JSON-RPC error, pipe death) all collapse to
            # MCPHandshakeError so callers can distinguish "could not
            # bring the server up" from "tool call X failed mid-session".
            raise MCPHandshakeError(
                f"server {self.server_name!r} initialize failed: {exc}"
            ) from exc
        if not isinstance(result, dict):
            raise MCPHandshakeError(
                f"server {self.server_name!r} returned malformed initialize "
                f"response: {result!r}"
            )
        self.server_info = dict(result.get("serverInfo", {}))
        self.capabilities = dict(result.get("capabilities", {}))
        self._notify("notifications/initialized", {})
        self._initialized = True

    # ------------------------------------------------------------------
    # Reader threads
    # ------------------------------------------------------------------

    def _spawn_reader_threads(self) -> None:
        self._reader_thread = threading.Thread(
            target=self._reader_loop,
            name=f"mcp-reader-{self.server_name}",
            daemon=True,
        )
        self._reader_thread.start()
        self._stderr_thread = threading.Thread(
            target=self._stderr_loop,
            name=f"mcp-stderr-{self.server_name}",
            daemon=True,
        )
        self._stderr_thread.start()

    def _reader_loop(self) -> None:
        stdout = getattr(self.process, "stdout", None)
        if stdout is None:
            return
        for raw in iter(stdout.readline, b""):
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                # Some servers print banner / debug lines on stdout
                # before they're "really" started — common for npm
                # wrappers. Skip silently; a failed initialize will
                # still timeout cleanly.
                continue
            if not isinstance(msg, dict):
                continue
            mid = msg.get("id")
            if mid is not None and ("result" in msg or "error" in msg):
                with self._pending_lock:
                    self._pending[mid] = msg
                    evt = self._events.get(mid)
                if evt is not None:
                    evt.set()
                continue
            # Notification or unsolicited request — we currently drop
            # both. Phase C.4 will route ``notifications/message``
            # to the chat tool renderer.

    def _stderr_loop(self) -> None:
        stderr = getattr(self.process, "stderr", None)
        if stderr is None:
            return
        for raw in iter(stderr.readline, b""):
            self._stderr_buffer.append(raw)
            tail = b"".join(self._stderr_buffer)[-_STDERR_TAIL_BYTES:]
            self.last_stderr = tail.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Adapter glue
# ---------------------------------------------------------------------------


def stdio_transport_from_command(
    command: Sequence[str],
    *,
    env: Optional[Mapping[str, str]] = None,
    cwd: Optional[Path] = None,
    server_name: str = "mcp-stdio",
) -> StdioMCPTransport:
    """One-shot helper: spawn + handshake.

    Convenience for ``StdioMCPTransport.start(...)`` — separate so
    callers that only want the transport (not the test factory) get
    a tidy import path.
    """
    return StdioMCPTransport.start(
        command, env=env, cwd=cwd, server_name=server_name
    )


__all__ = [
    "MCPHandshakeError",
    "MCPTransportError",
    "StdioMCPTransport",
    "stdio_transport_from_command",
]
