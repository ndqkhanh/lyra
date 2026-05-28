"""Skills management commands — wired to lyra-skills infrastructure."""

from __future__ import annotations

import typer
from lyra_skills import SkillRouter, load_skills, shipped_pack_roots
from lyra_skills.ledger import load_ledger, top_n
from rich.console import Console
from rich.table import Table

from lyra_cli.cli.output import OutputFormatter

app = typer.Typer()
console = Console()
formatter = OutputFormatter(console)


def _pack_name(manifest) -> str:
    """Derive pack name from the skill's source path."""
    import os
    parts = manifest.path.split(os.sep)
    for i, part in enumerate(parts):
        if part == "packs" and i + 1 < len(parts):
            return parts[i + 1]
    return "unknown"


@app.command()
def list_cmd(
    pack: str | None = typer.Option(None, "--pack", "-p", help="Filter by pack name"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full descriptions"),
) -> None:
    """List available skills from all shipped packs."""
    try:
        manifests = load_skills(shipped_pack_roots())
    except Exception as exc:
        formatter.error_message(f"Failed to load skills: {exc}")
        raise typer.Exit(1)

    if pack:
        manifests = [m for m in manifests if _pack_name(m) == pack]

    if not manifests:
        formatter.warning_message("No skills found.")
        return

    table = Table(title=f"Lyra Skills ({len(manifests)} loaded)")
    table.add_column("Pack", style="cyan")
    table.add_column("ID", style="green")
    table.add_column("Name", style="bold")
    table.add_column("Keywords", style="yellow")
    if verbose:
        table.add_column("Description", style="dim")

    for m in sorted(manifests, key=lambda m: (_pack_name(m), m.id)):
        row = [
            _pack_name(m),
            m.id,
            m.name,
            ", ".join(m.keywords[:3]) + ("..." if len(m.keywords) > 3 else ""),
        ]
        if verbose:
            row.append(m.description[:80] + ("..." if len(m.description) > 80 else ""))
        table.add_row(*row)

    console.print(table)
    formatter.info_message(
        f"Total: {len(manifests)} skills across "
        f"{len(set(_pack_name(m) for m in manifests))} packs"
    )


@app.command()
def show(skill_name: str) -> None:
    """Show full details for a skill."""
    try:
        manifests = load_skills(shipped_pack_roots())
    except Exception as exc:
        formatter.error_message(f"Failed to load skills: {exc}")
        raise typer.Exit(1)

    for m in manifests:
        if m.id == skill_name:
            console.print(f"[bold]Skill:[/bold] {m.name} ({m.id})")
            console.print(f"[bold]Pack:[/bold]  {_pack_name(m)}")
            console.print(f"[bold]Description:[/bold] {m.description}")
            console.print(f"[bold]Keywords:[/bold] {', '.join(m.keywords) if m.keywords else '(none)'}")
            if m.version:
                console.print(f"[bold]Version:[/bold] {m.version}")
            if m.applies_to:
                console.print(f"[bold]Applies to:[/bold] {', '.join(m.applies_to)}")
            if m.requires:
                console.print(f"[bold]Requires:[/bold] {', '.join(m.requires)}")
            console.print("\n[bold]Body:[/bold]")
            console.print(m.body[:2000] if m.body else "(empty)")
            return

    formatter.warning_message(f"Skill '{skill_name}' not found.")
    raise typer.Exit(1)


@app.command()
def stats(
    skill_name: str | None = typer.Argument(None, help="Skill ID or omit for summary"),
) -> None:
    """Show usage statistics for a skill or all skills."""
    ledger = load_ledger()
    manifests = load_skills(shipped_pack_roots())
    manifest_by_id = {m.id: m for m in manifests}

    if skill_name:
        skill_stats = ledger.get(skill_name)
        from lyra_skills.ledger import utility_score
        u = utility_score(skill_stats)
        console.print(f"[bold]{skill_name}[/bold]")
        console.print(f"  Successes: {skill_stats.successes}")
        console.print(f"  Failures:  {skill_stats.failures}")
        console.print(f"  Utility:   {u:+.3f}")
        console.print(f"  Last used: {skill_stats.last_used_at:.0f}" if skill_stats.last_used_at else "  Last used: never")
    else:
        table = Table(title="Skill Usage Statistics")
        table.add_column("Skill", style="green")
        table.add_column("Pack", style="cyan")
        table.add_column("Successes", justify="right")
        table.add_column("Failures", justify="right")
        table.add_column("Utility", justify="right")

        top = top_n(ledger, n=30)
        for s in top:
            m = manifest_by_id.get(s.skill_id)
            pack = _pack_name(m) if m else "—"
            table.add_row(
                s.skill_id, pack,
                str(s.successes), str(s.failures),
                f"{s.utility:+.2f}",
            )

        if not top:
            formatter.warning_message("No skill usage data yet.")

        console.print(table)


@app.command()
def search(query: str) -> None:
    """Search for skills matching a query."""
    manifests = load_skills(shipped_pack_roots())
    router = SkillRouter(manifests)
    matches = router.route(query, top_k=10)

    if not matches:
        formatter.warning_message(f"No skills match '{query}'.")
        return

    formatter.info_message(f"Found {len(matches)} matching skill(s):")
    for m in matches:
        console.print(
            f"  [green]{m.id}[/green] "
            f"({_pack_name(m)}) — "
            f"{m.description[:100]}"
        )
