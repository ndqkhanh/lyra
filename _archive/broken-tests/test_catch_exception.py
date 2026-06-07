#!/usr/bin/env python3
"""Catch any exception that causes early exit."""

import sys
import traceback
from pathlib import Path

from lyra_cli.tui_v2 import launch_tui_v2
from lyra_cli.tui_v2.app import LyraHarnessApp
from textual.app import App

sys.path.insert(0, "packages/lyra-cli/src")
sys.path.insert(0, "packages/lyra-ui/src")

# Patch Textual's App.run to catch exceptions

original_run = App.run


def patched_run(self, *args, **kwargs):
    try:
        print(f"[PATCH] App.run() starting for {type(self).__name__}", file=sys.stderr, flush=True)
        result = original_run(self, *args, **kwargs)
        print("[PATCH] App.run() completed normally", file=sys.stderr, flush=True)
        return result
    except Exception as e:
        print(f"[PATCH] App.run() EXCEPTION: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        raise


App.run = patched_run

# Also patch the app's on_mount and _post_mount

original_on_mount = LyraHarnessApp.on_mount
original_post_mount = LyraHarnessApp._post_mount


def patched_on_mount(self):
    try:
        print("[PATCH] LyraHarnessApp.on_mount() starting", file=sys.stderr, flush=True)
        original_on_mount(self)
        print("[PATCH] LyraHarnessApp.on_mount() completed", file=sys.stderr, flush=True)
    except Exception as e:
        print(
            f"[PATCH] LyraHarnessApp.on_mount() EXCEPTION: {type(e).__name__}: {e}",
            file=sys.stderr,
            flush=True,
        )
        traceback.print_exc(file=sys.stderr)
        raise


def patched_post_mount(self):
    try:
        print("[PATCH] LyraHarnessApp._post_mount() starting", file=sys.stderr, flush=True)
        original_post_mount(self)
        print("[PATCH] LyraHarnessApp._post_mount() completed", file=sys.stderr, flush=True)
    except Exception as e:
        print(
            f"[PATCH] LyraHarnessApp._post_mount() EXCEPTION: {type(e).__name__}: {e}",
            file=sys.stderr,
            flush=True,
        )
        traceback.print_exc(file=sys.stderr)
        raise


LyraHarnessApp.on_mount = patched_on_mount
LyraHarnessApp._post_mount = patched_post_mount

# Now run the TUI

print("[TEST] Launching TUI...", file=sys.stderr, flush=True)
exit_code = launch_tui_v2(
    repo_root=Path.cwd(),
    model="claude-sonnet-4.6",
    mock=False,
    max_steps=20,
)
print(f"[TEST] Exit code: {exit_code}", file=sys.stderr, flush=True)
sys.exit(exit_code)
