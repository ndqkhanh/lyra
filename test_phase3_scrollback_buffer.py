#!/usr/bin/env python3
"""Test Scrollback Buffer - Phase 3"""

import sys
import os
import tempfile
from datetime import datetime, timedelta

# Add to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/lyra-cli/src'))


def test_imports():
    """Test scrollback buffer imports"""
    print("Testing imports...")

    try:
        from lyra_cli.scrollback import ScrollbackBuffer, ScrollbackLine
        print("✓ ScrollbackBuffer import successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_buffer_creation():
    """Test creating ScrollbackBuffer"""
    print("\nTesting ScrollbackBuffer creation...")

    try:
        from lyra_cli.scrollback import ScrollbackBuffer

        # Default buffer
        buffer = ScrollbackBuffer()
        assert buffer.max_lines == 10000
        print("✓ Default buffer created (10,000 lines)")

        # Custom size buffer
        buffer2 = ScrollbackBuffer(max_lines=100)
        assert buffer2.max_lines == 100
        print("✓ Custom buffer created (100 lines)")

        return True
    except Exception as e:
        print(f"✗ Creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_append_lines():
    """Test appending lines"""
    print("\nTesting line appending...")

    try:
        from lyra_cli.scrollback import ScrollbackBuffer

        buffer = ScrollbackBuffer(max_lines=100)

        # Append single line
        buffer.append("Hello, world!", "text")
        assert buffer.get_line_count() == 1
        print("✓ Single line appended")

        # Append multiple lines
        buffer.append_multiple(["Line 1", "Line 2", "Line 3"], "text")
        assert buffer.get_line_count() == 4
        print("✓ Multiple lines appended")

        # Append different types
        buffer.append("Tool call", "tool")
        buffer.append("Error message", "error")
        buffer.append("System message", "system")
        assert buffer.get_line_count() == 7
        print("✓ Different line types appended")

        return True
    except Exception as e:
        print(f"✗ Append failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_line_limit():
    """Test automatic pruning at line limit"""
    print("\nTesting line limit pruning...")

    try:
        from lyra_cli.scrollback import ScrollbackBuffer

        buffer = ScrollbackBuffer(max_lines=10)

        # Add more than limit
        for i in range(15):
            buffer.append(f"Line {i}", "text")

        # Should be pruned to 10
        assert buffer.get_line_count() == 10
        print("✓ Buffer pruned to limit (10 lines)")

        # Verify oldest lines were removed
        lines = buffer.get_lines()
        assert lines[0].content == "Line 5"  # Lines 0-4 should be pruned
        print("✓ Oldest lines removed correctly")

        return True
    except Exception as e:
        print(f"✗ Line limit failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_get_lines():
    """Test getting lines from buffer"""
    print("\nTesting line retrieval...")

    try:
        from lyra_cli.scrollback import ScrollbackBuffer

        buffer = ScrollbackBuffer()

        # Add test data
        for i in range(10):
            buffer.append(f"Text {i}", "text")
        for i in range(5):
            buffer.append(f"Tool {i}", "tool")

        # Get all lines
        all_lines = buffer.get_lines()
        assert len(all_lines) == 15
        print("✓ Get all lines")

        # Get range
        range_lines = buffer.get_lines(start=5, end=10)
        assert len(range_lines) == 5
        print("✓ Get line range")

        # Get by type
        text_lines = buffer.get_lines(line_type="text")
        assert len(text_lines) == 10
        print("✓ Get lines by type")

        tool_lines = buffer.get_lines(line_type="tool")
        assert len(tool_lines) == 5
        print("✓ Get tool lines")

        # Get recent
        recent = buffer.get_recent(count=3)
        assert len(recent) == 3
        print("✓ Get recent lines")

        return True
    except Exception as e:
        print(f"✗ Get lines failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_search():
    """Test searching through buffer"""
    print("\nTesting search...")

    try:
        from lyra_cli.scrollback import ScrollbackBuffer

        buffer = ScrollbackBuffer()

        # Add test data
        buffer.append("Hello world", "text")
        buffer.append("HELLO WORLD", "text")
        buffer.append("Goodbye world", "text")
        buffer.append("Tool: read file", "tool")

        # Case-insensitive search
        results = buffer.search("hello", case_sensitive=False)
        assert len(results) == 2
        print("✓ Case-insensitive search")

        # Case-sensitive search
        results = buffer.search("HELLO", case_sensitive=True)
        assert len(results) == 1
        print("✓ Case-sensitive search")

        # Search with type filter
        results = buffer.search("world", line_type="text")
        assert len(results) == 3
        print("✓ Search with type filter")

        return True
    except Exception as e:
        print(f"✗ Search failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_statistics():
    """Test buffer statistics"""
    print("\nTesting statistics...")

    try:
        from lyra_cli.scrollback import ScrollbackBuffer

        buffer = ScrollbackBuffer(max_lines=100)

        # Add test data
        for i in range(10):
            buffer.append(f"Text {i}", "text")
        for i in range(5):
            buffer.append(f"Tool {i}", "tool")
        for i in range(3):
            buffer.append(f"Error {i}", "error")

        # Get statistics
        stats = buffer.get_statistics()
        print("✓ Statistics retrieved")

        # Verify statistics
        assert stats["total_lines"] == 18
        assert stats["by_type"]["text"] == 10
        assert stats["by_type"]["tool"] == 5
        assert stats["by_type"]["error"] == 3
        print("✓ Statistics correct")

        # Display statistics
        print("\nBuffer Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

        return True
    except Exception as e:
        print(f"✗ Statistics failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_save_load():
    """Test saving and loading buffer"""
    print("\nTesting save/load...")

    try:
        from lyra_cli.scrollback import ScrollbackBuffer

        buffer = ScrollbackBuffer()

        # Add test data
        buffer.append("Line 1", "text")
        buffer.append("Line 2", "tool")
        buffer.append("Line 3", "error")

        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name

        try:
            # Save as JSON
            buffer.save_to_file(filepath, format="json")
            print("✓ Saved to JSON")

            # Load from JSON
            buffer2 = ScrollbackBuffer()
            buffer2.load_from_file(filepath, format="json")
            assert buffer2.get_line_count() == 3
            print("✓ Loaded from JSON")

            # Verify content
            lines = buffer2.get_lines()
            assert lines[0].content == "Line 1"
            assert lines[1].content == "Line 2"
            assert lines[2].content == "Line 3"
            print("✓ Content preserved")

            # Test text format
            text_path = filepath.replace('.json', '.txt')
            buffer.save_to_file(text_path, format="text")
            print("✓ Saved to text")

            # Test markdown format
            md_path = filepath.replace('.json', '.md')
            buffer.save_to_file(md_path, format="markdown")
            print("✓ Saved to markdown")

            # Cleanup
            os.unlink(text_path)
            os.unlink(md_path)

        finally:
            os.unlink(filepath)

        return True
    except Exception as e:
        print(f"✗ Save/load failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_context_window():
    """Test context window retrieval"""
    print("\nTesting context window...")

    try:
        from lyra_cli.scrollback import ScrollbackBuffer

        buffer = ScrollbackBuffer()

        # Add test data
        for i in range(20):
            buffer.append(f"Line {i}", "text")

        # Get context around line 10
        context = buffer.get_context_window(center_index=10, before=2, after=2)
        assert len(context) == 5  # 2 before + center + 2 after
        print("✓ Context window retrieved")

        # Verify content
        assert context[0].content == "Line 8"
        assert context[2].content == "Line 10"
        assert context[4].content == "Line 12"
        print("✓ Context window content correct")

        return True
    except Exception as e:
        print(f"✗ Context window failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 80)
    print("PHASE 3: SCROLLBACK BUFFER - TEST SUITE")
    print("=" * 80)
    print()

    results = []

    results.append(("Imports", test_imports()))
    results.append(("Buffer Creation", test_buffer_creation()))
    results.append(("Append Lines", test_append_lines()))
    results.append(("Line Limit", test_line_limit()))
    results.append(("Get Lines", test_get_lines()))
    results.append(("Search", test_search()))
    results.append(("Statistics", test_statistics()))
    results.append(("Save/Load", test_save_load()))
    results.append(("Context Window", test_context_window()))

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
        print("Phase 3 complete:")
        print("  ✓ ScrollbackBuffer class created")
        print("  ✓ Line appending with types working")
        print("  ✓ Automatic pruning at 10,000 line limit")
        print("  ✓ Search functionality working")
        print("  ✓ Save/load in multiple formats")
        print("  ✓ Statistics and context windows")
        print()
        print("Ready to commit and push Phase 3!")
        sys.exit(0)
    else:
        print("✗ SOME TESTS FAILED")
        sys.exit(1)
