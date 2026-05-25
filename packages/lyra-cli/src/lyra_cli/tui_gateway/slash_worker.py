"""Persistent slash-command worker — one LyraCLI per TUI session.

Protocol: reads JSON lines from stdin {id, command}, writes {id, ok, output|error} to stdout.

This is a placeholder that provides the protocol layer.  The actual Lyra CLI
processing will be wired when the CLI module is available.
"""

import argparse
import contextlib
import io
import json
import os
import sys
from pathlib import Path


def _run(command: str) -> str:
    """Execute a slash command in the Lyra context.

    TODO: Wire actual Lyra CLI processing here.  Currently a passthrough
    for commands that don't start with '/' — returns the command text as
    a simple echo, or attempts a future CLI dispatch.
    """
    cmd = (command or "").strip()
    if not cmd:
        return ""

    buf = io.StringIO()

    # TODO: Replace with actual Lyra CLI dispatch once the CLI module is available.
    # For now, echo commands that look like slash commands and pass through plain text.
    if cmd.startswith("/"):
        # Placeholder: return a "not implemented" response for slash commands.
        result = f"[Lyra TUI] Slash command '{cmd}' is not yet implemented in the gateway worker."
    else:
        result = cmd

    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            print(result)
    finally:
        pass

    return buf.getvalue().rstrip()


def main():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--session-key", required=True)
    p.add_argument("--model", default="")
    args = p.parse_args()

    os.environ["LYRA_SESSION_KEY"] = args.session_key
    os.environ["LYRA_INTERACTIVE"] = "1"

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        pass  # TODO: Initialize Lyra CLI here when available

    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue

        rid = None
        try:
            req = json.loads(line)
            rid = req.get("id")
            out = _run(req.get("command", ""))
            sys.stdout.write(json.dumps({"id": rid, "ok": True, "output": out}) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(json.dumps({"id": rid, "ok": False, "error": str(e)}) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
