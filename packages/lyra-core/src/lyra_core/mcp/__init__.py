"""Wave-D Task 12: MCP (Model-Context-Protocol) registry + trust banner.

Lyra ships the *user-facing* surface of MCP: a registry the
``/mcp`` slash reads, a typed :class:`MCPServer` record, and a
:func:`trust_banner_for` helper the REPL prints whenever an
untrusted server is about to be invoked.

The wire transport (websockets, stdio, etc.) is intentionally left
to a future wave — third-party MCP servers all ship their own
binaries today, and the surface that actually matters for the
parity matrix is "Lyra knows about MCP servers, surfaces them in
``/mcp``, and refuses to call an untrusted one without a banner".

Trust state is **per-process and sticky**: once a user runs
``/mcp trust <name>`` the registry remembers it for the session.
Persisting trust to disk across REPL runs is Wave-E (lands with
the broader policy file).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


TrustState = Literal["trusted", "untrusted"]


@dataclass
class MCPServer:
    """One row in the MCP registry."""

    name: str
    url: str
    trust: TrustState = "untrusted"
    tools: list[str] = field(default_factory=list)


class MCPRegistry:
    """In-memory ledger of registered MCP servers.

    The contract is intentionally tiny — :meth:`register`,
    :meth:`trust`, :meth:`untrust`, :meth:`get`, :meth:`list_servers`.
    The slash dispatcher and the trust banner read from it; the wire
    client (Wave-E) will write back the discovered tool list when
    it connects.
    """

    def __init__(self) -> None:
        self._servers: dict[str, MCPServer] = {}

    # ---- mutations ----------------------------------------------------

    def register(
        self,
        *,
        name: str,
        url: str,
        tools: list[str] | None = None,
    ) -> MCPServer:
        """Add a server (or refresh an existing one).

        Re-registering an existing name **preserves the trust state**
        — operators trust a server, not a particular URL revision.
        Updating tools is allowed (and expected; the wire client
        refreshes the catalog after each connect).
        """
        existing = self._servers.get(name)
        if existing is not None:
            existing.url = url
            if tools is not None:
                existing.tools = list(tools)
            return existing
        srv = MCPServer(
            name=name,
            url=url,
            trust="untrusted",
            tools=list(tools or []),
        )
        self._servers[name] = srv
        return srv

    def trust(self, name: str) -> bool:
        srv = self._servers.get(name)
        if srv is None:
            return False
        srv.trust = "trusted"
        return True

    def untrust(self, name: str) -> bool:
        srv = self._servers.get(name)
        if srv is None:
            return False
        srv.trust = "untrusted"
        return True

    def remove(self, name: str) -> bool:
        return self._servers.pop(name, None) is not None

    # ---- reads --------------------------------------------------------

    def get(self, name: str) -> MCPServer | None:
        return self._servers.get(name)

    def list_servers(self) -> list[MCPServer]:
        return list(self._servers.values())


def trust_banner_for(server: MCPServer) -> str | None:
    """Return the warning banner for an untrusted MCP server.

    Returns ``None`` when the server is trusted (the REPL hides the
    banner in that case so it doesn't become wallpaper).
    """
    if server.trust == "trusted":
        return None
    return (
        f"⚠ MCP server {server.name!r} ({server.url}) is untrusted. "
        f"Calling its tools may execute remote code in your environment. "
        f"Run /mcp trust {server.name} to allow."
    )


__all__ = [
    "MCPRegistry",
    "MCPServer",
    "TrustState",
    "trust_banner_for",
]
