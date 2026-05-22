"""Debug and diagnostic commands"""

import typer
from rich.console import Console
from lyra_cli.cli.output import OutputFormatter

app = typer.Typer()
console = Console()
formatter = OutputFormatter(console)


@app.command()
def status():
    """Show system status"""
    formatter.info_message("System Status")
    console.print("\n[dim]Status display coming in Phase 3[/dim]")


@app.command()
def logs():
    """Show agent logs"""
    formatter.info_message("Agent Logs")
    console.print("\n[dim]Log display coming in Phase 3[/dim]")


@app.command()
def tokens():
    """Show token usage"""
    formatter.info_message("Token Usage")
    console.print("\n[dim]Token tracking coming in Phase 3[/dim]")


@app.command()
def test():
    """Test agent connection"""
    formatter.info_message("Testing agent connection...")
    formatter.warning_message("Agent testing coming in Phase 3")
