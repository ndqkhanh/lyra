"""Docker-backed sandbox.

When the ``docker`` CLI is on PATH and the daemon is up, each
:meth:`DockerSandbox.run` call shells out to ``docker run --rm``
against a configurable image, mounting the host workspace at
``/workspace`` and pinning the working directory there. This gives
us cheap, throw-away isolation per command without holding a
container open between turns — fewer moving parts than the
``docker exec`` approach.

Files are written / read through the bind-mounted host directory
so :meth:`write_file` / :meth:`read_file` reuse the same
:class:`LocalSandbox` machinery: the *workspace* is just a tempdir
that happens to also live inside a container at run time.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Iterable, Mapping

from .base import CommandResult, SandboxError, SandboxNotAvailable
from .local_sandbox import LocalSandbox


class DockerSandbox(LocalSandbox):
    """Bind-mount a tempdir into a fresh container per command.

    Args:
        image: Docker image to run. Defaults to a tiny Python image
            (``python:3.11-slim``) so the common eval/code-exec
            workload Just Works. Override per call site for
            language-specific tooling.
        prefix: Tempdir prefix.
        docker_bin: Override for the docker CLI path. Tests pass an
            executable shim; production code leaves it ``None`` so
            the binary is resolved from PATH.
        network: ``"none"`` (default) cuts the container off from
            the network — appropriate for "run untrusted snippet"
            workloads. Pass ``"bridge"`` (or another network name)
            to enable outbound traffic explicitly.
    """

    def __init__(
        self,
        *,
        image: str = "python:3.11-slim",
        prefix: str = "lyra-sandbox-",
        docker_bin: str | None = None,
        network: str = "none",
    ) -> None:
        self._docker_bin = docker_bin or shutil.which("docker")
        if not self._docker_bin:
            raise SandboxNotAvailable(
                "`docker` CLI not found on PATH; install Docker or use LocalSandbox"
            )
        self._image = image
        self._network = network
        super().__init__(prefix=prefix)

    def run(
        self,
        argv: Iterable[str] | str,
        *,
        timeout: float | None = None,
        env: Mapping[str, str] | None = None,
        cwd: str | None = None,
    ) -> CommandResult:
        if self._closed:
            raise SandboxError("sandbox already closed")

        if isinstance(argv, str):
            display_argv = [argv]
            inner: list[str] = ["bash", "-c", argv]
        else:
            display_argv = list(argv)
            inner = display_argv

        # Construct the docker invocation. ``--rm`` so we never leak
        # containers, ``--network=<network>`` for opt-in networking,
        # ``-v <host>:/workspace`` to surface the workspace inside
        # the container without cp.
        cmd: list[str] = [
            self._docker_bin, "run", "--rm",
            "--network", self._network,
            "-v", f"{self._workspace}:/workspace",
            "-w", "/workspace" if cwd is None else f"/workspace/{cwd}",
        ]
        for k, v in (env or {}).items():
            cmd += ["-e", f"{k}={v}"]
        cmd.append(self._image)
        cmd += inner

        start = time.time()
        timed_out = False
        try:
            proc = subprocess.run(  # noqa: S603 — explicit argv
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            stdout, stderr, exit_code = proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired as e:
            timed_out = True
            exit_code = 124
            stdout = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode("utf-8", "replace")
            stderr = e.stderr if isinstance(e.stderr, str) else (e.stderr or b"").decode("utf-8", "replace")
        except FileNotFoundError as e:
            # The CLI vanished mid-run — surface as not-available so
            # the picker can downgrade to LocalSandbox on retry.
            raise SandboxNotAvailable(f"docker CLI disappeared: {e}") from e
        duration_ms = (time.time() - start) * 1000.0

        return CommandResult(
            argv=display_argv,
            exit_code=exit_code,
            stdout=stdout or "",
            stderr=stderr or "",
            duration_ms=duration_ms,
            timed_out=timed_out,
        )


__all__ = ["DockerSandbox"]
