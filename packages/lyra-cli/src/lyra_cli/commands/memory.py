"""``lyra memory`` — inspect and operate the ReasoningBank store.

Lyra's reasoning bank (``lyra_core.memory.reasoning_bank.ReasoningBank``
and the SQLite-backed ``SqliteReasoningBank``) carries lessons distilled
from prior trajectories — both successful strategies and failure-driven
anti-skills. The bank works fine without operator intervention, but
sometimes you want to:

- read what the bank thinks it knows about a query,
- list the lessons that have accumulated,
- get a quick summary of polarity counts,
- wipe the store after a noisy debug session,
- record a synthetic lesson by hand for testing.

This subcommand provides exactly that surface, all aimed at the
``<repo>/.lyra/memory/reasoning_bank.sqlite`` store by default. Pass
``--db`` to point at a different file.
"""
from __future__ import annotations

import json as _json
from pathlib import Path
from typing import Optional  # noqa: UP035 — typer needs runtime-resolvable annotations on Python 3.9

import typer
from rich.console import Console
from rich.table import Table

memory_app = typer.Typer(
    name="memory",
    help=(
        "Inspect and operate the ReasoningBank — Lyra's lessons memory "
        "(both success strategies and failure-driven anti-skills)."
    ),
    no_args_is_help=True,
)
_console = Console()


def _resolve_db_path(db: Optional[str], repo_root: Optional[str]) -> Path:
    """Resolve the ReasoningBank SQLite path.

    Priority:
        1. explicit --db
        2. ``<repo>/.lyra/memory/reasoning_bank.sqlite`` from --repo-root
        3. ``<cwd>/.lyra/memory/reasoning_bank.sqlite``
    """
    from lyra_core.memory import default_db_path

    if db is not None:
        return Path(db)
    root = Path(repo_root) if repo_root else Path.cwd()
    return default_db_path(root)


def _open_bank(db: Optional[str], repo_root: Optional[str]) -> object:
    """Open a SQLite-backed bank with the heuristic distiller wired in."""
    from lyra_core.memory import HeuristicDistiller, SqliteReasoningBank

    db_path = _resolve_db_path(db, repo_root)
    return SqliteReasoningBank(distiller=HeuristicDistiller(), db_path=db_path)


# ---------------------------------------------------------------------------
# recall
# ---------------------------------------------------------------------------


@memory_app.command("recall")
def recall(
    query: str = typer.Argument(
        ...,
        help="Task signature / free-text query to recall lessons for.",
    ),
    k: int = typer.Option(5, "--k", "-k", help="Maximum number of lessons to return."),
    polarity: Optional[str] = typer.Option(
        None,
        "--polarity",
        help="Filter to 'success' or 'failure' lessons only.",
    ),
    diversify: bool = typer.Option(
        False,
        "--diversify",
        help="Apply MMR diversity re-ranking to the recall window.",
    ),
    db: Optional[str] = typer.Option(
        None, "--db", help="Override path to the bank SQLite file."
    ),
    repo_root: Optional[str] = typer.Option(
        None,
        "--repo-root",
        help="Repository root used to resolve the default DB path.",
    ),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """Recall lessons relevant to a task signature."""
    from lyra_core.memory import TrajectoryOutcome

    pol: TrajectoryOutcome | None = None
    if polarity is not None:
        norm = polarity.strip().lower()
        if norm not in {"success", "failure"}:
            raise typer.BadParameter(
                f"--polarity must be 'success' or 'failure' (got {polarity!r})"
            )
        pol = (
            TrajectoryOutcome.SUCCESS if norm == "success" else TrajectoryOutcome.FAILURE
        )

    bank = _open_bank(db, repo_root)
    lessons = bank.recall(  # type: ignore[attr-defined]
        query, k=k, polarity=pol, diversity_weighted=diversify
    )

    if json_out:
        out = [
            {
                "id": lesson.id,
                "polarity": lesson.polarity.value,
                "title": lesson.title,
                "body": lesson.body,
                "task_signatures": list(lesson.task_signatures),
                "source_trajectory_ids": list(lesson.source_trajectory_ids),
            }
            for lesson in lessons
        ]
        typer.echo(_json.dumps(out, indent=2))
        return

    if not lessons:
        _console.print(
            f"[yellow]No lessons found for query[/] [bold]{query}[/] "
            f"(k={k}, polarity={polarity or 'any'})."
        )
        return

    table = Table(
        title=f"Recall for {query!r}",
        title_style="bold cyan",
        show_lines=False,
    )
    table.add_column("Polarity", style="dim", width=8)
    table.add_column("Title", style="bold")
    table.add_column("Body")
    for lesson in lessons:
        polarity_label = (
            "[green]do[/]"
            if lesson.polarity is TrajectoryOutcome.SUCCESS
            else "[red]avoid[/]"
        )
        table.add_row(polarity_label, lesson.title, lesson.body)
    _console.print(table)


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@memory_app.command("list")
def list_lessons(
    polarity: Optional[str] = typer.Option(
        None, "--polarity", help="Filter to 'success' or 'failure' lessons only."
    ),
    limit: int = typer.Option(50, "--limit", "-n", help="Cap rows shown."),
    db: Optional[str] = typer.Option(None, "--db"),
    repo_root: Optional[str] = typer.Option(None, "--repo-root"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """List lessons currently in the bank, newest first."""
    from lyra_core.memory import TrajectoryOutcome

    pol: TrajectoryOutcome | None = None
    if polarity is not None:
        norm = polarity.strip().lower()
        if norm not in {"success", "failure"}:
            raise typer.BadParameter(
                f"--polarity must be 'success' or 'failure' (got {polarity!r})"
            )
        pol = (
            TrajectoryOutcome.SUCCESS if norm == "success" else TrajectoryOutcome.FAILURE
        )

    bank = _open_bank(db, repo_root)
    lessons = bank.all_lessons(polarity=pol, limit=limit)  # type: ignore[attr-defined]

    if json_out:
        typer.echo(
            _json.dumps(
                [
                    {
                        "id": lesson.id,
                        "polarity": lesson.polarity.value,
                        "title": lesson.title,
                        "body": lesson.body,
                    }
                    for lesson in lessons
                ],
                indent=2,
            )
        )
        return

    if not lessons:
        _console.print("[yellow]Bank is empty.[/]")
        return

    table = Table(
        title=f"ReasoningBank ({len(lessons)} lesson{'' if len(lessons) == 1 else 's'})",
        title_style="bold cyan",
    )
    table.add_column("ID", style="dim", width=22)
    table.add_column("Polarity", width=8)
    table.add_column("Title", style="bold")
    for lesson in lessons:
        polarity_label = (
            "[green]success[/]"
            if lesson.polarity is TrajectoryOutcome.SUCCESS
            else "[red]failure[/]"
        )
        table.add_row(lesson.id, polarity_label, lesson.title)
    _console.print(table)


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------


@memory_app.command("show")
def show(
    lesson_id: str = typer.Argument(..., help="Lesson id (from `lyra memory list`)."),
    db: Optional[str] = typer.Option(None, "--db"),
    repo_root: Optional[str] = typer.Option(None, "--repo-root"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Show one lesson in full, including signatures + source trajectories."""
    bank = _open_bank(db, repo_root)
    lessons = bank.all_lessons()  # type: ignore[attr-defined]
    match = next((lesson for lesson in lessons if lesson.id == lesson_id), None)
    if match is None:
        _console.print(f"[red]No lesson with id[/] [bold]{lesson_id}[/].")
        raise typer.Exit(1)

    if json_out:
        typer.echo(
            _json.dumps(
                {
                    "id": match.id,
                    "polarity": match.polarity.value,
                    "title": match.title,
                    "body": match.body,
                    "task_signatures": list(match.task_signatures),
                    "source_trajectory_ids": list(match.source_trajectory_ids),
                },
                indent=2,
            )
        )
        return

    _console.print(f"[bold cyan]{match.id}[/]  [dim]({match.polarity.value})[/]")
    _console.print(f"[bold]{match.title}[/]")
    _console.print()
    _console.print(match.body)
    _console.print()
    if match.task_signatures:
        _console.print(
            f"[dim]signatures:[/] {', '.join(match.task_signatures)}"
        )
    if match.source_trajectory_ids:
        _console.print(
            f"[dim]sources:[/]    {', '.join(match.source_trajectory_ids)}"
        )


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------


@memory_app.command("stats")
def stats(
    db: Optional[str] = typer.Option(None, "--db"),
    repo_root: Optional[str] = typer.Option(None, "--repo-root"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """One-screen summary of what's in the bank."""
    bank = _open_bank(db, repo_root)
    bank_stats = bank.stats()  # type: ignore[attr-defined]
    if json_out:
        typer.echo(_json.dumps(bank_stats, indent=2))
        return
    table = Table(title="ReasoningBank stats", title_style="bold cyan")
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right")
    for key, val in bank_stats.items():
        table.add_row(key.replace("_", " "), str(val))
    _console.print(table)


# ---------------------------------------------------------------------------
# wipe
# ---------------------------------------------------------------------------


@memory_app.command("wipe")
def wipe(
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip the confirmation prompt."
    ),
    db: Optional[str] = typer.Option(None, "--db"),
    repo_root: Optional[str] = typer.Option(None, "--repo-root"),
) -> None:
    """Delete every lesson in the bank. Cannot be undone."""
    bank = _open_bank(db, repo_root)
    count_before = bank.stats()["lessons_total"]  # type: ignore[attr-defined]
    if count_before == 0:
        _console.print("[yellow]Bank is already empty.[/]")
        return
    if not yes:
        confirm = typer.confirm(
            f"Wipe {count_before} lessons from the bank? This cannot be undone."
        )
        if not confirm:
            _console.print("[dim]Aborted.[/]")
            raise typer.Exit(0)
    deleted = bank.wipe()  # type: ignore[attr-defined]
    _console.print(f"[green]Deleted {deleted} lessons.[/]")


# ---------------------------------------------------------------------------
# record  (manual seed for testing / smoke-checks)
# ---------------------------------------------------------------------------


@memory_app.command("record")
def record(
    task_signature: str = typer.Argument(
        ..., help="Task signature this lesson should be retrievable under."
    ),
    outcome: str = typer.Argument(
        ..., help="'success' or 'failure'."
    ),
    summary: str = typer.Option(
        ...,
        "--summary",
        help="A short message describing what happened in the trajectory.",
    ),
    trajectory_id: str = typer.Option(
        "manual",
        "--trajectory-id",
        help="Identifier for the synthetic trajectory (audit trail).",
    ),
    db: Optional[str] = typer.Option(None, "--db"),
    repo_root: Optional[str] = typer.Option(None, "--repo-root"),
) -> None:
    """Record a synthetic trajectory.

    Useful for seeding the bank with hand-curated lessons or smoke-testing
    a fresh install. The HeuristicDistiller will turn the supplied
    summary into a one-line lesson with the requested polarity.
    """
    from lyra_core.memory import (
        Trajectory,
        TrajectoryOutcome,
        TrajectoryStep,
    )

    norm = outcome.strip().lower()
    if norm not in {"success", "failure"}:
        raise typer.BadParameter(
            f"outcome must be 'success' or 'failure' (got {outcome!r})"
        )
    polarity = (
        TrajectoryOutcome.SUCCESS if norm == "success" else TrajectoryOutcome.FAILURE
    )

    bank = _open_bank(db, repo_root)
    trajectory = Trajectory(
        id=trajectory_id,
        task_signature=task_signature,
        outcome=polarity,
        steps=(TrajectoryStep(index=0, kind="message", payload=summary),),
        final_artefact="(manual record)",
    )
    lessons = bank.record(trajectory)  # type: ignore[attr-defined]
    _console.print(
        f"[green]Recorded[/] {len(lessons)} lesson(s) for "
        f"signature [bold]{task_signature}[/] (polarity={norm})."
    )


__all__ = ["memory_app"]
