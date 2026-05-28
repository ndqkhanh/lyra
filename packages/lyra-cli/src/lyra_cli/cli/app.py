"""Main Typer CLI application"""

import sys

import typer
from rich.console import Console

app = typer.Typer(
    name="lyra",
    help="Lyra - AI Research Assistant",
    add_completion=False,
    rich_markup_mode="rich",
)

# Global console instance
console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
    model: str = typer.Option("opus", "--model", "-m", help="Model to use (opus, sonnet, haiku)"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode"),
):
    """Lyra - AI Research Assistant

    Start interactive chat by running without arguments, or use subcommands.
    """
    if version:
        console.print("Lyra v0.1.0", style="cyan")
        raise typer.Exit()

    # Set debug mode
    if debug:
        import os
        os.environ["DEBUG"] = "1"

    # If no command provided, start interactive chat
    if ctx.invoked_subcommand is None:
        from lyra_cli.cli.commands.chat import interactive_chat
        try:
            interactive_chat(model=model)
        except KeyboardInterrupt:
            console.print("\n\nInterrupted by user", style="yellow")
            sys.exit(130)
        except EOFError:
            console.print("\n\nGoodbye!", style="cyan")
            sys.exit(0)
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            if debug:
                import traceback
                traceback.print_exc()
            sys.exit(1)


# Import and register command modules
from lyra_cli.cli.commands import chat, config, session, skills
from lyra_cli.cli.commands import debug as debug_cmd

# Register subcommands
app.command(name="chat")(chat.chat)
app.add_typer(config.app, name="config", help="Configuration management")
app.add_typer(session.app, name="session", help="Session management")
app.add_typer(skills.app, name="skills", help="Skills and MCP management")
app.add_typer(debug_cmd.app, name="debug", help="Debug and diagnostics")


# OpenClaw-inspired commands
@app.command()
def onboard():
    """Setup wizard for first-time users (OpenClaw pattern)"""
    from lyra_cli.cli.onboarding import run_onboarding
    run_onboarding()


@app.command()
def doctor():
    """Check your Lyra setup (OpenClaw pattern)"""
    from lyra_cli.cli.doctor import run_doctor
    run_doctor()
