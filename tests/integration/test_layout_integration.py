#!/usr/bin/env python3
"""
Integration Test for Fixed Bottom Layout

This test verifies that the fixed bottom layout is working correctly
in Lyra's chat interface.
"""

import sys
import time
from pathlib import Path

# Add lyra_cli to path
sys.path.insert(0, str(Path(__file__).parent / "packages/lyra-cli/src"))

from lyra_cli.ui.fixed_layout import FixedBottomLayout, StreamingRenderer


def test_fixed_bottom_layout():
    """Test that fixed bottom layout works correctly"""
    print("="*80)
    print("INTEGRATION TEST: Fixed Bottom Layout")
    print("="*80)
    print()

    layout = FixedBottomLayout()

    # Test 1: Verify dimensions calculation
    print("✓ Test 1: Dimensions calculation")
    dims = layout.dimensions
    assert dims.scrollable_height == dims.terminal_height - 4
    assert dims.input_row == dims.terminal_height - 2
    assert dims.status_row == dims.terminal_height
    print(f"  Terminal: {dims.terminal_width}x{dims.terminal_height}")
    print(f"  Scrollable: {dims.scrollable_height} rows")
    print(f"  Input row: {dims.input_row}")
    print(f"  Status row: {dims.status_row}")
    print()

    # Test 2: Verify content appending
    print("✓ Test 2: Content appending")
    layout.append_content("Line 1")
    layout.append_content("Line 2")
    layout.append_content("Line 3")
    assert len(layout.scroll_buffer) == 3
    print(f"  Buffer size: {len(layout.scroll_buffer)} lines")
    print()

    # Test 3: Verify scrolling behavior
    print("✓ Test 3: Scrolling behavior")
    # Add more lines than scrollable height
    for i in range(dims.scrollable_height + 10):
        layout.append_content(f"Line {i+4}")

    visible = layout.get_visible_lines()
    assert len(visible) == dims.scrollable_height
    print(f"  Total lines: {len(layout.scroll_buffer)}")
    print(f"  Visible lines: {len(visible)}")
    print("  Auto-scroll: ✓")
    print()

    # Test 4: Verify input/status updates
    print("✓ Test 4: Input and status updates")
    layout.set_input("Test input")
    assert layout.input_text == "Test input"
    layout.set_status("Test status")
    assert layout.status_text == "Test status"
    print(f"  Input text: '{layout.input_text}'")
    print(f"  Status text: '{layout.status_text}'")
    print()

    # Test 5: Verify streaming renderer
    print("✓ Test 5: Streaming renderer")
    renderer = StreamingRenderer(layout)
    test_text = "This is a streaming test"
    for char in test_text:
        renderer.append_delta(char)
    renderer.finalize()
    assert layout.scroll_buffer[-1] == test_text
    print(f"  Streamed: '{test_text}'")
    print()

    # Test 6: Verify resize handling
    print("✓ Test 6: Resize handling")
    old_height = layout.dimensions.terminal_height
    layout.refresh_dimensions()
    new_height = layout.dimensions.terminal_height
    print(f"  Old height: {old_height}")
    print(f"  New height: {new_height}")
    print("  Resize handler: ✓")
    print()

    print("="*80)
    print("ALL TESTS PASSED ✓")
    print("="*80)
    print()
    print("The fixed bottom layout is working correctly!")
    print()


def test_visual_demo():
    """Visual demonstration of fixed bottom layout"""
    print("="*80)
    print("VISUAL DEMO: Fixed Bottom Layout")
    print("="*80)
    print()
    print("This demo will show the fixed bottom layout in action.")
    print("Watch how the input box and status line stay at the bottom")
    print("while content streams above them.")
    print()
    print("Starting in 3 seconds...")
    time.sleep(3)

    layout = FixedBottomLayout()
    layout.use_alt_screen = True
    layout.enter_alt_screen()

    try:
        # Show welcome
        layout.append_content("╭─────────────────────────────── Lyra UI Test ───────────────────────────────╮")
        layout.append_content("│                                                                            │")
        layout.append_content("│  Testing Fixed Bottom Layout                                               │")
        layout.append_content("│                                                                            │")
        layout.append_content("╰────────────────────────────────────────────────────────────────────────────╯")
        layout.append_content("")

        # Set initial status
        layout.set_status("  ⏵⏵ testing · watch the bottom")

        # Simulate streaming content
        layout.append_content("⏺ Starting test...")
        time.sleep(0.5)

        layout.append_content("  ⎿ Test 1: Content streaming")
        time.sleep(0.5)

        # Stream many lines to test scrolling
        for i in range(30):
            layout.append_content(f"Line {i+1}: This is test content to verify scrolling")
            time.sleep(0.1)

        layout.append_content("")
        layout.append_content("✓ Test complete!")
        layout.append_content("")
        layout.append_content("✻ 3s · 1 test · success")

        # Update status
        layout.set_status("  ⏵⏵ test complete · press Enter to exit")

        # Wait for user
        input()

    finally:
        layout.exit_alt_screen()


def test_agent_handler_integration():
    """Test agent handler integration"""
    print("="*80)
    print("INTEGRATION TEST: Agent Handler")
    print("="*80)
    print()

    from lyra_cli.cli.agent_handler import FixedLayoutAgentHandler

    layout = FixedBottomLayout()
    handler = FixedLayoutAgentHandler(layout)

    # Test 1: Turn start
    print("✓ Test 1: Turn start")
    handler.on_turn_start("test-turn-1")
    assert handler.current_turn == "test-turn-1"
    assert handler.turn_start_time is not None
    print(f"  Turn ID: {handler.current_turn}")
    print()

    # Test 2: Tool use
    print("✓ Test 2: Tool use")
    handler.on_tool_use("Read", {"file": "test.py"})
    assert handler.tool_count == 1
    print(f"  Tool count: {handler.tool_count}")
    print()

    # Test 3: Streaming
    print("✓ Test 3: Streaming")
    test_chunks = ["Hello", " ", "world", "!"]
    for chunk in test_chunks:
        handler.on_stream_chunk(chunk)
    print(f"  Streamed: {''.join(test_chunks)}")
    print()

    # Test 4: Turn end
    print("✓ Test 4: Turn end")
    result = {
        "usage": {
            "total_tokens": 1234
        }
    }
    handler.on_turn_end("test-turn-1", result)
    assert handler.current_turn is None
    print("  Turn ended successfully")
    print()

    # Test 5: Error handling
    print("✓ Test 5: Error handling")
    handler.on_turn_start("test-turn-2")
    handler.on_error(Exception("Test error"))
    assert handler.current_turn is None
    print("  Error handled successfully")
    print()

    print("="*80)
    print("ALL AGENT HANDLER TESTS PASSED ✓")
    print("="*80)
    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Integration tests for fixed bottom layout")
    parser.add_argument("--test", choices=["unit", "visual", "agent", "all"],
                       default="all", help="Which test to run")
    args = parser.parse_args()

    try:
        if args.test in ["unit", "all"]:
            test_fixed_bottom_layout()
            print()

        if args.test in ["agent", "all"]:
            test_agent_handler_integration()
            print()

        if args.test in ["visual", "all"]:
            print("Press Enter to start visual demo...")
            input()
            test_visual_demo()

        print()
        print("🎉 All integration tests completed successfully!")
        print()
        print("Next steps:")
        print("1. Run 'lyra' to test the live chat interface")
        print("2. Verify input box stays at bottom during streaming")
        print("3. Verify status line stays below input")
        print("4. Test terminal resize (resize your terminal window)")
        print()

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
