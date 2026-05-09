"""MCP autoload glue for the interactive REPL.

This module is imported once at REPL boot to populate
``session.mcp_servers`` from ``~/.lyra/mcp.json`` (user-global) and
``<repo>/.lyra/mcp.json`` (project-local). It does **not** spawn child
processes — that's deferred to first-use in
:func:`ensure_mcp_client_started`. Boot stays cheap so a user who
configured a server but doesn't end up calling its tools never pays
the handshake cost.

The autoload also exposes a tiny shutdown helper so the REPL can
terminate every spawned MCP child cleanly on exit (Ctrl-D /
``/exit``). Without this, npx/uvx-based servers like
``@modelcontextprotocol/server-filesystem`` linger as zombie children.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional


def autoload_mcp_servers(session: Any) -> None:
    """Populate ``session.mcp_servers`` from the standard config paths.

    Tolerates every realistic boot-time failure:

    * lyra-mcp not installed → no-op (Lyra still ships without MCP).
    * config file missing → empty list (the marquee "no MCP yet" state).
    * malformed JSON → entries with errors are stored on
      ``session._mcp_load_issues`` so ``/mcp doctor`` can show them.

    Honours ``LYRA_DISABLE_MCP_AUTOLOAD=1`` to disable the entire
    flow (test isolation, paranoid CI, etc.).
    """
    if os.environ.get("LYRA_DISABLE_MCP_AUTOLOAD", "").strip().lower() in (
        "1", "true", "yes", "on"
    ):
        session.mcp_servers = []
        session._mcp_load_issues = []
        return
    try:
        from lyra_mcp.client.config import load_mcp_config
    except Exception:
        session.mcp_servers = []
        session._mcp_load_issues = []
        return
    try:
        result = load_mcp_config(Path(session.repo_root))
    except Exception:
        session.mcp_servers = []
        session._mcp_load_issues = []
        return
    session.mcp_servers = list(result.servers)
    session._mcp_load_issues = list(result.issues)


def find_mcp_server(session: Any, name: str) -> Optional[Any]:
    """Return the :class:`MCPServerConfig` named ``name``, or ``None``."""
    for s in getattr(session, "mcp_servers", []) or []:
        if getattr(s, "name", None) == name:
            return s
    return None


def ensure_mcp_client_started(session: Any, name: str) -> Optional[Any]:
    """Spawn (and handshake) the MCP child for ``name`` on demand.

    Returns the live transport (already cached on
    ``session._mcp_clients``) or ``None`` if the server isn't
    declared, lyra-mcp isn't importable, or the handshake fails.

    Intentionally never raises so callers can do
    ``client = ensure_mcp_client_started(session, name)`` without
    having to wrap every call site in ``try: ... except: ...``.
    """
    cached = getattr(session, "_mcp_clients", {}).get(name)
    if cached is not None:
        return cached
    cfg = find_mcp_server(session, name)
    if cfg is None:
        return None
    try:
        from lyra_mcp.client.stdio import StdioMCPTransport
    except Exception:
        return None
    try:
        transport = StdioMCPTransport.start(
            command=list(cfg.command),
            env=dict(cfg.env),
            cwd=str(cfg.cwd) if cfg.cwd else None,
            server_name=cfg.name,
        )
    except Exception:
        return None
    if not hasattr(session, "_mcp_clients") or session._mcp_clients is None:
        session._mcp_clients = {}
    session._mcp_clients[name] = transport
    return transport


def shutdown_all_mcp_clients(session: Any) -> None:
    """Close every spawned MCP child, swallowing per-client errors.

    Called from REPL exit hooks. Best-effort — we don't want a hung
    server to block teardown of the whole REPL.
    """
    clients = getattr(session, "_mcp_clients", {}) or {}
    for transport in list(clients.values()):
        try:
            transport.close()
        except Exception:
            pass
    session._mcp_clients = {}


__all__ = [
    "autoload_mcp_servers",
    "ensure_mcp_client_started",
    "find_mcp_server",
    "shutdown_all_mcp_clients",
]
