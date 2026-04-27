"""Coverage-regression gating."""
from __future__ import annotations

from dataclasses import dataclass


class CoverageRegressionError(Exception):
    """Raised when post-change coverage drops beyond tolerance."""


@dataclass
class CoverageDelta:
    before: float
    after: float
    tolerance_pct: float = 1.0  # absolute percentage points of drop allowed


def check_coverage_delta(delta: CoverageDelta) -> None:
    drop = delta.before - delta.after
    if drop > delta.tolerance_pct:
        raise CoverageRegressionError(
            f"coverage dropped {drop:.2f}% "
            f"(from {delta.before:.2f}% to {delta.after:.2f}%); "
            f"tolerance is {delta.tolerance_pct:.2f}%"
        )
