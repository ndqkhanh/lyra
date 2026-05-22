"""
CLI Entry Point - Command-line interface for Lyra streaming REPL.

Usage:
    lyra-repl                    # Start with default config
    lyra-repl --mode plan        # Start in plan mode
    lyra-repl --model opus       # Use opus model
    lyra-repl --vim              # Enable vim mode
"""

import argparse
import asyncio
import sys

from lyra_ui.streaming_repl import REPLConfig, REPLMode, StreamingREPL


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Lyra Streaming REPL - Claude Code-style interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["agent", "plan", "ask", "auto"],
        default="agent",
        help="REPL mode (default: agent)",
    )

    parser.add_argument(
        "--model",
        type=str,
        choices=["sonnet", "opus", "haiku"],
        default="sonnet",
        help="Model to use (default: sonnet)",
    )

    parser.add_argument(
        "--no-streaming",
        action="store_true",
        help="Disable streaming output",
    )

    parser.add_argument(
        "--no-multiline",
        action="store_true",
        help="Disable multi-line input",
    )

    parser.add_argument(
        "--vim",
        action="store_true",
        help="Enable vim-style navigation",
    )

    parser.add_argument(
        "--theme",
        type=str,
        default="default",
        help="UI theme (default: default)",
    )

    parser.add_argument(
        "--no-status-bar",
        action="store_true",
        help="Hide status bar",
    )

    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Hide progress indicators",
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Create config from args
    config = REPLConfig(
        mode=REPLMode(args.mode),
        model=args.model,
        streaming=not args.no_streaming,
        multiline=not args.no_multiline,
        show_status_bar=not args.no_status_bar,
        show_progress=not args.no_progress,
        vim_mode=args.vim,
        theme=args.theme,
    )

    # Create and run REPL
    repl = StreamingREPL(config)

    try:
        asyncio.run(repl.run())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
