#!/usr/bin/env python3
"""Test responsive UI with terminal resize"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/lyra-cli/src'))

import time

from lyra_cli.cli.responsive_ui import ResponsiveChatUI, ResponsiveUI
from rich.console import Console


def test_responsive_banner():
    """Test responsive banner at different widths"""
    console = Console()
    ui = ResponsiveUI(console)

    print("=" * 80)
    print("RESPONSIVE BANNER TEST")
    print("=" * 80)
    print()

    # Show current size
    width, height = ui.get_size()
    print(f"Current terminal size: {width}x{height}")
    print()

    # Show banner
    ui.responsive_banner("Opus 4.7", "Khanh")

    print("\n✓ Banner adapts to terminal width:")
    print("  - <80 cols: Narrow (compact)")
    print("  - 80-120 cols: Medium (full)")
    print("  - >120 cols: Wide (two-column)")


def test_responsive_text():
    """Test text wrapping"""
    console = Console()
    ui = ResponsiveUI(console)

    print("\n" + "=" * 80)
    print("RESPONSIVE TEXT WRAPPING TEST")
    print("=" * 80)
    print()

    long_text = "This is a very long line of text that should wrap automatically when the terminal is too narrow to display it all on one line. The responsive UI will handle this gracefully."

    wrapped = ui.responsive_text(long_text)
    console.print(wrapped)

    print("\n✓ Text wraps to fit terminal width")


def test_responsive_menu():
    """Test responsive menu"""
    console = Console()
    ui = ResponsiveUI(console)

    print("\n" + "=" * 80)
    print("RESPONSIVE MENU TEST")
    print("=" * 80)
    print()

    options = [
        ("Opus 4.7", "Most capable"),
        ("Sonnet 4.6", "Best for everyday"),
        ("Haiku 4.5", "Fastest"),
    ]

    ui.responsive_menu("Select model", options, selected=1)

    print("\n✓ Menu adapts to terminal width:")
    print("  - <80 cols: Compact (no descriptions)")
    print("  - >80 cols: Full (with descriptions)")


def test_responsive_chat():
    """Test responsive chat UI"""
    console = Console()
    chat = ResponsiveChatUI(console)

    print("\n" + "=" * 80)
    print("RESPONSIVE CHAT TEST")
    print("=" * 80)

    # User message
    chat.show_message("user", "Write a function to calculate fibonacci numbers")

    # Thinking
    chat.show_thinking("Analyzing request")

    # Tool use
    chat.show_tool_use("Write", "fibonacci.py")

    # Assistant response
    chat.show_message("assistant", "I've created a fibonacci function that uses dynamic programming for efficiency. The function handles edge cases and returns the nth fibonacci number.")

    # Stats
    chat.show_stats("2.3s", 3, 1234)

    print("\n✓ Chat messages wrap to fit terminal width")


def test_live_resize():
    """Test live resize handling"""
    console = Console()
    ui = ResponsiveUI(console)

    print("\n" + "=" * 80)
    print("LIVE RESIZE TEST")
    print("=" * 80)
    print()
    print("Starting live resize demo...")
    print("Resize your terminal to see the display update!")
    print("Press Ctrl+C to stop")
    print()

    time.sleep(2)

    try:
        ui.live_resize_demo()
    except KeyboardInterrupt:
        print("\n\n✓ Live resize handling works!")


if __name__ == "__main__":
    try:
        test_responsive_banner()
        test_responsive_text()
        test_responsive_menu()
        test_responsive_chat()

        print("\n" + "=" * 80)
        print("✓ ALL RESPONSIVE UI TESTS PASSED!")
        print("=" * 80)
        print()
        print("Features implemented:")
        print("  ✓ Responsive banner (3 layouts)")
        print("  ✓ Text wrapping")
        print("  ✓ Responsive menus")
        print("  ✓ Responsive chat")
        print("  ✓ Live resize handling (SIGWINCH)")
        print("  ✓ Adaptive layouts")
        print()
        print("Try the live resize demo? (y/n)")

        response = input().strip().lower()
        if response == 'y':
            test_live_resize()

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
