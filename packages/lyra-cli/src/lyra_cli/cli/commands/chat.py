"""Chat command - Simple REPL with streaming"""

import typer
from lyra_cli.cli.repl import LyraREPL
from lyra_cli.cli.agent_handler import StreamingAgentHandler
from lyra_cli.ui.welcome_banner import print_welcome_banner
from lyra_cli.cli.models import get_registry
import os


def chat(
    message: str = typer.Argument(None, help="Message to send"),
    model: str = typer.Option("opus", help="Model to use (opus, sonnet, haiku)"),
):
    """Start interactive chat or send single message"""
    if message:
        # Single message mode
        send_message(message, model)
    else:
        # Interactive mode
        interactive_chat(model=model)


def interactive_chat(model: str = "opus"):
    """Interactive chat with integrated REPL (Claude Code style)"""
    from lyra_cli.repl import IntegratedREPL

    # Model mapping
    model_map = {
        "opus": "claude-opus-4-20250514",
        "sonnet": "claude-sonnet-4-20250514",
        "haiku": "claude-haiku-4-20250514"
    }

    api_model = model_map.get(model, "claude-opus-4-20250514")

    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print(f"\x1b[31m✘ Error: ANTHROPIC_API_KEY environment variable not set\x1b[0m")
        print("Please set ANTHROPIC_API_KEY to use Lyra")
        return

    # Create and run integrated REPL
    try:
        repl = IntegratedREPL(
            api_key=api_key,
            model=api_model,
            max_tokens=4096
        )
        repl.run()
    except Exception as e:
        print(f"\x1b[31m✘ Error: {e}\x1b[0m")
        return


def send_message(message: str, model: str):
    """Send single message (non-interactive)"""
    print(f"Sending message with {model}: {message}")
    # TODO: Implement single message mode
