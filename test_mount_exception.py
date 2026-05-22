#!/usr/bin/env python3
"""Test Lyra TUI with exception catching in on_mount."""
import sys
import traceback
from pathlib import Path

# Patch LyraHarnessApp.on_mount to catch exceptions
from lyra_cli.tui_v2.app import LyraHarnessApp

original_on_mount = LyraHarnessApp.on_mount

def patched_on_mount(self):
    print("=== LyraHarnessApp.on_mount() called ===", file=sys.stderr, flush=True)
    try:
        result = original_on_mount(self)
        print("=== LyraHarnessApp.on_mount() completed successfully ===", file=sys.stderr, flush=True)
        return result
    except Exception as e:
        print(f"=== LyraHarnessApp.on_mount() raised exception: {e} ===", file=sys.stderr, flush=True)
        traceback.print_exc()
        raise

LyraHarnessApp.on_mount = patched_on_mount

# Now launch
from lyra_cli.tui_v2 import launch_tui_v2

print("Launching TUI with on_mount exception catching...", file=sys.stderr, flush=True)
print("Press Ctrl+Q to quit if it appears", file=sys.stderr, flush=True)

try:
    exit_code = launch_tui_v2(repo_root=Path.cwd(), model='claude-sonnet-4.6')
    print(f"\nTUI exited with code: {exit_code}", file=sys.stderr)
except Exception as e:
    print(f"\nException during launch: {e}", file=sys.stderr)
    traceback.print_exc()
