"""``/lyra <subcommand> [args...]`` — escape hatch to the Typer CLI.

Phase 2 ports the 8 highest-value slash commands directly; the
remaining ~120 legacy slashes (``/investigate``, ``/burn``,
``/evolve``, ``/retro``, ``/ultrareview``, ``/autopilot``, …) reach
the user through this one entry. It runs ``lyra <subcommand>`` as a
subprocess in the working directory and streams stdout/stderr into the
chat log. Long-running commands are cancellable via ``Ctrl+C`` in the
spawned process (the TUI's ``Esc`` does not yet kill subprocesses —
that's a Phase 5 follow-up).

Why subprocess instead of in-process invocation: each Lyra subcommand
constructs its own Typer/argparse state, opens its own LLM provider,
and may swap stdout writers. Running it as a subprocess gives a clean
boundary with no shared mutable state, and matches what a user would
type at the shell.
"""
from __future__ import annotations

import asyncio
import os
import shlex
import shutil
import sys
from typing import TYPE_CHECKING

from harness_tui.commands.registry import register_command

if TYPE_CHECKING:  # pragma: no cover
    from harness_tui.app import HarnessApp


# Output cap — defends the chat log against multi-MB subprocess output
# (e.g. ``lyra evals run`` can stream a long JSONL).
_MAX_OUTPUT_BYTES = 64 * 1024


@register_command(
    name="lyra",
    description="Run any 'lyra' subcommand — '/lyra investigate ...', '/lyra burn list'",
    category="Lyra",
    examples=[
        "/lyra doctor",
        "/lyra investigate 'why does the daemon crash on resume?'",
        "/lyra burn list",
    ],
)
async def cmd_lyra(app: "HarnessApp", args: str) -> None:
    parts = shlex.split(args or "")
    if not parts:
        app.shell.chat_log.write_system(
            "lyra: usage — '/lyra <subcommand> [args]'  (e.g. '/lyra doctor')"
        )
        return

    exe = _lyra_executable()
    if exe is None:
        app.shell.chat_log.write_system(
            "lyra: cannot locate 'lyra' executable on PATH"
        )
        return

    cwd = app.cfg.working_dir or os.getcwd()
    app.shell.chat_log.write_system(f"$ lyra {' '.join(parts)}")

    proc = await asyncio.create_subprocess_exec(
        exe,
        *parts,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    output = await _read_capped(proc.stdout, _MAX_OUTPUT_BYTES)
    rc = await proc.wait()

    text = output.decode("utf-8", errors="replace").rstrip()
    if text:
        app.shell.chat_log.write_system(text)
    app.shell.chat_log.write_system(f"(exit code {rc})")


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _lyra_executable() -> str | None:
    """Locate the ``lyra`` entry point. Prefer the one in this venv."""
    here = shutil.which("lyra")
    if here:
        return here
    # In an editable install the script may live next to the interpreter.
    candidate = os.path.join(os.path.dirname(sys.executable), "lyra")
    if os.path.exists(candidate):
        return candidate
    return None


async def _read_capped(reader, cap: int) -> bytes:
    """Read up to ``cap`` bytes from ``reader``; drain remainder."""
    if reader is None:
        return b""
    buf = bytearray()
    while True:
        chunk = await reader.read(4096)
        if not chunk:
            return bytes(buf)
        if len(buf) < cap:
            take = min(len(chunk), cap - len(buf))
            buf.extend(chunk[:take])
            if len(buf) == cap:
                buf.extend(b"\n[...output truncated...]")
        # keep draining so the subprocess pipe doesn't block on PIPE-full
