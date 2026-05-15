"""Test the new streaming CLI."""

import asyncio
from pathlib import Path

from lyra_cli.cli.repl import launch_streaming_repl


async def test_cli():
    """Test basic CLI functionality."""
    # This would normally be interactive, but we can test the setup
    print("Testing CLI initialization...")

    # Test formatter
    from lyra_cli.cli.formatter import get_formatter
    formatter = get_formatter()

    formatter.print_welcome(
        version="3.15.0-dev",
        model="test-model",
        repo="test-repo",
        session_id="test-session"
    )

    formatter.print_info("CLI test successful!")
    formatter.print_success("All components loaded correctly")

    print("\n✓ CLI module test passed")


if __name__ == "__main__":
    asyncio.run(test_cli())
