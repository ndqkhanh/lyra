"""
Request logging middleware for the Lyra API server.

Logs every request with method, path, status code, and duration.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

import structlog
from aiohttp import web

RequestHandler = Callable[[web.Request], Awaitable[web.StreamResponse]]

logger = structlog.get_logger(__name__)


@web.middleware
async def middleware(
    request: web.Request,
    handler: RequestHandler,
) -> web.StreamResponse:
    """Log the incoming request and measure response time."""
    start = time.monotonic()
    try:
        response = await handler(request)
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "request",
            method=request.method,
            path=request.path,
            status=response.status,
            duration_ms=round(elapsed_ms, 1),
        )
        return response
    except web.HTTPException as exc:
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "request",
            method=request.method,
            path=request.path,
            status=exc.status,
            duration_ms=round(elapsed_ms, 1),
        )
        raise
