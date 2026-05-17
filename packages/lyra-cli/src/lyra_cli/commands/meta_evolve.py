"""``lyra meta-evolve`` — AEVO-style meta-evolution CLI.

Run meta-evolution on a task using the AEVO two-phase loop.
"""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from lyra_cli.evolution import (
    EvolutionHarness,
    CostMeter,
    BudgetCap,
    MetaAgent,
    EvolutionSegment,
    aevo_loop,
)

_console = Console()


def meta_evolve_command(
    task: str = typer.Option(
        ...,
        "--task",
        "-t",
        help="Task description for evolution.",
    ),
    mode: str = typer.Option(
        "agent",
        "--mode",
        "-m",
        help="Evolution mode: 'agent' or 'procedure'.",
    ),
    rounds: int = typer.Option(
        10,
        "--rounds",
        "-r",
        help="Number of meta-evolution rounds.",
    ),
    segment_size: int = typer.Option(
        5,
        "--segment-size",
        "-s",
        help="Evolution segment size (iterations per round).",
    ),
    budget: float = typer.Option(
        10.0,
        "--budget",
        "-b",
        help="Budget cap in dollars.",
    ),
) -> None:
    """Run meta-evolution on a task using AEVO two-phase loop."""
    _console.print(
        f"[bold cyan]lyra meta-evolve[/bold cyan] — task={task}, "
        f"mode={mode}, rounds={rounds}, segment_size={segment_size}, "
        f"budget=${budget:.2f}"
    )

    # Initialize components
    evolution_dir = Path.cwd() / ".lyra" / "evolution"
    harness = EvolutionHarness(evolution_dir)
    cost_meter = CostMeter()
    budget_cap = BudgetCap(max_dollars=budget)
    meta_agent = MetaAgent(evolution_dir)
    segment_runner = EvolutionSegment(harness, cost_meter)

    # Placeholder evolver
    def evolver() -> dict:
        return {"id": "placeholder", "prompt": task}

    # Run AEVO loop
    _console.print("[yellow]Starting meta-evolution...[/yellow]")
    context = aevo_loop(
        meta_agent,
        segment_runner,
        evolver,
        rounds,
        segment_size,
        budget_cap,
    )

    # Report results
    stats = cost_meter.get_stats()
    _console.print(
        f"[bold green]Complete[/bold green] — "
        f"{len(context.candidates)} candidates, "
        f"{len(context.meta_edits)} edits, "
        f"${stats['dollars_spent']:.2f} spent"
    )


__all__ = ["meta_evolve_command"]
