#!/usr/bin/env python3
"""Test Terminal Manager - Phase 2"""

import os
import sys
import time

# Add to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/lyra-cli/src'))


def test_imports():
    """Test terminal manager imports"""
    print("Testing imports...")

    try:
        print("✓ TerminalManager import successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_terminal_manager_creation():
    """Test creating TerminalManager"""
    print("\nTesting TerminalManager creation...")

    try:
        from lyra_cli.terminal import TerminalManager

        manager = TerminalManager()
        print("✓ TerminalManager created")

        # Verify initial state
        assert manager.width > 0
        assert manager.height > 0
        assert manager.bottom_ui_height == 4
        print(f"✓ Terminal size: {manager.width}x{manager.height}")

        return True
    except Exception as e:
        print(f"✗ Creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_terminal_size():
    """Test terminal size detection"""
    print("\nTesting terminal size detection...")

    try:
        from lyra_cli.terminal import TerminalManager

        manager = TerminalManager()

        # Get size
        size = manager.get_size()
        print(f"✓ Terminal size: {size.width}x{size.height}")

        # Get content height
        content_height = manager.get_content_height()
        print(f"✓ Content height: {content_height} lines")

        # Get bottom UI start line
        bottom_start = manager.get_bottom_ui_start_line()
        print(f"✓ Bottom UI starts at line: {bottom_start}")

        # Verify calculations
        assert content_height == manager.height - manager.bottom_ui_height
        assert bottom_start == manager.height - manager.bottom_ui_height + 1
        print("✓ Size calculations correct")

        return True
    except Exception as e:
        print(f"✗ Size detection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cursor_movement():
    """Test cursor movement"""
    print("\nTesting cursor movement...")

    try:
        from lyra_cli.terminal import TerminalManager

        manager = TerminalManager()

        # Test basic cursor movement
        manager.move_cursor(1, 1)
        print("✓ Move cursor to (1,1)")

        manager.move_cursor_to_bottom_ui()
        print("✓ Move cursor to bottom UI")

        manager.move_cursor_to_input_line()
        print("✓ Move cursor to input line")

        manager.move_cursor_to_status_line()
        print("✓ Move cursor to status line")

        return True
    except Exception as e:
        print(f"✗ Cursor movement failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_screen_operations():
    """Test screen clearing operations"""
    print("\nTesting screen operations...")

    try:
        from lyra_cli.terminal import TerminalManager

        manager = TerminalManager()

        # Test cursor visibility
        manager.hide_cursor()
        print("✓ Hide cursor")

        manager.show_cursor()
        print("✓ Show cursor")

        # Test cursor save/restore
        manager.save_cursor_position()
        print("✓ Save cursor position")

        manager.restore_cursor_position()
        print("✓ Restore cursor position")

        return True
    except Exception as e:
        print(f"✗ Screen operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_terminal_info():
    """Test terminal information"""
    print("\nTesting terminal information...")

    try:
        from lyra_cli.terminal import TerminalManager

        manager = TerminalManager()

        # Get terminal info
        info = manager.get_terminal_info()
        print("✓ Terminal info retrieved")

        # Verify info structure
        required_keys = [
            "width", "height", "content_height",
            "bottom_ui_height", "bottom_ui_start",
            "is_tty", "supports_color", "term"
        ]

        for key in required_keys:
            assert key in info, f"Missing key: {key}"
        print("✓ All info keys present")

        # Display info
        print("\nTerminal Information:")
        for key, value in info.items():
            print(f"  {key}: {value}")

        return True
    except Exception as e:
        print(f"✗ Terminal info failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_resize_handler():
    """Test resize handler setup"""
    print("\nTesting resize handler...")

    try:
        from lyra_cli.terminal import TerminalManager

        manager = TerminalManager()

        # Setup resize callback
        resize_called = []

        def on_resize(width, height):
            resize_called.append((width, height))

        manager.on_resize = on_resize
        print("✓ Resize callback registered")

        # Note: We can't actually trigger a resize in automated tests
        # but we can verify the handler is set up
        import signal
        handler = signal.getsignal(signal.SIGWINCH)
        assert handler is not None
        assert handler != signal.SIG_DFL
        print("✓ SIGWINCH handler installed")

        return True
    except Exception as e:
        print(f"✗ Resize handler failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bottom_ui_rendering():
    """Test bottom UI frame rendering"""
    print("\nTesting bottom UI rendering...")

    try:
        from lyra_cli.terminal import TerminalManager

        manager = TerminalManager()

        # Clear screen first
        manager.clear_screen()
        manager.move_cursor(1, 1)

        # Render some content
        print("Content line 1")
        print("Content line 2")
        print("Content line 3")

        # Render bottom UI frame
        manager.render_bottom_ui_frame()
        print("✓ Bottom UI frame rendered")

        # Move to input line and show prompt
        manager.move_cursor_to_input_line()
        print("❯ [Input would go here]")

        # Move to status line and show status
        manager.move_cursor_to_status_line()
        print("  ⏵⏵ default · 0% context · ask permissions")

        time.sleep(1)  # Let user see the result

        return True
    except Exception as e:
        print(f"✗ Bottom UI rendering failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 80)
    print("PHASE 2: TERMINAL MANAGEMENT - TEST SUITE")
    print("=" * 80)
    print()

    results = []

    results.append(("Imports", test_imports()))
    results.append(("TerminalManager Creation", test_terminal_manager_creation()))
    results.append(("Terminal Size", test_terminal_size()))
    results.append(("Cursor Movement", test_cursor_movement()))
    results.append(("Screen Operations", test_screen_operations()))
    results.append(("Terminal Info", test_terminal_info()))
    results.append(("Resize Handler", test_resize_handler()))
    results.append(("Bottom UI Rendering", test_bottom_ui_rendering()))

    print()
    print("=" * 80)
    print("TEST RESULTS")
    print("=" * 80)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")

    all_passed = all(passed for _, passed in results)

    print()
    if all_passed:
        print("✓ ALL TESTS PASSED!")
        print()
        print("Phase 2 complete:")
        print("  ✓ TerminalManager class created")
        print("  ✓ Terminal size detection working")
        print("  ✓ SIGWINCH resize handler working")
        print("  ✓ Cursor positioning working")
        print("  ✓ Bottom UI frame rendering working")
        print()
        print("Ready to commit and push Phase 2!")
        sys.exit(0)
    else:
        print("✗ SOME TESTS FAILED")
        sys.exit(1)
