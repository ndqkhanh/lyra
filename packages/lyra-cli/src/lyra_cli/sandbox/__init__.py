"""Ephemeral workspace providers (Phase N.5).

A *sandbox* is a temporary working directory the agent can write to,
run shell commands in, and tear down without polluting the user's
real repo. Inspired by DeerFlow's AioSandbox concept (drop-in,
docker-backed when available, local-tempdir fallback otherwise).

Two providers ship today:

* :class:`LocalSandbox` — pure-Python ``tempfile.mkdtemp`` workspace
  with a thin :func:`subprocess.run` wrapper. Always available, but
  shares the host's filesystem and shell, so trust the caller.
* :class:`DockerSandbox` — runs each command inside a fresh
  ``docker run`` invocation against a configurable image
  (``python:3.11-slim`` by default). Soft-dependent on the ``docker``
  CLI being on PATH; gracefully degrades to "unavailable" otherwise.

Both implement :class:`Sandbox` so callers (Lyra agents, eval
harnesses, the future ``lyra serve`` HTTP API) can swap one for the
other without rewriting tool definitions. :func:`pick_sandbox`
returns the best-effort default for the current host.
"""
from __future__ import annotations

from .base import (
    CommandResult,
    Sandbox,
    SandboxError,
    SandboxNotAvailable,
)
from .docker_sandbox import DockerSandbox
from .local_sandbox import LocalSandbox
from .picker import pick_sandbox

__all__ = [
    "CommandResult",
    "DockerSandbox",
    "LocalSandbox",
    "Sandbox",
    "SandboxError",
    "SandboxNotAvailable",
    "pick_sandbox",
]
