#!/usr/bin/env python3
"""Test with detailed logging at each step."""
import sys
from pathlib import Path

def log(msg):
    print(f"[TEST] {msg}", file=sys.stderr, flush=True)

log("=== Starting detailed test ===")

log("1. Importing LyraTransport...")
from lyra_cli.tui_v2.transport import LyraTransport
log("   ✓ Import successful")

log("2. Creating transport instance...")
transport = LyraTransport(repo_root=Path.cwd(), model='claude-sonnet-4.6', max_steps=20)
log("   ✓ Transport created")

log("3. Importing config classes...")
from harness_tui import ProjectConfig
from lyra_cli.tui_v2 import lyra_theme
from lyra_cli.tui_v2.sidebar import build_lyra_sidebar_tabs
from lyra_cli.tui_v2.commands import register_lyra_commands
log("   ✓ Imports successful")

log("4. Building sidebar tabs...")
sidebar_tabs = build_lyra_sidebar_tabs(Path.cwd())
log(f"   ✓ Got {len(sidebar_tabs)} tabs")

log("5. Creating ProjectConfig...")
cfg = ProjectConfig(
    name='lyra',
    description='Test',
    theme=lyra_theme(),
    transport=transport,
    model='claude-sonnet-4.6',
    working_dir=str(Path.cwd()),
    sidebar_tabs=sidebar_tabs,
    extra_commands=[register_lyra_commands],
)
log("   ✓ Config created")

log("6. Importing LyraHarnessApp...")
from lyra_cli.tui_v2.app import LyraHarnessApp
log("   ✓ Import successful")

log("7. Creating app instance (this calls __init__)...")
app = LyraHarnessApp(cfg)
log("   ✓ App instance created")

log("8. About to call app.run()...")
log("   (If it hangs here, the issue is in app.run() or compose())")
log("   (If TUI appears, press 'q' to quit)")

try:
    app.run()
    log("✓ App exited normally")
except KeyboardInterrupt:
    log("✓ Interrupted by user")
except Exception as e:
    log(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
