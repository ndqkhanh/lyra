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
    """Interactive chat loop with fixed bottom layout"""
    # Import fixed layout components
    from lyra_cli.ui.fixed_layout import FixedBottomLayout
    from lyra_cli.cli.agent_handler import FixedLayoutAgentHandler
    from lyra_cli.agent import AgentLoopFactory
    import signal

    # Create fixed bottom layout
    layout = FixedBottomLayout()
    layout.use_alt_screen = True
    layout.enter_alt_screen()

    try:
        # Show welcome banner using new Lyra welcome
        from lyra_cli.ui.welcome_banner import create_welcome_banner
        from lyra_cli.cli.models import get_registry
        import os

        # Get model info
        registry = get_registry()
        model_info = registry.get_model(api_model)
        if model_info:
            model_display = model_info.name
            context_display = registry.format_context_window(model_info.context_window)
        else:
            model_display = model.capitalize()
            context_display = None

        welcome = create_welcome_banner(
            version="0.1.0",
            model=model_display,
            effort="high",  # Default effort
            provider="Anthropic API",
            working_dir=os.getcwd(),
            context_window=context_display,
            width=layout.dimensions.terminal_width
        )
        layout.append_content(welcome)

        # Set initial status
        layout.set_status("  ⏵⏵ ready · type to chat")

        # Map model names to API model IDs
        model_map = {
            "opus": "claude-opus-4-20250514",
            "sonnet": "claude-sonnet-4-20250514",
            "haiku": "claude-haiku-4-20250514"
        }
        api_model = model_map.get(model.lower(), "claude-opus-4-20250514")

        # Initialize agent loop with fixed layout handler
        try:
            agent_handler = FixedLayoutAgentHandler(layout)
            agent_loop = AgentLoopFactory.create_simple_loop(
                callback=agent_handler,
                model=api_model
            )
        except ValueError:
            layout.append_content("")
            layout.append_content("⚠ API key not configured")
            layout.append_content("  Run 'lyra onboard' to set up, or set ANTHROPIC_API_KEY")
            layout.set_status("  ⏵⏵ demo mode · no API key")
            agent_loop = None

        # Handle terminal resize
        def handle_resize(signum, frame):
            layout.handle_resize()

        signal.signal(signal.SIGWINCH, handle_resize)

        # Initialize prompt
        prompt = LyraPrompt()
        current_model = model

        # Main chat loop
        while True:
            try:
                user_input = prompt.get_input()

                if not user_input.strip():
                    continue

                # Handle slash commands
                if user_input.startswith("/"):
                    cmd = user_input.lower().strip()
                    if cmd in ["/exit", "/quit", "/q", "/bye"]:
                        break
                    elif cmd == "/clear":
                        layout.clear_scrollable()
                        layout.append_content("Screen cleared")
                        continue
                    elif cmd.startswith("/model"):
                        # Show interactive model selection menu
                        from lyra_cli.ui.model_menu import show_model_menu

                        layout.append_content("")
                        layout.append_content("Opening model selection menu...")

                        # Show menu (this will handle its own rendering)
                        action = show_model_menu(api_model, "high")

                        if action and action.action == "confirm":
                            # User selected a model
                            new_model_id = action.model_id
                            new_effort = action.effort

                            # Update current model
                            from lyra_cli.cli.models import get_registry
                            registry = get_registry()
                            model_info = registry.get_model(new_model_id)

                            if model_info:
                                api_model = new_model_id
                                current_model = model_info.name

                                # Reinitialize agent loop
                                try:
                                    agent_handler = FixedLayoutAgentHandler(layout)
                                    agent_loop = AgentLoopFactory.create_simple_loop(
                                        callback=agent_handler,
                                        model=api_model
                                    )
                                    layout.append_content("")
                                    layout.append_content(f"✓ Switched to {model_info.name} with {new_effort} effort")
                                except ValueError:
                                    agent_loop = None
                                    layout.append_content("")
                                    layout.append_content(f"⚠ API key not configured for {model_info.provider}")
                        elif action and action.action == "set_default":
                            # User wants to set as default
                            layout.append_content("")
                            layout.append_content("✓ Model set as default (feature coming soon)")
                        else:
                            # User cancelled
                            layout.append_content("")
                            layout.append_content("Model selection cancelled")

                        continue
                    else:
                        layout.append_content(f"Unknown command: {user_input}")
                        layout.append_content("Type /exit to quit, /clear to clear, /model <name> to switch model")
                        continue

                # Show user message
                layout.append_content("")
                layout.append_content(f"❯ {user_input}")
                layout.append_content("")

                # Send to agent loop
                if agent_loop:
                    agent_loop.process_message(user_input)
                else:
                    layout.append_content("⚠ Demo mode - run 'lyra onboard' to enable agent")

            except (KeyboardInterrupt, EOFError):
                layout.append_content("")
                layout.append_content("Goodbye!")
                break
            except Exception as e:
                layout.append_content("")
                layout.append_content(f"✗ Error: {e}")
                import os
                if os.getenv("DEBUG"):
                    import traceback
                    traceback.print_exc()

    finally:
        layout.exit_alt_screen()


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
