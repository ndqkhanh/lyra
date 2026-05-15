"""Cross-platform clipboard writer for ``/copy`` and friends.

Implementation policy: try the OS-native CLI tool first because it's the
only path that works under SSH-forwarded sessions, headless tmux, and
the various Linux desktops where the right command depends on the
session type (X11 vs Wayland) — any pure-Python clipboard library would
fail or hang in at least one of those.

Fallback order:

1. **macOS** — ``pbcopy``
2. **Wayland** — ``wl-copy`` (preferred when ``WAYLAND_DISPLAY`` is set)
3. **X11** — ``xclip -selection clipboard`` then ``xsel --clipboard --input``
4. **Windows** — ``clip.exe``

If none are available we return ``CopyResult(ok=False, ...)`` with a
human-readable hint instead of raising — the caller can then fall back
to the ``w`` write-to-file path. We deliberately do NOT raise: ``/copy``
should be best-effort and a missing clipboard tool is a normal state on
many CI / SSH boxes.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CopyResult:
    """Outcome of a clipboard copy attempt.

    Returned (never raised) so callers can branch on success without a
    try/except — keeps the slash-command handler readable.
    """

    ok: bool
    backend: str
    detail: Optional[str] = None


def _run(cmd: list[str], payload: str) -> Optional[str]:
    """Pipe ``payload`` to ``cmd``; return None on success, error string otherwise."""
    try:
        proc = subprocess.run(
            cmd,
            input=payload.encode("utf-8"),
            capture_output=True,
            timeout=2.0,
            check=False,
        )
    except FileNotFoundError:
        return f"{cmd[0]} not found"
    except subprocess.TimeoutExpired:
        return f"{cmd[0]} timed out"
    except OSError as exc:
        return f"{cmd[0]} failed: {exc}"
    if proc.returncode != 0:
        stderr = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
        return stderr or f"{cmd[0]} exit={proc.returncode}"
    return None


def _candidates() -> list[tuple[str, list[str]]]:
    """Ordered list of (backend-name, argv) to try on this platform.

    Platform detection mirrors the rationale in the module docstring:
    Wayland gets priority over X11 because mixed-stack desktops (where
    both ``wl-copy`` and ``xclip`` exist) are easier to break by writing
    to the wrong selection.
    """
    out: list[tuple[str, list[str]]] = []
    sys = platform.system().lower()
    if sys == "darwin":
        out.append(("pbcopy", ["pbcopy"]))
        return out
    if sys == "windows":
        out.append(("clip.exe", ["clip"]))
        return out
    # Linux / BSD — order matters; first found wins.
    if os.environ.get("WAYLAND_DISPLAY"):
        out.append(("wl-copy", ["wl-copy"]))
    out.append(("xclip", ["xclip", "-selection", "clipboard"]))
    out.append(("xsel", ["xsel", "--clipboard", "--input"]))
    return out


def copy_to_clipboard(text: str) -> CopyResult:
    """Copy ``text`` to the system clipboard via the first available backend.

    Returns a :class:`CopyResult` rather than raising — the slash-command
    layer presents this as a one-line status line, and a missing tool on
    a headless box is not exceptional.
    """
    if not text:
        return CopyResult(ok=False, backend="(none)", detail="nothing to copy")
    last_err = "no clipboard backend available"
    for backend, argv in _candidates():
        if not shutil.which(argv[0]):
            continue
        err = _run(argv, text)
        if err is None:
            return CopyResult(ok=True, backend=backend)
        last_err = err
    return CopyResult(ok=False, backend="(none)", detail=last_err)


__all__ = ["CopyResult", "copy_to_clipboard"]
