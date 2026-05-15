"""Tests for harness_core.verifier — multi-axis composer + built-in verifiers."""
from __future__ import annotations

import pytest

from harness_core.verifier import (
    AxisVerdict,
    CompositeVerdict,
    HITLVerifier,
    Severity,
    StubDiffVerifier,
    StubDryRunVerifier,
    StubPermissionVerifier,
    StubPolicyVerifier,
    VerifierAxis,
    VerifierComposer,
)


# --- AxisVerdict / CompositeVerdict ------------------------------------


class TestAxisVerdict:
    def test_valid(self):
        v = AxisVerdict(
            axis=VerifierAxis.DRY_RUN,
            passed=True,
            severity=Severity.INFO,
        )
        assert v.passed is True

    def test_immutable(self):
        v = AxisVerdict(axis=VerifierAxis.POLICY, passed=True)
        with pytest.raises(Exception):
            v.passed = False  # type: ignore[misc]


class TestCompositeVerdict:
    def test_by_axis_finds(self):
        verdicts = (
            AxisVerdict(axis=VerifierAxis.DRY_RUN, passed=True),
            AxisVerdict(axis=VerifierAxis.POLICY, passed=False),
        )
        composite = CompositeVerdict(
            axis_verdicts=verdicts,
            passed=False,
            blocking=True,
            severity=Severity.ERROR,
        )
        found = composite.by_axis(VerifierAxis.POLICY)
        assert found is not None
        assert found.passed is False

    def test_by_axis_missing_returns_none(self):
        composite = CompositeVerdict(
            axis_verdicts=(),
            passed=True,
            blocking=False,
            severity=Severity.INFO,
        )
        assert composite.by_axis(VerifierAxis.HITL) is None

    def test_failed_axes(self):
        verdicts = (
            AxisVerdict(axis=VerifierAxis.DRY_RUN, passed=True),
            AxisVerdict(axis=VerifierAxis.POLICY, passed=False),
            AxisVerdict(axis=VerifierAxis.HITL, passed=False),
        )
        composite = CompositeVerdict(
            axis_verdicts=verdicts,
            passed=False,
            blocking=True,
            severity=Severity.ERROR,
        )
        assert set(composite.failed_axes()) == {VerifierAxis.POLICY, VerifierAxis.HITL}


# --- Built-in stub verifiers --------------------------------------------


class TestStubDryRunVerifier:
    def test_passes(self):
        v = StubDryRunVerifier(should_pass=True)
        verdict = v.verify(action={"op": "write_file", "path": "/tmp/x"})
        assert verdict.passed is True
        assert verdict.axis == VerifierAxis.DRY_RUN

    def test_fails(self):
        v = StubDryRunVerifier(should_pass=False, severity_on_fail=Severity.CRITICAL)
        verdict = v.verify(action={"op": "rm_rf"})
        assert verdict.passed is False
        assert verdict.severity == Severity.CRITICAL


class TestStubDiffVerifier:
    def test_within_cap(self):
        v = StubDiffVerifier(max_lines_changed=100)
        verdict = v.verify(action={"diff_lines": 50})
        assert verdict.passed is True
        assert "within" in verdict.note

    def test_overflow(self):
        v = StubDiffVerifier(max_lines_changed=100, severity_on_overflow=Severity.ERROR)
        verdict = v.verify(action={"diff_lines": 500})
        assert verdict.passed is False
        assert verdict.severity == Severity.ERROR
        assert verdict.details["diff_lines"] == 500

    def test_zero_diff_passes(self):
        v = StubDiffVerifier(max_lines_changed=100)
        verdict = v.verify(action={})  # no diff_lines key → 0
        assert verdict.passed is True


class TestStubPolicyVerifier:
    def test_allowed(self):
        v = StubPolicyVerifier(forbidden_ops=frozenset({"rm_rf"}))
        verdict = v.verify(action={"op": "write_file"})
        assert verdict.passed is True

    def test_forbidden(self):
        v = StubPolicyVerifier(forbidden_ops=frozenset({"rm_rf"}))
        verdict = v.verify(action={"op": "rm_rf"})
        assert verdict.passed is False
        assert verdict.severity == Severity.CRITICAL

    def test_should_pass_override(self):
        # should_pass=False forces deny regardless of forbidden_ops.
        v = StubPolicyVerifier(should_pass=False)
        verdict = v.verify(action={"op": "anything"})
        assert verdict.passed is False


class TestStubPermissionVerifier:
    def test_all_scopes_present(self):
        v = StubPermissionVerifier(granted_scopes=frozenset({"read", "write"}))
        verdict = v.verify(action={"required_scopes": ["read"]})
        assert verdict.passed is True

    def test_missing_scope(self):
        v = StubPermissionVerifier(granted_scopes=frozenset({"read"}))
        verdict = v.verify(action={"required_scopes": ["write"]})
        assert verdict.passed is False
        assert verdict.severity == Severity.ERROR
        assert "write" in verdict.details["missing"]

    def test_no_required_scopes_passes(self):
        v = StubPermissionVerifier(granted_scopes=frozenset())
        verdict = v.verify(action={})
        assert verdict.passed is True


class TestHITLVerifier:
    def test_below_threshold_auto_passes(self):
        v = HITLVerifier(require_review_above=Severity.WARNING)
        verdict = v.verify(action={"severity": "info"})
        assert verdict.passed is True
        assert "auto-approved" in verdict.note

    def test_above_threshold_no_approval_blocks(self):
        v = HITLVerifier(require_review_above=Severity.WARNING)
        verdict = v.verify(action={"severity": "error"})
        assert verdict.passed is False
        assert verdict.severity == Severity.WARNING

    def test_above_threshold_with_approval_passes(self):
        v = HITLVerifier(require_review_above=Severity.WARNING)
        verdict = v.verify(action={"severity": "error", "hitl_approval": "alice"})
        assert verdict.passed is True
        assert "alice" in verdict.note

    def test_invalid_severity_treated_as_info(self):
        v = HITLVerifier(require_review_above=Severity.WARNING)
        verdict = v.verify(action={"severity": "bogus"})
        assert verdict.passed is True

    def test_critical_action_requires_approval(self):
        v = HITLVerifier(require_review_above=Severity.WARNING)
        verdict = v.verify(action={"severity": "critical"})
        assert verdict.passed is False


# --- VerifierComposer --------------------------------------------------


class TestVerifierComposer:
    def test_all_pass(self):
        composer = VerifierComposer(verifiers=[
            StubDryRunVerifier(should_pass=True),
            StubPolicyVerifier(should_pass=True),
        ])
        verdict = composer.verify(action={"op": "write_file"})
        assert verdict.passed is True
        assert verdict.blocking is False
        assert verdict.severity == Severity.INFO

    def test_one_fails(self):
        composer = VerifierComposer(verifiers=[
            StubDryRunVerifier(should_pass=True),
            StubPolicyVerifier(should_pass=False, severity_on_violation=Severity.ERROR),
        ])
        verdict = composer.verify(action={"op": "x"})
        assert verdict.passed is False
        assert verdict.blocking is True
        assert verdict.severity == Severity.ERROR

    def test_warning_below_blocking_threshold(self):
        # blocking_severity defaults to ERROR; a WARNING failure shouldn't block.
        composer = VerifierComposer(
            verifiers=[
                StubDiffVerifier(max_lines_changed=10, severity_on_overflow=Severity.WARNING),
            ],
            blocking_severity=Severity.ERROR,
        )
        verdict = composer.verify(action={"diff_lines": 100})
        assert verdict.passed is False  # axis failed
        assert verdict.blocking is False  # but not blocking
        assert verdict.severity == Severity.WARNING

    def test_fail_fast(self):
        composer = VerifierComposer(
            verifiers=[
                StubPolicyVerifier(should_pass=False),  # fails first
                StubDryRunVerifier(should_pass=True),  # never runs
            ],
            fail_fast=True,
        )
        verdict = composer.verify(action={"op": "x"})
        # Only one verdict, because fail_fast stopped at the first.
        assert len(verdict.axis_verdicts) == 1
        assert verdict.axis_verdicts[0].axis == VerifierAxis.POLICY

    def test_fail_fast_off_runs_all(self):
        composer = VerifierComposer(
            verifiers=[
                StubPolicyVerifier(should_pass=False),
                StubDryRunVerifier(should_pass=True),
            ],
            fail_fast=False,
        )
        verdict = composer.verify(action={"op": "x"})
        assert len(verdict.axis_verdicts) == 2

    def test_duplicate_axis_rejected(self):
        with pytest.raises(ValueError):
            VerifierComposer(verifiers=[
                StubDryRunVerifier(),
                StubDryRunVerifier(),  # duplicate axis
            ])

    def test_severity_aggregates_to_max(self):
        composer = VerifierComposer(verifiers=[
            StubDiffVerifier(max_lines_changed=10, severity_on_overflow=Severity.WARNING),
            StubPolicyVerifier(should_pass=False, severity_on_violation=Severity.CRITICAL),
        ])
        verdict = composer.verify(action={"op": "x", "diff_lines": 100})
        assert verdict.severity == Severity.CRITICAL

    def test_aegis_canonical_composition(self):
        """Aegis-Ops's canonical 5-axis composition: dry-run + diff + policy +
        permission + HITL."""
        composer = VerifierComposer(verifiers=[
            StubDryRunVerifier(should_pass=True),
            StubDiffVerifier(max_lines_changed=100),
            StubPolicyVerifier(forbidden_ops=frozenset({"rm_rf", "drop_table"})),
            StubPermissionVerifier(granted_scopes=frozenset({"k8s.write", "aws.iam"})),
            HITLVerifier(require_review_above=Severity.ERROR),
        ])
        # A safe action passes all 5.
        verdict = composer.verify(action={
            "op": "write_file",
            "diff_lines": 5,
            "required_scopes": ["k8s.write"],
            "severity": "info",
        })
        assert verdict.passed is True
        assert len(verdict.axis_verdicts) == 5

    def test_aegis_canonical_blocks_unsafe(self):
        """A forbidden op should block."""
        composer = VerifierComposer(verifiers=[
            StubDryRunVerifier(should_pass=True),
            StubDiffVerifier(max_lines_changed=100),
            StubPolicyVerifier(forbidden_ops=frozenset({"rm_rf"})),
            StubPermissionVerifier(granted_scopes=frozenset({"k8s.write"})),
            HITLVerifier(),
        ])
        verdict = composer.verify(action={
            "op": "rm_rf",
            "required_scopes": [],
            "severity": "info",
        })
        assert verdict.passed is False
        assert verdict.blocking is True
        # Policy axis specifically failed.
        policy_verdict = verdict.by_axis(VerifierAxis.POLICY)
        assert policy_verdict is not None
        assert policy_verdict.passed is False

    def test_orion_canonical_composition(self):
        """Orion-Code's canonical: test + lint + type-check + security + HITL."""
        # Use CUSTOM axes for the code verifiers (test/lint stubs would need
        # their own axis types; we reuse stubs with custom axis labels).
        # For this test, we just confirm the composer handles 5 stubs cleanly.
        composer = VerifierComposer(verifiers=[
            StubDryRunVerifier(should_pass=True),  # acts as 'test'
            StubDiffVerifier(max_lines_changed=200),  # acts as 'lint' diff size
            StubPolicyVerifier(should_pass=True),  # acts as 'type_check'
            StubPermissionVerifier(granted_scopes=frozenset({"write"})),  # acts as 'security_scan'
            HITLVerifier(),
        ])
        verdict = composer.verify(action={
            "op": "edit_file",
            "diff_lines": 20,
            "required_scopes": ["write"],
            "severity": "info",
        })
        assert verdict.passed is True
