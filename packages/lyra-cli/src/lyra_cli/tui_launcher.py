#!/usr/bin/env python3
"""Launch the TypeScript/Ink TUI from Python CLI"""

import atexit
import subprocess
import sys
import termios
import time
import tty
from pathlib import Path


def find_ui_terminal_path() -> Path | None:
    """Find the ui-terminal package directory"""
    # Try relative to this file
    cli_dir = Path(__file__).parent
    ui_terminal = cli_dir.parent.parent.parent / "ui-terminal"

    if ui_terminal.exists() and (ui_terminal / "src" / "index.tsx").exists():
        return ui_terminal

    # Try from current working directory
    cwd_ui_terminal = Path.cwd() / "packages" / "ui-terminal"
    if cwd_ui_terminal.exists() and (cwd_ui_terminal / "src" / "index.tsx").exists():
        return cwd_ui_terminal

    return None


def start_server_background() -> subprocess.Popen | None:
    """Start the Lyra UI server in the background."""
    try:
        # Start server as a subprocess
        server_process = subprocess.Popen(
            [sys.executable, "-m", "lyra_cli.ui_server"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        # Wait a bit for server to start
        time.sleep(0.5)

        # Check if server is running
        if server_process.poll() is not None:
            # Server died immediately
            return None

        # Register cleanup
        def cleanup():
            if server_process.poll() is None:
                server_process.terminate()
                server_process.wait(timeout=2)

        atexit.register(cleanup)

        return server_process
    except Exception:
        return None


def launch_tui() -> int:
    """Launch the TypeScript TUI using tsx"""
    ui_terminal_path = find_ui_terminal_path()

    if not ui_terminal_path:
        print("Error: ui-terminal package not found.", file=sys.stderr)
        print("Please ensure packages/ui-terminal exists.", file=sys.stderr)
        return 1

    # Start the HTTP server in background
    print("Starting Lyra server...", file=sys.stderr)
    server_process = start_server_background()

    if not server_process:
        print("Warning: Failed to start Lyra server. LLM calls may not work.", file=sys.stderr)

    # Save terminal settings
    old_settings = None
    if sys.stdin.isatty():
        try:
            old_settings = termios.tcgetattr(sys.stdin)
            # Put terminal in raw mode immediately to prevent echo
            tty.setraw(sys.stdin.fileno())

            # Clear screen
            sys.stdout.write('\033[2J\033[H')
            sys.stdout.flush()

            # Restore terminal for subprocess
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        except Exception:
            # If we can't set raw mode, just continue
            pass

    # Launch the TUI using tsx (no build needed)
    entry_point = ui_terminal_path / "src" / "index.tsx"

    try:
        # Try tsx first (development mode, no build needed)
        result = subprocess.run(
            ["npx", "tsx", str(entry_point)],
            cwd=str(ui_terminal_path),
        )
        return result.returncode
    except FileNotFoundError:
        print("Error: Node.js/npx not found. Please install Node.js.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        # Restore terminal settings on exit
        if old_settings is not None:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            except Exception:
                pass

        # Stop server
        if server_process and server_process.poll() is None:
            server_process.terminate()
            try:
                server_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                server_process.kill()


if __name__ == "__main__":
    sys.exit(launch_tui())
