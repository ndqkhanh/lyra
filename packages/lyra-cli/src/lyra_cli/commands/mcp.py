"""``lyra mcp`` — manage Model Context Protocol server entries.

This subcommand lets the user list, add, remove, and doctor the MCP
servers that Lyra autoloads at REPL boot. Two storage locations are
supported:

* user-global, ``~/.lyra/mcp.json`` (default for ``add``/``remove``),
* project-local, ``./.lyra/mcp.json`` (read-only here, edit by hand).

The format is identical to Claude Code / Codex MCP configs, so users
can copy-paste between them. See
:mod:`lyra_mcp.client.config` for the schema.

Examples::

    lyra mcp list
    lyra mcp add filesystem --command npx \\
        --arg -y --arg @modelcontextprotocol/server-filesystem --arg /tmp \\
        --trust third-party
    lyra mcp remove filesystem
    lyra mcp doctor
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

mcp_app = typer.Typer(
    name="mcp",
    help="Manage MCP server config (~/.lyra/mcp.json).",
    no_args_is_help=True,
)

_console = Console()


def _load(repo_root: Path):
    from lyra_mcp.client.config import load_mcp_config

    return load_mcp_config(repo_root.resolve())


@mcp_app.command("list")
def list_servers(
    repo_root: Path = typer.Option(
        Path.cwd(), "--repo-root", "-C", help="Repo root for project-local config."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON instead of a table."
    ),
) -> None:
    """List every MCP server discovered across user-global + project configs."""
    result = _load(repo_root)
    if json_output:
        payload = [
            {
                "name": s.name,
                "command": list(s.command),
                "trust": s.trust,
                "source": str(s.source) if s.source else None,
            }
            for s in result.servers
        ]
        _console.print_json(json.dumps({"servers": payload, "issues": [
            {"source": str(i.source), "name": i.name, "message": i.message}
            for i in result.issues
        ]}))
        return
    if not result.servers and not result.issues:
        _console.print("[dim]no MCP servers configured (run `lyra mcp add ...` to add one)[/dim]")
        return
    table = Table(title="MCP servers", show_lines=False)
    table.add_column("name", style="bold")
    table.add_column("command")
    table.add_column("trust")
    table.add_column("source", style="dim")
    for s in result.servers:
        table.add_row(
            s.name,
            " ".join(s.command),
            s.trust,
            str(s.source) if s.source else "<inline>",
        )
    _console.print(table)
    if result.issues:
        _console.print("[yellow]issues:[/yellow]")
        for issue in result.issues:
            _console.print(
                f"  [yellow]•[/yellow] {issue.source}::{issue.name} — {issue.message}"
            )


@mcp_app.command("add")
def add_server(
    name: str = typer.Argument(..., help="Logical name (used in mcp__<server>__<tool>)."),
    command: str = typer.Option(..., "--command", "-c", help="Executable, e.g. 'npx' or 'uvx'."),
    arg: list[str] = typer.Option(
        None,
        "--arg",
        "-a",
        help="Repeat for each argv item passed after the executable.",
    ),
    env: list[str] = typer.Option(
        None,
        "--env",
        "-e",
        help="Repeat for each KEY=VAL env var to inject.",
    ),
    cwd: Optional[str] = typer.Option(
        None, "--cwd", help="Working directory for the spawned MCP server."
    ),
    trust: str = typer.Option(
        "third-party",
        "--trust",
        help="'first-party' to skip the trust banner; 'third-party' (default) wraps tool output.",
    ),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        help="Override the user-global config path (default: ~/.lyra/mcp.json).",
    ),
) -> None:
    """Add (or replace) an MCP server in the user-global config."""
    from lyra_mcp.client.config import add_user_mcp_server

    env_dict: dict[str, str] = {}
    for kv in env or []:
        if "=" not in kv:
            _console.print(f"[red]bad --env value[/red]: {kv} (expected KEY=VAL)")
            raise typer.Exit(code=2)
        k, v = kv.split("=", 1)
        env_dict[k.strip()] = v
    written = add_user_mcp_server(
        name=name,
        command=command,
        args=list(arg or ()),
        env=env_dict,
        cwd=cwd,
        trust=trust,
        config_path=config_path,
    )
    _console.print(f"[green]added[/green] MCP server '{name}' → {written}")


@mcp_app.command("remove")
def remove_server(
    name: str = typer.Argument(..., help="Logical name to remove."),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        help="Override the user-global config path (default: ~/.lyra/mcp.json).",
    ),
) -> None:
    """Remove an MCP server from the user-global config."""
    from lyra_mcp.client.config import remove_user_mcp_server

    removed = remove_user_mcp_server(name, config_path=config_path)
    if removed:
        _console.print(f"[green]removed[/green] MCP server '{name}'")
    else:
        _console.print(
            f"[yellow]not removed[/yellow] (no entry named '{name}' in user config)"
        )


@mcp_app.command("doctor")
def doctor_servers(
    repo_root: Path = typer.Option(
        Path.cwd(), "--repo-root", "-C", help="Repo root for project-local config."
    ),
) -> None:
    """Quick health check on every configured MCP server.

    For each server we report whether the executable is on ``PATH``;
    we don't actually spawn it (no side effects, no API calls).
    """
    import shutil

    result = _load(repo_root)
    if not result.servers:
        _console.print("[dim]no MCP servers configured[/dim]")
        if result.issues:
            for issue in result.issues:
                _console.print(
                    f"[yellow]•[/yellow] {issue.source}::{issue.name} — {issue.message}"
                )
        raise typer.Exit(code=0 if not result.issues else 1)
    table = Table(title="MCP doctor", show_lines=False)
    table.add_column("name", style="bold")
    table.add_column("executable")
    table.add_column("status")
    bad = 0
    for s in result.servers:
        exe = s.command[0] if s.command else ""
        path = shutil.which(exe) if exe else None
        if path:
            table.add_row(s.name, exe, f"[green]ok[/green] ({path})")
        else:
            bad += 1
            table.add_row(s.name, exe, "[red]missing on PATH[/red]")
    _console.print(table)
    if result.issues:
        _console.print("[yellow]config issues:[/yellow]")
        for issue in result.issues:
            _console.print(
                f"  [yellow]•[/yellow] {issue.source}::{issue.name} — {issue.message}"
            )
    raise typer.Exit(code=0 if bad == 0 and not result.issues else 1)
