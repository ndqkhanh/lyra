"""
Health check endpoint.

Returns server status, version, and uptime.
"""

from __future__ import annotations

import time

from aiohttp import web

from lyra import __version__

_start_time = time.monotonic()


async def handle(request: web.Request) -> web.Response:
    """Return server health information.

    Returns:
        JSON with ``status``, ``version``, and ``uptime`` (seconds).
    """
    uptime = time.monotonic() - _start_time
    return web.json_response(
        {
            "status": "ok",
            "version": __version__,
            "uptime": round(uptime, 1),
        },
    )
