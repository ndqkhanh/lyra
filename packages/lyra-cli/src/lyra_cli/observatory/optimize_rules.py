"""Pluggable rule registry for ``lyra burn optimize``."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Iterable, Literal, Mapping

from .classifier import classify_turn, Classification


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: Literal["info", "warn", "error"]
    title: str
    detail: str
    estimated_savings_usd: Decimal | None
    evidence: tuple[str, ...]


def _classify_all(rows: Iterable[Mapping]) -> list[tuple[Mapping, Classification]]:
    out: list[tuple[Mapping, Classification]] = []
    prev: Classification | None = None
    for r in rows:
        if r.get("kind") not in (None, "turn"):
            continue
        cls = classify_turn(r, prev=prev)
        prev = cls
        out.append((r, cls))
    return out


def _r_retry_streak_3(rows: list[Mapping]) -> list[Finding]:
    pairs = _classify_all(rows)
    bad: list[str] = []
    for row, cls in pairs:
        if cls.retry_streak >= 3 and cls.category in ("coding", "debugging"):
            bad.append(f"turn {row.get('turn')} ({cls.category} streak={cls.retry_streak})")
    if not bad:
        return []
    return [Finding(
        rule_id="R-RETRY-STREAK-3", severity="warn",
        title="Long retry streak detected",
        detail=(
            ">=3 consecutive coding/debugging retries - switch tier or "
            "simplify the next prompt."
        ),
        estimated_savings_usd=None,
        evidence=tuple(bad[:5]),
    )]


def _r_low_one_shot(rows: list[Mapping]) -> list[Finding]:
    pairs = _classify_all(rows)
    cd = [(r, c) for r, c in pairs if c.category in ("coding", "debugging")]
    if len(cd) < 5:
        return []
    first = sum(1 for _, c in cd if c.retry_streak == 1)
    rate = first / len(cd)
    if rate >= 0.6:
        return []
    return [Finding(
        rule_id="R-LOW-1SHOT-RATE", severity="warn",
        title=f"One-shot rate {rate*100:.0f}% (target >=60%)",
        detail=(
            "Most coding turns required a retry. Likely missing context, "
            "wrong model tier, or under-specified prompt."
        ),
        estimated_savings_usd=None,
        evidence=(f"{len(cd)} coding/debugging turns, {first} succeeded first try",),
    )]


def _r_explore_heavy(rows: list[Mapping]) -> list[Finding]:
    pairs = _classify_all(rows)
    if not pairs:
        return []
    expl = sum(1 for _, c in pairs if c.category == "explore")
    if expl / len(pairs) < 0.4:
        return []
    return [Finding(
        rule_id="R-EXPLORE-HEAVY", severity="info",
        title=f"{expl}/{len(pairs)} turns spent exploring",
        detail=(
            "Consider distilling repeat findings into SOUL.md so future "
            "sessions don't re-pay the discovery cost."
        ),
        estimated_savings_usd=None,
        evidence=(f"{expl} explore turns",),
    )]


def _r_flash_over_pro(rows: list[Mapping]) -> list[Finding]:
    pairs = _classify_all(rows)
    bad = [r for r, c in pairs
           if c.category == "feature" and (r.get("model") or "").endswith("flash")]
    if len(bad) < 3:
        return []
    return [Finding(
        rule_id="R-FLASH-OVER-PRO", severity="info",
        title="Flash model used for feature work",
        detail=(
            "Flash tiers often need extra retries on multi-step features. "
            "Pro tier may be cheaper-per-success here."
        ),
        estimated_savings_usd=None,
        evidence=tuple(f"turn {r.get('turn')}" for r in bad[:5]),
    )]


RULES: list[Callable[[list[Mapping]], list[Finding]]] = [
    _r_retry_streak_3, _r_low_one_shot, _r_explore_heavy, _r_flash_over_pro,
]
