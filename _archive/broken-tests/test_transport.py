#!/usr/bin/env python3
"""Check if transport is set."""
import sys
from pathlib import Path


def log(msg):
    print(f"[DEBUG] {msg}", file=sys.stderr, flush=True)

from harness_tui import ProjectConfig  # noqa: E402
from lyra_cli.tui_v2 import lyra_theme  # noqa: E402
from lyra_cli.tui_v2.app import LyraHarnessApp  # noqa: E402
from lyra_cli.tui_v2.commands import register_lyra_commands  # noqa: E402
from lyra_cli.tui_v2.sidebar import build_lyra_sidebar_tabs  # noqa: E402
from lyra_cli.tui_v2.transport import LyraTransport  # noqa: E402

log("Creating transport...")
transport = LyraTransport(repo_root=Path.cwd(), model='claude-sonnet-4.6', max_steps=20)
log(f"  transport: {transport}")
log(f"  transport type: {type(transport)}")
log(f"  transport bool: {bool(transport)}")

log("Creating config...")
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

log(f"  cfg.transport: {cfg.transport}")
log(f"  cfg.transport type: {type(cfg.transport)}")
log(f"  cfg.transport bool: {bool(cfg.transport)}")

log("Creating app...")
app = LyraHarnessApp(cfg)

log(f"  app.cfg.transport: {app.cfg.transport}")
log(f"  app.cfg.transport bool: {bool(app.cfg.transport)}")

# Check if transport has a stream method
if hasattr(app.cfg.transport, 'stream'):
    log(f"  transport.stream exists: {app.cfg.transport.stream}")
else:
    log("  ✗ transport.stream does NOT exist!")

log("Done checking")
