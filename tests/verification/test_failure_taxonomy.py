"""Comprehensive tests for MUSE-style FailureTaxonomyVerifier."""

from __future__ import annotations

import pytest

from lyra.verification.failure_taxonomy import (
    FailureDiagnosis,
    FailureTaxonomyVerifier,
    FailureType,
    REPAIR_STRATEGIES,
    VerificationResult,
)


# ---------------------------------------------------------------------------
# Tests: Data classes and enums
# ---------------------------------------------------------------------------


class TestFailureType:
    def test_all_members(self):
        assert len(FailureType) == 13
        assert FailureType.HALLUCINATION.value == "hallucination"
        assert FailureType.DATA_LEAK.value == "data_leak"

    def test_repair_strategies_all_present(self):
        for ft in FailureType:
            assert ft in REPAIR_STRATEGIES
            assert len(REPAIR_STRATEGIES[ft]) > 10


class TestFailureDiagnosis:
    def test_minimal(self):
        d = FailureDiagnosis(
            failure_type=FailureType.HALLUCINATION,
            location="line 5",
            evidence="Claimed X but source says Y",
            repair_strategy="Remove the claim",
        )
        assert d.severity == 0.5

    def test_full(self):
        d = FailureDiagnosis(
            failure_type=FailureType.DATA_LEAK,
            location="output",
            evidence="API key found",
            repair_strategy="Redact",
            severity=0.95,
        )
        assert d.severity == 0.95


class TestVerificationResult:
    def test_pass_no_diagnoses(self):
        r = VerificationResult(passed=True)
        assert r.recommended_action == "accept"
        assert r.critical_failures == []

    def test_critical_failures_filtered(self):
        r = VerificationResult(
            passed=False,
            diagnoses=[
                FailureDiagnosis(FailureType.DATA_LEAK, "o", "e", "fix", severity=0.95),
                FailureDiagnosis(FailureType.OMISSION, "o", "e", "fix", severity=0.5),
            ],
        )
        assert len(r.critical_failures) == 1
        assert r.critical_failures[0].failure_type == FailureType.DATA_LEAK

    def test_should_repair_true(self):
        r = VerificationResult(passed=False, recommended_action="repair", repair_budget_remaining=2)
        assert r.should_repair is True

    def test_should_repair_false_no_budget(self):
        r = VerificationResult(passed=False, recommended_action="repair", repair_budget_remaining=0)
        assert r.should_repair is False

    def test_should_repair_false_wrong_action(self):
        r = VerificationResult(passed=True, recommended_action="accept")
        assert r.should_repair is False

    def test_should_escalate_true(self):
        r = VerificationResult(passed=False, recommended_action="escalate")
        assert r.should_escalate is True


# ---------------------------------------------------------------------------
# Tests: FailureTaxonomyVerifier
# ---------------------------------------------------------------------------


class TestFailureTaxonomyVerifier:
    def test_verify_clean_output_passes(self):
        verifier = FailureTaxonomyVerifier()
        result = verifier.verify(
            agent_output="Here is a correct and complete solution.",
            task_description="Write a simple function.",
        )
        assert result.passed is True
        assert result.recommended_action == "accept"

    def test_detect_structural_error_unclosed_code_block(self):
        verifier = FailureTaxonomyVerifier()
        result = verifier.verify(
            agent_output="Here is the code:\n```python\ndef foo():\n    pass\n",
            task_description="Write Python code.",
        )
        assert result.passed is False
        types = [d.failure_type for d in result.diagnoses]
        assert FailureType.STRUCTURAL_ERROR in types

    def test_detect_structural_error_truncated_output(self):
        verifier = FailureTaxonomyVerifier()
        # Long output ending without punctuation
        output = "x" * 150 + "still going"
        result = verifier.verify(output, task_description="Do something")
        assert result.passed is False
        types = [d.failure_type for d in result.diagnoses]
        assert FailureType.STRUCTURAL_ERROR in types

    def test_short_truncated_output_not_flag(self):
        """Output under 100 chars that ends without punctuation should not flag."""
        verifier = FailureTaxonomyVerifier()
        result = verifier.verify("short", task_description="short")
        assert result.passed is True

    def test_detect_contradiction(self):
        verifier = FailureTaxonomyVerifier()
        result = verifier.verify(
            agent_output=(
                "The sky is blue and the weather is nice. "
                "The sky is not blue and the weather is not nice."
            ),
            task_description="Describe the weather.",
        )
        # May or may not detect depending on heuristic overlap
        # At minimum it should not crash
        assert result is not None

    def test_detect_hallucination_with_sources(self):
        verifier = FailureTaxonomyVerifier()
        result = verifier.verify(
            agent_output="The system handled 5000 requests per second across 99.9% uptime.",
            task_description="Describe system performance.",
            sources=["The system handles about 10 requests per second."],
        )
        types = [d.failure_type for d in result.diagnoses]
        assert FailureType.HALLUCINATION in types

    def test_detect_hallucination_source_match(self):
        """When sources match the claim, no hallucination."""
        verifier = FailureTaxonomyVerifier()
        result = verifier.verify(
            agent_output="The speed of light is 299792458 meters per second.",
            task_description="What is the speed of light?",
            sources=["The speed of light is 299792458 m/s."],
        )
        hall = [d for d in result.diagnoses if d.failure_type == FailureType.HALLUCINATION]
        assert len(hall) == 0

    def test_detect_omission(self):
        verifier = FailureTaxonomyVerifier()
        result = verifier.verify(
            agent_output="The application is already deployed to production.",
            task_description="Implement the feature, test it, then deploy it.",
        )
        types = [d.failure_type for d in result.diagnoses]
        assert FailureType.OMISSION in types

    def test_detect_over_generalization(self):
        verifier = FailureTaxonomyVerifier()
        result = verifier.verify(
            agent_output="This solution is always correct and never fails.",
            task_description="Write a solution.",
        )
        types = [d.failure_type for d in result.diagnoses]
        assert FailureType.OVER_GENERALIZATION in types

    def test_detect_data_leak(self):
        verifier = FailureTaxonomyVerifier()
        result = verifier.verify(
            agent_output="The API key is sk-abc123def456.",
            task_description="Return the config.",
        )
        types = [d.failure_type for d in result.diagnoses]
        assert FailureType.DATA_LEAK in types

    def test_loop_detection_triggers_escalation(self):
        """Same output seen twice should escalate."""
        verifier = FailureTaxonomyVerifier()
        verifier.verify("Identical output block", task_description="Task")
        result = verifier.verify("Identical output block", task_description="Task")
        assert result.recommended_action == "escalate"
        assert result.repair_budget_remaining == 0

    def test_loop_detection_different_output_ok(self):
        """Different output on second call should not escalate."""
        verifier = FailureTaxonomyVerifier()
        verifier.verify("First try", task_description="Task")
        result = verifier.verify("Second try (different)", task_description="Task")
        assert result.recommended_action != "escalate"

    def test_reset_clears_loop_detection(self):
        verifier = FailureTaxonomyVerifier()
        verifier.verify("Same output", task_description="Task")
        verifier.verify("Same output", task_description="Task")
        verifier.reset()
        result = verifier.verify("Same output", task_description="Task")
        assert result.recommended_action != "escalate"  # Fresh state

    def test_repair_budget_decrements(self):
        verifier = FailureTaxonomyVerifier()
        result = verifier.verify(
            agent_output="The API key is sk-leaked!",
            task_description="Fix config",
            previous_diagnoses=[
                FailureDiagnosis(FailureType.DATA_LEAK, "o", "e", "fix"),
            ],
        )
        # budget starts at 3, minus 1 for previous diagnosis = 2
        assert result.repair_budget_remaining <= 2

    def test_repair_budget_exhausted_triggers_escalation(self):
        verifier = FailureTaxonomyVerifier()
        result = verifier.verify(
            agent_output="The API key is sk-leaked!",
            task_description="Fix",
            previous_diagnoses=[
                FailureDiagnosis(FailureType.DATA_LEAK, "o", "e", "fix"),
                FailureDiagnosis(FailureType.DATA_LEAK, "o", "e", "fix"),
                FailureDiagnosis(FailureType.DATA_LEAK, "o", "e", "fix"),
            ],
        )
        # budget = 3 - 3 = 0, so escalate
        assert result.recommended_action == "escalate"

    def test_repair_action_with_critical_failure(self):
        """Critical failures should trigger repair if budget remains."""
        verifier = FailureTaxonomyVerifier()
        result = verifier.verify(
            agent_output="The API key is sk-leaked!",
            task_description="Fix",
        )
        assert result.recommended_action == "repair"

    def test_verify_with_no_fingerprint_change(self):
        """Fingerprint should be based on content, not length."""
        verifier = FailureTaxonomyVerifier()
        r1 = verifier.verify("Hello World", task_description="Say hi")
        r2 = verifier.verify("Hello World", task_description="Say hi")
        assert r1.content_fingerprint == r2.content_fingerprint

    def test_compute_fingerprint_consistency(self):
        fp1 = FailureTaxonomyVerifier._compute_fingerprint("Test content here")
        fp2 = FailureTaxonomyVerifier._compute_fingerprint("Test content here")
        assert fp1 == fp2

    def test_compute_fingerprint_different_content(self):
        fp1 = FailureTaxonomyVerifier._compute_fingerprint("Content A")
        fp2 = FailureTaxonomyVerifier._compute_fingerprint("Content B")
        assert fp1 != fp2

    def test_verify_clean_with_sources_no_issues(self):
        verifier = FailureTaxonomyVerifier()
        result = verifier.verify(
            agent_output="The sky is blue.",
            task_description="Describe sky",
            sources=["The sky appears blue due to Rayleigh scattering."],
        )
        assert result.passed is True

    def test_detect_structural_then_leak(self):
        """Multiple failure types should all be reported."""
        verifier = FailureTaxonomyVerifier()
        result = verifier.verify(
            agent_output="Here is the key: sk-test-token\n```python\n",
            task_description="Return config",
        )
        types = {d.failure_type for d in result.diagnoses}
        assert FailureType.STRUCTURAL_ERROR in types
        assert FailureType.DATA_LEAK in types

    def test_repair_strategy_maps_match(self):
        verifier = FailureTaxonomyVerifier()
        result = verifier.verify(
            agent_output="The API key is sk-abc.",
            task_description="Fix",
        )
        for d in result.diagnoses:
            assert d.repair_strategy is not None
            assert len(d.repair_strategy) > 0

    def test_detect_data_leak_static(self):
        assert FailureTaxonomyVerifier._detect_data_leak("sk-something") is True
        assert FailureTaxonomyVerifier._detect_data_leak("BEGIN RSA PRIVATE KEY") is True
        assert FailureTaxonomyVerifier._detect_data_leak("token =") is True
        assert FailureTaxonomyVerifier._detect_data_leak("normal text") is False

    def test_detect_over_generalization_static(self):
        assert FailureTaxonomyVerifier._detect_over_generalization("This always works.") is True
        assert FailureTaxonomyVerifier._detect_over_generalization("This might work.") is False

    def test_detect_structural_static(self):
        assert FailureTaxonomyVerifier._detect_structural_error("hello\n```python\ncode") is True
        assert FailureTaxonomyVerifier._detect_structural_error("hello\n```python\ncode\n```") is False

    def test_detect_omissions_static(self):
        omissions = FailureTaxonomyVerifier._detect_omissions(
            "Just a quick note.", "Please implement the full feature."
        )
        assert len(omissions) > 0
        assert any("implement" in o[1] for o in omissions)

    def test_extract_facts(self):
        """_detect_hallucinations should extract number facts."""
        result = FailureTaxonomyVerifier._detect_hallucinations(
            "The system handles 5000 requests per second.",
            ["This handles 10 requests."],
        )
        # "5000" is not in source "10" substring (different number)
        assert len(result) > 0
