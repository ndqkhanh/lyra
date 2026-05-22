#!/usr/bin/env python3
"""Intercept Textual's driver to see what's happening."""
import sys
from pathlib import Path

def log(msg):
    print(f"[DEBUG] {msg}", file=sys.stderr, flush=True)

log("Starting instrumented test...")

from lyra_cli.tui_v2.transport import LyraTransport
from harness_tui import ProjectConfig
from lyra_cli.tui_v2 import lyra_theme
from lyra_cli.tui_v2.sidebar import build_lyra_sidebar_tabs
from lyra_cli.tui_v2.commands import register_lyra_commands
from lyra_cli.tui_v2.app import LyraHarnessApp

# Patch the app to log lifecycle events
original_run = LyraHarnessApp.run

def instrumented_run(self, *args, **kwargs):
    log("app.run() called")
    log(f"  args: {args}")
    log(f"  kwargs: {kwargs}")
    
    # Patch the driver to see what's happening
    import textual.app
    original_process_messages = textual.app.App._process_messages
    
    async def logged_process_messages(app_self):
        log("  → _process_messages started")
        try:
            result = await original_process_messages(app_self)
            log(f"  → _process_messages returned: {result}")
            return result
        except Exception as e:
            log(f"  → _process_messages raised: {e}")
            raise
    
    textual.app.App._process_messages = logged_process_messages
    
    try:
        result = original_run(self, *args, **kwargs)
        log(f"app.run() returned: {result}")
        return result
    except Exception as e:
        log(f"app.run() raised: {e}")
        import traceback
        traceback.print_exc()
        raise

LyraHarnessApp.run = instrumented_run

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

log("Creating app...")
app = LyraHarnessApp(cfg)
log("Calling run...")
app.run()
log("Done")
