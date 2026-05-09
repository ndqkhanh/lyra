"""Red tests for coverage-regression gating."""
from __future__ import annotations

import pytest

from lyra_core.tdd.coverage import (
    CoverageDelta,
    CoverageRegressionError,
    check_coverage_delta,
)


def test_improvement_passes() -> None:
    delta = CoverageDelta(before=80.0, after=85.0, tolerance_pct=1.0)
    check_coverage_delta(delta)  # no raise


def test_within_tolerance_passes() -> None:
    delta = CoverageDelta(before=80.0, after=79.5, tolerance_pct=1.0)
    check_coverage_delta(delta)


def test_regression_beyond_tolerance_blocks() -> None:
    delta = CoverageDelta(before=80.0, after=70.0, tolerance_pct=1.0)
    with pytest.raises(CoverageRegressionError):
        check_coverage_delta(delta)


def test_zero_tolerance_blocks_any_drop() -> None:
    delta = CoverageDelta(before=80.0, after=79.9, tolerance_pct=0.0)
    with pytest.raises(CoverageRegressionError):
        check_coverage_delta(delta)
