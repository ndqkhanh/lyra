#!/usr/bin/env python3
"""Test script for new CLI"""

import os
import sys

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/lyra-cli/src'))

from lyra_cli.cli import OutputFormatter, cli_app, console


def test_imports():
    """Test that all imports work"""
    print("✓ CLI imports successful")
    print(f"  - cli_app: {cli_app}")
    print(f"  - console: {console}")
    print(f"  - OutputFormatter: {OutputFormatter}")

def test_formatter():
    """Test OutputFormatter"""
    formatter = OutputFormatter(console)

    print("\n✓ Testing OutputFormatter:")
    formatter.success_message("Success message test")
    formatter.error_message("Error message test")
    formatter.warning_message("Warning message test")
    formatter.info_message("Info message test")
    formatter.status_message("Status message test")

def test_welcome():
    """Test welcome screen"""
    from lyra_cli.cli.welcome import show_welcome

    print("\n✓ Testing welcome screen:")
    show_welcome(console, model="Opus 4.7")

if __name__ == "__main__":
    try:
        test_imports()
        test_formatter()
        test_welcome()
        print("\n✓ All tests passed!")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
