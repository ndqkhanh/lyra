"""``lyra trace`` and ``lyra cost`` — call-trace and cost reporting (Phase 5).

    lyra trace                          — timeline of events across all sessions
    lyra trace --session ID             — filter to one session
    lyra trace --depth N                — show N indentation levels for nesting
    lyra cost                           — cost/token breakdown by session + model
    lyra cost --session ID              — cost for one session
    lyra cost --json                    — machine-readable JSON

Research grounding: agenttrace log record schema, ccusage cost breakdown,
claudelytics 9-tab taxonomy.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

_console = Console()

trace_app = typer.Typer(
    name="trace",
    help="Call-trace timeline and cost breakdown for Lyra sessions.",
    no_args_is_help=False,
    invoke_without_command=True,
)

# ---------------------------------------------------------------------------
# lyra trace
# ---------------------------------------------------------------------------

_TRACE_INDENT = "  "

_KIND_SYMBOLS = {
    "llm": "🤖",
    "tool": "⚙",
    "subagent": "👾",
    "blocked": "🚫",
    "cron": "⏰",
    "stop": "⛔",
    "permission": "🔑",
}


@trace_app.callback(invoke_without_command=True)
def trace_command(
    ctx: typer.Context,
    session: Optional[str] = typer.Option(None, "--session", "-s"),
    tail: int = typer.Option(40, "--tail", "-n", help="Last N events."),
    repo_root: Path = typer.Option(Path.cwd(), "--repo-root", "-C"),
) -> None:
    """Show a call-trace timeline of agent events."""
    if ctx.invoked_subcommand is not None:
        return

    lyra_dir = repo_root / ".lyra"
    files = _find_jsonl(lyra_dir, session)

    if not files:
        _console.print("[dim]No event files found. Run a Lyra session first.[/dim]")
        raise typer.Exit(0)

    rows = _load_events(files, tail)
    _render_trace(rows)


def _find_jsonl(lyra_dir: Path, session: str | None) -> list[Path]:
    if session:
        candidates = [
            lyra_dir / session / "events.jsonl",
            lyra_dir / "sessions" / session / "events.jsonl",
        ]
        return [p for p in candidates if p.exists()]
    return sorted(lyra_dir.rglob("events.jsonl"))


def _load_events(files: list[Path], tail: int) -> list[dict]:
    rows: list[dict] = []
    for f in files:
        try:
            for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        except OSError:
            pass
    return rows[-tail:]


def _classify_kind(record: dict) -> str:
    kind = str(record.get("kind", record.get("event_type", ""))).lower()
    if "llm" in kind or "model" in kind:
        return "llm"
    if "tool" in kind:
        return "blocked" if "block" in kind else "tool"
    if "agent" in kind:
        return "subagent"
    if "cron" in kind:
        return "cron"
    if "stop" in kind:
        return "stop"
    if "permission" in kind:
        return "permission"
    return "tool"


def _render_trace(rows: list[dict]) -> None:
    table = Table(
        title=f"Lyra Trace (last {len(rows)} events)",
        box=box.SIMPLE,
        expand=True,
    )
    table.add_column("Time", style="dim", width=9, no_wrap=True)
    table.add_column("Session", style="dim", width=12, no_wrap=True)
    table.add_column("Event", overflow="fold")
    table.add_column("Detail", overflow="fold")

    for r in rows:
        ts = str(r.get("ts", r.get("timestamp", "")))
        ts_short = ts[11:19] if len(ts) >= 19 else ts
        session = str(r.get("session_id", ""))[:12]
        kind = _classify_kind(r)
        symbol = _KIND_SYMBOLS.get(kind, "·")
        event_name = str(r.get("kind", r.get("event_type", "—")))

        detail_parts = []
        for key in ("tool_name", "tool", "model", "agent_id", "agent_role",
                     "job_name", "reason", "decision", "status"):
            val = r.get(key)
            if val:
                detail_parts.append(f"{key}={val}")
        detail = "  ".join(detail_parts) or "—"

        # Indent subagents one level
        indent = _TRACE_INDENT if kind == "subagent" else ""
        event_text = Text(f"{indent}{symbol} {event_name}")

        table.add_row(ts_short, session, event_text, detail)

    _console.print(table)


# ---------------------------------------------------------------------------
# lyra cost  (subcommand)
# ---------------------------------------------------------------------------


@trace_app.command("cost")
def cost_command(
    session: Optional[str] = typer.Option(None, "--session", "-s",
                                           help="Filter to one session."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON."),
    repo_root: Path = typer.Option(Path.cwd(), "--repo-root", "-C"),
) -> None:
    """Show token and cost breakdown by session."""
    lyra_dir = repo_root / ".lyra"
    files = _find_jsonl(lyra_dir, session)

    if not files:
        _console.print("[dim]No event files found. Run a Lyra session first.[/dim]")
        raise typer.Exit(0)

    buckets = _aggregate_cost(files)

    if json_out:
        typer.echo(json.dumps(buckets, indent=2))
        return

    _render_cost_table(buckets)


def _aggregate_cost(files: list[Path]) -> list[dict]:
    """Aggregate token usage from LLMCallFinished events per session+model."""
    sessions: dict[str, dict] = {}

    for f in files:
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue

            kind = str(r.get("kind", r.get("event_type", ""))).lower()
            if "llmcallfinished" not in kind and "llm.finished" not in kind:
                continue

            sid = str(r.get("session_id", "unknown"))
            model = str(r.get("model", "—"))
            key = f"{sid}::{model}"

            bucket = sessions.setdefault(key, {
                "session_id": sid,
                "model": model,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_tokens": 0,
                "calls": 0,
                "duration_ms": 0.0,
            })
            bucket["input_tokens"] += int(r.get("input_tokens", 0))
            bucket["output_tokens"] += int(r.get("output_tokens", 0))
            bucket["cache_read_tokens"] += int(r.get("cache_read_tokens", 0))
            bucket["calls"] += 1
            bucket["duration_ms"] += float(r.get("duration_ms", 0.0))

    return list(sessions.values())


def _render_cost_table(buckets: list[dict]) -> None:
    if not buckets:
        _console.print("[dim]No LLM call records found in event files.[/dim]")
        return

    table = Table(title="Lyra Cost Breakdown", box=box.ROUNDED)
    table.add_column("Session", style="dim", no_wrap=True, max_width=20)
    table.add_column("Model", width=16)
    table.add_column("Calls", justify="right", width=6)
    table.add_column("Tok in", justify="right", width=9)
    table.add_column("Tok out", justify="right", width=9)
    table.add_column("Cache hit", justify="right", width=9)
    table.add_column("Cache%", justify="right", width=7)
    table.add_column("Avg ms", justify="right", width=8)

    for b in buckets:
        total_in = b["input_tokens"]
        cache = b["cache_read_tokens"]
        cache_pct = cache / max(1, total_in)
        avg_ms = b["duration_ms"] / max(1, b["calls"])
        table.add_row(
            b["session_id"][:20],
            b["model"],
            str(b["calls"]),
            f"{total_in:,}",
            f"{b['output_tokens']:,}",
            f"{cache:,}",
            f"{cache_pct:.0%}",
            f"{avg_ms:.0f}",
        )

    _console.print(table)
