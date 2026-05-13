"""``lyra ps`` and ``lyra events`` — postmortem process inspection (Phase 2).

Both commands require no live connection — they read from files written
by the EventBus ``ProcessStateWriter`` and the HIR emitter.

    lyra ps                         — current process state table
    lyra ps --json                  — machine-readable JSON
    lyra events                     — tail recent events across all sessions
    lyra events --session SESSION   — filter to one session
    lyra events --type ToolCall     — filter by event kind substring
    lyra events --tail N            — last N lines (default 20)
    lyra events --follow            — stream new events as they arrive

Research grounding: ccusage (~9.7k stars), claudelytics 9-tab taxonomy,
``claude_code_agent_farm`` JSON state pattern, agenttrace log record schema.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.table import Table

_console = Console()

ps_app = typer.Typer(
    name="ps",
    help="Inspect current process state and event log (no live connection needed).",
    no_args_is_help=False,
    invoke_without_command=True,
)

# ---------------------------------------------------------------------------
# lyra ps
# ---------------------------------------------------------------------------

_STATUS_COLORS = {
    "running": "green",
    "verifying": "yellow",
    "stopped": "dim",
    "done": "dim",
    "failed": "red",
    "killed": "red",
}


def _color_status(status: str) -> str:
    color = _STATUS_COLORS.get(status, "white")
    return f"[{color}]{status}[/{color}]"


@ps_app.callback(invoke_without_command=True)
def ps_command(
    ctx: typer.Context,
    repo_root: Path = typer.Option(Path.cwd(), "--repo-root", "-C", help="Repo root."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of a table."),
) -> None:
    """Show the current process state table from .lyra/process_state.json."""
    if ctx.invoked_subcommand is not None:
        return

    state_path = repo_root / ".lyra" / "process_state.json"

    if not state_path.exists():
        # Fall back: scan .lyra/state/ directories for any state files
        states = _scan_state_dirs(repo_root / ".lyra" / "state")
    else:
        try:
            data = json.loads(state_path.read_text())
            states = [data]
        except (json.JSONDecodeError, OSError):
            states = []

    if not states:
        _console.print("[dim]No process state found. Run a Lyra session first.[/dim]")
        raise typer.Exit(0)

    if json_out:
        typer.echo(json.dumps(states if len(states) > 1 else states[0], indent=2))
        return

    table = Table(title="Lyra Processes", box=box.ROUNDED)
    table.add_column("Session", style="dim", no_wrap=True, max_width=20)
    table.add_column("Status", width=10)
    table.add_column("Role", width=12)
    table.add_column("Mode", width=8)
    table.add_column("Step", justify="right", width=8)
    table.add_column("Tokens in", justify="right", width=10)
    table.add_column("Cost $", justify="right", width=8)
    table.add_column("Last tool", overflow="fold")

    for s in states:
        step_str = (
            f"{s.get('current_step', 0)}/{s.get('max_steps', '?')}"
            if s.get("max_steps")
            else str(s.get("current_step", 0))
        )
        last = s.get("last_tool") or {}
        last_tool = last.get("name", "—")
        if last_tool != "—":
            t_status = last.get("status", "")
            t_color = "red" if t_status == "error" else ("yellow" if t_status == "blocked" else "")
            last_tool = f"[{t_color}]{last_tool}[/{t_color}]" if t_color else last_tool

        table.add_row(
            str(s.get("session_id", ""))[:20],
            _color_status(s.get("status", "unknown")),
            s.get("agent_role", "—") or "—",
            s.get("permission_mode", "—") or "—",
            step_str,
            f"{s.get('token_in', 0):,}",
            f"{s.get('cost_usd_so_far', 0.0):.4f}",
            last_tool,
        )

    _console.print(table)


def _scan_state_dirs(state_dir: Path) -> list[dict]:
    """Scan .lyra/state/ for any process_state.json files."""
    states = []
    if not state_dir.exists():
        return states
    for p in state_dir.glob("*/process_state.json"):
        try:
            states.append(json.loads(p.read_text()))
        except (json.JSONDecodeError, OSError):
            pass
    return states


# ---------------------------------------------------------------------------
# lyra events  (subcommand)
# ---------------------------------------------------------------------------


@ps_app.command("events")
def events_command(
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Filter by session ID."),
    event_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Filter by event kind substring (e.g. 'Tool')."
    ),
    tail: int = typer.Option(20, "--tail", "-n", help="Show last N events."),
    follow: bool = typer.Option(False, "--follow", "-f", help="Stream new events as they arrive."),
    repo_root: Path = typer.Option(Path.cwd(), "--repo-root", "-C"),
) -> None:
    """Show recent events from .lyra/<session>/events.jsonl."""
    lyra_dir = repo_root / ".lyra"

    # Collect JSONL files to read
    jsonl_files = _find_event_files(lyra_dir, session)

    if not jsonl_files:
        _console.print("[dim]No event files found. Run a Lyra session first.[/dim]")
        raise typer.Exit(0)

    if follow:
        _follow_events(jsonl_files, event_type)
    else:
        rows = _collect_events(jsonl_files, event_type, tail)
        _render_events_table(rows)


def _find_event_files(lyra_dir: Path, session: str | None) -> list[Path]:
    """Find all events.jsonl files under .lyra/."""
    files: list[Path] = []
    if session:
        # Try .lyra/<session>/events.jsonl
        p = lyra_dir / session / "events.jsonl"
        if p.exists():
            files.append(p)
        # Also try .lyra/sessions/<session>/events.jsonl
        p2 = lyra_dir / "sessions" / session / "events.jsonl"
        if p2.exists():
            files.append(p2)
    else:
        files.extend(lyra_dir.rglob("events.jsonl"))
    return sorted(files)


def _parse_line(line: str) -> dict | None:
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def _matches_filter(record: dict, event_type: str | None) -> bool:
    if event_type is None:
        return True
    kind = str(record.get("kind", record.get("event_type", "")))
    return event_type.lower() in kind.lower()


def _collect_events(
    files: list[Path], event_type: str | None, tail: int
) -> list[dict]:
    rows: list[dict] = []
    for f in files:
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            record = _parse_line(line)
            if record and _matches_filter(record, event_type):
                rows.append(record)
    return rows[-tail:]


def _render_events_table(rows: list[dict]) -> None:
    if not rows:
        _console.print("[dim]No events matched.[/dim]")
        return
    table = Table(title=f"Events (last {len(rows)})", box=box.SIMPLE)
    table.add_column("Time", style="dim", width=12, no_wrap=True)
    table.add_column("Kind", width=28, no_wrap=True)
    table.add_column("Session", style="dim", width=16, no_wrap=True)
    table.add_column("Detail", overflow="fold")

    for r in rows:
        ts = str(r.get("ts", r.get("timestamp", "")))
        ts_short = ts[11:19] if len(ts) >= 19 else ts  # HH:MM:SS
        kind = str(r.get("kind", r.get("event_type", "—")))
        session_id = str(r.get("session_id", ""))[:16]
        # Build a short detail string from known fields
        detail_parts = []
        for key in ("tool", "tool_name", "model", "agent_id", "job_name", "reason", "decision"):
            val = r.get(key)
            if val:
                detail_parts.append(f"{key}={val}")
        detail = "  ".join(detail_parts) or "—"
        table.add_row(ts_short, kind, session_id, detail)

    _console.print(table)


def _follow_events(files: list[Path], event_type: str | None) -> None:
    """tail -f style: poll files and print new lines as they appear."""
    # Track file sizes so we only read new bytes
    offsets: dict[Path, int] = {}
    for f in files:
        try:
            offsets[f] = f.stat().st_size
        except OSError:
            offsets[f] = 0

    _console.print("[dim]Following events… (Ctrl-C to stop)[/dim]")
    try:
        while True:
            for f in files:
                try:
                    size = f.stat().st_size
                except OSError:
                    continue
                if size > offsets[f]:
                    with f.open(encoding="utf-8", errors="replace") as fh:
                        fh.seek(offsets[f])
                        new_lines = fh.readlines()
                    offsets[f] = size
                    for line in new_lines:
                        record = _parse_line(line)
                        if record and _matches_filter(record, event_type):
                            ts = str(record.get("ts", record.get("timestamp", "")))
                            ts_short = ts[11:19] if len(ts) >= 19 else ts
                            kind = str(record.get("kind", record.get("event_type", "—")))
                            _console.print(f"[dim]{ts_short}[/dim]  {kind}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
