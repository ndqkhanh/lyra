#!/usr/bin/env python3
"""Lyra CLI entry point - New CLI implementation"""

import sys


def main():
    """Main entry point for Lyra CLI"""
    try:
        from lyra_cli.cli import cli_app
        cli_app()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import os
        if os.getenv("DEBUG"):
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
