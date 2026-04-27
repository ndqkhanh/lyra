"""``lyra serve`` — expose the embedded client over HTTP.

Thin Typer wrapper around :func:`lyra_cli.serve.run_server`. Logic
lives in the WSGI app so unit tests don't need to bind sockets.
"""
from __future__ import annotations

import logging

import typer

from ..serve import run_server


def serve_command(
    host: str = typer.Option(
        "127.0.0.1", "--host",
        help="Address to bind. Use 0.0.0.0 to expose on all interfaces.",
    ),
    port: int = typer.Option(
        9099, "--port", "-p", help="TCP port to listen on.",
    ),
    log_level: str = typer.Option(
        "INFO", "--log-level", help="Logging level (DEBUG/INFO/WARNING/ERROR).",
    ),
) -> None:
    """Run the Lyra HTTP API.

    Set ``LYRA_API_TOKEN`` in the environment to require a Bearer
    token on every non-health endpoint. Without the env var the
    server is unauthenticated — fine for ``localhost``, never run
    that on a public IP.
    """
    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run_server(host=host, port=port)


__all__ = ["serve_command"]
