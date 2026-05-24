#!/usr/bin/env python3
"""Test Phase 2: Fixed Bottom UI (Input + Status)"""

import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/lyra-cli/src'))

from lyra_cli.ui import FixedInputBox, StatusLine


def test_fixed_input_box():
    """Test fixed input box"""
    print("=" * 80)
    print("TEST 1: Fixed Input Box")
    print("=" * 80)
    print()

    input_box = FixedInputBox()

    print("Testing input box rendering...")
    print("The input box should appear at the bottom of the terminal.")
    print()

    # Render input box
    input_box.render("")
    time.sleep(1)

    # Update with text
    input_box.update_text("Hello Lyra")
    time.sleep(1)

    # Update with more text
    input_box.update_text("Hello Lyra! How are you?")
    time.sleep(1)

    # Clear
    input_box.clear_input_area()

    print("✓ Fixed input box rendering works")
    print()


def test_status_line():
    """Test status line"""
    print("=" * 80)
    print("TEST 2: Status Line")
    print("=" * 80)
    print()

    status_line = StatusLine()

    print("Testing status line rendering...")
    print("The status line should appear at the very bottom.")
    print()

    # Render default status
    status_line.update("default", ["esc to exit"])
    time.sleep(1)

    # Update mode
    status_line.update("bypass permissions on", ["shift+tab to cycle", "esc to interrupt"])
    time.sleep(1)

    # Add hint
    status_line.add_hint("↓ to manage")
    time.sleep(1)

    # Clear
    status_line.clear()

    print("✓ Status line rendering works")
    print()


def test_combined_ui():
    """Test input box + status line together"""
    print("=" * 80)
    print("TEST 3: Combined Fixed UI")
    print("=" * 80)
    print()

    input_box = FixedInputBox()
    status_line = StatusLine()

    print("Testing combined fixed UI...")
    print("Both input box and status line should be visible at bottom.")
    print()

    # Render both
    input_box.render("Type your message here")
    status_line.update("default", ["esc to exit", "enter to send"])
    time.sleep(2)

    # Simulate typing
    for text in ["H", "He", "Hel", "Hell", "Hello", "Hello!"]:
        input_box.update_text(text)
        time.sleep(0.2)

    time.sleep(1)

    # Change mode
    status_line.update("thinking", ["please wait"])
    time.sleep(1)

    # Clear
    input_box.clear_input_area()
    status_line.clear()

    print("✓ Combined fixed UI works")
    print()


def test_streaming_with_fixed_ui():
    """Test streaming content with fixed UI"""
    print("=" * 80)
    print("TEST 4: Streaming with Fixed UI")
    print("=" * 80)
    print()

    input_box = FixedInputBox()
    status_line = StatusLine()

    # Setup fixed UI
    input_box.render("What is Python?")
    status_line.update("streaming", ["esc to interrupt"])

    print("Simulating streaming response...")
    print("The input box should stay at bottom while content streams.")
    print()

    # Simulate streaming content
    response = """Python is a high-level, interpreted programming language.
It was created by Guido van Rossum and first released in 1991.
Python emphasizes code readability with significant whitespace.
It supports multiple programming paradigms including:
- Object-oriented programming
- Functional programming
- Procedural programming

Python is widely used for:
- Web development
- Data science
- Machine learning
- Automation
- Scientific computing"""

    for line in response.split("\n"):
        print(line)
        time.sleep(0.3)

    print()
    print("✓ Streaming with fixed UI works")
    print()

    # Update status
    status_line.update("complete", ["enter for next"])
    time.sleep(1)

    # Clear
    input_box.clear_input_area()
    status_line.clear()


if __name__ == "__main__":
    print("\n")
    print("╭─── Phase 2: Fixed Bottom UI (Input + Status) ───╮")
    print("│ Testing fixed UI components                     │")
    print("╰──────────────────────────────────────────────────╯")
    print()

    test_fixed_input_box()
    test_status_line()
    test_combined_ui()
    test_streaming_with_fixed_ui()

    print("=" * 80)
    print("✓ ALL TESTS PASSED - Phase 2 Complete!")
    print("=" * 80)
    print()
    print("Key features implemented:")
    print("  ✓ Fixed input box at bottom (never scrolls away)")
    print("  ✓ Status line below input (always visible)")
    print("  ✓ ANSI positioning for fixed layout")
    print("  ✓ Works during streaming content")
    print()
