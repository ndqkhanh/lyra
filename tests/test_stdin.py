#!/usr/bin/env python3
"""Test with stdin monitoring."""
import sys
from pathlib import Path


def log(msg):
    print(f"[DEBUG] {msg}", file=sys.stderr, flush=True)

log("Checking stdin...")
log(f"  stdin.isatty(): {sys.stdin.isatty()}")
log(f"  stdin.closed: {sys.stdin.closed}")

# Check if stdin has data or is closed
if sys.stdin.isatty():
    import termios
    try:
        attrs = termios.tcgetattr(sys.stdin)
        log("  Terminal attributes OK")
    except Exception as e:
        log(f"  Cannot get terminal attributes: {e}")

log("Starting app...")

from harness_tui import ProjectConfig  # noqa: E402
from lyra_cli.tui_v2 import lyra_theme  # noqa: E402
from lyra_cli.tui_v2.app import LyraHarnessApp  # noqa: E402
from lyra_cli.tui_v2.commands import register_lyra_commands  # noqa: E402
from lyra_cli.tui_v2.sidebar import build_lyra_sidebar_tabs  # noqa: E402
from lyra_cli.tui_v2.transport import LyraTransport  # noqa: E402

transport = LyraTransport(repo_root=Path.cwd(), model='claude-sonnet-4.6', max_steps=20)
cfg = ProjectConfig(
    name='lyra',
    description='Test',
    theme=lyra_theme(),
    transport=transport,
    model='claude-sonnet-4.6',
    working_dir=str(Path.cwd()),
    sidebar_tabs=build_lyra_sidebar_tabs(Path.cwd()),
    extra_commands=[register_lyra_commands],
)

app = LyraHarnessApp(cfg)

log("About to call app.run()...")
log("Press Ctrl+C to exit if it hangs")

try:
    app.run()
    log("app.run() returned normally")
except KeyboardInterrupt:
    log("Interrupted by user")
except EOFError as e:
    log(f"EOFError: {e}")
except Exception as e:
    log(f"Exception: {e}")
    import traceback
    traceback.print_exc()

log("After app.run()")
log(f"  stdin.closed: {sys.stdin.closed}")
