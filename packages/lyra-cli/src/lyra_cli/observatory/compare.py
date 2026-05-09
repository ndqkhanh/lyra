"""``lyra burn compare`` - side-by-side model metrics."""
from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Optional

from rich.console import RenderableType
from rich.panel import Panel
from rich.table import Table

from .classifier import classify_turn, Classification
from .pricing import cost_for_turn


@dataclass(frozen=True)
class ModelMetrics:
    model: str
    turns: int
    total_cost_usd: Decimal
    avg_cost_per_turn_usd: Decimal
    avg_tokens_in: float
    avg_tokens_out: float
    avg_latency_ms: float
    one_shot_rate: float
    retry_rate: float


@dataclass(frozen=True)
class ComparisonReport:
    models: tuple[ModelMetrics, ...]
    winner_cost: Optional[str]
    winner_one_shot: Optional[str]
    winner_speed: Optional[str]


def compare(
    sessions_root: Path, model_slugs: list[str], *,
    since: float | None = None, until: float | None = None,
) -> ComparisonReport:
    if not sessions_root.exists():
        return ComparisonReport(
            tuple(ModelMetrics(m, 0, Decimal("0"), Decimal("0"),
                               0.0, 0.0, 0.0, 1.0, 0.0)
                  for m in model_slugs), None, None, None,
        )

    counters: dict[str, dict] = {
        m: {"cost": Decimal("0"), "tin": 0, "tout": 0, "lat": 0.0,
            "n": 0, "first_try": 0, "codedebug": 0}
        for m in model_slugs
    }

    for sess_dir in sorted(sessions_root.iterdir()):
        if not sess_dir.is_dir():
            continue
        prev: Classification | None = None
        path = sess_dir / "turns.jsonl"
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("kind") != "turn":
                continue
            ts = row.get("ts")
            if since is not None and ts is not None and ts < since:
                continue
            if until is not None and ts is not None and ts > until:
                continue
            cls = classify_turn(row, prev=prev)
            prev = cls
            m = row.get("model")
            if m not in counters:
                continue
            c = counters[m]
            cost = row.get("cost_delta_usd")
            if cost is not None:
                c["cost"] += Decimal(str(cost))
            else:
                rec = cost_for_turn(row)
                if rec is not None:
                    c["cost"] += rec
            c["tin"] += int(row.get("tokens_in") or 0)
            c["tout"] += int(row.get("tokens_out") or 0)
            c["lat"] += float(row.get("latency_ms") or 0.0)
            c["n"] += 1
            if cls.category in ("coding", "debugging"):
                c["codedebug"] += 1
                if cls.retry_streak == 1:
                    c["first_try"] += 1

    models = tuple(
        ModelMetrics(
            model=m,
            turns=c["n"],
            total_cost_usd=c["cost"],
            avg_cost_per_turn_usd=(c["cost"] / c["n"]) if c["n"] else Decimal("0"),
            avg_tokens_in=(c["tin"] / c["n"]) if c["n"] else 0.0,
            avg_tokens_out=(c["tout"] / c["n"]) if c["n"] else 0.0,
            avg_latency_ms=(c["lat"] / c["n"]) if c["n"] else 0.0,
            one_shot_rate=(c["first_try"] / c["codedebug"]) if c["codedebug"] else 1.0,
            retry_rate=1.0 - (c["first_try"] / c["codedebug"]
                              if c["codedebug"] else 1.0),
        )
        for m, c in counters.items()
    )
    nonzero = [m for m in models if m.turns > 0]
    if not nonzero:
        return ComparisonReport(models, None, None, None)
    winner_cost = min(nonzero, key=lambda m: m.avg_cost_per_turn_usd).model
    winner_one_shot = max(nonzero, key=lambda m: m.one_shot_rate).model
    winner_speed = min(nonzero, key=lambda m: m.avg_latency_ms).model
    return ComparisonReport(models, winner_cost, winner_one_shot, winner_speed)


def render_comparison(rep: ComparisonReport) -> RenderableType:
    t = Table(title="model comparison", expand=True, show_header=True,
              header_style="bold cyan")
    t.add_column("model")
    t.add_column("turns")
    t.add_column("$/turn")
    t.add_column("avg in")
    t.add_column("avg out")
    t.add_column("avg latency")
    t.add_column("1-shot")
    for m in rep.models:
        t.add_row(
            m.model, str(m.turns),
            f"${m.avg_cost_per_turn_usd:.4f}",
            f"{m.avg_tokens_in:.0f}", f"{m.avg_tokens_out:.0f}",
            f"{m.avg_latency_ms:.0f} ms",
            f"{m.one_shot_rate*100:.0f}%",
        )
    foot = (
        f"cheapest: [bold]{rep.winner_cost or '-'}[/]   "
        f"highest 1-shot: [bold]{rep.winner_one_shot or '-'}[/]   "
        f"fastest: [bold]{rep.winner_speed or '-'}[/]"
    )
    return Panel(t, title="lyra burn compare", subtitle=foot)
