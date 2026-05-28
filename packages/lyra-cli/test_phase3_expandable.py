#!/usr/bin/env python3
"""Test Phase 3: Expandable Content System"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from lyra_cli.ui import (
    CollapseState,
    ExpandableRenderer,
    ExpandableSection,
    TruncationEngine,
)


def print_section(title: str):
    """Print test section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_collapse_state():
    """Test collapse state manager"""
    print_section("TESTING COLLAPSE STATE MANAGER")

    state = CollapseState()

    print("\n✓ Initial State:")
    print(f"  section1 expanded: {state.is_expanded('section1')}")

    print("\n✓ Toggle State:")
    new_state = state.toggle('section1')
    print(f"  section1 toggled to: {new_state}")
    print(f"  section1 expanded: {state.is_expanded('section1')}")

    print("\n✓ Expand/Collapse:")
    state.expand('section2')
    print(f"  section2 expanded: {state.is_expanded('section2')}")
    state.collapse('section2')
    print(f"  section2 collapsed: {not state.is_expanded('section2')}")


def test_truncation():
    """Test truncation engine"""
    print_section("TESTING TRUNCATION ENGINE")

    engine = TruncationEngine(use_colors=True)

    # Create long content
    lines = [f"Line {i+1}: This is some content" for i in range(50)]

    print("\n✓ Truncate Lines:")
    truncated, hidden = engine.truncate_lines(lines, max_lines=10, preserve_first=5, preserve_last=3)
    print(f"  Original: {len(lines)} lines")
    print(f"  Truncated: {len(truncated)} lines")
    print(f"  Hidden: {hidden} lines")
    print(f"  First line: {truncated[0]}")
    print(f"  Last line: {truncated[-1]}")

    print("\n✓ Truncation Indicator:")
    indicator = engine.create_truncation_indicator(hidden, indent=2)
    print(f"  {indicator}")

    print("\n✓ Expand Hint:")
    hint = engine.create_expand_hint(indent=2)
    print(f"  {hint}")


def test_expandable_section():
    """Test expandable section rendering"""
    print_section("TESTING EXPANDABLE SECTION RENDERING")

    renderer = ExpandableRenderer(use_colors=True, use_unicode=True)

    # Create long content
    long_content = "\n".join([f"Line {i+1}: This is some content that will be truncated" for i in range(30)])

    section = ExpandableSection(
        id="test_section",
        title="Tool Result",
        content=long_content,
        collapsed=True,
        truncate_at=10
    )

    print("\n✓ Collapsed State:")
    lines = renderer.render_section(section, indent=2)
    for line in lines[:15]:  # Show first 15 lines
        print(line)
    if len(lines) > 15:
        print(f"  ... ({len(lines) - 15} more lines)")

    print("\n✓ Expanded State:")
    renderer.collapse_state.expand(section.id)
    lines = renderer.render_section(section, indent=2)
    for line in lines[:15]:  # Show first 15 lines
        print(line)
    if len(lines) > 15:
        print(f"  ... ({len(lines) - 15} more lines)")


def test_diagnostic_summary():
    """Test diagnostic summary rendering"""
    print_section("TESTING DIAGNOSTIC SUMMARY")

    renderer = ExpandableRenderer(use_colors=True, use_unicode=True)

    diagnostics = [
        {
            "severity": "error",
            "file": "src/main.py",
            "line": 42,
            "message": "Undefined variable 'foo'"
        },
        {
            "severity": "error",
            "file": "src/main.py",
            "line": 58,
            "message": "Type mismatch: expected str, got int"
        },
        {
            "severity": "warning",
            "file": "src/utils.py",
            "line": 15,
            "message": "Unused import 'os'"
        },
        {
            "severity": "warning",
            "file": "src/utils.py",
            "line": 23,
            "message": "Variable 'x' is never used"
        },
    ]

    print("\n✓ Collapsed State:")
    lines = renderer.render_diagnostic_summary(
        section_id="diag1",
        error_count=2,
        warning_count=2,
        file_count=2,
        diagnostics=diagnostics,
        indent=2
    )
    for line in lines:
        print(line)

    print("\n✓ Expanded State:")
    renderer.collapse_state.expand("diag1")
    lines = renderer.render_diagnostic_summary(
        section_id="diag1",
        error_count=2,
        warning_count=2,
        file_count=2,
        diagnostics=diagnostics,
        indent=2
    )
    for line in lines:
        print(line)


def test_compaction_event():
    """Test conversation compaction event rendering"""
    print_section("TESTING CONVERSATION COMPACTION EVENT")

    renderer = ExpandableRenderer(use_colors=True, use_unicode=True)

    files_read = [
        ("src/lyra_cli/cli/agent_integration.py", 228),
        ("src/lyra_cli/cli/tui.py", 156),
        (".claude/rules/python/coding-style.md", 43),
    ]

    files_referenced = [
        "src/lyra_cli/hooks/__init__.py",
    ]

    skills_restored = ["deep-research", "tdd-guide"]

    print("\n✓ Collapsed State:")
    lines = renderer.render_compaction_event(
        section_id="compact1",
        files_read=files_read,
        files_referenced=files_referenced,
        skills_restored=skills_restored,
        indent=0
    )
    for line in lines:
        print(line)

    print("\n✓ Expanded State:")
    renderer.collapse_state.expand("compact1")
    lines = renderer.render_compaction_event(
        section_id="compact1",
        files_read=files_read,
        files_referenced=files_referenced,
        skills_restored=skills_restored,
        indent=0
    )
    for line in lines:
        print(line)


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("  PHASE 3: EXPANDABLE CONTENT SYSTEM - TEST SUITE")
    print("=" * 80)

    try:
        test_collapse_state()
        test_truncation()
        test_expandable_section()
        test_diagnostic_summary()
        test_compaction_event()

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
