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
    # Use Claude Code-style minimal welcome
    from lyra_cli.cli.welcome import show_welcome_claude_code_style
    show_welcome_claude_code_style(console, model=model.capitalize())

    prompt = LyraPrompt()
    formatter = OutputFormatter(console)

    # Initialize agent loop
    from lyra_cli.cli.agent_handler import CLIAgentHandler
    from lyra_cli.agent import AgentLoopFactory

    # Map model names to API model IDs
    model_map = {
        "opus": "claude-opus-4-20250514",
        "sonnet": "claude-sonnet-4-20250514",
        "haiku": "claude-haiku-4-20250514"
    }
    api_model = model_map.get(model.lower(), "claude-opus-4-20250514")

    try:
        agent_handler = CLIAgentHandler(console)
        agent_loop = AgentLoopFactory.create_simple_loop(
            callback=agent_handler,
            model=api_model
        )
        formatter.success_message("Agent loop initialized")
    except ValueError as e:
        formatter.error_message(str(e))
        formatter.info_message("Set ANTHROPIC_API_KEY environment variable to use agent features")
        formatter.info_message("Continuing in demo mode...")
        agent_loop = None

    formatter.info_message("Interactive chat mode - Type your message or /help for commands")

    current_model = model
    while True:
        try:
            user_input = prompt.get_input()

            if not user_input.strip():
                continue

            # Handle slash commands
            if user_input.startswith("/"):
                new_model = handle_slash_command(user_input, formatter, current_model)
                if new_model != current_model:
                    # Reinitialize agent loop with new model
                    current_model = new_model
                    api_model = model_map.get(current_model.lower(), "claude-opus-4-20250514")
                    try:
                        agent_handler = CLIAgentHandler(console)
                        agent_loop = AgentLoopFactory.create_simple_loop(
                            callback=agent_handler,
                            model=api_model
                        )
                        formatter.success_message(f"Agent loop reinitialized with {current_model.capitalize()}")
                    except ValueError:
                        agent_loop = None
                continue

            # Send to agent loop
            if agent_loop:
                agent_loop.process_message(user_input)
            else:
                # Demo mode - just echo
                formatter.status_message("Processing (demo mode)...")
                console.print(f"\n[dim]Echo: {user_input}[/dim]")
                formatter.warning_message("Set ANTHROPIC_API_KEY to enable real agent responses")

        except (KeyboardInterrupt, EOFError):
            console.print("\n\nGoodbye!", style="cyan")
            break
        except Exception as e:
            formatter.error_message(f"Error: {e}")
            import os
            if os.getenv("DEBUG"):
                import traceback
                traceback.print_exc()


def send_message(message: str, model: str):
    """Send single message"""
    formatter = OutputFormatter(console)

    # Initialize agent loop
    from lyra_cli.cli.agent_handler import CLIAgentHandler
    from lyra_cli.agent import AgentLoopFactory

    # Map model names
    model_map = {
        "opus": "claude-opus-4-20250514",
        "sonnet": "claude-sonnet-4-20250514",
        "haiku": "claude-haiku-4-20250514"
    }
    api_model = model_map.get(model.lower(), "claude-opus-4-20250514")

    try:
        agent_handler = CLIAgentHandler(console)
        agent_loop = AgentLoopFactory.create_simple_loop(
            callback=agent_handler,
            model=api_model
        )
        agent_loop.process_message(message)
    except ValueError as e:
        formatter.error_message(str(e))
        formatter.info_message("Set ANTHROPIC_API_KEY environment variable")
    except Exception as e:
        formatter.error_message(f"Error: {e}")
        import os
        if os.getenv("DEBUG"):
            import traceback
            traceback.print_exc()


def handle_slash_command(command: str, formatter: OutputFormatter, current_model: str = "opus") -> str:
    """Handle slash commands

    Returns: Updated model name if changed, otherwise current_model
    """
    cmd = command.lower().strip()
    parts = cmd.split()
    base_cmd = parts[0] if parts else cmd

    if base_cmd in ["/help", "/h", "/?", "/commands"]:
        show_help(formatter)
    elif base_cmd in ["/exit", "/quit", "/q", "/bye"]:
        console.print("\nGoodbye!", style="cyan")
        raise typer.Exit()
    elif base_cmd == "/clear":
        console.clear()
        formatter.success_message("Screen cleared")
    elif base_cmd in ["/model", "/m"]:
        # Handle model switching
        if len(parts) > 1:
            new_model = parts[1].lower()
            if new_model in ["opus", "sonnet", "haiku"]:
                formatter.success_message(f"Model switched to {new_model.capitalize()}")
                return new_model
            else:
                formatter.error_message(f"Unknown model: {parts[1]}")
                formatter.info_message("Available models: opus, sonnet, haiku")
        else:
            formatter.info_message(f"Current model: {current_model.capitalize()}")
            formatter.info_message("Usage: /model <opus|sonnet|haiku>")
    elif base_cmd in ["/config", "/settings"]:
        show_config(formatter)
    elif base_cmd in ["/session", "/sessions"]:
        show_sessions(formatter)
    elif base_cmd in ["/skills", "/skill"]:
        show_skills(formatter)
    elif base_cmd in ["/debug", "/status"]:
        show_debug(formatter)
    elif base_cmd in ["/history", "/hist"]:
        formatter.info_message("Command history available with ↑/↓ arrows")
    elif base_cmd in ["/version", "/v"]:
        console.print("Lyra v0.1.0", style="cyan")
    else:
        formatter.error_message(f"Unknown command: {command}")
        formatter.info_message("Type /help for available commands")

    return current_model


def show_help(formatter: OutputFormatter):
    """Show help message"""
    console.print("\n[bold cyan]Available Commands:[/bold cyan]\n")

    commands = [
        ("/help, /h, /?", "Show this help message"),
        ("/exit, /quit, /q", "Exit the application"),
        ("/clear", "Clear the screen"),
        ("/model <name>", "Switch model (opus, sonnet, haiku)"),
        ("/config", "Show configuration"),
        ("/session", "Manage sessions"),
        ("/skills", "List available skills"),
        ("/debug", "Show debug information"),
        ("/version", "Show version"),
    ]

    for cmd, desc in commands:
        console.print(f"  [cyan]{cmd:20}[/cyan] {desc}")

    console.print("\n[bold cyan]Keyboard Shortcuts:[/bold cyan]\n")
    shortcuts = [
        ("↑/↓", "Navigate command history"),
        ("Tab", "Auto-complete commands"),
        ("Ctrl+C", "Interrupt current operation"),
        ("Ctrl+D", "Exit application"),
    ]

    for key, desc in shortcuts:
        console.print(f"  [cyan]{key:20}[/cyan] {desc}")

    console.print()


def show_config(formatter: OutputFormatter):
    """Show configuration"""
    formatter.info_message("Configuration management coming soon")
    console.print("\n[dim]Config file: ~/.lyra/config.toml[/dim]")


def show_sessions(formatter: OutputFormatter):
    """Show sessions"""
    formatter.info_message("Session management coming soon")
    console.print("\n[dim]Sessions directory: ~/.lyra/sessions/[/dim]")


def show_skills(formatter: OutputFormatter):
    """Show skills"""
    formatter.info_message("Skills management coming soon")
    console.print("\n[dim]Skills directory: ~/.lyra/skills/[/dim]")


def show_debug(formatter: OutputFormatter):
    """Show debug information"""
    import sys
    import os

    console.print("\n[bold cyan]Debug Information:[/bold cyan]\n")
    console.print(f"  Python: {sys.version.split()[0]}")
    console.print(f"  Platform: {sys.platform}")
    console.print(f"  CWD: {os.getcwd()}")
    console.print(f"  API Key: {'✓ Set' if os.getenv('ANTHROPIC_API_KEY') else '✗ Not set'}")
    console.print()
