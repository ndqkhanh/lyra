"""
Lyra HTTP API server application factory.

Creates and configures an ``aiohttp.web.Application`` with all routes and
middleware wired up.
"""

from __future__ import annotations

import structlog
from aiohttp import web

from lyra.server.middleware import cors, logging as logging_mw
from lyra.server.routes import chat, health, providers, sessions

logger = structlog.get_logger(__name__)


def create_app() -> web.Application:
    """Create and return a fully configured Lyra API application.

    Middleware is applied in order: CORS first, then request logging.
    """
    app = web.Application(middlewares=[cors.middleware, logging_mw.middleware])

    # Health
    app.router.add_get("/health", health.handle)

    # Providers
    app.router.add_get("/providers", providers.handle)

    # Sessions
    app.router.add_get("/sessions", sessions.list_sessions)
    app.router.add_post("/sessions", sessions.create_session)
    app.router.add_delete("/sessions/{id}", sessions.delete_session)

    # Chat
    app.router.add_post("/chat/{id}/stream", chat.stream_chat)

    logger.info("lyra server app created")
    return app


def run_server(port: int = 8580) -> None:
    """Run the Lyra API server.

    Args:
        port: HTTP listen port (default 8580).
    """
    app = create_app()
    logger.info("starting lyra server", port=port)
    web.run_app(app, port=port)


if __name__ == "__main__":
    run_server()
