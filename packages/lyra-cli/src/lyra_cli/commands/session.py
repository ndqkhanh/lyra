"""``lyra session list|show|resume|continue|delete`` — session bookkeeping CLI.

v3.2.0 (Phase L) ground-up rewrite. Pre-v3.2 ``list`` only returned the raw
directory names and ``show`` was a one-line stub that printed the path. Now
both commands inspect the on-disk JSONL transcript that
:class:`lyra_cli.interactive.session.InteractiveSession` writes for every
REPL run, which means ``lyra session …`` is finally useful for inspecting
sessions from a separate shell — the Claude-Code-style "consume your past
sessions outside the REPL" UX the user asked for.

Storage layout (matches Claude Code / claw-code):

    <repo>/.lyra/sessions/<session_id>/
        turns.jsonl           # one JSON event per turn (kind=turn|chat)
        meta.json             # display name, created_at, forked_from
"""
from __future__ import annotations

import datetime as _dt
import json as _json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from ..paths import RepoLayout

session_app = typer.Typer(
    name="session",
    help=(
        "List and inspect Lyra sessions stored under ``.lyra/sessions/``. "
        "Use ``lyra --resume <id>`` (or the bare ``lyra --continue``) to "
        "actually attach the REPL to a session."
    ),
    no_args_is_help=True,
)

_console = Console()


# ----------------------------------------------------------------------
# small helpers (kept here so the test surface stays narrow)
# ----------------------------------------------------------------------


@dataclass
class _SessionSummary:
    session_id: str
    name: Optional[str]
    msgs: int
    turns: int
    modified: float
    mode: Optional[str]
    model: Optional[str]
    cost_usd: float
    tokens: int
    forked_from: Optional[str]
    path: Path


def _humanize_age(seconds: float) -> str:
    """Compact age string ("12s ago", "4m ago", "3h ago", "2d ago")."""
    if seconds < 0:
        seconds = 0.0
    if seconds < 60:
        return f"{int(seconds)}s ago"
    if seconds < 3600:
        return f"{int(seconds / 60)}m ago"
    if seconds < 86_400:
        return f"{int(seconds / 3600)}h ago"
    return f"{int(seconds / 86_400)}d ago"


def _read_meta(session_dir: Path) -> dict:
    meta_path = session_dir / "meta.json"
    if not meta_path.is_file():
        return {}
    try:
        return _json.loads(meta_path.read_text(encoding="utf-8"))
    except (_json.JSONDecodeError, OSError):
        return {}


def _summarize_session(session_dir: Path) -> Optional[_SessionSummary]:
    """Walk the JSONL once and roll up everything ``list`` / ``show`` need.

    Returns ``None`` when there's no ``turns.jsonl`` (the directory was
    created but never written — common when the user typed `/exit`
    immediately on a fresh REPL).
    """
    log = session_dir / "turns.jsonl"
    if not log.is_file():
        return None
    meta = _read_meta(session_dir)
    msgs = 0
    turns = 0
    last_mode: Optional[str] = None
    last_model: Optional[str] = None
    cost_usd = 0.0
    tokens = 0
    try:
        for raw in log.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            try:
                row = _json.loads(raw)
            except _json.JSONDecodeError:
                continue
            kind = row.get("kind") or "turn"
            if kind == "chat":
                msgs += 1
                if isinstance(row.get("model"), str):
                    last_model = row["model"]
                continue
            turns += 1
            if isinstance(row.get("mode"), str):
                last_mode = row["mode"]
            if isinstance(row.get("model"), str):
                last_model = row["model"]
            if isinstance(row.get("cost_usd"), (int, float)):
                cost_usd = max(cost_usd, float(row["cost_usd"]))
            if isinstance(row.get("tokens_used"), (int, float)):
                tokens = max(tokens, int(row["tokens_used"]))
    except OSError:
        return None
    try:
        modified = log.stat().st_mtime
    except OSError:
        modified = 0.0
    return _SessionSummary(
        session_id=session_dir.name,
        name=meta.get("name") if isinstance(meta.get("name"), str) else None,
        msgs=msgs,
        turns=turns,
        modified=modified,
        mode=last_mode,
        model=last_model,
        cost_usd=cost_usd,
        tokens=tokens,
        forked_from=(
            meta.get("forked_from")
            if isinstance(meta.get("forked_from"), str)
            else None
        ),
        path=session_dir,
    )


def _collect(layout: RepoLayout) -> list[_SessionSummary]:
    """Return every summarisable session, recency-sorted (newest first)."""
    if not layout.sessions_dir.is_dir():
        return []
    out: list[_SessionSummary] = []
    for entry in layout.sessions_dir.iterdir():
        if not entry.is_dir():
            continue
        summary = _summarize_session(entry)
        if summary is not None:
            out.append(summary)
    out.sort(key=lambda s: s.modified, reverse=True)
    return out


# ----------------------------------------------------------------------
# CLI commands
# ----------------------------------------------------------------------


@session_app.command("list")
def list_sessions(
    repo_root: Path = typer.Option(
        Path.cwd(), "--repo-root", "-C", help="Repo to inspect."
    ),
    limit: int = typer.Option(
        20,
        "--limit",
        "-n",
        help="Show at most N sessions (default 20). Use ``--limit 0`` for all.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit a machine-readable JSON array (one object per session).",
    ),
) -> None:
    """List sessions under ``<repo>/.lyra/sessions/`` (newest first).

    Each row shows the session id, status (●current / ○saved — current
    is the most recent), msg / turn count, recency, last mode and
    model, total cost, and a 'forked-from' hint when the session was
    spawned via ``/fork``. Mirrors the ``claw session list`` UX so a
    user familiar with Claude Code feels at home.
    """
    layout = RepoLayout(repo_root=repo_root.resolve())
    summaries = _collect(layout)

    if json_out:
        payload = [
            {
                "session_id": s.session_id,
                "name": s.name,
                "msgs": s.msgs,
                "turns": s.turns,
                "modified_unix": s.modified,
                "modified_iso": _dt.datetime.fromtimestamp(s.modified).isoformat(
                    timespec="seconds"
                ),
                "mode": s.mode,
                "model": s.model,
                "cost_usd": round(s.cost_usd, 6),
                "tokens": s.tokens,
                "forked_from": s.forked_from,
                "path": str(s.path),
            }
            for s in summaries
        ]
        _console.print_json(_json.dumps(payload))
        return

    if not summaries:
        _console.print(
            f"[dim]no sessions yet under {layout.sessions_dir}.[/]\n"
            f"start one with [cyan]lyra[/] (or [cyan]lyra --continue[/])."
        )
        return

    table = Table(
        show_header=True,
        header_style="bold #00E5FF",
        box=None,
        pad_edge=False,
        padding=(0, 1),
    )
    table.add_column("", style="#FFC857", no_wrap=True, width=2)
    table.add_column("session id", style="bold #00E5FF", no_wrap=True)
    table.add_column("msgs", justify="right", style="#A1A7B3")
    table.add_column("modified", style="#A1A7B3", no_wrap=True)
    table.add_column("mode", style="#FF2D95", no_wrap=True)
    table.add_column("model", style="#7CFFB2", no_wrap=True)
    table.add_column("cost", justify="right", style="#A1A7B3")
    table.add_column("note", style="#6B7280", no_wrap=True)

    now = _dt.datetime.now().timestamp()
    rows = summaries if limit <= 0 else summaries[:limit]
    for i, s in enumerate(rows):
        marker = "●" if i == 0 else "○"
        note_bits: list[str] = []
        if s.name:
            note_bits.append(s.name)
        if s.forked_from:
            note_bits.append(f"fork-of={s.forked_from}")
        table.add_row(
            marker,
            s.session_id,
            str(s.msgs) if s.msgs else "—",
            _humanize_age(now - s.modified),
            s.mode or "—",
            s.model or "—",
            f"${s.cost_usd:.4f}" if s.cost_usd > 0 else "—",
            "  ".join(note_bits) or "—",
        )

    _console.print()
    _console.print(
        Text.assemble(
            (" sessions dir  ", "#6B7280"),
            (str(layout.sessions_dir), "bright_white"),
        )
    )
    _console.print(table)
    if limit > 0 and len(summaries) > limit:
        _console.print(
            f"[dim]… and {len(summaries) - limit} older "
            f"sessions; pass --limit 0 to see all.[/]"
        )
    _console.print(
        "[dim]resume with [/]"
        "[cyan]lyra --resume <id>[/]"
        "[dim] or [/]"
        "[cyan]lyra --continue[/]"
        "[dim] (latest).[/]"
    )


@session_app.command("show")
def show_session(
    session_id: str = typer.Argument(
        ...,
        help=(
            "Session id (full or unique prefix). Pass ``latest`` to show "
            "the most recently modified session in this repo."
        ),
    ),
    repo_root: Path = typer.Option(
        Path.cwd(), "--repo-root", "-C", help="Repo to inspect."
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help=(
            "Print the per-turn breakdown (mode, model, tokens, cost, "
            "latency, timestamp). Without this flag only the manifest "
            "header is shown."
        ),
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit the manifest as JSON (machine-readable).",
    ),
) -> None:
    """Print the manifest of a session.

    v3.2.0 (Phase L): the long-promised real implementation. Resolves
    ``latest`` or a unique prefix the same way ``lyra --resume`` does,
    then dumps the session header (id, name, repo, dates, mode, model,
    turns, msgs, cost, tokens, fork lineage). With ``--verbose`` it
    also walks the JSONL and prints one row per turn — useful for
    "what did I run yesterday and what did it cost?".
    """
    layout = RepoLayout(repo_root=repo_root.resolve())
    summaries = _collect(layout)
    by_id = {s.session_id: s for s in summaries}

    # Resolve "latest" / unique-prefix the same way the slash command
    # does so the CLI feels symmetric.
    target: Optional[str]
    ref = session_id.strip().lower()
    if ref in ("latest", "last", "recent"):
        target = summaries[0].session_id if summaries else None
    elif session_id in by_id:
        target = session_id
    else:
        prefix_matches = [sid for sid in by_id if sid.startswith(session_id)]
        target = prefix_matches[0] if len(prefix_matches) == 1 else None

    if target is None:
        _console.print(f"[red]unknown session[/red]: {session_id!r}")
        if summaries:
            _console.print(
                "[dim]available:[/] "
                + ", ".join(s.session_id for s in summaries[:10])
                + (" …" if len(summaries) > 10 else "")
            )
        raise typer.Exit(code=2)

    summary = by_id[target]
    rows = _read_jsonl(summary.path / "turns.jsonl")
    created_at = _read_meta(summary.path).get("created_at")

    manifest = {
        "session_id": summary.session_id,
        "name": summary.name,
        "repo_root": str(layout.repo_root),
        "path": str(summary.path),
        "created_at": created_at,
        "modified_at": _dt.datetime.fromtimestamp(summary.modified).isoformat(
            timespec="seconds"
        ),
        "turns": summary.turns,
        "msgs": summary.msgs,
        "mode": summary.mode,
        "model": summary.model,
        "cost_usd": round(summary.cost_usd, 6),
        "tokens": summary.tokens,
        "forked_from": summary.forked_from,
    }
    if json_out:
        if verbose:
            manifest["events"] = rows
        _console.print_json(_json.dumps(manifest))
        return

    _print_manifest(manifest)
    if verbose:
        _print_verbose_events(rows)


@session_app.command("delete")
def delete_session(
    session_id: str = typer.Argument(
        ...,
        help="Session id (full or unique prefix) to delete.",
    ),
    repo_root: Path = typer.Option(
        Path.cwd(), "--repo-root", "-C", help="Repo to inspect."
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip the y/n confirmation prompt.",
    ),
) -> None:
    """Delete a session's directory.

    Refuses if the id doesn't resolve to exactly one session. The
    deletion is irreversible — there's no trash bin — so we confirm
    interactively unless ``--yes`` is passed.
    """
    import shutil

    layout = RepoLayout(repo_root=repo_root.resolve())
    summaries = _collect(layout)
    by_id = {s.session_id: s for s in summaries}
    if session_id in by_id:
        target = session_id
    else:
        matches = [sid for sid in by_id if sid.startswith(session_id)]
        if len(matches) != 1:
            _console.print(
                f"[red]ambiguous or unknown session[/red]: {session_id!r}"
            )
            raise typer.Exit(code=2)
        target = matches[0]

    summary = by_id[target]
    if not yes:
        ok = typer.confirm(
            f"delete {summary.session_id} ({summary.turns} turns, "
            f"{_humanize_age(_dt.datetime.now().timestamp() - summary.modified)})?",
            default=False,
        )
        if not ok:
            _console.print("[dim]cancelled[/]")
            raise typer.Exit(code=1)

    try:
        shutil.rmtree(summary.path)
    except OSError as exc:
        _console.print(f"[red]delete failed[/red]: {exc}")
        raise typer.Exit(code=1)
    _console.print(f"[green]deleted[/] {summary.session_id}")


# ----------------------------------------------------------------------
# rendering helpers
# ----------------------------------------------------------------------


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out: list[dict] = []
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            try:
                out.append(_json.loads(raw))
            except _json.JSONDecodeError:
                continue
    except OSError:
        return []
    return out


def _print_manifest(m: dict) -> None:
    _console.print()
    _console.print(
        Text.assemble(
            (" session ", "#6B7280"),
            (m["session_id"], "bold #00E5FF"),
            ("  ", ""),
            (m.get("name") or "", "italic #A1A7B3"),
        )
    )
    table = Table(
        show_header=False,
        box=None,
        pad_edge=False,
        padding=(0, 2),
    )
    table.add_column(style="#6B7280", no_wrap=True)
    table.add_column(style="bright_white")
    table.add_row("repo", m["repo_root"])
    table.add_row("path", m["path"])
    if m.get("created_at"):
        table.add_row("created", m["created_at"])
    table.add_row("modified", m["modified_at"])
    table.add_row("mode", m.get("mode") or "—")
    table.add_row("model", m.get("model") or "—")
    table.add_row("turns", str(m["turns"]))
    table.add_row("msgs", str(m["msgs"]))
    table.add_row("cost", f"${m['cost_usd']:.6f}")
    table.add_row("tokens", f"{m['tokens']:,}")
    if m.get("forked_from"):
        table.add_row("forked from", m["forked_from"])
    _console.print(table)


def _print_verbose_events(rows: list[dict]) -> None:
    if not rows:
        return
    _console.print()
    _console.print("[bold #00E5FF]turn-by-turn breakdown[/]")
    table = Table(
        show_header=True,
        header_style="bold #6B7280",
        box=None,
        pad_edge=False,
        padding=(0, 1),
    )
    table.add_column("#", justify="right", style="#6B7280", no_wrap=True)
    table.add_column("kind", style="#FFC857", no_wrap=True)
    table.add_column("mode", style="#FF2D95", no_wrap=True)
    table.add_column("model", style="#7CFFB2", no_wrap=True)
    table.add_column("tok in", justify="right", style="#A1A7B3")
    table.add_column("tok out", justify="right", style="#A1A7B3")
    table.add_column("cost Δ", justify="right", style="#A1A7B3")
    table.add_column("ms", justify="right", style="#A1A7B3")
    table.add_column("ts", style="#6B7280", no_wrap=True)
    table.add_column("preview", style="bright_white")

    for i, row in enumerate(rows, start=1):
        kind = row.get("kind") or "turn"
        mode = row.get("mode") or ""
        model = row.get("model") or ""
        tin = row.get("tokens_in")
        tout = row.get("tokens_out")
        cdelta = row.get("cost_delta_usd")
        ms = row.get("latency_ms")
        ts = row.get("ts")
        ts_str = ""
        if isinstance(ts, (int, float)):
            ts_str = _dt.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
        if kind == "chat":
            preview = (row.get("user") or "").splitlines()[0][:60]
        else:
            preview = (row.get("line") or "").splitlines()[0][:60]
        table.add_row(
            str(i),
            kind,
            mode if kind != "chat" else "—",
            model or "—",
            f"{tin:,}" if isinstance(tin, (int, float)) else "—",
            f"{tout:,}" if isinstance(tout, (int, float)) else "—",
            f"${cdelta:.6f}" if isinstance(cdelta, (int, float)) else "—",
            f"{ms:.0f}" if isinstance(ms, (int, float)) else "—",
            ts_str or "—",
            preview,
        )
    _console.print(table)
