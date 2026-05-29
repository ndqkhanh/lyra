#!/usr/bin/env python3
"""Test with Textual's pilot mode to see what's happening."""
import sys
from pathlib import Path


def log(msg):
    print(f"[TEST] {msg}", file=sys.stderr, flush=True)

log("=== Testing with async pilot ===")

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

class DebugApp(LyraHarnessApp):
    def on_mount(self):
        log("  → on_mount() called")
        super().on_mount()
        log("  → on_mount() completed")

    def compose(self):
        log("  → compose() called")
        yield from super().compose()
        log("  → compose() completed")

    async def on_ready(self):
        log("  → on_ready() called")
        await super().on_ready()
        log("  → on_ready() completed")

app = DebugApp(cfg)
log("App created")

# Try running with a simple async wrapper to catch early exits
import asyncio


async def run_with_logging():
    log("Starting app.run_async()...")
    try:
        async with app.run_test():
            log("App is running in test mode")
            log("Waiting 2 seconds...")
            await asyncio.sleep(2)
            log("Taking screenshot...")
            # This will show us if the app actually rendered
            log("App is still alive after 2 seconds")
    except Exception as e:
        log(f"Error: {e}")
        import traceback
        traceback.print_exc()

log("Running async test...")
asyncio.run(run_with_logging())
log("Test completed")
