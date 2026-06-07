#!/usr/bin/env python3
"""Debug script to diagnose TUI v2 launch issues."""
import os
import sys
import traceback
from pathlib import Path

# Enable unbuffered output
os.environ['PYTHONUNBUFFERED'] = '1'

# Create a log file
log_file = Path.cwd() / "tui_debug.log"

def log(msg):
    """Log to both stderr and file."""
    with open(log_file, "a") as f:
        f.write(f"{msg}\n")
    print(msg, file=sys.stderr, flush=True)

log("=" * 60)
log("TUI v2 Launch Debug")
log("=" * 60)

# Check environment
log(f"Python: {sys.version}")
log(f"CWD: {Path.cwd()}")
log(f"stdin.isatty(): {sys.stdin.isatty()}")
log(f"stdout.isatty(): {sys.stdout.isatty()}")
log(f"TERM: {os.environ.get('TERM', 'not set')}")
log(f"LYRA_TUI: {os.environ.get('LYRA_TUI', 'not set')}")

# Try importing
log("\n--- Import Phase ---")
try:
    log("Importing lyra_cli.tui_v2...")
    log("✓ Import successful")
except Exception as e:
    log(f"✗ Import failed: {e}")
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

# Try creating transport
log("\n--- Transport Phase ---")
try:
    log("Creating LyraTransport...")
    from lyra_cli.tui_v2.transport import LyraTransport
    transport = LyraTransport(repo_root=Path.cwd(), model='claude-sonnet-4.6', max_steps=20)
    log("✓ Transport created")
except Exception as e:
    log(f"✗ Transport creation failed: {e}")
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

# Try creating app
log("\n--- App Creation Phase ---")
try:
    log("Creating app...")
    from harness_tui import ProjectConfig
    from lyra_cli.tui_v2 import lyra_theme
    from lyra_cli.tui_v2.app import LyraHarnessApp
    from lyra_cli.tui_v2.commands import register_lyra_commands
    from lyra_cli.tui_v2.sidebar import build_lyra_sidebar_tabs

    cfg = ProjectConfig(
        name="lyra",
        description="General-purpose, CLI-native agent harness",
        theme=lyra_theme(),
        transport=transport,
        model='claude-sonnet-4.6',
        working_dir=str(Path.cwd()),
        sidebar_tabs=build_lyra_sidebar_tabs(Path.cwd()),
        extra_commands=[register_lyra_commands],
    )
    app = LyraHarnessApp(cfg)
    log("✓ App created")
except Exception as e:
    log(f"✗ App creation failed: {e}")
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

# Try running
log("\n--- Launch Phase ---")
log("Calling app.run()...")
log("(If you see this and the TUI doesn't appear, check for exceptions below)")
try:
    app.run()
    log("✓ App exited normally")
except KeyboardInterrupt:
    log("✓ Interrupted by user (Ctrl+C)")
except Exception as e:
    log(f"✗ App crashed: {e}")
    traceback.print_exc(file=sys.stderr)
    with open(log_file, "a") as f:
        traceback.print_exc(file=f)
    sys.exit(1)

log("\n--- Complete ---")
log(f"Log saved to: {log_file}")
