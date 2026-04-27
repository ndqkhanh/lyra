"""Remote-backend stubs: Docker / Modal / SSH / Daytona / Singularity.

Each raises :class:`NotImplementedError` with a pointer to the v1.7 /
v1.8 roadmap block that implements it. They're here so the rest of
the runtime can register and route *as if* the backends existed —
the discovery layer still lights up the right ``/backend`` listing.
"""
from __future__ import annotations

from dataclasses import dataclass

from .backend import CommandResult, TerminalError

__all__ = [
    "DockerBackend",
    "ModalBackend",
    "SSHBackend",
    "DaytonaBackend",
    "SingularityBackend",
]


def _unimplemented(name: str, block: str) -> CommandResult:
    raise TerminalError(
        f"{name} backend is a scaffold (ships in {block}); "
        "fall back to LocalBackend for now"
    )


@dataclass
class DockerBackend:
    name: str = "docker"
    image: str = "python:3.12-slim"

    def run(self, cmd: list[str], **_: object) -> CommandResult:
        return _unimplemented("docker", "v1.7 Phase 11 block 15")


@dataclass
class ModalBackend:
    name: str = "modal"

    def run(self, cmd: list[str], **_: object) -> CommandResult:
        return _unimplemented("modal", "v1.7 Phase 11 block 16")


@dataclass
class SSHBackend:
    name: str = "ssh"
    host: str = ""

    def run(self, cmd: list[str], **_: object) -> CommandResult:
        return _unimplemented("ssh", "v1.7 Phase 11 block 17")


@dataclass
class DaytonaBackend:
    name: str = "daytona"

    def run(self, cmd: list[str], **_: object) -> CommandResult:
        return _unimplemented("daytona", "v1.7 Phase 11 block 18")


@dataclass
class SingularityBackend:
    name: str = "singularity"

    def run(self, cmd: list[str], **_: object) -> CommandResult:
        return _unimplemented("singularity", "v1.7 Phase 11 block 19")
