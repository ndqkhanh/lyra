"""
Relay WebSocket Transport — aiohttp WebSocket handler for the Lyra relay.

Wires the RelayServer session/credential management to actual WebSocket
connections. Local Lyra processes connect as LOCAL clients; browsers/phones
connect as REMOTE clients. Messages are routed between them.

References: §4.29 Remote Access Plan, Claude Code Remote Control
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import structlog

from lyra.server.relay import RelayServer, SessionStatus

logger = structlog.get_logger(__name__)


async def handle_local_ws(
    relay: RelayServer,
    ws: Any,
    session_id: str,
) -> None:
    """Handle a WebSocket connection from a local Lyra process.

    The local process sends:
    - ``{"type": "heartbeat"}`` — keepalive (every 30s)
    - ``{"type": "message", "to": "<client_id>", "data": {...}}`` — route to remote

    The local process receives:
    - ``{"type": "message", "from": "<client_id>", "data": {...}}`` — from remote
    - ``{"type": "remote_joined", "client_id": "..."}`` — new remote attached
    - ``{"type": "remote_left", "client_id": "..."}`` — remote disconnected
    """
    session = relay.get_session(session_id)
    if session is None:
        await ws.close(code=4004, reason="Unknown session")
        return

    session.local_ws = ws
    session.status = SessionStatus.ONLINE

    try:
        async for msg in ws:
            if msg.type == "close":
                break

            try:
                data = json.loads(msg.data) if msg.data else {}
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type", "")

            if msg_type == "heartbeat":
                relay.heartbeat(session_id)

            elif msg_type == "message":
                target_id = data.get("to", "")
                payload = data.get("data", {})
                await _route_to_remote(session, target_id, payload)

            elif msg_type == "broadcast":
                payload = data.get("data", {})
                await _broadcast_to_remotes(session, payload)

    except (asyncio.CancelledError, ConnectionError):
        pass
    finally:
        session.local_ws = None
        if relay.get_session(session_id):
            session.status = SessionStatus.OFFLINE
        logger.info("local disconnected", session_id=session_id)


async def handle_remote_ws(
    relay: RelayServer,
    ws: Any,
    session_id: str,
    credential: str,
) -> None:
    """Handle a WebSocket connection from a remote client (browser/phone).

    The remote client sends:
    - ``{"type": "message", "data": {...}}`` — send to local process

    The remote client receives:
    - ``{"type": "connected", "session_name": "..."}`` — handshake complete
    - ``{"type": "message", "data": {...}}`` — from local process
    """
    if not relay.verify_attach(session_id, credential):
        await ws.close(code=4001, reason="Invalid credential")
        return

    session = relay.get_session(session_id)
    if session is None:
        await ws.close(code=4004, reason="Unknown session")
        return

    client_id = f"remote-{hex(int(time.time() * 1000))[-8:]}"
    session.remote_clients[client_id] = ws

    # Notify local that a remote joined
    if session.local_ws:
        await _safe_send(session.local_ws, {
            "type": "remote_joined",
            "client_id": client_id,
        })

    # Send handshake
    await _safe_send(ws, {
        "type": "connected",
        "session_name": session.name,
        "client_id": client_id,
    })

    try:
        async for msg in ws:
            if msg.type == "close":
                break

            try:
                data = json.loads(msg.data) if msg.data else {}
            except json.JSONDecodeError:
                continue

            if data.get("type") == "message" and session.local_ws:
                await _safe_send(session.local_ws, {
                    "type": "message",
                    "from": client_id,
                    "data": data.get("data", {}),
                })

    except (asyncio.CancelledError, ConnectionError):
        pass
    finally:
        session.remote_clients.pop(client_id, None)
        if session.local_ws:
            await _safe_send(session.local_ws, {
                "type": "remote_left",
                "client_id": client_id,
            })
        logger.info("remote disconnected", session_id=session_id, client_id=client_id)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _route_to_remote(
    session: Any, target_id: str, payload: dict[str, Any]
) -> None:
    """Route a message from local to a specific remote client."""
    ws = session.remote_clients.get(target_id)
    if ws:
        await _safe_send(ws, {"type": "message", "from": "local", "data": payload})


async def _broadcast_to_remotes(
    session: Any, payload: dict[str, Any]
) -> None:
    """Broadcast a message from local to ALL remote clients."""
    for ws in list(session.remote_clients.values()):
        await _safe_send(ws, {"type": "message", "from": "local", "data": payload})


async def _safe_send(ws: Any, data: dict[str, Any]) -> None:
    """Send JSON through a WebSocket, ignoring connection errors."""
    try:
        await ws.send_json(data)
    except (ConnectionError, asyncio.CancelledError):
        pass
