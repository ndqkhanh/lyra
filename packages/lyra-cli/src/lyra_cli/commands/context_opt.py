"""``lyra context-opt`` — Context Optimisation Dashboard & Tuning.

Subcommands:
    status     — Rich table: cache hit ratio, compression, decisions, cost
    tune       — adjust thresholds live (compaction, cache_alert, compress)
    decisions  — list pinned decisions with confidence and source turn
    facts      — show temporal facts, flagging recently invalidated ones
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from lyra_core.context.cache_telemetry import CacheTelemetry
from lyra_core.context.context_evaluator import (
    ContextMetrics,
    OptimisationTrendTracker,
)
from lyra_core.memory.pinned_decisions import PinnedDecisionStore
from lyra_core.memory.temporal_fact_store import TemporalFactStore

_console = Console()

context_opt_app = typer.Typer(
    name="context-opt",
    help="Context optimisation dashboard and threshold tuning.",
    no_args_is_help=True,
)


def _lyra_dir(repo_root: Path) -> Path:
    return repo_root / ".lyra"


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@context_opt_app.command("status")
def status_command(
    repo_root: Path = typer.Option(Path.cwd(), "--repo-root", "-C", help="Repo root."),
) -> None:
    """Show context optimisation metrics for the current session."""
    lyra_dir = _lyra_dir(repo_root)

    # Cache telemetry
    telemetry_path = lyra_dir / "cache_telemetry.json"
    telemetry = CacheTelemetry(
        store_path=telemetry_path if telemetry_path.exists() else None
    )
    summary = telemetry.summary()

    # Pinned decisions
    decisions_path = lyra_dir / "pinned_decisions.json"
    decision_store = PinnedDecisionStore(
        store_path=decisions_path if decisions_path.exists() else None
    )
    decisions = decision_store.recall()

    # Latest optimisation trend
    trend_path = lyra_dir / "opt_trend.json"
    trend = OptimisationTrendTracker(
        store_path=trend_path if trend_path.exists() else None
    )
    latest: ContextMetrics | None = trend.latest()

    table = Table(title="Context Optimisation Status", box=box.ROUNDED)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_column("Target", justify="right", style="dim")
    table.add_column("Status", justify="right")

    def _ok(val: float, target: float, *, higher_better: bool = True) -> str:
        good = val >= target if higher_better else val <= target
        return "[green]OK[/green]" if good else "[yellow]WARN[/yellow]"

    hit_ratio = summary.mean_hit_ratio if summary.turn_count > 0 else 0.0

    table.add_row(
        "Cache hit ratio",
        f"{hit_ratio:.1%}",
        "≥ 70 %",
        _ok(hit_ratio, 0.70),
    )
    table.add_row(
        "Total turns recorded",
        str(summary.turn_count),
        "—",
        "—",
    )
    table.add_row(
        "Cache alert count",
        str(summary.alert_count),
        "0",
        "[green]OK[/green]" if summary.alert_count == 0 else "[yellow]WARN[/yellow]",
    )
    table.add_row(
        "Pinned decisions",
        str(len(decisions)),
        "—",
        "—",
    )

    if latest:
        table.add_row(
            "Tokens saved (compression)",
            f"{latest.tokens_saved_by_compression:,}",
            "> 0",
            (
                "[green]OK[/green]"
                if latest.tokens_saved_by_compression > 0
                else "[dim]—[/dim]"
            ),
        )
        table.add_row(
            "Decisions preserved",
            f"{latest.decisions_preserved:.1%}",
            "≥ 95 %",
            _ok(latest.decisions_preserved, 0.95),
        )
        table.add_row(
            "Compaction count",
            str(latest.compaction_count),
            "—",
            "—",
        )
        table.add_row(
            "Estimated cost (session)",
            f"${latest.estimated_cost_usd:.4f}",
            "—",
            "—",
        )
    else:
        table.add_row("Trend data", "[dim]none yet[/dim]", "—", "—")

    _console.print(table)


# ---------------------------------------------------------------------------
# tune
# ---------------------------------------------------------------------------


@context_opt_app.command("tune")
def tune_command(
    compaction: Optional[float] = typer.Option(
        None, "--compaction", help="Compaction trigger % (e.g. 60)."
    ),
    cache_alert: Optional[float] = typer.Option(
        None, "--cache-alert", help="Cache hit alert threshold (e.g. 0.7)."
    ),
    compress_threshold: Optional[int] = typer.Option(
        None, "--compress-threshold", help="Min chars before compression applies."
    ),
    repo_root: Path = typer.Option(Path.cwd(), "--repo-root", "-C"),
) -> None:
    """Adjust optimisation thresholds (persisted to .lyra/context_opt_config.json)."""
    config_path = _lyra_dir(repo_root) / "context_opt_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    current: dict = {}
    if config_path.exists():
        try:
            current = json.loads(config_path.read_text())
        except (json.JSONDecodeError, TypeError):
            pass

    updated = False
    if compaction is not None:
        current["compaction_pct"] = compaction
        updated = True
    if cache_alert is not None:
        current["cache_alert_threshold"] = cache_alert
        updated = True
    if compress_threshold is not None:
        current["compress_threshold_chars"] = compress_threshold
        updated = True

    if not updated:
        _console.print(
            "[yellow]No parameters given. "
            "Use --compaction, --cache-alert, or --compress-threshold.[/yellow]"
        )
        if current:
            _console.print(f"Current config:\n{json.dumps(current, indent=2)}")
        return

    config_path.write_text(json.dumps(current, indent=2))
    _console.print(f"[green]Config saved → {config_path}[/green]")
    _console.print(json.dumps(current, indent=2))


# ---------------------------------------------------------------------------
# decisions
# ---------------------------------------------------------------------------


@context_opt_app.command("decisions")
def decisions_command(
    min_confidence: float = typer.Option(
        0.0, "--min-confidence", "-c", help="Minimum confidence filter (0–1)."
    ),
    top_k: int = typer.Option(20, "--top", "-n", help="Max rows to show."),
    repo_root: Path = typer.Option(Path.cwd(), "--repo-root", "-C"),
) -> None:
    """List pinned decisions with source turn and confidence."""
    decisions_path = _lyra_dir(repo_root) / "pinned_decisions.json"
    store = PinnedDecisionStore(
        store_path=decisions_path if decisions_path.exists() else None
    )
    entries = store.recall(top_k=top_k, min_confidence=min_confidence)

    if not entries:
        _console.print("[dim]No pinned decisions found.[/dim]")
        return

    table = Table(title=f"Pinned Decisions ({len(entries)})", box=box.SIMPLE)
    table.add_column("Turn", justify="right", style="dim", width=5)
    table.add_column("Conf", justify="right", width=6)
    table.add_column("Decision", overflow="fold")
    table.add_column("Tags", style="dim", width=16)

    for entry in entries:
        color = "green" if entry.confidence >= 0.7 else "yellow"
        table.add_row(
            str(entry.source_turn),
            f"[{color}]{entry.confidence:.0%}[/{color}]",
            entry.text[:120],
            ", ".join(entry.tags) if entry.tags else "—",
        )
    _console.print(table)


# ---------------------------------------------------------------------------
# facts
# ---------------------------------------------------------------------------


@context_opt_app.command("facts")
def facts_command(
    include_invalid: bool = typer.Option(
        False, "--include-invalid", "-a", help="Show invalidated facts too."
    ),
    category: Optional[str] = typer.Option(
        None, "--category", help="Filter by category."
    ),
    repo_root: Path = typer.Option(Path.cwd(), "--repo-root", "-C"),
) -> None:
    """Show temporal facts, flagging recently invalidated ones."""
    facts_path = _lyra_dir(repo_root) / "temporal_facts.json"
    store = TemporalFactStore(
        store_path=facts_path if facts_path.exists() else None
    )
    entries = store.recall(category=category, include_invalid=include_invalid)

    if not entries:
        _console.print("[dim]No temporal facts found.[/dim]")
        return

    table = Table(
        title=f"Temporal Facts ({len(entries)})", box=box.SIMPLE
    )
    table.add_column("ID", width=8, style="dim")
    table.add_column("Category", width=14)
    table.add_column("Fact", overflow="fold")
    table.add_column("Valid from", width=10, style="dim")
    table.add_column("Status", width=12, justify="right")

    for f in entries:
        status = "[green]active[/green]" if f.is_valid else "[red]invalidated[/red]"
        valid_from = (f.valid_from or "")[:10] or "—"
        table.add_row(
            f.fact_id[:8],
            f.category or "—",
            f.fact[:100],
            valid_from,
            status,
        )
    _console.print(table)
