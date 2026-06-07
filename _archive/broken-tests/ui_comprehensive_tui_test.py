#!/usr/bin/env python3
"""Comprehensive TUI diagnostic with all possible failure points logged."""
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

log_file = Path.cwd() / "tui_comprehensive_debug.log"

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{timestamp}] {msg}"
    with open(log_file, "a") as f:
        f.write(f"{line}\n")
    print(line, file=sys.stderr, flush=True)

log("=" * 80)
log("COMPREHENSIVE TUI DIAGNOSTIC")
log("=" * 80)

# Environment check
log(f"Python: {sys.version}")
log(f"CWD: {Path.cwd()}")
log(f"stdin.isatty(): {sys.stdin.isatty()}")
log(f"stdout.isatty(): {sys.stdout.isatty()}")
log(f"stderr.isatty(): {sys.stderr.isatty()}")
log(f"TERM: {os.environ.get('TERM', 'not set')}")
log(f"COLORTERM: {os.environ.get('COLORTERM', 'not set')}")
log(f"LYRA_TUI: {os.environ.get('LYRA_TUI', 'not set')}")

# Patch Textual App to log lifecycle events
log("\n--- Patching Textual App ---")
try:
    from textual.app import App

    original_run = App.run
    original_on_mount = App.on_mount

    def patched_run(self, *args, **kwargs):
        log(f"App.run() called on {self.__class__.__name__}")
        log(f"  args: {args}")
        log(f"  kwargs: {kwargs}")
        try:
            result = original_run(self, *args, **kwargs)
            log(f"App.run() returned: {result}")
            return result
        except Exception as e:
            log(f"App.run() raised: {type(e).__name__}: {e}")
            traceback.print_exc()
            raise

    async def patched_on_mount(self, *args, **kwargs):
        log(f"App.on_mount() called on {self.__class__.__name__}")
        try:
            result = await original_on_mount(self, *args, **kwargs)
            log("App.on_mount() completed successfully")
            return result
        except Exception as e:
            log(f"App.on_mount() raised: {type(e).__name__}: {e}")
            traceback.print_exc()
            raise

    App.run = patched_run
    App.on_mount = patched_on_mount
    log("✓ Textual App patched")
except Exception as e:
    log(f"✗ Failed to patch Textual App: {e}")

# Import and launch
log("\n--- Importing lyra_cli.tui_v2 ---")
try:
    from lyra_cli.tui_v2 import launch_tui_v2
    log("✓ Import successful")
except Exception as e:
    log(f"✗ Import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

log("\n--- Launching TUI ---")
log("If the TUI appears, press Ctrl+Q to quit")
log("If it doesn't appear, check this log for errors")

try:
    exit_code = launch_tui_v2(repo_root=Path.cwd(), model='claude-sonnet-4.6')
    log("\n--- TUI Exited ---")
    log(f"Exit code: {exit_code}")
except KeyboardInterrupt:
    log("\n--- Interrupted by user (Ctrl+C) ---")
except Exception as e:
    log("\n--- TUI Crashed ---")
    log(f"Exception: {type(e).__name__}: {e}")
    traceback.print_exc()
    with open(log_file, "a") as f:
        traceback.print_exc(file=f)

log("\n" + "=" * 80)
log(f"Log saved to: {log_file}")
log("=" * 80)
