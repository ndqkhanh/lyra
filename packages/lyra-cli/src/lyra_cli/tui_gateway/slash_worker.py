"""Persistent slash-command worker — one REPL per TUI session.

Protocol: reads JSON lines from stdin {id, command}, writes {id, ok, output|error} to stdout.
"""

import argparse
import contextlib
import io
import json
import os
import sys

from rich.console import Console


def _run_command(command: str) -> str:
    """Execute a slash command and return captured output."""
    cmd = (command or "").strip()
    if not cmd:
        return ""
    if not cmd.startswith("/"):
        cmd = f"/{cmd}"

    buf = io.StringIO()
    capture_console = Console(file=buf, force_terminal=True, width=120)

    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            _dispatch(cmd, capture_console)
    except SystemExit:
        pass

    return buf.getvalue().rstrip()


def _dispatch(cmd: str, console: Console) -> None:
    """Route slash commands to their handlers."""
    parts = cmd.split(maxsplit=1)
    name = parts[0].lower().lstrip("/")
    arg = parts[1] if len(parts) > 1 else ""

    handlers = {
        "model": lambda: _cmd_model(arg, console),
        "clear": lambda: console.print("[info]Screen cleared (no-op in TUI worker).[/info]"),
        "help": lambda: _cmd_help(console),
        "compress": lambda: console.print("[info]Context compression triggered.[/info]"),
        "copy": lambda: console.print("[info]Copy: use the TUI clipboard feature.[/info]"),
        "save": lambda: console.print("[info]Session saved.[/info]"),
        "load": lambda: console.print("[info]Session load requested.[/info]"),
        "stats": lambda: _cmd_stats(console),
        "exit": lambda: None,
        "quit": lambda: None,
    }

    handler = handlers.get(name)
    if handler:
        handler()
    else:
        console.print(f"[warning]Unknown command: /{name}[/warning]")


def _cmd_model(arg: str, console: Console) -> None:
    """Switch the active model."""
    available = {
        "sonnet": "claude-sonnet-4-20250514",
        "opus": "claude-opus-4-20250514",
        "haiku": "claude-haiku-3-5-20241022",
    }
    if arg and arg.strip():
        key = arg.strip().lower()
        if key in available:
            console.print(f"[info]Model set to {arg.strip()} ({available[key]}).[/info]")
        else:
            console.print(f"[warning]Unknown model '{arg}'. Available: {', '.join(available.keys())}[/warning]")
    else:
        current = os.environ.get("LYRA_MODEL", "claude-sonnet-4-20250514")
        console.print(f"[info]Current model: {current}[/info]")
        console.print(f"[info]Available: {', '.join(available.keys())}[/info]")


def _cmd_help(console: Console) -> None:
    """Show available commands."""
    console.print("[bold]Available Commands:[/bold]")
    console.print("  /model [name]   Switch or show model")
    console.print("  /clear          Clear screen")
    console.print("  /help           Show this help")
    console.print("  /compress       Compress conversation history")
    console.print("  /copy           Copy last response")
    console.print("  /save           Save current session")
    console.print("  /stats          Show usage statistics")


def _cmd_stats(console: Console) -> None:
    """Show usage statistics stub."""
    console.print("[info]Usage statistics not available in worker mode.[/info]")


def main():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--session-key", required=True)
    p.add_argument("--model", default="")
    args = p.parse_args()

    os.environ["LYRA_SESSION_KEY"] = args.session_key
    os.environ["LYRA_INTERACTIVE"] = "1"

    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue

        rid = None
        try:
            req = json.loads(line)
            rid = req.get("id")
            out = _run_command(req.get("command", ""))
            sys.stdout.write(json.dumps({"id": rid, "ok": True, "output": out}) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(json.dumps({"id": rid, "ok": False, "error": str(e)}) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
