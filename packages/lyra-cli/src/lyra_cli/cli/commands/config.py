"""Configuration management commands"""

import typer
from rich.console import Console

from lyra_cli.cli.output import OutputFormatter

app = typer.Typer()
console = Console()
formatter = OutputFormatter(console)


@app.command()
def show():
    """Show current configuration"""
    formatter.info_message("Configuration display coming in Phase 3")
    console.print("\n[dim]Config file: ~/.lyra/config.toml[/dim]")


@app.command()
def get(key: str):
    """Get configuration value"""
    formatter.info_message(f"Getting config key: {key}")
    formatter.warning_message("Config management coming in Phase 3")


@app.command()
def set(key: str, value: str):
    """Set configuration value"""
    formatter.info_message(f"Setting {key} = {value}")
    formatter.warning_message("Config management coming in Phase 3")


@app.command()
def edit():
    """Edit configuration file"""
    formatter.info_message("Opening config editor...")
    formatter.warning_message("Config editing coming in Phase 3")
