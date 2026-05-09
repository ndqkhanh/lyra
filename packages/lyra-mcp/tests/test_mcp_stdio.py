"""Phase C.1 (v2.5.0) — real MCP stdio JSON-RPC transport.

These tests pin down :class:`lyra_mcp.client.stdio.StdioMCPTransport`,
which speaks newline-delimited JSON-RPC 2.0 to a child MCP server's
stdin/stdout. A real production server (e.g. ``mcp-server-fs``) is
expensive to spawn and depends on ``npx``, so we use a pure-Python
"server" that writes the same JSON-RPC frames a spec-compliant server
would.

The fixture builds a child process that runs ``python -c "..."`` so
we exercise the *real* subprocess + pipe machinery — including the
spawn lifecycle, the handshake, the request/response correlation,
and the SIGTERM-on-close path. Only the server logic is fake; the
transport code is the same one production will use.

Coverage:

* handshake: ``initialize`` round-trip + ``initialized`` notification,
  capabilities + serverInfo are surfaced.
* ``list_tools`` returns the server's advertised tools array.
* ``call_tool`` round-trips a tool name + arguments and returns the
  unmodified content payload.
* request id correlation: a second call after the first works, and
  IDs increment monotonically.
* subprocess lifecycle: ``close()`` is idempotent and SIGTERMs the
  child.
* error paths: a JSON-RPC error response surfaces as
  ``MCPTransportError``; a missing executable surfaces as
  ``FileNotFoundError`` *before* anything weird happens.
* tools/list returning a non-list crashes loudly with
  ``MCPTransportError`` rather than silently lying.
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path
from typing import Iterator

import pytest

from lyra_mcp.client.stdio import (
    MCPHandshakeError,
    MCPTransportError,
    StdioMCPTransport,
)


# ---------------------------------------------------------------------------
# Fake-server helpers
# ---------------------------------------------------------------------------


def _fake_server_command(server_script: str) -> list[str]:
    """Return an argv for ``python -c <server_script>``.

    Uses ``sys.executable`` so the test always runs the same Python
    that's running the suite (no ``python`` PATH ambiguity).
    """
    return [sys.executable, "-c", server_script]


_BASE_SERVER = textwrap.dedent(
    """
    import json
    import sys

    def _send(obj):
        sys.stdout.write(json.dumps(obj) + "\\n")
        sys.stdout.flush()

    initialized = False
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = req.get("method")
        rid = req.get("id")
        if method == "initialize":
            _send({
                "jsonrpc": "2.0",
                "id": rid,
                "result": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "fake-fs", "version": "0.0.1"},
                },
            })
        elif method == "notifications/initialized":
            initialized = True
        elif method == "tools/list":
            _send({
                "jsonrpc": "2.0",
                "id": rid,
                "result": {
                    "tools": [
                        {
                            "name": "echo",
                            "description": "echo the input back",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"text": {"type": "string"}},
                                "required": ["text"],
                            },
                        }
                    ]
                },
            })
        elif method == "tools/call":
            params = req.get("params", {})
            name = params.get("name")
            args = params.get("arguments", {})
            if name == "echo":
                _send({
                    "jsonrpc": "2.0",
                    "id": rid,
                    "result": {
                        "content": [
                            {"type": "text", "text": args.get("text", "")}
                        ]
                    },
                })
            elif name == "boom":
                _send({
                    "jsonrpc": "2.0",
                    "id": rid,
                    "error": {
                        "code": -32603,
                        "message": "internal error: simulated",
                    },
                })
            else:
                _send({
                    "jsonrpc": "2.0",
                    "id": rid,
                    "error": {
                        "code": -32601,
                        "message": f"unknown tool {name!r}",
                    },
                })
        else:
            _send({
                "jsonrpc": "2.0",
                "id": rid,
                "error": {
                    "code": -32601,
                    "message": f"unknown method {method!r}",
                },
            })
    """
).strip()


# Banner-then-comply server: prints non-JSON garbage on stdout before
# the first real reply. Tests the reader's tolerance for garbage.
_BANNER_SERVER = textwrap.dedent(
    """
    import json
    import sys

    sys.stdout.write("Welcome to Fake MCP Server v0.1\\n")
    sys.stdout.flush()

    def _send(obj):
        sys.stdout.write(json.dumps(obj) + "\\n")
        sys.stdout.flush()

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        req = json.loads(line)
        method = req.get("method")
        rid = req.get("id")
        if method == "initialize":
            _send({
                "jsonrpc": "2.0",
                "id": rid,
                "result": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "serverInfo": {"name": "fake-banner", "version": "0.0.1"},
                },
            })
        elif method == "tools/list":
            _send({"jsonrpc": "2.0", "id": rid, "result": {"tools": []}})
    """
).strip()


# Server that ignores ``initialize`` to test handshake timeout.
_DEAD_SERVER = textwrap.dedent(
    """
    import sys
    while True:
        line = sys.stdin.readline()
        if not line:
            break
    """
).strip()


# Server whose tools/list returns a non-list result.
_BAD_TOOLS_SERVER = textwrap.dedent(
    """
    import json
    import sys

    def _send(obj):
        sys.stdout.write(json.dumps(obj) + "\\n")
        sys.stdout.flush()

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        req = json.loads(line)
        method = req.get("method")
        rid = req.get("id")
        if method == "initialize":
            _send({
                "jsonrpc": "2.0",
                "id": rid,
                "result": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "serverInfo": {"name": "fake", "version": "0"},
                },
            })
        elif method == "tools/list":
            _send({
                "jsonrpc": "2.0",
                "id": rid,
                "result": {"tools": "definitely-not-a-list"},
            })
    """
).strip()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def base_server() -> Iterator[StdioMCPTransport]:
    transport = StdioMCPTransport.start(
        _fake_server_command(_BASE_SERVER),
        server_name="fake-fs",
        init_timeout_s=5.0,
        call_timeout_s=5.0,
    )
    try:
        yield transport
    finally:
        transport.close()


# ---------------------------------------------------------------------------
# Handshake
# ---------------------------------------------------------------------------


def test_start_completes_handshake_and_records_server_info(
    base_server: StdioMCPTransport,
) -> None:
    assert base_server.server_info.get("name") == "fake-fs"
    assert base_server.server_info.get("version") == "0.0.1"
    assert "tools" in base_server.capabilities
    assert base_server._initialized is True


def test_start_raises_handshake_error_on_unresponsive_server() -> None:
    with pytest.raises(MCPHandshakeError):
        StdioMCPTransport.start(
            _fake_server_command(_DEAD_SERVER),
            server_name="dead",
            init_timeout_s=1.0,
        )


def test_start_raises_filenotfound_when_command_missing() -> None:
    with pytest.raises(FileNotFoundError):
        StdioMCPTransport.start(
            ["this-binary-definitely-does-not-exist-mcp"],
            server_name="missing",
            init_timeout_s=1.0,
        )


def test_start_tolerates_banner_lines_on_stdout() -> None:
    """npm-style wrappers print banners before the first JSON line."""
    transport = StdioMCPTransport.start(
        _fake_server_command(_BANNER_SERVER),
        server_name="banner",
        init_timeout_s=5.0,
    )
    try:
        assert transport.server_info.get("name") == "fake-banner"
        assert transport.list_tools() == []
    finally:
        transport.close()


# ---------------------------------------------------------------------------
# tools/list and tools/call
# ---------------------------------------------------------------------------


def test_list_tools_returns_advertised_array(base_server: StdioMCPTransport) -> None:
    tools = base_server.list_tools()
    assert len(tools) == 1
    echo = tools[0]
    assert echo["name"] == "echo"
    assert "inputSchema" in echo


def test_call_tool_round_trips_args(base_server: StdioMCPTransport) -> None:
    result = base_server.call_tool("echo", {"text": "hello mcp"})
    content = result.get("content", [])
    assert content == [{"type": "text", "text": "hello mcp"}]


def test_call_tool_propagates_jsonrpc_error_as_transport_error(
    base_server: StdioMCPTransport,
) -> None:
    with pytest.raises(MCPTransportError) as exc:
        base_server.call_tool("boom", {})
    assert "internal error: simulated" in str(exc.value)


def test_unknown_tool_raises_transport_error(base_server: StdioMCPTransport) -> None:
    with pytest.raises(MCPTransportError) as exc:
        base_server.call_tool("nope", {})
    assert "unknown tool" in str(exc.value)


def test_request_ids_increment_monotonically(
    base_server: StdioMCPTransport,
) -> None:
    base_server.list_tools()
    base_server.list_tools()
    base_server.list_tools()
    assert base_server._id_counter >= 3 + 1  # +1 for the initialize call


def test_list_tools_rejects_non_list_response() -> None:
    transport = StdioMCPTransport.start(
        _fake_server_command(_BAD_TOOLS_SERVER),
        server_name="bad-tools",
        init_timeout_s=5.0,
    )
    try:
        with pytest.raises(MCPTransportError) as exc:
            transport.list_tools()
        assert "non-list" in str(exc.value)
    finally:
        transport.close()


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_close_is_idempotent(base_server: StdioMCPTransport) -> None:
    base_server.close()
    base_server.close()  # second call must not raise
    assert base_server._closed is True


def test_call_after_close_raises_transport_error() -> None:
    transport = StdioMCPTransport.start(
        _fake_server_command(_BASE_SERVER),
        server_name="will-close",
    )
    transport.close()
    with pytest.raises(MCPTransportError):
        transport.list_tools()


def test_context_manager_closes_on_exit() -> None:
    with StdioMCPTransport.start(
        _fake_server_command(_BASE_SERVER),
        server_name="ctx-mgr",
    ) as transport:
        tools = transport.list_tools()
        assert tools[0]["name"] == "echo"
    assert transport._closed is True


# ---------------------------------------------------------------------------
# Adapter compatibility
# ---------------------------------------------------------------------------


def test_stdio_transport_satisfies_adapter_protocol(
    base_server: StdioMCPTransport,
) -> None:
    """:class:`StdioMCPTransport` must duck-type as :class:`MCPAdapter` Transport."""
    from lyra_mcp.client.adapter import MCPAdapter

    adapter = MCPAdapter(transport=base_server)
    assert isinstance(adapter.list_tools(), list)
    out = adapter.call_tool("echo", {"text": "via-adapter"})
    assert out["content"][0]["text"] == "via-adapter"
