#!/usr/bin/env python3
"""Test Phase 4: Tool Call Formatting"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from lyra_cli.ui.tool_formatter import (
    ToolCall, ToolResult, Diagnostic, DiffHunk, ToolCallFormatter
)

def print_section(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def test_tool_call():
    print_section("TESTING TOOL CALL RENDERING")
    formatter = ToolCallFormatter(use_colors=True, use_unicode=True)

    tool_call = ToolCall(
        id="call1",
        name="Read",
        parameters={"file_path": "/path/to/file.py", "offset": 0, "limit": 100},
        status="success"
    )

    lines = formatter.render_tool_call(tool_call, indent=0)
    for line in lines:
        print(line)

def test_tool_result():
    print_section("TESTING TOOL RESULT RENDERING")
    formatter = ToolCallFormatter(use_colors=True, use_unicode=True)

    result = ToolResult(success=True, data="File read successfully (228 lines)")
    lines = formatter.render_tool_result(result, indent=2)
    for line in lines:
        print(line)

def test_diagnostics():
    print_section("TESTING DIAGNOSTICS RENDERING")
    formatter = ToolCallFormatter(use_colors=True, use_unicode=True)

    diagnostics = [
        Diagnostic(severity="error", message="Undefined variable", file="main.py", line=42),
        Diagnostic(severity="warning", message="Unused import", file="utils.py", line=15),
    ]

    lines = formatter.render_diagnostics(diagnostics, indent=2)
    for line in lines:
        print(line)

def test_file_update():
    print_section("TESTING FILE UPDATE RENDERING")
    formatter = ToolCallFormatter(use_colors=True, use_unicode=True)

    hunk = DiffHunk(
        start_line=263,
        context_before=[(263, "    def on_mount(self) -> None:")],
        removed=[(266, "        super().on_mount()")],
        added=[(266, "        try:"), (267, "            super().on_mount()")],
        context_after=[]
    )

    lines = formatter.render_file_update(
        "src/app.py", added_lines=8, removed_lines=2, hunks=[hunk]
    )
    for line in lines:
        print(line)

def main():
    print("\n" + "=" * 80)
    print("  PHASE 4: TOOL CALL FORMATTING - TEST SUITE")
    print("=" * 80)

    try:
        test_tool_call()
        test_tool_result()
        test_diagnostics()
        test_file_update()

        print("\n" + "=" * 80)
        print("  ✓ ALL TESTS PASSED")
        print("=" * 80)
        return 0
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
