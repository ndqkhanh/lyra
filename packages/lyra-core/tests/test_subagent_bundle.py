"""Tests for the SubagentBundle return-contract (Phase CE.1, P0-3)."""
from __future__ import annotations

from typing import Any

import pytest

from lyra_core.subagent.bundle import (
    MAX_FINDING_CLAIM_CHARS,
    MAX_SUMMARY_TOKENS,
    Finding,
    SubagentBundle,
    SubagentBundleError,
    bundle_to_result,
    result_to_bundle,
    rough_token_count,
)
from lyra_core.subagent.orchestrator import SubagentResult


def _ok_bundle(**overrides: Any) -> SubagentBundle:
    base: dict[str, Any] = dict(
        summary="explored 12 files; found 2 failing tests in tests/test_api.py",
        findings=(
            Finding(
                claim="test_login_rejects_empty_password fails at line 41",
                evidence_hash="sha256:abc",
                confidence=0.9,
            ),
        ),
        artifacts=("sha256:abc", "sha256:def"),
        open_questions=("which fixture set up the bogus password?",),
        tokens_consumed=8120,
        elapsed_ms=4400,
    )
    base.update(overrides)
    return SubagentBundle(**base)


# ────────────────────────────────────────────────────────────────
# Finding validation
# ────────────────────────────────────────────────────────────────


def test_finding_rejects_empty_claim():
    with pytest.raises(SubagentBundleError, match="non-empty"):
        Finding(claim="", evidence_hash="sha256:x", confidence=0.5)


def test_finding_rejects_whitespace_only_claim():
    with pytest.raises(SubagentBundleError, match="non-empty"):
        Finding(claim="   \n  ", evidence_hash="sha256:x", confidence=0.5)


def test_finding_rejects_overlong_claim():
    big = "x" * (MAX_FINDING_CLAIM_CHARS + 1)
    with pytest.raises(SubagentBundleError, match="exceeds"):
        Finding(claim=big, evidence_hash="sha256:x", confidence=0.5)


@pytest.mark.parametrize("bad", [-0.01, 1.01, 2.0, -1.0])
def test_finding_rejects_out_of_range_confidence(bad: float):
    with pytest.raises(SubagentBundleError, match="confidence"):
        Finding(claim="ok", evidence_hash="sha256:x", confidence=bad)


# ────────────────────────────────────────────────────────────────
# Bundle validation
# ────────────────────────────────────────────────────────────────


def test_bundle_rejects_empty_summary():
    with pytest.raises(SubagentBundleError, match="summary"):
        SubagentBundle(summary="")


def test_bundle_rejects_oversized_summary():
    too_big = "x" * (MAX_SUMMARY_TOKENS * 4 + 8)  # > 2k tokens estimated
    with pytest.raises(SubagentBundleError, match="exceeds"):
        SubagentBundle(summary=too_big)


def test_bundle_accepts_summary_at_cap():
    """A summary just inside the cap is accepted."""
    body = "x" * (MAX_SUMMARY_TOKENS * 4 - 8)
    b = SubagentBundle(summary=body)
    assert b.summary_token_estimate() <= MAX_SUMMARY_TOKENS


def test_bundle_rejects_negative_consumption_metrics():
    with pytest.raises(SubagentBundleError, match="tokens_consumed"):
        SubagentBundle(summary="ok", tokens_consumed=-1)
    with pytest.raises(SubagentBundleError, match="elapsed_ms"):
        SubagentBundle(summary="ok", elapsed_ms=-1)


def test_bundle_is_frozen():
    b = _ok_bundle()
    with pytest.raises(Exception):  # FrozenInstanceError
        b.summary = "mutated"  # type: ignore[misc]


# ────────────────────────────────────────────────────────────────
# Views
# ────────────────────────────────────────────────────────────────


def test_summary_token_estimate_uses_char_heuristic():
    b = SubagentBundle(summary="abcdefghij" * 4)  # 40 chars → ~10 tokens
    assert b.summary_token_estimate() == 10


def test_has_open_questions_distinguishes_empty_from_whitespace():
    assert _ok_bundle(open_questions=()).has_open_questions() is False
    assert _ok_bundle(open_questions=("   ",)).has_open_questions() is False
    assert _ok_bundle(open_questions=("why?",)).has_open_questions() is True


def test_best_findings_filters_and_sorts():
    findings = (
        Finding("low", "h1", 0.3),
        Finding("high", "h2", 0.95),
        Finding("mid", "h3", 0.72),
    )
    b = _ok_bundle(findings=findings)
    best = b.best_findings(min_confidence=0.7)
    assert [f.claim for f in best] == ["high", "mid"]


def test_best_findings_empty_when_floor_too_high():
    b = _ok_bundle()
    assert b.best_findings(min_confidence=0.99) == []


# ────────────────────────────────────────────────────────────────
# Envelope helpers
# ────────────────────────────────────────────────────────────────


def test_bundle_to_result_wraps_with_ok_status():
    bundle = _ok_bundle()
    res = bundle_to_result(bundle, spec_id="explorer-1")
    assert isinstance(res, SubagentResult)
    assert res.id == "explorer-1"
    assert res.status == "ok"
    assert res.payload is bundle
    assert res.error is None


def test_result_to_bundle_round_trips():
    bundle = _ok_bundle()
    res = bundle_to_result(bundle, spec_id="x")
    assert result_to_bundle(res) is bundle


def test_result_to_bundle_rejects_legacy_payload():
    res = SubagentResult(id="x", status="ok", payload={"foo": "bar"})
    with pytest.raises(SubagentBundleError, match="not a SubagentBundle"):
        result_to_bundle(res)


def test_result_to_bundle_rejects_none_payload():
    res = SubagentResult(id="x", status="ok", payload=None)
    with pytest.raises(SubagentBundleError):
        result_to_bundle(res)


def test_rough_token_count_handles_empty_and_short():
    assert rough_token_count("") == 0
    assert rough_token_count("a") == 1
    assert rough_token_count("a" * 16) == 4
