"""CLI command for installing production resources."""

import typer
from rich.console import Console
from rich.table import Table

from lyra_skills.mcp_integration import (
    PRODUCTION_MCP_SERVERS,
    install_production_mcp_servers,
)
from lyra_skills.production_installer import (
    PRODUCTION_SKILLS,
    install_production_skills,
)

app = typer.Typer(help="Install production-ready resources for Lyra")
console = Console()


@app.command()
def skills(
    names: list[str] = typer.Argument(
        None, help="Skill names to install (empty = all)"
    ),
    list_only: bool = typer.Option(
        False, "--list", "-l", help="List available skills"
    ),
):
    """Install production-ready skills."""
    if list_only:
        table = Table(title="Production Skills")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="green")
        table.add_column("Priority", style="yellow")

        for name, info in PRODUCTION_SKILLS.items():
            table.add_row(
                name,
                info["description"],
                info["priority"],
            )

        console.print(table)
        return

    console.print("[bold]Installing production skills...[/bold]")

    results = install_production_skills(names if names else None)

    for skill_name, success in results.items():
        if success:
            console.print(f"✅ {skill_name}: Installed")
        else:
            console.print(f"❌ {skill_name}: Failed")

    success_count = sum(1 for s in results.values() if s)
    console.print(
        f"\n[bold]Installed {success_count}/{len(results)} skills[/bold]"
    )


@app.command()
def mcp(
    names: list[str] = typer.Argument(
        None, help="MCP server names to install (empty = all)"
    ),
    list_only: bool = typer.Option(
        False, "--list", "-l", help="List available MCP servers"
    ),
):
    """Install production-ready MCP servers."""
    if list_only:
        table = Table(title="Production MCP Servers")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="green")
        table.add_column("Package", style="yellow")

        for name, info in PRODUCTION_MCP_SERVERS.items():
            table.add_row(
                name,
                info["description"],
                info["package"],
            )

        console.print(table)
        return

    console.print("[bold]Installing production MCP servers...[/bold]")

    results = install_production_mcp_servers(names if names else None)

    for server_name, success in results.items():
        if success:
            console.print(f"✅ {server_name}: Installed")
        else:
            console.print(f"❌ {server_name}: Failed")

    success_count = sum(1 for s in results.values() if s)
    console.print(
        f"\n[bold]Installed {success_count}/{len(results)} MCP servers[/bold]"
    )


@app.command()
def all(
    skip_skills: bool = typer.Option(
        False, "--skip-skills", help="Skip skill installation"
    ),
    skip_mcp: bool = typer.Option(
        False, "--skip-mcp", help="Skip MCP server installation"
    ),
):
    """Install all production resources (skills + MCP servers)."""
    console.print(
        "[bold cyan]Installing all production resources...[/bold cyan]\n"
    )

    if not skip_skills:
        console.print("[bold]1. Installing Skills[/bold]")
        skill_results = install_production_skills()
        skill_success = sum(1 for s in skill_results.values() if s)
        console.print(
            f"✅ Installed {skill_success}/{len(skill_results)} skills\n"
        )

    if not skip_mcp:
        console.print("[bold]2. Installing MCP Servers[/bold]")
        mcp_results = install_production_mcp_servers()
        mcp_success = sum(1 for s in mcp_results.values() if s)
        console.print(
            f"✅ Installed {mcp_success}/{len(mcp_results)} MCP servers\n"
        )

    console.print("[bold green]✨ Installation complete![/bold green]")


if __name__ == "__main__":
    app()
