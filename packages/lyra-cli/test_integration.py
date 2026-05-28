#!/usr/bin/env python3
"""Integration Test - Complete UI System"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from lyra_cli.ui import (
    ExpandableRenderer,
    LyraUIRenderer,
    ToolCallFormatter,
    TreeNode,
    TreeRenderer,
)


def print_section(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_complete_response():
    """Test complete response rendering with all components"""
    print_section("COMPLETE RESPONSE RENDERING")

    # Initialize renderers
    ui = LyraUIRenderer()
    tree = TreeRenderer()
    expandable = ExpandableRenderer()
    tool_fmt = ToolCallFormatter()

    print("\n" + ui.render_separator(80))
    print()

    # Status line
    status = ui.render_status(
        "Analyzing codebase",
        elapsed_seconds=125,
        tokens_in=12450,
        tokens_out=8320,
        phase="phase 1/3"
    )
    print(status)
    print()

    # Tree structure with tool calls
    root = TreeNode(
        id="root",
        content="Response",
        children=[
            TreeNode(id="tool1", content="Read src/main.py"),
            TreeNode(id="tool2", content="Read src/utils.py"),
            TreeNode(id="tool3", content="Update src/main.py"),
        ]
    )

    tree_lines = tree.render_tree(root)
    for line in tree_lines:
        print(line)

    # Tool result
    result_line = ui.render_tool_result("File read successfully (228 lines)", indent_level=1)
    print(result_line)
    print()

    # File update
    update_lines = ui.render_file_update("src/main.py", added_lines=8, removed_lines=2)
    print(update_lines)

    # Diff lines
    print(ui.render_diff_line(263, "    def on_mount(self) -> None:", "context"))
    print(ui.render_diff_line(266, "        super().on_mount()", "remove"))
    print(ui.render_diff_line(266, "        try:", "add"))
    print(ui.render_diff_line(267, "            super().on_mount()", "add"))
    print()

    # Diagnostic summary
    diagnostic = ui.render_diagnostic_summary(error_count=2, file_count=1, collapsed=True)
    print(diagnostic)
    print()

    # Agent status panel
    print(ui.render_agent_status("main", "", elapsed_seconds=0, is_main=True))
    print(ui.render_agent_status(
        "general-purpose",
        "Research GitHub repos on token reduction",
        elapsed_seconds=30,
        is_main=False
    ))
    print()

    print(ui.render_separator(80))


def test_parallel_agents():
    """Test parallel agent execution display"""
    print_section("PARALLEL AGENT EXECUTION")

    tree = TreeRenderer()

    agents = [
        {
            "task": "Research provided GitHub repos",
            "tool_uses": 10,
            "tokens": 29700,
            "last_tool": "Bash: Fetch README via gh API"
        },
        {
            "task": "Search GitHub for compression repos",
            "tool_uses": 6,
            "tokens": 29900,
            "last_tool": "Web Search: llmlingua context compression"
        },
        {
            "task": "Research academic papers",
            "tool_uses": 5,
            "tokens": 29800,
            "last_tool": "Web Search: LLMlingua paper arxiv"
        },
    ]

    lines = tree.render_parallel_agents(agents, show_last_tool=True)
    for line in lines:
        print(line)


def test_expandable_diagnostics():
    """Test expandable diagnostic display"""
    print_section("EXPANDABLE DIAGNOSTICS")

    expandable = ExpandableRenderer()

    diagnostics = [
        {"severity": "error", "file": "main.py", "line": 42, "message": "Undefined variable"},
        {"severity": "warning", "file": "utils.py", "line": 15, "message": "Unused import"},
    ]

    print("\nCollapsed:")
    lines = expandable.render_diagnostic_summary(
        "diag1", error_count=1, warning_count=1, file_count=2, diagnostics=diagnostics
    )
    for line in lines:
        print(line)

    print("\nExpanded:")
    expandable.collapse_state.expand("diag1")
    lines = expandable.render_diagnostic_summary(
        "diag1", error_count=1, warning_count=1, file_count=2, diagnostics=diagnostics
    )
    for line in lines:
        print(line)


def main():
    print("\n" + "=" * 80)
    print("  LYRA UI SYSTEM - INTEGRATION TEST")
    print("=" * 80)

    try:
        test_complete_response()
        test_parallel_agents()
        test_expandable_diagnostics()

        print("\n" + "=" * 80)
        print("  ✓ ALL INTEGRATION TESTS PASSED")
        print("=" * 80)
        print("\n✨ Lyra UI System is ready for integration!")
        print("\nNext steps:")
        print("  1. Integrate with Lyra's agent system")
        print("  2. Add syntax highlighting (Phase 6)")
        print("  3. Add interactive keyboard controls (Phase 7)")
        print("  4. Performance optimization and profiling")
        print()
        return 0

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
