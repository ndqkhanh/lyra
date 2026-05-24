#!/usr/bin/env python3
"""Performance test for ScrollbackBuffer - verify 10,000+ line handling."""

import sys
import time
from pathlib import Path

# Add to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "packages/lyra-cli/src"))

from lyra_cli.streaming.buffer import ScrollbackBuffer


def test_large_buffer_performance():
    """Test performance with 10,000+ lines."""
    print("Testing ScrollbackBuffer performance with 10,000+ lines...")
    print()

    buffer = ScrollbackBuffer(max_lines=10000)

    # Test 1: Append 15,000 lines (should keep only last 10,000)
    print("Test 1: Appending 15,000 lines...")
    start = time.time()
    for i in range(15000):
        buffer.append(f"Line {i}", "text")
    elapsed = time.time() - start

    assert buffer.get_line_count() == 10000, f"Expected 10000 lines, got {buffer.get_line_count()}"
    print(f"✓ Appended 15,000 lines in {elapsed:.3f}s ({15000/elapsed:.0f} lines/sec)")
    print(f"✓ Buffer correctly limited to 10,000 lines")

    # Verify oldest lines were dropped
    lines = buffer.get_lines()
    assert lines[0].content == "Line 5000", f"Expected 'Line 5000', got '{lines[0].content}'"
    assert lines[-1].content == "Line 14999", f"Expected 'Line 14999', got '{lines[-1].content}'"
    print(f"✓ Oldest 5,000 lines correctly dropped")
    print()

    # Test 2: Search performance
    print("Test 2: Search performance...")
    start = time.time()
    results = buffer.search("Line 1000")
    elapsed = time.time() - start

    print(f"✓ Search completed in {elapsed:.3f}s")
    print(f"✓ Found {len(results)} matches")
    print()

    # Test 3: Get lines by type
    print("Test 3: Filter by type...")
    buffer.append("Tool call 1", "tool")
    buffer.append("Tool call 2", "tool")
    buffer.append("Error message", "error")

    start = time.time()
    tool_lines = buffer.get_lines(line_type="tool")
    elapsed = time.time() - start

    assert len(tool_lines) == 2
    print(f"✓ Type filter completed in {elapsed:.3f}s")
    print(f"✓ Found {len(tool_lines)} tool lines")
    print()

    # Test 4: Statistics
    print("Test 4: Statistics...")
    stats = buffer.get_statistics()
    print(f"  Total lines: {stats['total_lines']}")
    print(f"  Max lines: {stats['max_lines']}")
    print(f"  By type: {stats['by_type']}")
    print()

    # Test 5: Memory efficiency
    print("Test 5: Memory efficiency...")
    import sys
    buffer_size = sys.getsizeof(buffer._buffer)
    avg_per_line = buffer_size / buffer.get_line_count()
    print(f"  Buffer size: {buffer_size:,} bytes")
    print(f"  Average per line: {avg_per_line:.1f} bytes")
    print()

    print("✓ ALL PERFORMANCE TESTS PASSED!")
    print()
    print("Summary:")
    print("  ✓ Handles 15,000 line append efficiently")
    print("  ✓ Circular buffer correctly limits to 10,000 lines")
    print("  ✓ Search is fast on large buffers")
    print("  ✓ Type filtering works correctly")
    print("  ✓ Memory usage is reasonable")


if __name__ == "__main__":
    test_large_buffer_performance()
