"""Tests for altitude prompt-eval scaffolding (Phase CE.3, P2-4)."""
from __future__ import annotations

import pytest

from lyra_core.context.altitude import (
    AltitudeReport,
    PromptVariant,
    TaskScore,
    aggregate,
    render_report,
)


def _v(name: str, body: str = "non-empty body") -> PromptVariant:
    return PromptVariant(name=name, body=body)


# ────────────────────────────────────────────────────────────────
# Validators
# ────────────────────────────────────────────────────────────────


def test_prompt_variant_rejects_empty_name():
    with pytest.raises(ValueError):
        PromptVariant(name="", body="x")


def test_prompt_variant_rejects_empty_body():
    with pytest.raises(ValueError):
        PromptVariant(name="x", body="")


@pytest.mark.parametrize("bad", [-0.01, 1.01])
def test_task_score_clamps_range(bad: float):
    with pytest.raises(ValueError):
        TaskScore(task_id="t", family="f", variant_name="v", score=bad)


# ────────────────────────────────────────────────────────────────
# aggregate
# ────────────────────────────────────────────────────────────────


def test_aggregate_empty_scores_yields_empty_report():
    rep = aggregate(canonical=_v("c"), variant=_v("v"), scores=[])
    assert rep.families == ()
    assert rep.overall_delta() == 0.0
    assert rep.winner() == "tie"


def test_aggregate_variant_wins_a_family():
    scores = [
        TaskScore("t1", "refactor", "canon", 0.5),
        TaskScore("t2", "refactor", "canon", 0.6),
        TaskScore("t1", "refactor", "var", 0.8),
        TaskScore("t2", "refactor", "var", 0.9),
    ]
    rep = aggregate(
        canonical=_v("canon"), variant=_v("var"), scores=scores
    )
    assert len(rep.families) == 1
    fam = rep.families[0]
    assert fam.family == "refactor"
    assert fam.winner == "var"
    assert fam.delta > 0
    assert rep.winner() == "var"


def test_aggregate_canonical_wins_when_variant_underperforms():
    scores = [
        TaskScore("t1", "debug", "canon", 0.9),
        TaskScore("t1", "debug", "var", 0.4),
    ]
    rep = aggregate(canonical=_v("canon"), variant=_v("var"), scores=scores)
    assert rep.families[0].winner == "canon"
    assert rep.overall_delta() < 0
    assert rep.winner() == "canon"


def test_aggregate_tie_inside_tie_band():
    scores = [
        TaskScore("t1", "x", "canon", 0.50),
        TaskScore("t1", "x", "var", 0.505),
    ]
    rep = aggregate(canonical=_v("canon"), variant=_v("var"), scores=scores)
    assert rep.families[0].winner == "tie"
    assert rep.winner() == "tie"


def test_aggregate_skips_one_sided_families():
    """A family with only canonical scores is skipped, not raised."""
    scores = [
        TaskScore("t1", "lonely", "canon", 0.7),
        TaskScore("t2", "balanced", "canon", 0.6),
        TaskScore("t2", "balanced", "var", 0.9),
    ]
    rep = aggregate(canonical=_v("canon"), variant=_v("var"), scores=scores)
    families = {f.family for f in rep.families}
    assert families == {"balanced"}


def test_aggregate_families_sorted():
    scores = [
        TaskScore("t1", "zeta", "canon", 0.5),
        TaskScore("t1", "zeta", "var", 0.5),
        TaskScore("t2", "alpha", "canon", 0.5),
        TaskScore("t2", "alpha", "var", 0.5),
    ]
    rep = aggregate(canonical=_v("canon"), variant=_v("var"), scores=scores)
    assert [f.family for f in rep.families] == ["alpha", "zeta"]


def test_aggregate_sample_size_uses_min():
    """If canonical has 3 samples and variant has 2, sample_size == 2."""
    scores = [
        TaskScore("t1", "x", "canon", 0.5),
        TaskScore("t2", "x", "canon", 0.5),
        TaskScore("t3", "x", "canon", 0.5),
        TaskScore("t1", "x", "var", 0.5),
        TaskScore("t2", "x", "var", 0.5),
    ]
    rep = aggregate(canonical=_v("canon"), variant=_v("var"), scores=scores)
    assert rep.families[0].sample_size == 2


def test_aggregate_rejects_negative_tie_band():
    with pytest.raises(ValueError):
        aggregate(
            canonical=_v("c"),
            variant=_v("v"),
            scores=[],
            tie_band=-0.1,
        )


# ────────────────────────────────────────────────────────────────
# Reporting
# ────────────────────────────────────────────────────────────────


def test_render_empty_report_explains():
    rep = aggregate(canonical=_v("c"), variant=_v("v"), scores=[])
    text = render_report(rep)
    assert "Altitude eval" in text
    assert "no families with two-sided coverage" in text


def test_render_with_families_shows_each():
    scores = [
        TaskScore("t1", "refactor", "canon", 0.6),
        TaskScore("t1", "refactor", "var", 0.9),
        TaskScore("t2", "debug", "canon", 0.5),
        TaskScore("t2", "debug", "var", 0.4),
    ]
    rep = aggregate(canonical=_v("canon"), variant=_v("var"), scores=scores)
    text = render_report(rep)
    assert "refactor" in text
    assert "debug" in text
    assert "winner=" in text


def test_overall_delta_averages_per_family_deltas():
    scores = [
        TaskScore("t1", "a", "canon", 0.5),
        TaskScore("t1", "a", "var", 0.7),  # +0.2
        TaskScore("t2", "b", "canon", 0.6),
        TaskScore("t2", "b", "var", 0.5),  # -0.1
    ]
    rep = aggregate(canonical=_v("canon"), variant=_v("var"), scores=scores)
    # average of [+0.2, -0.1] = +0.05
    assert rep.overall_delta() == pytest.approx(0.05, abs=1e-6)


def test_report_is_serialisable_via_dataclass_fields():
    """Sanity: AltitudeReport is a plain dataclass — fields enumerable."""
    rep = AltitudeReport(canonical=_v("c"), variant=_v("v"))
    assert hasattr(rep, "families")
    assert hasattr(rep, "canonical")
    assert hasattr(rep, "variant")
