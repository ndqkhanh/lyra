"""Git correlation for ``lyra burn yield``.

A session is:
  * **productive**: >=1 commit during the session window survives to HEAD
  * **reverted**:   >=1 commit during the session window was later
                    reverted (``git revert``) or dropped (``git reset --hard``)
  * **abandoned**:  no commits during the session window

We use ``git log --since=<start> --until=<end>`` for the window and
``git log --grep="^Revert "`` to detect reverts.
"""
from __future__ import annotations

import datetime as _dt
import json
import subprocess
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Literal, Mapping, Optional

from rich.console import RenderableType
from rich.panel import Panel
from rich.table import Table


Outcome = Literal["productive", "reverted", "abandoned"]


@dataclass(frozen=True)
class YieldRow:
    session_id: str
    cost_usd: Decimal
    started_at: float
    last_turn_at: float
    commits_during: int
    reverts_after: int
    outcome: Outcome


@dataclass(frozen=True)
class YieldReport:
    rows: tuple[YieldRow, ...]
    total_cost_usd: Decimal
    productive_cost_usd: Decimal
    reverted_cost_usd: Decimal
    abandoned_cost_usd: Decimal


def yield_report(
    repo_root: Path, *,
    since: float | None = None, until: float | None = None,
) -> YieldReport:
    sessions_root = repo_root / ".lyra" / "sessions"
    if not sessions_root.exists():
        return YieldReport((), Decimal("0"), Decimal("0"),
                           Decimal("0"), Decimal("0"))

    rows: list[YieldRow] = []
    for sess_dir in sorted(sessions_root.iterdir()):
        if not sess_dir.is_dir():
            continue
        path = sess_dir / "turns.jsonl"
        if not path.exists():
            continue
        meta = _read_session(path)
        if meta is None:
            continue
        if since is not None and meta["last_turn_at"] < since:
            continue
        if until is not None and meta["started_at"] > until:
            continue
        commits = _commits_in_window(repo_root, meta["started_at"], meta["last_turn_at"])
        reverts = _reverts_referencing(repo_root, commits)
        if not commits:
            outcome: Outcome = "abandoned"
        elif reverts and reverts >= len(commits):
            outcome = "reverted"
        else:
            outcome = "productive"
        rows.append(YieldRow(
            session_id=sess_dir.name,
            cost_usd=meta["cost"], started_at=meta["started_at"],
            last_turn_at=meta["last_turn_at"],
            commits_during=len(commits), reverts_after=reverts,
            outcome=outcome,
        ))

    total = sum((r.cost_usd for r in rows), Decimal("0"))
    prod = sum((r.cost_usd for r in rows if r.outcome == "productive"), Decimal("0"))
    rev = sum((r.cost_usd for r in rows if r.outcome == "reverted"), Decimal("0"))
    aban = sum((r.cost_usd for r in rows if r.outcome == "abandoned"), Decimal("0"))
    return YieldReport(tuple(rows), total, prod, rev, aban)


def render_yield(rep: YieldReport) -> RenderableType:
    t = Table(title="yield", expand=True, show_header=True, header_style="bold cyan")
    for h in ("session", "cost", "commits", "reverts", "outcome"):
        t.add_column(h)
    for r in rep.rows:
        colour = {
            "productive": "green", "reverted": "yellow", "abandoned": "red",
        }[r.outcome]
        t.add_row(
            r.session_id, f"${r.cost_usd:.2f}",
            str(r.commits_during), str(r.reverts_after),
            f"[{colour}]{r.outcome}[/]",
        )
    foot = (
        f"productive: [green]${rep.productive_cost_usd:.2f}[/]   "
        f"reverted: [yellow]${rep.reverted_cost_usd:.2f}[/]   "
        f"abandoned: [red]${rep.abandoned_cost_usd:.2f}[/]"
    )
    return Panel(t, title="lyra burn yield", subtitle=foot)


# ---- private helpers ------------------------------------------------------

def _read_session(path: Path) -> Optional[Mapping]:
    rows = [json.loads(line) for line in path.read_text().splitlines()
            if line.strip()]
    rows = [r for r in rows if r.get("kind") == "turn"]
    if not rows:
        return None
    started = float(rows[0].get("ts") or 0.0)
    ended = float(rows[-1].get("ts") or started)
    cost = sum(
        (Decimal(str(r.get("cost_delta_usd") or 0)) for r in rows),
        Decimal("0"),
    )
    return {"started_at": started, "last_turn_at": ended, "cost": cost}


def _git(repo_root: Path, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=True, capture_output=True, text=True, timeout=10,
        ).stdout
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""


def _commits_in_window(repo: Path, start: float, end: float) -> list[str]:
    if start <= 0 or end <= 0:
        return []
    s = _dt.datetime.fromtimestamp(start).isoformat()
    e = _dt.datetime.fromtimestamp(end + 60).isoformat()
    out = _git(repo, "log", "--since", s, "--until", e, "--format=%H")
    return [c for c in out.splitlines() if c]


def _reverts_referencing(repo: Path, commits: Iterable[str]) -> int:
    if not commits:
        return 0
    out = _git(repo, "log", "--grep", "^Revert ", "--format=%H %s")
    n = 0
    for c in commits:
        short = c[:7]
        if any(short in line for line in out.splitlines()):
            n += 1
    return n
