#!/usr/bin/env python3
"""Test improved CLI commands"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/lyra-cli/src'))

def test_command_parsing():
    """Test command parsing logic"""
    from lyra_cli.cli.commands.chat import handle_slash_command
    from lyra_cli.cli.output import OutputFormatter
    from rich.console import Console

    console = Console()
    formatter = OutputFormatter(console)

    print("✓ Testing command parsing:")

    # Test model command
    result = handle_slash_command("/model opus", formatter, "sonnet")
    assert result == "opus", f"Expected 'opus', got '{result}'"
    print("  ✓ /model opus works")

    # Test model shorthand
    result = handle_slash_command("/m haiku", formatter, "opus")
    assert result == "haiku", f"Expected 'haiku', got '{result}'"
    print("  ✓ /m haiku works")

    # Test help aliases
    for cmd in ["/help", "/h", "/?"]:
        result = handle_slash_command(cmd, formatter, "opus")
        assert result == "opus", f"Model shouldn't change for {cmd}"
        print(f"  ✓ {cmd} works")

    # Test version
    result = handle_slash_command("/version", formatter, "opus")
    print("  ✓ /version works")

    # Test debug
    result = handle_slash_command("/debug", formatter, "opus")
    print("  ✓ /debug works")

    print("\n✓ All command parsing tests passed!")

if __name__ == "__main__":
    try:
        test_command_parsing()
        print("\n✓ All tests passed!")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
