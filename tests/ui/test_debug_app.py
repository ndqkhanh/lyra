#!/usr/bin/env python3
"""Test with exception catching and keep-alive."""
import sys
from pathlib import Path


def log(msg):
    print(f"[TEST] {msg}", file=sys.stderr, flush=True)

log("=== Starting test with exception handling ===")

from harness_tui import ProjectConfig
from lyra_cli.tui_v2 import lyra_theme
from lyra_cli.tui_v2.app import LyraHarnessApp
from lyra_cli.tui_v2.commands import register_lyra_commands
from lyra_cli.tui_v2.sidebar import build_lyra_sidebar_tabs
from lyra_cli.tui_v2.transport import LyraTransport

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

log("Creating app with custom exception handling...")

class DebugApp(LyraHarnessApp):
    def on_mount(self):
        log("  → on_mount() called")
        try:
            super().on_mount()
            log("  → on_mount() completed successfully")
        except Exception as e:
            log(f"  ✗ on_mount() raised: {e}")
            import traceback
            traceback.print_exc()
            raise

    def compose(self):
        log("  → compose() called")
        try:
            yield from super().compose()
            log("  → compose() completed")
        except Exception as e:
            log(f"  ✗ compose() raised: {e}")
            import traceback
            traceback.print_exc()
            raise

app = DebugApp(cfg)
log("App created, calling run()...")

try:
    app.run()
    log("✓ App exited normally")
except KeyboardInterrupt:
    log("✓ Interrupted by user")
except Exception as e:
    log(f"✗ App.run() raised: {e}")
    import traceback
    traceback.print_exc()
