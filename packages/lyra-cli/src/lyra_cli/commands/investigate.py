"""`lyra investigate <question>` — DCI-mode against a corpus mount.

Cite: arXiv:2605.05242 — *Beyond Semantic Similarity: Rethinking
Retrieval for Agentic Search via Direct Corpus Interaction*; reference
impl ``github.com/DCI-Agent/DCI-Agent-Lite``.

The command builds an :class:`InvestigationRunner`, points it at the
corpus root, drives one turn, and prints the cited answer to stdout.
The trajectory ledger lands at ``<output-dir>/conversation_full.json``.
"""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from lyra_core.investigate import (
    ContextLevel,
    CorpusMount,
    InvestigationBudget,
    InvestigationRunner,
)

from ..llm_factory import build_llm

_console = Console()


def investigate_command(
    question: str = typer.Argument(..., help="The question to investigate."),
    corpus: Path = typer.Option(
        Path.cwd(), "--corpus", "-c",
        help="Corpus root the agent may search (read-only).",
    ),
    context_level: int = typer.Option(
        int(ContextLevel.TRUNCATE_PLUS_COMPACT),
        "--context-level", "-L", min=0, max=4,
        help="DCI context-management rung 0..4 (paper default: 3).",
    ),
    max_turns: int = typer.Option(
        300, "--max-turns",
        help="Hard cap on LLM turns. DCI-Agent-Lite default = 300.",
    ),
    wall_clock_s: float = typer.Option(
        1800.0, "--wall-clock",
        help="Wall-clock cap in seconds. Default 30 minutes.",
    ),
    output_dir: Path = typer.Option(
        None, "--output-dir", "-o",
        help="Write final.txt + conversation_full.json here.",
    ),
    llm: str = typer.Option(
        "auto", "--llm",
        help="LLM provider (see lyra plan --help for the list).",
    ),
    read_only: bool = typer.Option(
        True, "--read-only/--writable",
        help="Whether the mount is read-only (default) or writable.",
    ),
) -> None:
    """Investigate a corpus directly with grep + read — no semantic retriever."""
    corpus = corpus.resolve()
    if not corpus.is_dir():
        _console.print(f"[red]corpus must be a directory: {corpus}[/red]")
        raise typer.Exit(code=2)

    mount = CorpusMount(root=corpus, read_only=read_only)
    budget = InvestigationBudget(
        max_turns=max_turns, wall_clock_s=wall_clock_s,
    )
    level = ContextLevel(context_level)
    runner = InvestigationRunner(
        llm=build_llm(llm),
        mount=mount, budget=budget, context_level=level,
        output_dir=output_dir.resolve() if output_dir else None,
    )

    _console.print(
        f"[cyan]investigating[/cyan] corpus={corpus} level={level.name} "
        f"max_turns={max_turns}",
    )
    result = runner.run(question)
    _console.print()
    _console.print(result.final_text or "(no answer)")
    _console.print()
    _console.print(
        f"[dim]stopped_by={result.stopped_by} turns={result.turns_used} "
        f"bash={result.bash_calls_used} "
        f"bytes={result.bytes_read_used} "
        f"wall_clock_s={result.wall_clock_used:.2f}[/dim]",
    )
    if result.output_dir is not None:
        _console.print(f"[dim]ledger: {result.output_dir}/conversation_full.json[/dim]")
