"""Wave-D Task 12: MCP client + server + trust banner.

The Model-Context-Protocol (MCP) is the Anthropic-spec wire that
opencode and claw-code use to expose external tool catalogs to an
agent. Lyra's surface is intentionally minimal:

* :class:`MCPServer` registers a name + URL + trust state +
  optional tool list.
* :class:`MCPRegistry` is the in-memory ledger ``/mcp`` reads.
* :func:`trust_banner_for` returns the warning string the REPL
  shows when a server's trust state is ``"untrusted"`` (so a user
  always sees a one-line "this server can run code in your
  environment, allow?" prompt before the first call).

The wire transport itself is left to a future wave (the spec is
non-trivial, the value here is the *surface* — banner + registry —
that any transport will hang off of).

Six RED tests:

1. Empty registry has no servers.
2. ``register`` then ``list_servers`` returns the registered server.
3. ``register`` defaults trust to ``untrusted``.
4. ``trust(name)`` flips the state to ``trusted`` (and is sticky).
5. ``trust_banner_for`` includes the server name + warning text for
   untrusted servers, returns ``None`` for trusted.
6. Re-registering the same name updates the URL and tools without
   resetting the trust state.
"""
from __future__ import annotations

import pytest


def test_empty_registry_has_no_servers() -> None:
    from lyra_core.mcp import MCPRegistry

    assert MCPRegistry().list_servers() == []


def test_register_returns_server() -> None:
    from lyra_core.mcp import MCPRegistry

    reg = MCPRegistry()
    reg.register(name="fs", url="ws://localhost:3000", tools=["read", "list"])
    servers = reg.list_servers()
    assert len(servers) == 1
    assert servers[0].name == "fs"
    assert servers[0].url == "ws://localhost:3000"
    assert "read" in servers[0].tools


def test_register_defaults_to_untrusted() -> None:
    from lyra_core.mcp import MCPRegistry

    reg = MCPRegistry()
    reg.register(name="fs", url="ws://localhost:3000")
    assert reg.list_servers()[0].trust == "untrusted"


def test_trust_marks_server_as_trusted() -> None:
    from lyra_core.mcp import MCPRegistry

    reg = MCPRegistry()
    reg.register(name="fs", url="ws://localhost:3000")
    reg.trust("fs")
    assert reg.list_servers()[0].trust == "trusted"


def test_trust_banner_for_untrusted_and_trusted() -> None:
    from lyra_core.mcp import MCPRegistry, trust_banner_for

    reg = MCPRegistry()
    reg.register(name="fs", url="ws://localhost:3000")
    untrusted = reg.list_servers()[0]
    banner = trust_banner_for(untrusted)
    assert banner is not None
    assert "fs" in banner
    assert "untrusted" in banner.lower()

    reg.trust("fs")
    trusted = reg.list_servers()[0]
    assert trust_banner_for(trusted) is None


def test_re_register_keeps_trust() -> None:
    from lyra_core.mcp import MCPRegistry

    reg = MCPRegistry()
    reg.register(name="fs", url="ws://localhost:3000")
    reg.trust("fs")
    reg.register(name="fs", url="ws://localhost:4000", tools=["read"])
    server = reg.list_servers()[0]
    assert server.url == "ws://localhost:4000"
    assert server.trust == "trusted"
    assert server.tools == ["read"]
