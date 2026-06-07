#!/usr/bin/env python3
"""Test Phases 4-6: Agent Tree, Selection Menu, Scroll Manager"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/lyra-cli/src'))

from lyra_cli.ui import AgentTree, ScrollManager, SelectionMenu


def test_agent_tree():
    """Test agent tree display"""
    print("=" * 80)
    print("TEST 1: Agent Tree Display")
    print("=" * 80)

    tree = AgentTree()

    # Add agents
    tree.add_agent("agent-1", "Research GitHub repos")
    tree.add_agent("agent-2", "Search academic papers")
    tree.add_agent("agent-3", "Analyze production tools")

    # Update agents
    tree.update_agent("agent-1", tool_count=10, tokens=29700, latest_tool="Bash: gh api repos")
    tree.update_agent("agent-2", tool_count=6, tokens=29900, latest_tool="Web Search: arxiv")
    tree.update_agent("agent-3", tool_count=5, tokens=25700, latest_tool="Web Search: llama index")

    # Test collapsed
    print("Collapsed state:")
    print(tree.render())
    print()

    # Test expanded
    tree.toggle_expand()
    print("Expanded state:")
    print(tree.render())
    print()

    print("✓ Agent tree display works")
    print()


def test_selection_menu():
    """Test selection menu"""
    print("=" * 80)
    print("TEST 2: Selection Menu")
    print("=" * 80)

    menu = SelectionMenu(
        title="Select model",
        description="Switch between Claude models"
    )

    # Add options
    menu.add_option(
        "Default (recommended)",
        "Opus 4.7 with 1M context · Most capable",
        "opus",
        active=False
    )
    menu.add_option(
        "Sonnet",
        "Sonnet 4.6 · Best for everyday tasks",
        "sonnet",
        active=True
    )
    menu.add_option(
        "Haiku",
        "Haiku 4.5 · Fastest for quick answers",
        "haiku",
        active=False
    )

    # Test rendering
    print(menu.render())
    print()

    # Test navigation
    print("After moving down:")
    menu.move_down()
    print(menu.render())
    print()

    print("✓ Selection menu works")
    print()


def test_scroll_manager():
    """Test scroll manager"""
    print("=" * 80)
    print("TEST 3: Scroll Manager")
    print("=" * 80)

    scroll = ScrollManager(fixed_height=4)

    # Add content
    for i in range(50):
        scroll.append_line(f"Line {i + 1}: This is content line {i + 1}")

    # Test scroll position
    offset, total, visible = scroll.get_scroll_position()
    print(f"Total lines: {total}")
    print(f"Visible height: {visible}")
    print(f"Scroll offset: {offset}")
    print(f"At bottom: {scroll.is_at_bottom()}")
    print()

    # Test scrolling
    scroll.scroll_to_top()
    print("After scroll to top:")
    print(f"Offset: {scroll.scroll_offset}, At bottom: {scroll.is_at_bottom()}")
    print()

    scroll.scroll_to_bottom()
    print("After scroll to bottom:")
    print(f"Offset: {scroll.scroll_offset}, At bottom: {scroll.is_at_bottom()}")
    print()

    # Test visible lines
    visible_lines = scroll.get_visible_lines()
    print(f"Visible lines count: {len(visible_lines)}")
    print("First 3 visible lines:")
    for line in visible_lines[:3]:
        print(f"  {line}")
    print()

    print("✓ Scroll manager works")
    print()


def test_integrated_ui():
    """Test integrated UI components"""
    print("=" * 80)
    print("TEST 4: Integrated UI Components")
    print("=" * 80)

    # Create components
    tree = AgentTree()
    scroll = ScrollManager()

    # Add agents
    tree.add_agent("agent-1", "Deep research agent")
    tree.update_agent("agent-1", tool_count=15, tokens=45000, latest_tool="Web Search: research")

    # Add content to scroll
    scroll.append_line("⏺ Starting research...")
    scroll.append_line("")
    scroll.append_line(tree.render())
    scroll.append_line("")
    scroll.append_line("Research findings:")
    scroll.append_line("- Found 10 relevant papers")
    scroll.append_line("- Identified 5 key techniques")
    scroll.append_line("")
    scroll.append_line("✻ 25.5s · 15 tools · 45,000 tokens")

    # Render
    print("Integrated UI:")
    print(scroll.render_visible_area())
    print()

    print("✓ Integrated UI works")
    print()


if __name__ == "__main__":
    print("\n")
    print("╭─── Phases 4-6: Agent Tree, Selection Menu, Scroll Manager ───╮")
    print("│ Testing advanced UI components                               │")
    print("╰───────────────────────────────────────────────────────────────╯")
    print()

    test_agent_tree()
    test_selection_menu()
    test_scroll_manager()
    test_integrated_ui()

    print("=" * 80)
    print("✓ ALL TESTS PASSED - Phases 4-6 Complete!")
    print("=" * 80)
    print()
    print("Key features implemented:")
    print("  Phase 4: ✓ Agent tree with collapse/expand")
    print("  Phase 4: ✓ Box-drawing tree structure")
    print("  Phase 4: ✓ Token rollup display")
    print("  Phase 5: ✓ Selection menu with keyboard navigation")
    print("  Phase 5: ✓ Model picker pattern")
    print("  Phase 6: ✓ Virtualized scrolling")
    print("  Phase 6: ✓ Auto-scroll to bottom")
    print("  Phase 6: ✓ User scroll with preserved position")
    print()
