#!/usr/bin/env python3
"""Test Phase 2: Hierarchical Display System"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from lyra_cli.ui import TreeNode, TreeRenderer


def print_section(title: str):
    """Print test section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_simple_tree():
    """Test simple tree rendering"""
    print_section("TESTING SIMPLE TREE")

    renderer = TreeRenderer(use_colors=True, use_unicode=True)

    # Create simple tree
    root = TreeNode(
        id="root",
        content="Response",
        children=[
            TreeNode(id="child1", content="Tool Call 1"),
            TreeNode(id="child2", content="Tool Call 2"),
            TreeNode(id="child3", content="Tool Call 3"),
        ]
    )

    lines = renderer.render_tree(root)
    for line in lines:
        print(line)


def test_nested_tree():
    """Test nested tree rendering"""
    print_section("TESTING NESTED TREE")

    renderer = TreeRenderer(use_colors=True, use_unicode=True)

    # Create nested tree
    root = TreeNode(
        id="root",
        content="Response",
        children=[
            TreeNode(
                id="child1",
                content="Tool Call 1",
                children=[
                    TreeNode(id="result1", content="Result: Success"),
                ]
            ),
            TreeNode(
                id="child2",
                content="Tool Call 2",
                children=[
                    TreeNode(id="result2", content="Result: 42 lines read"),
                ]
            ),
            TreeNode(
                id="child3",
                content="Tool Call 3",
                children=[
                    TreeNode(id="result3", content="Result: File updated"),
                ]
            ),
        ]
    )

    lines = renderer.render_tree(root)
    for line in lines:
        print(line)


def test_deep_tree():
    """Test deeply nested tree"""
    print_section("TESTING DEEP TREE")

    renderer = TreeRenderer(use_colors=True, use_unicode=True)

    # Create deep tree
    root = TreeNode(
        id="root",
        content="Main Agent",
        children=[
            TreeNode(
                id="sub1",
                content="Sub-agent 1",
                children=[
                    TreeNode(
                        id="task1",
                        content="Task 1.1",
                        children=[
                            TreeNode(id="result1", content="Result: Complete"),
                        ]
                    ),
                    TreeNode(id="task2", content="Task 1.2"),
                ]
            ),
            TreeNode(
                id="sub2",
                content="Sub-agent 2",
                children=[
                    TreeNode(id="task3", content="Task 2.1"),
                ]
            ),
        ]
    )

    lines = renderer.render_tree(root)
    for line in lines:
        print(line)


def test_parallel_agents():
    """Test parallel agent execution tree"""
    print_section("TESTING PARALLEL AGENT EXECUTION")

    renderer = TreeRenderer(use_colors=True, use_unicode=True)

    agents = [
        {
            "task": "Research provided GitHub repos on token reduction",
            "tool_uses": 10,
            "tokens": 29700,
            "last_tool": "Bash: Fetch RTK README via gh API"
        },
        {
            "task": "Search GitHub for top token/context compression repos",
            "tool_uses": 6,
            "tokens": 29900,
            "last_tool": "Web Search: llmlingua context compression github stars micros…"
        },
        {
            "task": "Research academic papers on context/token compression",
            "tool_uses": 5,
            "tokens": 29800,
            "last_tool": "Web Search: LLMlingua context compression paper arxiv"
        },
        {
            "task": "Research production token reduction tools and techniques",
            "tool_uses": 6,
            "tokens": 25700,
            "last_tool": "Web Search: llama index context management token reduction te…"
        },
    ]

    lines = renderer.render_parallel_agents(agents, show_last_tool=True)
    for line in lines:
        print(line)


def test_file_tree():
    """Test file tree rendering"""
    print_section("TESTING FILE TREE")

    renderer = TreeRenderer(use_colors=True, use_unicode=True)

    files = [
        "packages/lyra-cli/src/lyra_cli/ui/__init__.py",
        "packages/lyra-cli/src/lyra_cli/ui/colors.py",
        "packages/lyra-cli/src/lyra_cli/ui/layout.py",
        "packages/lyra-cli/src/lyra_cli/ui/renderer.py",
        "packages/lyra-cli/src/lyra_cli/ui/symbols.py",
        "packages/lyra-cli/src/lyra_cli/ui/tree.py",
    ]

    lines = renderer.render_file_tree(files, base_path="packages/lyra-cli/src/lyra_cli/ui/")
    for line in lines:
        print(line)


def test_collapsed_tree():
    """Test collapsed tree nodes"""
    print_section("TESTING COLLAPSED TREE")

    renderer = TreeRenderer(use_colors=True, use_unicode=True)

    # Create tree with collapsed node
    root = TreeNode(
        id="root",
        content="Response",
        children=[
            TreeNode(id="child1", content="Tool Call 1 (expanded)"),
            TreeNode(
                id="child2",
                content="Tool Call 2 (collapsed)",
                collapsed=True,
                children=[
                    TreeNode(id="hidden1", content="This should not appear"),
                    TreeNode(id="hidden2", content="This should not appear either"),
                ]
            ),
            TreeNode(id="child3", content="Tool Call 3 (expanded)"),
        ]
    )

    lines = renderer.render_tree(root)
    for line in lines:
        print(line)


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("  PHASE 2: HIERARCHICAL DISPLAY SYSTEM - TEST SUITE")
    print("=" * 80)

    try:
        test_simple_tree()
        test_nested_tree()
        test_deep_tree()
        test_parallel_agents()
        test_file_tree()
        test_collapsed_tree()

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
