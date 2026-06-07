"""
Session management endpoints.

Provides CRUD for conversation sessions using an in-memory store.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

import structlog
from aiohttp import web

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# In-memory session store
# ---------------------------------------------------------------------------

_SESSIONS: dict[str, dict[str, Any]] = {}


def _make_session(name: str) -> dict[str, Any]:
    """Create a new session object."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    session_id = uuid.uuid4().hex[:12]
    return {
        "id": session_id,
        "title": name or f"Session {len(_SESSIONS) + 1}",
        "created": int(now.timestamp()),
        "updated": int(now.timestamp()),
        "messageCount": 0,
        "status": "idle",
        "taskState": "completed",
        "processAlive": False,
    }


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


async def list_sessions(request: web.Request) -> web.Response:
    """List all sessions, newest first."""
    sessions = sorted(_SESSIONS.values(), key=lambda s: s["created"], reverse=True)
    return web.json_response({"sessions": sessions})


async def create_session(request: web.Request) -> web.Response:
    """Create a new session.

    Accepts ``{"name": "..."}`` (optional). Returns the created session object.
    """
    body = await request.json()
    name = body.get("name", "") if isinstance(body, dict) else ""
    session = _make_session(name)
    _SESSIONS[session["id"]] = session
    logger.info("session created", session_id=session["id"], name=name)
    return web.json_response({"session": session}, status=201)


async def delete_session(request: web.Request) -> web.Response:
    """Delete a session by ID. Returns 204 on success."""
    session_id = request.match_info.get("id", "")
    if session_id in _SESSIONS:
        del _SESSIONS[session_id]
        logger.info("session deleted", session_id=session_id)
    return web.Response(status=204)
