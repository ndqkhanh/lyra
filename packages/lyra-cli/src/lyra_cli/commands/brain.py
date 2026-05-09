"""``lyra brain`` — list, show, and install curated brain bundles.

A "brain" is a curated bundle of opinionated agent defaults
(``SOUL.md`` + ``policy.yaml`` + optional ``.lyra/commands/*.md``)
that a user can install with one command. Inspired by
``garrytan/gbrain``.

Subcommands:

    lyra brain list                   # show available bundles
    lyra brain show <name>            # describe one bundle
    lyra brain install <name>         # install into the current repo
    lyra brain install <name> --force --repo-root <path>

The installer never touches a live :class:`InteractiveSession`; the
user must restart ``lyra`` (or run ``/init --force``) to pick up the
new persona.
"""
from __future__ import annotations

from pathlib import Path

import typer
from lyra_core.brains import (
    BrainRegistry,
    default_registry,
    install_brain,
)
from rich.console import Console
from rich.table import Table

from ..paths import RepoLayout

_console = Console()

brain_app = typer.Typer(
    name="brain",
    help=(
        "Manage curated brain bundles — opinionated SOUL.md + "
        "policy.yaml + slash-command presets. Built-ins: default, "
        "tdd-strict, research, ship-fast."
    ),
    no_args_is_help=True,
)


def _registry() -> BrainRegistry:
    """Return the process-wide registry. Hook point for tests."""
    return default_registry()


@brain_app.command("list")
def list_command() -> None:
    """List all available brain bundles."""
    reg = _registry()
    table = Table(title="brain bundles", show_lines=False)
    table.add_column("name", style="cyan", no_wrap=True)
    table.add_column("toolset", style="magenta")
    table.add_column("tdd", style="yellow")
    table.add_column("description")
    for name in reg.names():
        b = reg.get(name)
        if b is None:  # pragma: no cover - registry invariant
            continue
        table.add_row(
            b.name,
            b.toolset,
            "on" if b.tdd_gate_default else "off",
            b.description,
        )
    _console.print(table)


@brain_app.command("show")
def show_command(
    name: str = typer.Argument(..., help="Brain bundle name."),
) -> None:
    """Print the full description of a bundle (SOUL preview + policy)."""
    reg = _registry()
    bundle = reg.get(name)
    if bundle is None:
        _console.print(f"[red]unknown brain:[/red] {name}")
        raise typer.Exit(code=2)
    _console.print(f"[bold cyan]{bundle.name}[/bold cyan]")
    _console.print(bundle.description)
    _console.print(f"[dim]toolset:[/dim] {bundle.toolset}")
    _console.print(f"[dim]model:[/dim]   {bundle.model_preference}")
    _console.print(
        f"[dim]tdd:[/dim]     {'on' if bundle.tdd_gate_default else 'off'}"
    )
    _console.print()
    _console.print("[bold]SOUL.md preview[/bold]")
    _console.print(bundle.soul_md)
    if bundle.policy_yaml is not None:
        _console.print("[bold]policy.yaml[/bold]")
        _console.print(bundle.policy_yaml)
    if bundle.commands:
        _console.print(f"[bold]commands ({len(bundle.commands)})[/bold]")
        for cmd in bundle.commands:
            _console.print(f"  /{cmd.name}")


@brain_app.command("install")
def install_command(
    name: str = typer.Argument(..., help="Brain bundle name to install."),
    repo_root: Path = typer.Option(
        Path.cwd(),
        "--repo-root",
        "-C",
        help="Repo to install into (default: cwd).",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing SOUL.md / policy.yaml / commands.",
    ),
) -> None:
    """Write the named bundle into ``<repo>/SOUL.md`` + ``.lyra/``.

    Idempotent unless ``--force`` is passed: existing files are
    preserved and reported as ``skipped``.
    """
    reg = _registry()
    bundle = reg.get(name)
    if bundle is None:
        _console.print(f"[red]unknown brain:[/red] {name}")
        raise typer.Exit(code=2)

    repo_root = repo_root.resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    layout = RepoLayout(repo_root=repo_root)
    report = install_brain(bundle, layout, force=force)

    _console.print(
        f"[green]installed brain[/green] [bold]{report.bundle}[/bold] "
        f"into {report.repo_root}"
    )
    if report.written:
        _console.print("[dim]written:[/dim]")
        for path in report.written:
            _console.print(f"  + {path}")
    if report.skipped:
        _console.print("[yellow]skipped (use --force to overwrite):[/yellow]")
        for path in report.skipped:
            _console.print(f"  · {path}")
    if not report.changed:
        _console.print(
            "[yellow]no files changed[/yellow] — re-run with --force "
            "to apply the bundle on top of existing files."
        )


__all__ = ["brain_app"]
