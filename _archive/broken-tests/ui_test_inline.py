#!/usr/bin/env python3
"""Test with inline mode."""
import sys
from pathlib import Path


def log(msg):
    print(f"[DEBUG] {msg}", file=sys.stderr, flush=True)

log("Starting inline test...")

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

log("Calling app.run(inline=True)...")
try:
    app.run(inline=True)
    log("app.run() returned")
except Exception as e:
    log(f"Exception: {e}")
    import traceback
    traceback.print_exc()
