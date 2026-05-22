"""Chat command - Main interactive chat loop"""

import typer
from rich.console import Console
from lyra_cli.cli.prompts import LyraPrompt
from lyra_cli.cli.welcome import show_welcome
from lyra_cli.cli.output import OutputFormatter

console = Console()


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
    """Interactive chat loop"""
    show_welcome(console, model=model.capitalize())

    prompt = LyraPrompt()
    formatter = OutputFormatter(console)

    formatter.info_message("Interactive chat mode - Type your message or /help for commands")

    while True:
        try:
            user_input = prompt.get_input()

            if not user_input.strip():
                continue

            # Handle slash commands
            if user_input.startswith("/"):
                handle_slash_command(user_input, formatter)
                continue

            # TODO: Send to agent loop (Phase 3)
            formatter.status_message("Processing your message...")
            console.print(f"\n[dim]You said: {user_input}[/dim]")
            formatter.warning_message("Agent integration coming in Phase 3")

        except (KeyboardInterrupt, EOFError):
            console.print("\n\nGoodbye!", style="cyan")
            break
        except Exception as e:
            formatter.error_message(f"Error: {e}")


def send_message(message: str, model: str):
    """Send single message"""
    formatter = OutputFormatter(console)
    formatter.status_message(f"Sending message with {model}...")

    # TODO: Send to agent loop (Phase 3)
    console.print(f"\n[dim]Message: {message}[/dim]")
    formatter.warning_message("Agent integration coming in Phase 3")


def handle_slash_command(command: str, formatter: OutputFormatter):
    """Handle slash commands"""
    cmd = command.lower().strip()

    if cmd in ["/help", "/h"]:
        show_help(formatter)
    elif cmd in ["/exit", "/quit", "/q"]:
        console.print("\nGoodbye!", style="cyan")
        raise typer.Exit()
    elif cmd == "/clear":
        console.clear()
        formatter.success_message("Screen cleared")
    else:
        formatter.error_message(f"Unknown command: {command}")
        formatter.info_message("Type /help for available commands")


def show_help(formatter: OutputFormatter):
    """Show help message"""
    console.print("\n[bold cyan]Available Commands:[/bold cyan]\n")

    commands = [
        ("/help", "Show this help message"),
        ("/exit", "Exit the application"),
        ("/clear", "Clear the screen"),
        ("/config", "Show configuration"),
        ("/session", "Manage sessions"),
        ("/skills", "List available skills"),
    ]

    for cmd, desc in commands:
        console.print(f"  [cyan]{cmd:15}[/cyan] {desc}")

    console.print()
