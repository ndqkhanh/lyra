"""Lyra TUI Gateway — stdin/stdout JSON-RPC dispatch loop.

Reads JSON-RPC lines from stdin, dispatches to the server module, and
writes JSON-RPC responses to stdout.  Starts by writing a ``gateway.ready``
event so the Ink TUI knows we are alive.
"""

import json
import signal
import sys

from .server import dispatch, resolve_skin, write_json

signal.signal(signal.SIGPIPE, signal.SIG_DFL)
signal.signal(signal.SIGINT, signal.SIG_IGN)


def main():
    if not write_json(
        {
            "jsonrpc": "2.0",
            "method": "event",
            "params": {"type": "gateway.ready", "payload": {"skin": resolve_skin()}},
        }
    ):
        sys.exit(0)

    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue

        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            if not write_json(
                {"jsonrpc": "2.0", "error": {"code": -32700, "message": "parse error"}, "id": None}
            ):
                sys.exit(0)
            continue

        resp = dispatch(req)
        if resp is not None:
            if not write_json(resp):
                sys.exit(0)


if __name__ == "__main__":
    main()
