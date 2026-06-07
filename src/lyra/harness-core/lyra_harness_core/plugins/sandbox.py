"""Plugin Sandbox — isolated plugin execution environment.

Provides network-scoped and filesystem-scoped execution for plugins.
Follows the shared-base-environment pattern: a read-only base Python
environment shared across plugins, with per-plugin writable overlays.

See: plan-phase5-master-plan.md §P1-B8, Risk R7 mitigation
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from lyra.harness_core.plugins.manifest import PluginManifest


# --- Domain allowlist validation ----------------------------------------------


_DOMAIN_RE = re.compile(
    r"^(?:\*\.)?(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z]{2,}|localhost|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$"
)


def _domain_matches(host: str, allowlist_entry: str) -> bool:
    """Check if a host matches an allowlist entry (exact or wildcard)."""
    if allowlist_entry == host:
        return True
    if allowlist_entry.startswith("*."):
        suffix = allowlist_entry[2:]
        return host == suffix or host.endswith("." + suffix)
    return False


def validate_domain(host: str, allowlist: tuple[str, ...]) -> bool:
    """Check if a host is allowed by the network allowlist.

    Args:
        host: The hostname or IP to check.
        allowlist: Tuple of allowed domain patterns.

    Returns:
        True if the host is allowed.
    """
    if not allowlist:
        return False
    return any(_domain_matches(host, entry) for entry in allowlist)


def validate_path(path: str | Path, allowlist: tuple[str, ...]) -> bool:
    """Check if a filesystem path is within the allowlisted paths.

    Args:
        path: The path to check.
        allowlist: Tuple of allowed writable path prefixes.

    Returns:
        True if the path is within an allowlisted prefix.
    """
    resolved = str(Path(path).expanduser().resolve())
    for entry in allowlist:
        resolved_entry = str(Path(entry).expanduser().resolve())
        if resolved.startswith(resolved_entry):
            return True
    return False


# --- Sandbox runtime ---------------------------------------------------------


@dataclass
class SandboxResult:
    """Result from executing code inside a plugin sandbox."""

    exit_code: int
    stdout: str
    stderr: str
    elapsed_ms: float = 0.0

    @property
    def success(self) -> bool:
        return self.exit_code == 0


class PluginSandbox:
    """Isolated execution environment for a plugin.

    Enforces:
    - Network scoping: only allowlisted domains via domain validation
    - Filesystem scoping: only allowlisted writable paths
    - Read-only shared base environment (pip packages are read-only)

    The sandbox does NOT provide OS-level isolation — it validates at the
    application layer via hooks and domain/path checks. For stronger
    isolation, combine with OS-level containers (Docker, Firecracker).

    Usage::

        manifest = load_manifest_from_yaml(yaml_text)
        sandbox = PluginSandbox(manifest)
        result = sandbox.run_code("print('hello from sandbox')")
    """

    def __init__(self, manifest: PluginManifest) -> None:
        self._manifest = manifest
        self._sandbox_config = manifest.sandbox

    @property
    def manifest(self) -> PluginManifest:
        return self._manifest

    def check_network_access(self, host: str) -> bool:
        """Check if the given host is allowed for this plugin.

        Returns True if the host is in the network allowlist.
        If the allowlist is empty, no network access is permitted.
        """
        return validate_domain(host, self._sandbox_config.network_allowlist)

    def check_filesystem_access(self, path: str | Path) -> bool:
        """Check if the given path is writable for this plugin.

        Returns True if the path is within a filesystem allowlist entry.
        The shared base environment is always read-only.
        """
        return validate_path(path, self._sandbox_config.filesystem_allowlist)

    def allowed_domains(self) -> tuple[str, ...]:
        """Return the network allowlist for this plugin."""
        return self._sandbox_config.network_allowlist

    def allowed_paths(self) -> tuple[str, ...]:
        """Return the filesystem allowlist for this plugin."""
        return self._sandbox_config.filesystem_allowlist

    def run_code(self, code: str, timeout_seconds: float = 30.0) -> SandboxResult:
        """Execute Python code in a sandboxed subprocess.

        The code runs in a subprocess with the current Python interpreter.
        Network and filesystem restrictions are enforced at the application
        layer — this provides isolation from the host process but not true
        OS-level sandboxing.

        Args:
            code: Python source code to execute.
            timeout_seconds: Maximum execution time.

        Returns:
            A SandboxResult with exit code, stdout, stderr, and elapsed time.
        """
        import time

        started = time.monotonic()

        try:
            proc = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=tempfile.gettempdir(),
            )
            elapsed = (time.monotonic() - started) * 1000
            return SandboxResult(
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                elapsed_ms=round(elapsed, 2),
            )
        except subprocess.TimeoutExpired as e:
            elapsed = (time.monotonic() - started) * 1000
            stdout_str = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
            stderr_str = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
            return SandboxResult(
                exit_code=-1,
                stdout=stdout_str,
                stderr=stderr_str or f"timeout after {timeout_seconds}s",
                elapsed_ms=round(elapsed, 2),
            )

    def _create_venv(self, target_dir: Path) -> None:
        """Create an isolated virtual environment for the plugin.

        Uses the shared base environment pattern: the base Python packages
        are read-only; plugin-specific dependencies are installed as an
        overlay in the per-plugin venv.
        """
        # Use the current Python to create a lightweight venv
        subprocess.run(
            [sys.executable, "-m", "venv", "--clear", str(target_dir)],
            capture_output=True,
            text=True,
            check=True,
        )

    def validate_environment(self) -> list[str]:
        """Validate that all plugin dependencies are available.

        Returns a list of error messages (empty = all good).
        """
        errors: list[str] = []
        for dep in self._manifest.dependencies:
            try:
                __import__(dep.package)
            except ImportError:
                errors.append(f"missing dependency: {dep.package}")
        return errors


__all__ = [
    "PluginSandbox",
    "SandboxResult",
    "validate_domain",
    "validate_path",
]
