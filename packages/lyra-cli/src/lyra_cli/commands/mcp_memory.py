"""``lyra mcp-memory`` — MCP Server Surface for CoALA Memory Architecture.

Exposes 8 MCP tools for memory operations:
  - recall: Retrieve fragments relevant to a query
  - write: Add a new memory fragment
  - pin: Mark a fragment as user-pinned (never evicted)
  - forget: Soft-delete a fragment
  - list-decisions: List all DECISION fragments
  - skill-invoke: Retrieve and format a SKILL fragment for execution
  - digest: Write a SubAgentDigest
  - recall-digests: Retrieve digests for peer agents in a task

Integration with CoALA 4-tier memory architecture (Phase M7).
"""
from __future__ import annotations

import json as _json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

mcp_memory_app = typer.Typer(
    name="mcp-memory",
    help=(
        "MCP Server Surface for CoALA Memory Architecture — "
        "8 tools for memory operations with access control."
    ),
    no_args_is_help=True,
)
_console = Console()


# ---------------------------------------------------------------------------
# recall
# ---------------------------------------------------------------------------


@mcp_memory_app.command("recall")
def recall(
    query: str = typer.Argument(
        ...,
        help="Search query (free text or entity).",
    ),
    tier: Optional[str] = typer.Option(
        None,
        "--tier",
        help="Filter by tier (t0_working, t1_session, t2_semantic, t2_procedural, t3_user, t3_team).",
    ),
    fragment_type: Optional[str] = typer.Option(
        None,
        "--type",
        help="Filter by type (fact, decision, preference, skill, observation).",
    ),
    limit: int = typer.Option(10, "--limit", "-n", help="Maximum number of fragments to return."),
    user_id: str = typer.Option("default", "--user-id", help="User ID for access control."),
    agent_id: Optional[str] = typer.Option(None, "--agent-id", help="Agent ID for access control."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """Retrieve fragments relevant to a query."""
    from lyra_core.memory.mcp_tools import mcp_recall

    result = mcp_recall(
        query=query,
        tier=tier,
        fragment_type=fragment_type,
        limit=limit,
        user_id=user_id,
        agent_id=agent_id,
    )

    if json_out:
        typer.echo(_json.dumps(result, indent=2))
        return

    if result["count"] == 0:
        _console.print(
            f"[yellow]No fragments found for query[/] [bold]{query}[/] "
            f"(tier={tier or 'any'}, type={fragment_type or 'any'})."
        )
        return

    table = Table(
        title=f"Recall for {query!r}",
        title_style="bold cyan",
        show_lines=False,
    )
    table.add_column("ID", style="dim", width=20)
    table.add_column("Type", width=12)
    table.add_column("Content", style="bold")
    table.add_column("Confidence", justify="right", width=10)
    for fragment in result["fragments"]:
        table.add_row(
            fragment["id"],
            fragment["type"],
            fragment["content"],
            f"{fragment['confidence']:.2f}",
        )
    _console.print(table)


# ---------------------------------------------------------------------------
# write
# ---------------------------------------------------------------------------


@mcp_memory_app.command("write")
def write(
    content: str = typer.Argument(..., help="Fragment content (≤ 200 chars recommended)."),
    fragment_type: str = typer.Option(
        ...,
        "--type",
        help="Type (fact, decision, preference, skill, observation).",
    ),
    tier: str = typer.Option(
        ...,
        "--tier",
        help="Target tier (t0_working, t1_session, t2_semantic, t2_procedural, t3_user, t3_team).",
    ),
    entities: Optional[str] = typer.Option(
        None,
        "--entities",
        help="Comma-separated entity mentions (≤ 5 noun-phrases).",
    ),
    confidence: float = typer.Option(0.8, "--confidence", help="Confidence score (0..1)."),
    agent_id: str = typer.Option("system", "--agent-id", help="Agent ID for provenance."),
    user_id: str = typer.Option("default", "--user-id", help="User ID for provenance."),
    task_id: Optional[str] = typer.Option(None, "--task-id", help="Task ID for task-scoped fragments."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """Add a new memory fragment."""
    from lyra_core.memory.mcp_tools import mcp_write

    entity_list = [e.strip() for e in entities.split(",")] if entities else None

    result = mcp_write(
        content=content,
        fragment_type=fragment_type,
        tier=tier,
        entities=entity_list,
        confidence=confidence,
        agent_id=agent_id,
        user_id=user_id,
        task_id=task_id,
    )

    if "error" in result:
        _console.print(f"[red]Error:[/] {result['error']}")
        raise typer.Exit(1)

    if json_out:
        typer.echo(_json.dumps(result, indent=2))
        return

    _console.print(
        f"[green]Created[/] fragment [bold]{result['fragment_id']}[/] "
        f"(tier={result['tier']}, type={result['type']})."
    )


# ---------------------------------------------------------------------------
# pin
# ---------------------------------------------------------------------------


@mcp_memory_app.command("pin")
def pin(
    fragment_id: str = typer.Argument(..., help="Fragment ID to pin."),
    user_id: str = typer.Option("default", "--user-id", help="User ID for access control."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """Mark a fragment as user-pinned (never evicted)."""
    from lyra_core.memory.mcp_tools import mcp_pin

    result = mcp_pin(fragment_id=fragment_id, user_id=user_id)

    if "error" in result:
        _console.print(f"[red]Error:[/] {result['error']}")
        raise typer.Exit(1)

    if json_out:
        typer.echo(_json.dumps(result, indent=2))
        return

    _console.print(
        f"[green]Pinned[/] fragment [bold]{result['fragment_id']}[/]."
    )


# ---------------------------------------------------------------------------
# forget
# ---------------------------------------------------------------------------


@mcp_memory_app.command("forget")
def forget(
    fragment_id: str = typer.Argument(..., help="Fragment ID to forget."),
    user_id: str = typer.Option("default", "--user-id", help="User ID for access control."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """Soft-delete a fragment (mark as invalid_at=now, kept for audit)."""
    from lyra_core.memory.mcp_tools import mcp_forget

    result = mcp_forget(fragment_id=fragment_id, user_id=user_id)

    if "error" in result:
        _console.print(f"[red]Error:[/] {result['error']}")
        raise typer.Exit(1)

    if json_out:
        typer.echo(_json.dumps(result, indent=2))
        return

    _console.print(
        f"[green]Forgotten[/] fragment [bold]{result['fragment_id']}[/] "
        f"(invalid_at={result['invalid_at']})."
    )


# ---------------------------------------------------------------------------
# list-decisions
# ---------------------------------------------------------------------------


@mcp_memory_app.command("list-decisions")
def list_decisions(
    tier: Optional[str] = typer.Option(
        None,
        "--tier",
        help="Filter by tier (optional).",
    ),
    limit: int = typer.Option(50, "--limit", "-n", help="Maximum number of decisions to return."),
    user_id: str = typer.Option("default", "--user-id", help="User ID for access control."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """List all DECISION fragments."""
    from lyra_core.memory.mcp_tools import mcp_list_decisions

    result = mcp_list_decisions(tier=tier, limit=limit, user_id=user_id)

    if json_out:
        typer.echo(_json.dumps(result, indent=2))
        return

    if result["count"] == 0:
        _console.print(
            f"[yellow]No decisions found[/] (tier={tier or 'any'})."
        )
        return

    table = Table(
        title=f"Decisions ({result['count']})",
        title_style="bold cyan",
        show_lines=False,
    )
    table.add_column("ID", style="dim", width=20)
    table.add_column("Content", style="bold")
    table.add_column("Rationale")
    for decision in result["decisions"]:
        table.add_row(
            decision["id"],
            decision["content"],
            decision.get("rationale", ""),
        )
    _console.print(table)


# ---------------------------------------------------------------------------
# skill-invoke
# ---------------------------------------------------------------------------


@mcp_memory_app.command("skill-invoke")
def skill_invoke(
    skill_name: str = typer.Argument(..., help="Skill name to retrieve."),
    user_id: str = typer.Option("default", "--user-id", help="User ID for access control."),
    agent_id: Optional[str] = typer.Option(None, "--agent-id", help="Agent ID for access control."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """Retrieve and format a SKILL fragment for execution."""
    from lyra_core.memory.mcp_tools import mcp_skill_invoke

    result = mcp_skill_invoke(
        skill_name=skill_name,
        user_id=user_id,
        agent_id=agent_id,
    )

    if json_out:
        typer.echo(_json.dumps(result, indent=2))
        return

    _console.print(f"[bold cyan]Skill:[/] {result['skill_name']}")
    _console.print(f"[dim]Executable:[/] {result['executable']}")
    _console.print()
    _console.print(result["content"])
    if result["executable"] and "code" in result:
        _console.print()
        _console.print("[dim]Code:[/]")
        _console.print(result["code"])


# ---------------------------------------------------------------------------
# digest
# ---------------------------------------------------------------------------


@mcp_memory_app.command("digest")
def digest(
    agent_id: str = typer.Argument(..., help="Sub-agent ID."),
    task_id: str = typer.Argument(..., help="Task ID."),
    step: int = typer.Argument(..., help="Step index in trajectory."),
    last_action: str = typer.Argument(..., help="Compact summary of last action (≤ 200 chars)."),
    findings: Optional[str] = typer.Option(
        None,
        "--findings",
        help="Comma-separated bullet points of findings.",
    ),
    open_questions: Optional[str] = typer.Option(
        None,
        "--questions",
        help="Comma-separated list of open questions.",
    ),
    next_intent: Optional[str] = typer.Option(None, "--next", help="Next intended action."),
    confidence: float = typer.Option(0.7, "--confidence", help="Confidence score (0..1)."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """Write a SubAgentDigest to the digest bus."""
    from lyra_core.memory.mcp_tools import mcp_digest

    findings_list = [f.strip() for f in findings.split(",")] if findings else None
    questions_list = [q.strip() for q in open_questions.split(",")] if open_questions else None

    result = mcp_digest(
        agent_id=agent_id,
        task_id=task_id,
        step=step,
        last_action=last_action,
        findings=findings_list,
        open_questions=questions_list,
        next_intent=next_intent,
        confidence=confidence,
    )

    if json_out:
        typer.echo(_json.dumps(result, indent=2))
        return

    _console.print(
        f"[green]Recorded[/] digest [bold]{result['digest_id']}[/] "
        f"(last_action: {result['last_action']})."
    )


# ---------------------------------------------------------------------------
# recall-digests
# ---------------------------------------------------------------------------


@mcp_memory_app.command("recall-digests")
def recall_digests(
    task_id: str = typer.Argument(..., help="Task ID."),
    agent_id: Optional[str] = typer.Option(None, "--agent-id", help="Filter by specific agent."),
    limit: int = typer.Option(10, "--limit", "-n", help="Maximum number of digests to return."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """Retrieve digests for peer agents in a task."""
    from lyra_core.memory.mcp_tools import mcp_recall_digests

    result = mcp_recall_digests(
        task_id=task_id,
        agent_id=agent_id,
        limit=limit,
    )

    if json_out:
        typer.echo(_json.dumps(result, indent=2))
        return

    if result["count"] == 0:
        _console.print(
            f"[yellow]No digests found for task[/] [bold]{task_id}[/] "
            f"(agent={agent_id or 'any'})."
        )
        return

    _console.print(f"[bold cyan]Summary:[/] {result['summary']}")
    _console.print()

    table = Table(
        title=f"Digests for task {task_id}",
        title_style="bold cyan",
        show_lines=True,
    )
    table.add_column("Agent", style="bold", width=15)
    table.add_column("Step", justify="right", width=6)
    table.add_column("Last Action")
    table.add_column("Confidence", justify="right", width=10)
    for d in result["digests"]:
        table.add_row(
            d["agent_id"],
            str(d["step"]),
            d["last_action"],
            f"{d['confidence']:.2f}",
        )
    _console.print(table)


__all__ = ["mcp_memory_app"]
