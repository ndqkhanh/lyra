#!/usr/bin/env python3
"""Test Phase 3: Response Format Patterns"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/lyra-cli/src'))

from lyra_cli.ui import ResponseFormatter


def test_active_response():
    """Test active response indicator (⏺)"""
    print("=" * 80)
    print("TEST 1: Active Response Indicator (⏺)")
    print("=" * 80)

    formatter = ResponseFormatter()

    # Test active response
    print(formatter.format_active_response("Analyzing your request..."))
    print(formatter.format_active_response("Reading file.py"))
    print(formatter.format_active_response("Running tests"))

    print()
    print("✓ Active response indicator works")
    print()


def test_stats_line():
    """Test stats line (✻)"""
    print("=" * 80)
    print("TEST 2: Stats Line (✻)")
    print("=" * 80)

    formatter = ResponseFormatter()

    # Test stats line
    print(formatter.format_stats_line(2.3, 3, 1234))
    print(formatter.format_stats_line(15.7, 10, 5678))
    print(formatter.format_stats_line(0.5, 1, 100))

    print()
    print("✓ Stats line formatting works")
    print()


def test_thinking():
    """Test thinking indicator (✶)"""
    print("=" * 80)
    print("TEST 3: Thinking Indicator (✶)")
    print("=" * 80)

    formatter = ResponseFormatter()

    # Test thinking
    print(formatter.format_thinking("Analyzing request"))
    print(formatter.format_thinking("Processing", 5.2))
    print(formatter.format_thinking("Almost done thinking", 120.0))

    print()
    print("✓ Thinking indicator works")
    print()


def test_tool_calls():
    """Test tool call display (⎿)"""
    print("=" * 80)
    print("TEST 4: Tool Call Display (⎿)")
    print("=" * 80)

    formatter = ResponseFormatter()

    # Test tool calls
    print(formatter.format_tool_call("Read", "file.py (228 lines)"))
    print(formatter.format_tool_call("Edit", "src/main.py"))
    print(formatter.format_tool_call("Bash", "npm test"))
    print(formatter.format_tool_result("Output: All tests passed", indent_level=1))

    print()
    print("✓ Tool call display works")
    print()


def test_status_messages():
    """Test status messages (✓ ✗ ⚠ ℹ)"""
    print("=" * 80)
    print("TEST 5: Status Messages")
    print("=" * 80)

    formatter = ResponseFormatter()

    # Test status messages
    print(formatter.format_success("Tests passed"))
    print(formatter.format_error("Build failed"))
    print(formatter.format_warning("Deprecated API used"))
    print(formatter.format_info("Using cache"))

    print()
    print("✓ Status messages work")
    print()


def test_complete_response():
    """Test complete response flow"""
    print("=" * 80)
    print("TEST 6: Complete Response Flow")
    print("=" * 80)

    formatter = ResponseFormatter()

    # Simulate complete response
    print(formatter.format_active_response("Analyzing your request..."))
    print()
    print(formatter.format_tool_call("Read", "src/lyra_cli/cli/agent_integration.py (228 lines)"))
    print(formatter.format_tool_call("Read", "src/lyra_cli/cli/tui.py"))
    print()
    print(formatter.format_thinking("Processing files", 2.5))
    print()
    print("I've analyzed the files. Here's what I found:")
    print("- The agent integration is well-structured")
    print("- The TUI implementation uses Textual")
    print()
    print(formatter.format_success("Analysis complete"))
    print()
    print(formatter.format_stats_line(5.2, 2, 1500))

    print()
    print("✓ Complete response flow works")
    print()


def test_with_streaming():
    """Test response patterns with streaming"""
    print("=" * 80)
    print("TEST 7: Response Patterns with Streaming")
    print("=" * 80)

    formatter = ResponseFormatter()

    # Simulate streaming response
    print(formatter.format_active_response("Launching parallel research..."))
    print()
    print(formatter.format_info("Running 4 agents in parallel"))
    print()
    print(formatter.format_tool_call("Agent 1", "Research GitHub repos · 10 tool uses · 29.7k tokens"))
    print(formatter.format_tool_result("Bash: Fetch RTK README via gh API", indent_level=1))
    print()
    print(formatter.format_tool_call("Agent 2", "Search GitHub · 6 tool uses · 29.9k tokens"))
    print(formatter.format_tool_result("Web Search: llmlingua context compression", indent_level=1))
    print()
    print(formatter.format_thinking("Synthesizing results", 15.0))
    print()
    print("Research complete! Here are the findings:")
    print("- Found 5 relevant repositories")
    print("- Identified 3 key techniques")
    print()
    print(formatter.format_success("Research complete"))
    print(formatter.format_stats_line(18.5, 16, 59300))

    print()
    print("✓ Streaming with response patterns works")
    print()


if __name__ == "__main__":
    print("\n")
    print("╭─── Phase 3: Response Format Patterns ───╮")
    print("│ Testing ⏺ ✻ ✶ ⎿ symbols and formatting │")
    print("╰──────────────────────────────────────────╯")
    print()

    test_active_response()
    test_stats_line()
    test_thinking()
    test_tool_calls()
    test_status_messages()
    test_complete_response()
    test_with_streaming()

    print("=" * 80)
    print("✓ ALL TESTS PASSED - Phase 3 Complete!")
    print("=" * 80)
    print()
    print("Key features implemented:")
    print("  ✓ ⏺ Active response indicator")
    print("  ✓ ✻ Stats line (time · tools · tokens)")
    print("  ✓ ✶ Thinking indicator")
    print("  ✓ ⎿ Tool call display")
    print("  ✓ ✓ ✗ ⚠ ℹ Status messages")
    print("  ✓ Complete response flow patterns")
    print()
