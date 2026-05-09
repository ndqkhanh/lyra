"""Period rollups across all session JSONL transcripts.

Walks ``<sessions_root>/*/turns.jsonl``, classifies each turn,
re-prices when ``cost_delta_usd`` is missing, and emits a
:class:`BurnReport` with breakdowns by model, category, and session.

Memory profile: one streaming pass per session. We never load all turns
of all sessions at once - even at 10k turns/session x 100 sessions the
RSS stays under 50 MB because we accumulate counters, not rows.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterator, Mapping

from .classifier import (
    Classification, TaskCategory, classify_turn,
)
from .pricing import cost_for_turn


@dataclass(frozen=True)
class ModelBreakdown:
    model: str
    cost_usd: Decimal
    tokens_in: int
    tokens_out: int
    turns: int
    one_shot_rate: float


@dataclass(frozen=True)
class CategoryBreakdown:
    category: TaskCategory
    cost_usd: Decimal
    turns: int


@dataclass(frozen=True)
class SessionRow:
    session_id: str
    started_at: float
    last_turn_at: float
    turns: int
    cost_usd: Decimal
    primary_category: TaskCategory
    primary_model: str


@dataclass(frozen=True)
class BurnReport:
    period_start: float
    period_end: float
    total_cost_usd: Decimal
    total_tokens_in: int
    total_tokens_out: int
    total_turns: int
    by_model: tuple[ModelBreakdown, ...]
    by_category: tuple[CategoryBreakdown, ...]
    by_session: tuple[SessionRow, ...]
    one_shot_rate: float
    retry_rate: float


def aggregate(
    sessions_root: Path,
    *,
    since: float | None = None,
    until: float | None = None,
    refresh_pricing: bool = False,
) -> BurnReport:
    if not sessions_root.exists():
        return _empty(since, until)

    m_cost: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    m_tin: dict[str, int] = defaultdict(int)
    m_tout: dict[str, int] = defaultdict(int)
    m_turns: dict[str, int] = defaultdict(int)
    m_first_try: dict[str, int] = defaultdict(int)
    m_codedebug: dict[str, int] = defaultdict(int)

    c_cost: dict[TaskCategory, Decimal] = defaultdict(lambda: Decimal("0"))
    c_turns: dict[TaskCategory, int] = defaultdict(int)

    sessions: list[SessionRow] = []

    total_cost = Decimal("0")
    total_tin = total_tout = total_turns = 0
    total_first_try = total_codedebug = 0
    seen_ts: list[float] = []

    for sess_dir in sorted(sessions_root.iterdir()):
        if not sess_dir.is_dir():
            continue
        sid = sess_dir.name
        rows = list(_iter_turns(sess_dir / "turns.jsonl",
                                since=since, until=until))
        if not rows:
            continue
        sess_cost = Decimal("0")
        prev: Classification | None = None
        cat_counts: dict[TaskCategory, int] = defaultdict(int)
        model_counts: dict[str, int] = defaultdict(int)
        sess_start = float(rows[0].get("ts") or 0.0)
        sess_end = float(rows[-1].get("ts") or sess_start)

        for row in rows:
            cls = classify_turn(row, prev=prev)
            prev = cls
            cat = cls.category
            model = str(row.get("model") or "unknown")
            cost = _row_cost(row, refresh_pricing)

            total_cost += cost
            sess_cost += cost
            total_turns += 1
            tin = int(row.get("tokens_in") or 0)
            tout = int(row.get("tokens_out") or 0)
            total_tin += tin
            total_tout += tout
            ts = row.get("ts") or 0.0
            if ts:
                seen_ts.append(float(ts))

            m_cost[model] += cost
            m_tin[model] += tin
            m_tout[model] += tout
            m_turns[model] += 1

            c_cost[cat] += cost
            c_turns[cat] += 1
            cat_counts[cat] += 1
            model_counts[model] += 1

            if cat in ("coding", "debugging"):
                m_codedebug[model] += 1
                total_codedebug += 1
                if cls.retry_streak == 1:
                    m_first_try[model] += 1
                    total_first_try += 1

        primary_cat: TaskCategory = (
            max(cat_counts.items(), key=lambda kv: kv[1])[0]
            if cat_counts else "general"
        )
        primary_model = (
            max(model_counts.items(), key=lambda kv: kv[1])[0]
            if model_counts else "unknown"
        )
        sessions.append(SessionRow(
            session_id=sid, started_at=sess_start, last_turn_at=sess_end,
            turns=len(rows), cost_usd=sess_cost,
            primary_category=primary_cat, primary_model=primary_model,
        ))

    by_model = tuple(sorted(
        [
            ModelBreakdown(
                model=m, cost_usd=m_cost[m],
                tokens_in=m_tin[m], tokens_out=m_tout[m],
                turns=m_turns[m],
                one_shot_rate=(m_first_try[m] / m_codedebug[m]) if m_codedebug[m] else 1.0,
            )
            for m in m_cost
        ],
        key=lambda r: r.cost_usd, reverse=True,
    ))
    by_category = tuple(sorted(
        [CategoryBreakdown(c, c_cost[c], c_turns[c]) for c in c_turns],
        key=lambda r: r.cost_usd, reverse=True,
    ))
    by_session = tuple(sorted(sessions, key=lambda r: r.last_turn_at, reverse=True))

    period_start = since if since is not None else (min(seen_ts) if seen_ts else 0.0)
    period_end = until if until is not None else (max(seen_ts) if seen_ts else 0.0)
    osr = (total_first_try / total_codedebug) if total_codedebug else 1.0
    retry_rate = 1.0 - osr

    return BurnReport(
        period_start=period_start, period_end=period_end,
        total_cost_usd=total_cost,
        total_tokens_in=total_tin, total_tokens_out=total_tout,
        total_turns=total_turns,
        by_model=by_model, by_category=by_category, by_session=by_session,
        one_shot_rate=osr, retry_rate=retry_rate,
    )


# ---- helpers --------------------------------------------------------------

def _iter_turns(
    path: Path, *,
    since: float | None, until: float | None,
) -> Iterator[Mapping[str, object]]:
    if not path.exists():
        return
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
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
            yield row


def _row_cost(row: Mapping[str, object], refresh: bool) -> Decimal:
    explicit = row.get("cost_delta_usd")
    if explicit is not None:
        try:
            return Decimal(str(explicit))
        except Exception:
            return Decimal("0")
    recomputed = cost_for_turn(row, refresh=refresh)
    return recomputed if recomputed is not None else Decimal("0")


def _empty(since: float | None, until: float | None) -> BurnReport:
    return BurnReport(
        period_start=since or 0.0, period_end=until or 0.0,
        total_cost_usd=Decimal("0"),
        total_tokens_in=0, total_tokens_out=0, total_turns=0,
        by_model=(), by_category=(), by_session=(),
        one_shot_rate=1.0, retry_rate=0.0,
    )
