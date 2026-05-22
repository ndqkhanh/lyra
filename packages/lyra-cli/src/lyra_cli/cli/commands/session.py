"""Session management commands"""

import typer
from rich.console import Console
from lyra_cli.cli.output import OutputFormatter

app = typer.Typer()
console = Console()
formatter = OutputFormatter(console)


@app.command()
def list():
    """List all sessions"""
    formatter.info_message("Listing sessions...")
    formatter.warning_message("Session management coming in Phase 3")


@app.command()
def switch(session_id: str):
    """Switch to a different session"""
    formatter.info_message(f"Switching to session: {session_id}")
    formatter.warning_message("Session management coming in Phase 3")


@app.command()
def new():
    """Create a new session"""
    formatter.info_message("Creating new session...")
    formatter.warning_message("Session management coming in Phase 3")


@app.command()
def delete(session_id: str):
    """Delete a session"""
    formatter.warning_message(f"Deleting session: {session_id}")
    formatter.warning_message("Session management coming in Phase 3")
