"""Phase 12 — Red tests for the contamination guard.

The landscape study (``docs/roadmap-v1.5-v2.md`` §0.1) showed Claude Opus
4.5 scores 80.9% on SWE-bench Verified vs 45.9% on SWE-bench Pro — the
Verified corpus pre-dates 4.5's training cutoff and is contaminated. Any
credible harness must refuse to evaluate on a contaminated corpus unless
the operator explicitly opts in.

These tests pin the contract:

1. ``ContaminationGuard.check`` raises ``ContaminationError`` when the
   corpus cutoff ≤ the model training cutoff.
2. With ``allow_contaminated=True`` the check passes but registers a
   warning on the guard.
3. Warnings flow into the ``Report`` so ``lyra retro`` can surface
   them (per the Phase 12 DoD).
4. An unknown / missing model cutoff is treated as contaminated by default
   — fail-closed.
"""
from __future__ import annotations

from datetime import date

import pytest

from lyra_evals.contamination import (
    ContaminationError,
    ContaminationGuard,
)

# ---------------------------------------------------------------------------
# 1. Fail-closed when corpus is older than model cutoff
# ---------------------------------------------------------------------------


def test_guard_raises_when_corpus_predates_model_cutoff() -> None:
    """SWE-bench Verified (Apr 2024) + Claude 4.5 (Oct 2025) → refuse.

    This is the 80.9%-vs-45.9% case from the landscape study. We refuse
    to attach Lyra's name to scores that depend on this contamination.
    """
    guard = ContaminationGuard(
        corpus_name="swe-bench-verified",
        corpus_cutoff=date(2024, 4, 1),
        model_name="claude-opus-4.5",
        model_training_cutoff=date(2025, 10, 1),
    )
    with pytest.raises(ContaminationError, match="contaminat"):
        guard.check()


def test_guard_passes_when_corpus_postdates_model_cutoff() -> None:
    """SWE-bench Pro (Feb 2026) + Claude 4.5 (Oct 2025) → allow.

    The whole point of Pro's contamination resistance is that it was
    curated after the model's training cutoff.
    """
    guard = ContaminationGuard(
        corpus_name="swe-bench-pro",
        corpus_cutoff=date(2026, 2, 1),
        model_name="claude-opus-4.5",
        model_training_cutoff=date(2025, 10, 1),
    )
    guard.check()  # must not raise
    assert guard.warnings == []


# ---------------------------------------------------------------------------
# 2. Explicit opt-in
# ---------------------------------------------------------------------------


def test_allow_contaminated_bypasses_refusal_with_warning() -> None:
    """``--allow-contaminated`` must attach a permanent warning record.

    The operator accepted the risk; the retro must still surface it so
    downstream readers don't treat the score as clean.
    """
    guard = ContaminationGuard(
        corpus_name="swe-bench-verified",
        corpus_cutoff=date(2024, 4, 1),
        model_name="claude-opus-4.5",
        model_training_cutoff=date(2025, 10, 1),
        allow_contaminated=True,
    )
    guard.check()
    assert len(guard.warnings) == 1
    assert "contaminat" in guard.warnings[0].lower()
    assert "swe-bench-verified" in guard.warnings[0]


# ---------------------------------------------------------------------------
# 3. Unknown model cutoff is fail-closed
# ---------------------------------------------------------------------------


def test_unknown_model_cutoff_is_fail_closed_by_default() -> None:
    """No cutoff recorded for the model → assume contaminated.

    Frontier models frequently release with vague 'as of ...' disclosures.
    Fail-closed forces the operator to either supply a cutoff or set the
    opt-in flag; silent runs on unlabelled models are the worst outcome.
    """
    guard = ContaminationGuard(
        corpus_name="swe-bench-pro",
        corpus_cutoff=date(2026, 2, 1),
        model_name="unknown-model",
        model_training_cutoff=None,
    )
    with pytest.raises(ContaminationError, match=r"unknown.*cutoff"):
        guard.check()


def test_unknown_model_cutoff_with_allow_bypasses() -> None:
    """With ``allow_contaminated=True`` even an unknown cutoff passes, w/ warning."""
    guard = ContaminationGuard(
        corpus_name="swe-bench-pro",
        corpus_cutoff=date(2026, 2, 1),
        model_name="unknown-model",
        model_training_cutoff=None,
        allow_contaminated=True,
    )
    guard.check()
    assert any("unknown" in w.lower() for w in guard.warnings)


# ---------------------------------------------------------------------------
# 4. Boundary: same day is contaminated (conservative)
# ---------------------------------------------------------------------------


def test_same_day_cutoff_is_contaminated_conservative() -> None:
    """If cutoffs land on the same day, default to contaminated.

    We prefer false positives over false negatives on a reproducibility
    flag; operators can always opt in.
    """
    guard = ContaminationGuard(
        corpus_name="some-corpus",
        corpus_cutoff=date(2025, 10, 1),
        model_name="some-model",
        model_training_cutoff=date(2025, 10, 1),
    )
    with pytest.raises(ContaminationError):
        guard.check()
