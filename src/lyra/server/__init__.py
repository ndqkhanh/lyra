"""
Lyra HTTP API server — aiohttp-based backend for the Desktop GUI.

Exports the application factory and the ``run_server`` CLI entry point.
"""

from lyra.server.app import create_app, run_server

__all__ = [
    "create_app",
    "run_server",
]
