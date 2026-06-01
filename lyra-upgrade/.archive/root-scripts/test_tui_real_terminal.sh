#!/bin/bash
# Test script to run Lyra TUI directly in your terminal
# This must be run DIRECTLY in iTerm2, not through Claude Code

cd "$(dirname "$0")"

echo "=========================================="
echo "Lyra TUI Test Script"
echo "=========================================="
echo ""
echo "This script will launch the Lyra TUI."
echo "If it works, you should see the TUI interface."
echo "Press 'q' to quit when you're done."
echo ""
echo "Checking environment..."
echo "  Current directory: $(pwd)"
echo "  Python: $(.venv/bin/python --version)"
echo "  stdin is TTY: $(python3 -c 'import sys; print(sys.stdin.isatty())')"
echo ""
echo "Launching Lyra TUI in 2 seconds..."
sleep 2

# Run Lyra
.venv/bin/lyra

EXIT_CODE=$?
echo ""
echo "=========================================="
echo "Lyra TUI exited with code: $EXIT_CODE"
echo "=========================================="

if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ TUI exited normally"
else
    echo "✗ TUI exited with error code $EXIT_CODE"
fi
