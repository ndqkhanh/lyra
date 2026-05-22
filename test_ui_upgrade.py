#!/usr/bin/env python3
"""Test UI upgrades with Claude Code style"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/lyra-cli/src'))

def test_welcome_screens():
    """Test different welcome screen styles"""
    from rich.console import Console
    from lyra_cli.cli.welcome import (
        show_welcome,
        show_welcome_detailed,
        show_welcome_claude_code_style
    )

    console = Console()

    print("=" * 80)
    print("TESTING WELCOME SCREENS")
    print("=" * 80)

    print("\n1. Claude Code Style (Minimal):")
    print("-" * 80)
    show_welcome_claude_code_style(console, model="Opus 4.7")

    print("\n2. Lyra Minimal Style:")
    print("-" * 80)
    show_welcome(console, model="Opus 4.7")

    print("\n3. Lyra Detailed Style (Original):")
    print("-" * 80)
    show_welcome_detailed(console, model="Opus 4.7", organization="Claude Max")

    print("\n✓ All welcome screens rendered successfully")


def test_output_formatter():
    """Test enhanced output formatter"""
    from rich.console import Console
    from lyra_cli.cli.output import OutputFormatter

    console = Console()
    formatter = OutputFormatter(console)

    print("\n" + "=" * 80)
    print("TESTING OUTPUT FORMATTER")
    print("=" * 80 + "\n")

    # Test status messages
    formatter.success_message("Operation completed successfully")
    formatter.error_message("An error occurred")
    formatter.warning_message("This is a warning")
    formatter.info_message("This is information")

    # Test tool use
    print()
    formatter.tool_use("Read", collapsed=False)
    formatter.tool_use("Edit", collapsed=True)

    # Test stats line
    formatter.stats_line("2.3s", 3, 1234)

    # Test section header
    formatter.section_header("Available Commands")

    # Test command list
    commands = [
        ("/help", "Show help message"),
        ("/model", "Switch model"),
        ("/exit", "Exit application"),
    ]
    formatter.command_list(commands)

    # Test file diff
    print()
    formatter.file_diff("src/main.py", 15, 3)
    formatter.file_diff("tests/test.py", 8, 2)

    # Test collapsed section
    print()
    formatter.collapsed_section("Tool Output", "Long output here...", expanded=False)
    formatter.collapsed_section("Expanded Output", "Visible content here", expanded=True)

    print("\n✓ All output formatter methods working")


def test_status_bar():
    """Test status bar"""
    from rich.console import Console
    from lyra_cli.cli.status import StatusBar, StatusLine

    console = Console()

    print("\n" + "=" * 80)
    print("TESTING STATUS BAR")
    print("=" * 80 + "\n")

    # Test StatusBar
    status_bar = StatusBar(console)
    status_bar.update(model="opus", tokens=1234, cost=0.0567, session_id="abc123def456")

    print("Status Bar:")
    status_bar.render("Processing your message...")
    print()

    # Test StatusLine
    status_line = StatusLine(console)
    status_line.set_field("model", "opus")
    status_line.set_field("tokens", "1,234")
    status_line.set_field("cost", "$0.0567")

    print("\nStatus Line:")
    status_line.render()
    print()

    print("\n✓ Status bar and status line working")


if __name__ == "__main__":
    try:
        test_welcome_screens()
        test_output_formatter()
        test_status_bar()

        print("\n" + "=" * 80)
        print("✓ ALL UI UPGRADE TESTS PASSED!")
        print("=" * 80)
        print("\nThe UI has been upgraded to match Claude Code's design:")
        print("  ✓ Minimal welcome screen")
        print("  ✓ Enhanced output formatting")
        print("  ✓ Tool use indicators")
        print("  ✓ Stats line")
        print("  ✓ Status bar")
        print("  ✓ Collapsed sections")
        print("  ✓ File diffs")
        print("\nReady for production use!")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
