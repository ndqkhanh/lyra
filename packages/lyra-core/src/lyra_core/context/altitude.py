"""Right-altitude prompt-eval scaffolding (Phase CE.3, P2-4).

Anthropic's *right altitude* framing is hand-wavy by design: a system
prompt is "too low" when it hardcodes brittle edge-case logic, and
"too high" when it offers no concrete signals. This module gives that
hand-wave a metric:

1. Take two prompt variants (``canonical`` and a deliberately
   shifted ``variant``).
2. Run a fixed eval set against both — each task returns a
   ``TaskScore`` in ``[0, 1]``.
3. Aggregate by task family, declare a winner per family, surface
   the overall delta.

The module owns *only* the bookkeeping. Actually running the eval is
the caller's job (typically wired into ``lyra-evals``). That keeps the
scaffolding free of LLM coupling while giving release-gate code a
concrete data shape to fill in.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PromptVariant:
    """One named system-prompt variant under test."""

    name: str
    body: str

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("PromptVariant.name must be non-empty")
        if not self.body or not self.body.strip():
            raise ValueError("PromptVariant.body must be non-empty")


@dataclass(frozen=True)
class TaskScore:
    """One eval task's outcome under one variant."""

    task_id: str
    family: str
    variant_name: str
    score: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(
                f"TaskScore.score must be in [0, 1]; got {self.score}"
            )


@dataclass(frozen=True)
class FamilyOutcome:
    """Per-family winner declaration."""

    family: str
    canonical_mean: float
    variant_mean: float
    sample_size: int
    winner: str  # name of the winning variant, or "tie"
    delta: float  # variant_mean - canonical_mean


@dataclass
class AltitudeReport:
    """Top-level eval report."""

    canonical: PromptVariant
    variant: PromptVariant
    families: tuple[FamilyOutcome, ...] = field(default_factory=tuple)

    def overall_delta(self) -> float:
        """Mean per-family delta (variant - canonical). Empty → 0."""
        if not self.families:
            return 0.0
        return statistics.fmean(f.delta for f in self.families)

    def winner(self, *, tie_band: float = 0.01) -> str:
        """Overall winner: canonical, variant, or 'tie' inside ``tie_band``."""
        d = self.overall_delta()
        if abs(d) <= tie_band:
            return "tie"
        return self.variant.name if d > 0 else self.canonical.name


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def aggregate(
    *,
    canonical: PromptVariant,
    variant: PromptVariant,
    scores: list[TaskScore],
    tie_band: float = 0.01,
) -> AltitudeReport:
    """Group scores by family and decide a winner per family.

    Both variants must appear in ``scores`` for at least one task in
    the family; families with one-sided data are skipped (logged via
    omission, not raised — the caller decides whether incomplete
    coverage is fatal).
    """
    if tie_band < 0:
        raise ValueError(f"tie_band must be >= 0; got {tie_band}")

    grouped: dict[str, dict[str, list[float]]] = {}
    for s in scores:
        family_bucket = grouped.setdefault(s.family, {})
        family_bucket.setdefault(s.variant_name, []).append(s.score)

    families: list[FamilyOutcome] = []
    for family, by_variant in grouped.items():
        canon = by_variant.get(canonical.name, [])
        var = by_variant.get(variant.name, [])
        if not canon or not var:
            continue
        canon_mean = _mean(canon)
        var_mean = _mean(var)
        delta = var_mean - canon_mean
        if abs(delta) <= tie_band:
            winner = "tie"
        elif delta > 0:
            winner = variant.name
        else:
            winner = canonical.name
        families.append(
            FamilyOutcome(
                family=family,
                canonical_mean=canon_mean,
                variant_mean=var_mean,
                sample_size=min(len(canon), len(var)),
                winner=winner,
                delta=delta,
            )
        )

    families.sort(key=lambda f: f.family)
    return AltitudeReport(
        canonical=canonical,
        variant=variant,
        families=tuple(families),
    )


def render_report(report: AltitudeReport) -> str:
    """Human-readable summary suitable for CLI output."""
    lines = [
        f"# Altitude eval: {report.canonical.name} vs {report.variant.name}",
        f"overall delta: {report.overall_delta():+.3f}",
        f"overall winner: {report.winner()}",
        "",
        "## Families",
    ]
    if not report.families:
        lines.append("(no families with two-sided coverage)")
    for f in report.families:
        lines.append(
            f"- {f.family:24s} n={f.sample_size:3d}  "
            f"canon={f.canonical_mean:.3f}  var={f.variant_mean:.3f}  "
            f"Δ={f.delta:+.3f}  winner={f.winner}"
        )
    return "\n".join(lines) + "\n"


__all__ = [
    "AltitudeReport",
    "FamilyOutcome",
    "PromptVariant",
    "TaskScore",
    "aggregate",
    "render_report",
]
