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
    """Interactive chat with simple REPL (Claude Code style)"""
    from lyra_cli.agent import AgentLoopFactory
    from rich.console import Console

    # Model mapping
    model_map = {
        "opus": "claude-opus-4-20250514",
        "sonnet": "claude-sonnet-4-20250514",
        "haiku": "claude-haiku-4-20250514"
    }

    api_model = model_map.get(model, "claude-opus-4-20250514")

    # Show welcome banner
    registry = get_registry()
    model_info = registry.get_model(api_model)
    if model_info:
        model_display = model_info.name
        context_display = registry.format_context_window(model_info.context_window)
    else:
        model_display = model.capitalize()
        context_display = None

    print_welcome_banner(
        version="0.1.0",
        model=model_display,
        effort="high",
        provider="Anthropic API",
        working_dir=os.getcwd(),
        context_window=context_display
    )

    # Create console and agent handler
    console = Console()
    agent_handler = StreamingAgentHandler(console)

    # Create agent loop
    try:
        agent_loop = AgentLoopFactory.create_simple_loop(
            callback=agent_handler,
            model=api_model
        )
    except ValueError as e:
        print(f"\x1b[31m✘ Error: {e}\x1b[0m")
        print("Please set ANTHROPIC_API_KEY environment variable")
        return

    # Message handler
    def handle_message(user_input: str):
        """Handle user message"""
        try:
            # Process message (callbacks are called internally)
            agent_loop.process_message(user_input)

        except Exception as e:
            agent_handler.on_error(e)

    # Create and run REPL
    repl = LyraREPL(model=api_model, on_message=handle_message)
    repl.run()


def send_message(message: str, model: str):
    """Send single message (non-interactive)"""
    print(f"Sending message with {model}: {message}")
    # TODO: Implement single message mode
