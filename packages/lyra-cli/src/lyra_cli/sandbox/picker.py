"""Choose a sandbox provider for the current host.

Order of preference: Docker → Local. The picker probes each backend
and returns the first that constructs successfully — Docker is
preferred when available because it gives real isolation, but we
never *fail* on a host without Docker (the local fallback is
fine for trusted workloads like eval harnesses).

Callers can override the cascade with ``preference="local"`` when
they want a deterministic backend (tests, CI on a container-less
host).
"""
from __future__ import annotations

import shutil
from typing import Literal

from .base import Sandbox, SandboxNotAvailable
from .docker_sandbox import DockerSandbox
from .local_sandbox import LocalSandbox


_Preference = Literal["auto", "docker", "local"]


def pick_sandbox(
    *,
    preference: _Preference = "auto",
    image: str = "python:3.11-slim",
    network: str = "none",
) -> Sandbox:
    """Return a constructed :class:`Sandbox`.

    Args:
        preference: ``"auto"`` cascades docker → local;
            ``"docker"`` raises :class:`SandboxNotAvailable` if
            Docker isn't available; ``"local"`` always returns
            a :class:`LocalSandbox`.
        image: Docker image (only meaningful for the docker path).
        network: Docker network mode (only meaningful for docker).

    Raises:
        SandboxNotAvailable: when ``preference="docker"`` but
            Docker isn't on PATH / the daemon is down.
    """
    if preference == "local":
        return LocalSandbox()
    if preference == "docker":
        return DockerSandbox(image=image, network=network)
    if preference != "auto":  # pragma: no cover - defensive
        raise ValueError(f"unknown sandbox preference: {preference!r}")
    # auto cascade
    if shutil.which("docker") is not None:
        try:
            return DockerSandbox(image=image, network=network)
        except SandboxNotAvailable:
            pass
    return LocalSandbox()


__all__ = ["pick_sandbox"]
