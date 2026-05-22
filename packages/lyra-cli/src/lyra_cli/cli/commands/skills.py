"""Skills and MCP management commands"""

import typer
from rich.console import Console
from lyra_cli.cli.output import OutputFormatter

app = typer.Typer()
console = Console()
formatter = OutputFormatter(console)


@app.command()
def list():
    """List available skills"""
    formatter.info_message("Listing skills...")
    formatter.warning_message("Skills management coming in Phase 3")


@app.command()
def show(skill_name: str):
    """Show skill details"""
    formatter.info_message(f"Showing skill: {skill_name}")
    formatter.warning_message("Skills management coming in Phase 3")


@app.command()
def enable(skill_name: str):
    """Enable a skill"""
    formatter.info_message(f"Enabling skill: {skill_name}")
    formatter.warning_message("Skills management coming in Phase 3")


@app.command()
def disable(skill_name: str):
    """Disable a skill"""
    formatter.warning_message(f"Disabling skill: {skill_name}")
    formatter.warning_message("Skills management coming in Phase 3")
