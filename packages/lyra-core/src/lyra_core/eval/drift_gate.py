"""Wave-E Task 14: drift gate.

Compares a fresh :class:`EvalReport` to a stored baseline. If pass
rate drops by more than ``tolerance`` (default 2 percentage points)
the gate ``decision.allowed = False`` and the new build is blocked
from promotion. Per-category regressions can also be checked
independently — a model can regress catastrophically on a single
skill while the global pass rate barely moves.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .corpus import EvalReport


__all__ = ["DriftDecision", "DriftGate"]


@dataclass(frozen=True)
class DriftDecision:
    allowed: bool
    baseline_pass_rate: float
    candidate_pass_rate: float
    delta: float
    regressed_categories: tuple[str, ...] = ()
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "baseline_pass_rate": self.baseline_pass_rate,
            "candidate_pass_rate": self.candidate_pass_rate,
            "delta": self.delta,
            "regressed_categories": list(self.regressed_categories),
            "reason": self.reason,
        }


@dataclass
class DriftGate:
    """Stateless comparator with optional disk-backed baseline."""

    tolerance: float = 0.02
    category_tolerance: float = 0.05

    def compare(self, *, baseline: EvalReport, candidate: EvalReport) -> DriftDecision:
        delta = candidate.pass_rate - baseline.pass_rate
        regressed: list[str] = []
        baseline_cats = baseline.by_category()
        candidate_cats = candidate.by_category()
        for cat, base_score in baseline_cats.items():
            cand_score = candidate_cats.get(cat, 0.0)
            if base_score - cand_score > self.category_tolerance:
                regressed.append(cat)
        if delta < -self.tolerance:
            return DriftDecision(
                allowed=False,
                baseline_pass_rate=baseline.pass_rate,
                candidate_pass_rate=candidate.pass_rate,
                delta=delta,
                regressed_categories=tuple(regressed),
                reason=(
                    f"global pass rate dropped by {-delta:.2%} "
                    f"(tolerance {self.tolerance:.2%})"
                ),
            )
        if regressed:
            return DriftDecision(
                allowed=False,
                baseline_pass_rate=baseline.pass_rate,
                candidate_pass_rate=candidate.pass_rate,
                delta=delta,
                regressed_categories=tuple(regressed),
                reason=(
                    "category regression beyond tolerance: "
                    + ", ".join(regressed)
                ),
            )
        return DriftDecision(
            allowed=True,
            baseline_pass_rate=baseline.pass_rate,
            candidate_pass_rate=candidate.pass_rate,
            delta=delta,
            regressed_categories=(),
            reason="within tolerance",
        )

    # ---- baseline I/O -------------------------------------------------

    def save_baseline(self, report: EvalReport, path: Path | str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(
            json.dumps(report.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def load_baseline(self, path: Path | str) -> dict:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    def compare_to_baseline_file(
        self, *, candidate: EvalReport, baseline_path: Path | str
    ) -> DriftDecision:
        """Compare *candidate* against an on-disk baseline JSON.

        We only need ``pass_rate`` + ``by_category`` from the
        baseline, so a thin synthetic ``EvalReport`` is reconstructed
        — never re-run the full corpus on baseline load.
        """
        data = self.load_baseline(baseline_path)
        baseline_pass_rate = float(data.get("pass_rate", 0.0))
        baseline_cats = dict(data.get("by_category", {}))

        # Synthesise a baseline-shaped object: only ``pass_rate`` and
        # ``by_category`` are read by ``compare``.
        class _BaselineShim:
            pass_rate = baseline_pass_rate

            def by_category(self):
                return baseline_cats

        return self.compare(baseline=_BaselineShim(), candidate=candidate)  # type: ignore[arg-type]
