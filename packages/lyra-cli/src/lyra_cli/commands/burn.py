"""``lyra burn`` - Token Observatory CLI surface (Phase M.4+)."""
from __future__ import annotations

import datetime as _dt
import json as _json
import re
import time as _time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ..paths import RepoLayout
from ..observatory.aggregator import aggregate, BurnReport
from ..observatory.compare import compare as _compare_fn, render_comparison
from ..observatory.dashboard import render_dashboard
from ..observatory.optimize import optimize as _optimize_fn, render_optimize
from ..observatory.yield_tracker import (
    yield_report as _yield_report_fn,
    render_yield,
)


burn_app = typer.Typer(
    name="burn",
    help=(
        "Token spend & activity observatory. Reads "
        "<repo>/.lyra/sessions/*/turns.jsonl and renders a dashboard."
    ),
    no_args_is_help=False,
    invoke_without_command=True,
)
_console = Console()


def _sleep(secs: float) -> None:
    """Indirection so tests can patch the watch loop."""
    _time.sleep(secs)


@burn_app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    since: Optional[str] = typer.Option(
        "7d", "--since",
        help="Lower bound: ISO date ('2026-04-20') or relative ('7d', '24h').",
    ),
    until: Optional[str] = typer.Option(None, "--until"),
    limit: int = typer.Option(10, "--limit"),
    json_out: bool = typer.Option(False, "--json"),
    refresh: bool = typer.Option(False, "--refresh-pricing"),
    watch: bool = typer.Option(False, "--watch",
        help="Re-render every 5s until Ctrl+C."),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    sessions_root = RepoLayout(Path.cwd()).sessions_dir
    since_ts = _resolve_period(since, default_back=7 * 86400)
    until_ts = _resolve_period(until, default_back=None) if until else None

    def _once() -> None:
        report = aggregate(
            sessions_root, since=since_ts, until=until_ts,
            refresh_pricing=refresh,
        )
        if json_out:
            _console.print_json(_to_json(report, limit=limit))
        else:
            _console.print(render_dashboard(report, console=_console))

    if not watch:
        _once()
        return
    try:
        while True:
            _once()
            _sleep(5.0)
    except KeyboardInterrupt:
        return


def _resolve_period(spec: Optional[str], *, default_back: Optional[int]) -> Optional[float]:
    if spec is None:
        if default_back is None:
            return None
        return _time.time() - default_back
    spec = spec.strip()
    rel = re.fullmatch(r"(\d+)([dh])", spec)
    if rel:
        n, unit = int(rel.group(1)), rel.group(2)
        secs = n * (86400 if unit == "d" else 3600)
        return _time.time() - secs
    try:
        return _dt.datetime.fromisoformat(spec).timestamp()
    except ValueError as exc:
        raise typer.BadParameter(f"unrecognised time spec: {spec!r}") from exc


@burn_app.command("compare")
def _compare_cmd(
    models: list[str] = typer.Argument(..., help=">=2 model slugs to compare"),
    since: Optional[str] = typer.Option("30d", "--since"),
    until: Optional[str] = typer.Option(None, "--until"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    if len(models) < 2:
        raise typer.BadParameter("compare needs >=2 models")
    sessions_root = RepoLayout(Path.cwd()).sessions_dir
    rep = _compare_fn(
        sessions_root, models,
        since=_resolve_period(since, default_back=30 * 86400),
        until=_resolve_period(until, default_back=None) if until else None,
    )
    if json_out:
        _console.print_json(_compare_to_json(rep))
        return
    _console.print(render_comparison(rep))


@burn_app.command("optimize")
def _optimize_cmd(
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    sessions_root = RepoLayout(Path.cwd()).sessions_dir
    findings = _optimize_fn(sessions_root)
    if json_out:
        _console.print_json(_json.dumps({
            "findings": [
                {"rule_id": f.rule_id, "severity": f.severity,
                 "title": f.title, "detail": f.detail,
                 "estimated_savings_usd":
                    str(f.estimated_savings_usd) if f.estimated_savings_usd else None,
                 "evidence": list(f.evidence)}
                for f in findings
            ],
        }, indent=2))
        return
    _console.print(render_optimize(findings))


@burn_app.command("yield")
def _yield_cmd(
    since: Optional[str] = typer.Option("30d", "--since"),
    until: Optional[str] = typer.Option(None, "--until"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    repo = Path.cwd()
    rep = _yield_report_fn(
        repo,
        since=_resolve_period(since, default_back=30 * 86400),
        until=_resolve_period(until, default_back=None) if until else None,
    )
    if json_out:
        _console.print_json(_json.dumps({
            "total_cost_usd": str(rep.total_cost_usd),
            "productive_cost_usd": str(rep.productive_cost_usd),
            "reverted_cost_usd": str(rep.reverted_cost_usd),
            "abandoned_cost_usd": str(rep.abandoned_cost_usd),
            "rows": [
                {"session_id": r.session_id, "cost_usd": str(r.cost_usd),
                 "started_at": r.started_at, "last_turn_at": r.last_turn_at,
                 "commits_during": r.commits_during,
                 "reverts_after": r.reverts_after, "outcome": r.outcome}
                for r in rep.rows
            ],
        }, indent=2))
        return
    _console.print(render_yield(rep))


def _compare_to_json(rep) -> str:
    return _json.dumps({
        "models": [
            {"model": m.model, "turns": m.turns,
             "total_cost_usd": str(m.total_cost_usd),
             "avg_cost_per_turn_usd": str(m.avg_cost_per_turn_usd),
             "avg_tokens_in": m.avg_tokens_in,
             "avg_tokens_out": m.avg_tokens_out,
             "avg_latency_ms": m.avg_latency_ms,
             "one_shot_rate": m.one_shot_rate,
             "retry_rate": m.retry_rate}
            for m in rep.models
        ],
        "winner_cost": rep.winner_cost,
        "winner_one_shot": rep.winner_one_shot,
        "winner_speed": rep.winner_speed,
    }, indent=2)


def _to_json(rep: BurnReport, *, limit: int) -> str:
    payload = {
        "period_start": rep.period_start, "period_end": rep.period_end,
        "total_cost_usd": str(rep.total_cost_usd),
        "total_tokens_in": rep.total_tokens_in,
        "total_tokens_out": rep.total_tokens_out,
        "total_turns": rep.total_turns,
        "one_shot_rate": rep.one_shot_rate,
        "retry_rate": rep.retry_rate,
        "by_model": [
            {"model": m.model, "cost_usd": str(m.cost_usd),
             "tokens_in": m.tokens_in, "tokens_out": m.tokens_out,
             "turns": m.turns, "one_shot_rate": m.one_shot_rate}
            for m in rep.by_model
        ],
        "by_category": [
            {"category": c.category, "cost_usd": str(c.cost_usd),
             "turns": c.turns}
            for c in rep.by_category
        ],
        "by_session": [
            {"session_id": s.session_id, "started_at": s.started_at,
             "last_turn_at": s.last_turn_at, "turns": s.turns,
             "cost_usd": str(s.cost_usd),
             "primary_category": s.primary_category,
             "primary_model": s.primary_model}
            for s in rep.by_session[:limit]
        ],
    }
    return _json.dumps(payload, indent=2)
