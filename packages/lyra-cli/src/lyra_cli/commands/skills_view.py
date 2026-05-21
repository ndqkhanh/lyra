"""``lyra skills --active`` and ``lyra dag`` — Phase 8 transparency commands.

Reads:
- ``.lyra/skills/active.json``  — snapshot from SkillPanel
- ``.lyra/dag/<session>.json``  — snapshot from AgentDAG

Both panels live in lyra_core.observability.context_gauge.  These CLI commands
expose them via simple JSON snapshots without requiring a live connection.

    lyra skills --active           — list activated skills
    lyra dag                       — render latest agent DAG
    lyra dag --session SESSION_ID  — specific session
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

_console = Console()


# ---------------------------------------------------------------------------
# lyra skills
# ---------------------------------------------------------------------------

skills_app = typer.Typer(
    name="skills",
    help="Inspect activated skills via the SkillPanel snapshot.",
    no_args_is_help=False,
    invoke_without_command=True,
)


def _load_skills(repo_root: Path) -> list[dict]:
    path = repo_root / ".lyra" / "skills" / "active.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, dict) and "skills" in data:
        return list(data["skills"])
    if isinstance(data, list):
        return list(data)
    return []


@skills_app.callback(invoke_without_command=True)
def skills_command(
    ctx: typer.Context,
    repo_root: Path = typer.Option(Path.cwd(), "--repo-root", "-C", help="Repo root."),
    active: bool = typer.Option(False, "--active", help="Show currently activated skills."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """Inspect activated skills."""
    if ctx.invoked_subcommand is not None:
        return

    if not active:
        _console.print(
            "[dim]Pass --active to view the SkillPanel snapshot.[/dim]\n"
            "Try: lyra skills --active"
        )
        raise typer.Exit(code=0)

    skills = _load_skills(repo_root)
    if json_out:
        _console.print_json(data=skills)
        return

    if not skills:
        _console.print(
            "[dim]No active skills "
            "(.lyra/skills/active.json missing). "
            "Skills activate only inside a live Lyra session.[/dim]"
        )
        raise typer.Exit(code=0)

    table = Table(
        title=f"Active skills ({len(skills)})",
        box=box.SIMPLE_HEAVY,
        title_style="bold",
    )
    table.add_column("name")
    table.add_column("tier")
    table.add_column("trust", justify="right")
    table.add_column("success", justify="right")
    table.add_column("last used", style="dim")

    for s in skills:
        table.add_row(
            str(s.get("name", ""))[:32],
            str(s.get("tier", "")),
            str(s.get("trust_tier", "")),
            f"{float(s.get('success_rate', 0.0)):.0%}",
            str(s.get("last_used", ""))[:19],
        )
    _console.print(table)


# ---------------------------------------------------------------------------
# lyra dag
# ---------------------------------------------------------------------------

dag_app = typer.Typer(
    name="dag",
    help="Render the AgentDAG wave-execution graph for a session.",
    no_args_is_help=False,
    invoke_without_command=True,
)


_STATUS_COLORS = {
    "pending": "dim",
    "running": "green",
    "parked": "yellow",
    "done": "blue",
    "failed": "red",
    "blocked": "red",
}


def _color_status(s: str) -> str:
    return f"[{_STATUS_COLORS.get(s, 'white')}]{s}[/]"


def _load_dag(repo_root: Path, session: Optional[str]) -> Optional[dict]:
    dag_dir = repo_root / ".lyra" / "dag"
    if not dag_dir.exists():
        return None
    if session:
        path = dag_dir / f"{session}.json"
        if not path.exists():
            return None
    else:
        candidates = sorted(
            (p for p in dag_dir.glob("*.json") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            return None
        path = candidates[0]
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _render_node(parent: Tree, node_id: str, nodes: dict, edges: list[dict], visited: set[str]) -> None:
    if node_id in visited:
        return
    visited.add(node_id)
    node = nodes.get(node_id, {})
    status = node.get("status", "pending")
    label = (
        f"[bold]{node_id}[/bold] "
        f"{_color_status(status)} "
        f"role={node.get('role', '?')} "
        f"cost=${float(node.get('cost_usd', 0.0)):.4f}"
    )
    branch = parent.add(label)
    children = [e.get("to") for e in edges if e.get("from") == node_id]
    for child in children:
        if child:
            _render_node(branch, child, nodes, edges, visited)


@dag_app.callback(invoke_without_command=True)
def dag_command(
    ctx: typer.Context,
    repo_root: Path = typer.Option(Path.cwd(), "--repo-root", "-C", help="Repo root."),
    session: Optional[str] = typer.Option(
        None, "--session", "-s", help="Session ID (defaults to most recent)."
    ),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a tree."),
) -> None:
    """Render the AgentDAG wave-execution graph."""
    if ctx.invoked_subcommand is not None:
        return

    data = _load_dag(repo_root, session)
    if data is None:
        _console.print(
            "[dim]No DAG snapshot found "
            "(.lyra/dag/*.json). Run lyra with --harness dag-teams first.[/dim]"
        )
        raise typer.Exit(code=0)

    if json_out:
        _console.print_json(data=data)
        return

    nodes_list = data.get("nodes") or []
    edges_list = data.get("edges") or []
    nodes: dict[str, dict] = {}
    for n in nodes_list:
        if not isinstance(n, dict):
            continue
        node_id = n.get("id") or n.get("node_id")
        if isinstance(node_id, str) and node_id:
            nodes[node_id] = n

    # roots = nodes with no incoming edges
    incoming = {e.get("to") for e in edges_list if isinstance(e, dict)}
    roots = [nid for nid in nodes if nid not in incoming]

    tree = Tree(
        f"[bold]Agent DAG[/bold]  "
        f"({len(nodes)} nodes, {len(edges_list)} edges, "
        f"total cost ${float(data.get('total_cost_usd', 0.0)):.4f})"
    )
    visited: set[str] = set()
    for root in roots:
        _render_node(tree, root, nodes, edges_list, visited)
    # orphan nodes (not reachable from any root)
    for nid in list(nodes):
        if nid not in visited:
            _render_node(tree, nid, nodes, edges_list, visited)
    _console.print(tree)


__all__ = ["skills_app", "dag_app"]
