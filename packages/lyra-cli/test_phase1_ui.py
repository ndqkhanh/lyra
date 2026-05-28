#!/usr/bin/env python3
"""Test Phase 1: Core Formatting Infrastructure"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from lyra_cli.ui import (
    BOX_CHARS,
    STATUS_SYMBOLS,
    ColorEngine,
    LayoutEngine,
    LyraUIRenderer,
    SymbolRegistry,
)


def print_section(title: str):
    """Print test section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_symbols():
    """Test symbol registry"""
    print_section("TESTING SYMBOL REGISTRY")

    registry = SymbolRegistry(use_unicode=True)

    print("\n✓ Status Symbols:")
    for status in ["running", "idle", "completed", "failed", "thinking", "flowing"]:
        symbol = registry.status(status)
        print(f"  {symbol} {status}")

    print("\n✓ Box Drawing Characters:")
    for pos in ["top_left", "top_right", "bottom_left", "bottom_right", "horizontal", "vertical"]:
        char = registry.box(pos)
        print(f"  {char} {pos}")

    print("\n✓ Global Symbol Maps:")
    print(f"  STATUS_SYMBOLS: {STATUS_SYMBOLS}")
    print(f"  BOX_CHARS: {BOX_CHARS}")


def test_colors():
    """Test color engine"""
    print_section("TESTING COLOR ENGINE")

    colors = ColorEngine(use_colors=True)

    print("\n✓ Basic Colors:")
    print(f"  {colors.red('Red text')}")
    print(f"  {colors.green('Green text')}")
    print(f"  {colors.yellow('Yellow text')}")
    print(f"  {colors.cyan('Cyan text')}")
    print(f"  {colors.white('White text')}")

    print("\n✓ Text Styles:")
    print(f"  {colors.bold('Bold text')}")
    print(f"  {colors.dim('Dim text')}")

    print("\n✓ ANSI Stripping:")
    styled_text = colors.red("Colored text")
    clean_text = colors.strip_ansi(styled_text)
    print(f"  Original: {styled_text}")
    print(f"  Stripped: {clean_text}")

    print("\n✓ Visual Width:")
    text = colors.bold(colors.cyan("Test"))
    width = colors.visual_width(text)
    print(f"  Text: {text}")
    print(f"  Visual width: {width}")


def test_layout():
    """Test layout engine"""
    print_section("TESTING LAYOUT ENGINE")

    layout = LayoutEngine()

    print("\n✓ Text Wrapping:")
    long_text = "This is a very long line of text that should be wrapped to multiple lines when it exceeds the maximum width"
    wrapped = layout.wrap_text(long_text, max_width=40)
    for line in wrapped:
        print(f"  |{line}|")

    print("\n✓ Text Truncation:")
    long_text = "This is a very long text that will be truncated"
    truncated = layout.truncate_text(long_text, max_width=30)
    print(f"  Original: {long_text}")
    print(f"  Truncated: {truncated}")

    print("\n✓ Number Formatting:")
    print(f"  1234 → {layout.format_number(1234)}")
    print(f"  1234567 → {layout.format_number(1234567)}")

    print("\n✓ Token Count Formatting:")
    print(f"  500 → {layout.format_token_count(500)}")
    print(f"  12450 → {layout.format_token_count(12450)}")
    print(f"  1500000 → {layout.format_token_count(1500000)}")

    print("\n✓ Time Formatting:")
    print(f"  45 seconds → {layout.format_time(45)}")
    print(f"  125 seconds → {layout.format_time(125)}")
    print(f"  3665 seconds → {layout.format_time(3665)}")

    print("\n✓ Text Alignment:")
    text = "Test"
    print(f"  Left:   |{layout.pad_to_width(text, 20, 'left')}|")
    print(f"  Right:  |{layout.pad_to_width(text, 20, 'right')}|")
    print(f"  Center: |{layout.pad_to_width(text, 20, 'center')}|")

    print("\n✓ Separator:")
    print(f"  {layout.create_separator(40)}")


def test_renderer():
    """Test unified renderer"""
    print_section("TESTING UNIFIED RENDERER")

    renderer = LyraUIRenderer(use_colors=True, use_unicode=True)

    print("\n✓ Box Rendering:")
    box_content = "Welcome to Lyra!\n\nThis is a test of the box rendering system."
    box = renderer.render_box(box_content, title="Test Box", width=60)
    print(box)

    print("\n✓ Status Line:")
    status = renderer.render_status(
        "Working on task",
        elapsed_seconds=125,
        tokens_in=12450,
        tokens_out=8320,
        phase="analyzing"
    )
    print(status)

    print("\n✓ Tree Node:")
    root = renderer.render_tree_node("Running 4 agents…", is_last=False, indent_level=0)
    print(root)

    child1 = renderer.render_tree_node("Research GitHub repos · 10 tool uses · 29.7k tokens", is_last=False, indent_level=1)
    print(child1)

    child2 = renderer.render_tree_node("Search academic papers · 5 tool uses · 29.8k tokens", is_last=True, indent_level=1)
    print(child2)

    print("\n✓ Tool Result:")
    result = renderer.render_tool_result("Bash: Fetch README via gh API", indent_level=2)
    print(result)

    print("\n✓ File Update:")
    update = renderer.render_file_update("src/lyra_cli/ui/renderer.py", added_lines=8, removed_lines=2)
    print(update)

    print("\n✓ Diff Lines:")
    print(renderer.render_diff_line(263, "    def on_mount(self) -> None:", "context"))
    print(renderer.render_diff_line(264, "        import sys", "context"))
    print(renderer.render_diff_line(266, "        super().on_mount()", "remove"))
    print(renderer.render_diff_line(266, "        try:", "add"))
    print(renderer.render_diff_line(267, "            super().on_mount()", "add"))

    print("\n✓ Diagnostic Summary:")
    diagnostic = renderer.render_diagnostic_summary(error_count=4, file_count=1, collapsed=True)
    print(diagnostic)

    print("\n✓ Agent Status:")
    main_agent = renderer.render_agent_status("main", "", elapsed_seconds=0, is_main=True)
    print(main_agent)

    sub_agent = renderer.render_agent_status(
        "general-purpose",
        "Research provided GitHub repos on token reduction",
        elapsed_seconds=30,
        is_main=False
    )
    print(sub_agent)

    print("\n✓ Separator:")
    print(renderer.render_separator(width=80))


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("  PHASE 1: CORE FORMATTING INFRASTRUCTURE - TEST SUITE")
    print("=" * 80)

    try:
        test_symbols()
        test_colors()
        test_layout()
        test_renderer()

        print("\n" + "=" * 80)
        print("  ✓ ALL TESTS PASSED")
        print("=" * 80)
        return 0

    except Exception as e:
        print("\n" + "=" * 80)
        print(f"  ✗ TEST FAILED: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
