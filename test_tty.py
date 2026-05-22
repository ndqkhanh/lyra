#!/usr/bin/env python3
"""Check if stdin is a TTY."""
import sys

print(f"stdin.isatty(): {sys.stdin.isatty()}")
print(f"stdout.isatty(): {sys.stdout.isatty()}")
print(f"stderr.isatty(): {sys.stderr.isatty()}")

# Try to get terminal size
try:
    import os
    size = os.get_terminal_size()
    print(f"Terminal size: {size.columns}x{size.lines}")
except Exception as e:
    print(f"Cannot get terminal size: {e}")

# Check TERM environment variable
import os
print(f"TERM: {os.environ.get('TERM', 'not set')}")
print(f"COLORTERM: {os.environ.get('COLORTERM', 'not set')}")
