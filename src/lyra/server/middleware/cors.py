"""
CORS middleware for the Lyra API server.

Allows requests from ``127.0.0.1`` origins (the Electron desktop client).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from aiohttp import web

RequestHandler = Callable[[web.Request], Awaitable[web.StreamResponse]]

_ALLOWED_ORIGINS = frozenset({
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8580",
    "http://localhost:5173",
    "http://localhost:8580",
    "file://",
})

_ALLOW_METHODS = "GET, POST, DELETE, OPTIONS"
_ALLOW_HEADERS = "Content-Type, Authorization"


@web.middleware
async def middleware(
    request: web.Request,
    handler: RequestHandler,
) -> web.StreamResponse:
    """Add CORS headers to every response and handle preflight requests."""
    if request.method == "OPTIONS":
        response = web.Response(status=204)
    else:
        response = await handler(request)

    origin = request.headers.get("Origin", "")
    if origin in _ALLOWED_ORIGINS or origin.startswith("file://"):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = _ALLOW_METHODS
        response.headers["Access-Control-Allow-Headers"] = _ALLOW_HEADERS
        response.headers["Access-Control-Allow-Credentials"] = "true"

    return response
