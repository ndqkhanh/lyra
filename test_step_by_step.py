#!/usr/bin/env python3
"""Test Lyra TUI initialization step by step."""
import sys
from pathlib import Path

print("Step 1: Creating transport...", file=sys.stderr, flush=True)
try:
    from lyra_cli.tui_v2.transport import LyraTransport
    transport = LyraTransport(repo_root=Path.cwd(), model='claude-sonnet-4.6', max_steps=20)
    print("✓ Transport created", file=sys.stderr, flush=True)
except Exception as e:
    print(f"✗ Transport failed: {e}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 2: Creating config...", file=sys.stderr, flush=True)
try:
    from harness_tui import ProjectConfig
    from lyra_cli.tui_v2 import lyra_theme
    from lyra_cli.tui_v2.sidebar import build_lyra_sidebar_tabs
    from lyra_cli.tui_v2.commands import register_lyra_commands
    
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
    print("✓ Config created", file=sys.stderr, flush=True)
except Exception as e:
    print(f"✗ Config failed: {e}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 3: Creating app (this initializes all widgets)...", file=sys.stderr, flush=True)
try:
    from lyra_cli.tui_v2.app import LyraHarnessApp
    app = LyraHarnessApp(cfg)
    print("✓ App created", file=sys.stderr, flush=True)
except Exception as e:
    print(f"✗ App creation failed: {e}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 4: Running app...", file=sys.stderr, flush=True)
print("If TUI appears, press Ctrl+Q to quit", file=sys.stderr, flush=True)
print("If it doesn't appear, there's an issue with app.run()", file=sys.stderr, flush=True)

try:
    app.run()
    print("\n✓ App exited normally", file=sys.stderr, flush=True)
except KeyboardInterrupt:
    print("\n✓ Interrupted by user", file=sys.stderr, flush=True)
except Exception as e:
    print(f"\n✗ App.run() failed: {e}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc()
