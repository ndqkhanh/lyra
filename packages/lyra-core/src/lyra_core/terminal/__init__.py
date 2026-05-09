"""Multi-backend terminal execution for agent-run shells.

Lyra treats a "shell" as a pluggable backend: local, Docker, Modal,
SSH, Daytona, Singularity. Each backend satisfies the same
:class:`TerminalBackend` protocol so policy wiring (dangerous-command
allow/deny) and output normalization live once in the core and not
in each transport.
"""
from __future__ import annotations

from .backend import (
    CommandResult,
    TerminalBackend,
    TerminalError,
)
from .local import LocalBackend

__all__ = [
    "CommandResult",
    "TerminalBackend",
    "TerminalError",
    "LocalBackend",
    "docker_backend",
]


def docker_backend(*args, **kwargs):
    """Lazy loader for :class:`DockerBackend` — avoids importing
    ``docker`` at package import time.
    """
    from .docker import DockerBackend  # local import keeps base import light

    return DockerBackend(*args, **kwargs)
