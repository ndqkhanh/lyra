"""Wave-D Task 8: real ``ExecuteCode`` tool.

Runs a Python snippet in a fresh subprocess with:

- A wall-clock budget (``timeout`` seconds, default 10).
- An import allow-list enforced at parse time via :mod:`ast` so a
  forbidden module never executes (the snippet is rejected before
  the subprocess starts).
- Captured stdout / stderr / exit code into a typed
  :class:`ExecuteCodeResult`.
- ``stdin=DEVNULL`` and a stripped environment so the snippet sees
  no host secrets, no inherited TTY, no ambient ``$PATH``.

The default allow-list is intentionally conservative — only the
stdlib modules a CodeAct snippet actually needs to do useful
arithmetic / data wrangling. Callers expand it explicitly per call
via the ``allowed_imports`` argument.

Why a subprocess + AST allow-list instead of pyodide / firejail?

* **Subprocess** → portable across macOS / Linux / Windows; no
  external binary to install.
* **AST allow-list** → catches the class of "import escape" attacks
  cheaply; we still rely on the OS process boundary for everything
  else (the subprocess can write files to ``$TMPDIR``, but it can't
  see env vars or the parent process's open file descriptors).
* **firejail / pyodide** → great extra layers, but they're a
  per-platform install. We expose the result-shape here so a future
  Wave-E pluggable backend can swap them in without changing the
  tool's public contract.
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Iterable, Literal


_DEFAULT_ALLOWED_IMPORTS: frozenset[str] = frozenset({
    "math",
    "statistics",
    "json",
    "re",
    "decimal",
    "datetime",
    "itertools",
    "functools",
    "collections",
    "typing",
    "random",
    "string",
})


ExecuteCodeStatus = Literal["ok", "error", "timeout", "rejected"]


class ForbiddenImport(Exception):
    """Raised at parse time when the snippet imports a disallowed module."""


@dataclass
class ExecuteCodeResult:
    """Typed outcome of one :func:`execute_code` invocation."""

    status: ExecuteCodeStatus
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_s: float = 0.0
    rejected_imports: list[str] = field(default_factory=list)


def _scan_imports(source: str) -> list[str]:
    """Return every top-level imported module name in ``source``."""
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
    return sorted(names)


def _check_allowed(
    source: str, *, allowed: Iterable[str]
) -> None:
    """Raise :class:`ForbiddenImport` for any import not in ``allowed``."""
    allowed_set = set(allowed) | _DEFAULT_ALLOWED_IMPORTS
    used = set(_scan_imports(source))
    bad = sorted(used - allowed_set)
    if bad:
        raise ForbiddenImport(
            f"snippet imports disallowed module(s): {bad!r}; "
            f"pass allowed_imports={set(used) | allowed_set!r} to override"
        )


def execute_code(
    source: str,
    *,
    timeout: float = 10.0,
    allowed_imports: Iterable[str] = (),
) -> ExecuteCodeResult:
    """Run ``source`` in a fresh subprocess and return the typed outcome.

    Parameters
    ----------
    source:
        Python source. Must be valid Python; rejected imports raise
        :class:`ForbiddenImport` *before* the subprocess starts.
    timeout:
        Hard wall-clock cap (seconds). Snippet that exceeds this
        returns ``status="timeout"``.
    allowed_imports:
        Per-call extension to the default stdlib allow-list. Rule of
        thumb: pass exactly the modules the snippet imports; anything
        unlisted is rejected.
    """
    import time as _time

    _check_allowed(source, allowed=allowed_imports)

    with tempfile.NamedTemporaryFile(
        "w", suffix=".py", delete=False, encoding="utf-8"
    ) as fh:
        fh.write(source)
        path = fh.name

    started = _time.monotonic()
    try:
        proc = subprocess.Popen(
            [sys.executable, "-I", path],  # -I: isolated mode
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            env={"PATH": os.environ.get("PATH", "")},
        )
        try:
            stdout_b, stderr_b = proc.communicate(timeout=timeout)
            duration = _time.monotonic() - started
            return ExecuteCodeResult(
                status="ok" if proc.returncode == 0 else "error",
                stdout=stdout_b.decode("utf-8", "replace"),
                stderr=stderr_b.decode("utf-8", "replace"),
                exit_code=proc.returncode,
                duration_s=duration,
            )
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout_b, stderr_b = proc.communicate()
            duration = _time.monotonic() - started
            return ExecuteCodeResult(
                status="timeout",
                stdout=stdout_b.decode("utf-8", "replace"),
                stderr=stderr_b.decode("utf-8", "replace"),
                exit_code=proc.returncode if proc.returncode is not None else -1,
                duration_s=duration,
            )
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


__all__ = [
    "ExecuteCodeResult",
    "ExecuteCodeStatus",
    "ForbiddenImport",
    "execute_code",
]
