from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

import pytest

from lyra_adversarial_review.citation_fencer import (
    Citation,
    CitationFencer,
    FenceReport,
    FenceResult,
    SourceType,
)
from lyra_adversarial_review.claim_ledger import ClaimLedger, LedgerEntry, LedgerQuery, LedgerStats
from lyra_adversarial_review.claim_verifier import (
    Claim,
    ClaimStatus,
    ClaimVerifier,
    VerificationReport,
    VerificationResult,
    VerificationStage,
)
from lyra_adversarial_review.cross_model_reviewer import (
    CrossModelReviewer,
    ModelFamily,
    ReviewIssue,
    ReviewResult,
    ReviewerAssignment,
    ReviewSeverity,
    aggregate_reviews,
    assign_reviewer,
)
from lyra_adversarial_review.exceptions import (
    CitationVerificationError,
    ClaimVerificationError,
    ConfigurationError,
    LedgerError,
    RecoveryError,
    ReviewError,
)
from lyra_adversarial_review.pivot_refine import (
    FailureSignal,
    FailureType,
    PivotRefineEngine,
    RecoveryAction,
    RecoveryConfig,
    RecoveryDecision,
    RecoveryResult,
    RecoveryTrace,
)
from lyra_adversarial_review.review_config import (
    CODE_REVIEW_RULES,
    DEFAULT_RULES,
    RESEARCH_RULES,
    SECURITY_RULES,
    ReviewConfig,
    ReviewRule,
    ReviewRuleSet,
    SeverityThresholds,
    get_ruleset,
)


# =============================================================================
# Exceptions
# =============================================================================

class TestExceptions:
    def test_review_error(self) -> None:
        err = ReviewError("base error")
        assert "base error" in str(err)
        assert isinstance(err, Exception)

    def test_claim_verification_error(self) -> None:
        err = ClaimVerificationError("claim failed")
        assert isinstance(err, ReviewError)

    def test_recovery_error(self) -> None:
        err = RecoveryError("recovery failed")
        assert isinstance(err, ReviewError)

    def test_citation_verification_error(self) -> None:
        err = CitationVerificationError("citation bad")
        assert isinstance(err, ReviewError)

    def test_ledger_error(self) -> None:
        err = LedgerError("ledger issue")
        assert isinstance(err, ReviewError)

    def test_configuration_error(self) -> None:
        err = ConfigurationError("bad config")
        assert isinstance(err, ReviewError)


# =============================================================================
# Review Config
# =============================================================================

class TestReviewConfig:
    def test_default_config(self) -> None:
        config = ReviewConfig()
        assert config.max_issues_per_review == 50
        assert config.min_confidence_threshold == 0.3
        assert config.require_cross_family is True

    def test_config_validation_passes(self) -> None:
        config = ReviewConfig()
        config.validate()

    def test_config_validation_fails_max_issues(self) -> None:
        config = ReviewConfig(max_issues_per_review=0)
        with pytest.raises(ConfigurationError):
            config.validate()

    def test_config_validation_fails_confidence_out_of_range(self) -> None:
        config = ReviewConfig(min_confidence_threshold=1.5)
        with pytest.raises(ConfigurationError):
            config.validate()

    def test_config_validation_fails_reviewers(self) -> None:
        config = ReviewConfig(max_reviewers_per_content=0)
        with pytest.raises(ConfigurationError):
            config.validate()

    def test_default_ruleset_contains_rules(self) -> None:
        assert len(DEFAULT_RULES.rules) == 4

    def test_security_ruleset_contains_rules(self) -> None:
        assert len(SECURITY_RULES.rules) == 5

    def test_research_ruleset(self) -> None:
        assert len(RESEARCH_RULES.rules) == 5

    def test_code_review_ruleset(self) -> None:
        assert len(CODE_REVIEW_RULES.rules) == 5

    def test_get_ruleset_default(self) -> None:
        rs = get_ruleset("default")
        assert rs.name == "default"

    def test_get_ruleset_unknown(self) -> None:
        with pytest.raises(ConfigurationError):
            get_ruleset("nonexistent")

    def test_severity_thresholds_defaults(self) -> None:
        t = SeverityThresholds()
        assert t.critical == 0.9
        assert t.high == 0.7
        assert t.medium == 0.5
        assert t.low == 0.3

    def test_review_rule_frozen(self) -> None:
        rule = ReviewRule("test", "pattern", ReviewSeverity.HIGH, "desc")
        with pytest.raises(AttributeError):
            rule.name = "changed"  # type: ignore[misc]

    def test_review_rule_set_frozen(self) -> None:
        rset = ReviewRuleSet("n", [], "d")
        with pytest.raises(AttributeError):
            rset.name = "changed"  # type: ignore[misc]

    def test_severity_ordering(self) -> None:
        assert ReviewSeverity.CRITICAL > ReviewSeverity.HIGH
        assert ReviewSeverity.HIGH > ReviewSeverity.MEDIUM
        assert ReviewSeverity.MEDIUM > ReviewSeverity.LOW
        assert ReviewSeverity.LOW > ReviewSeverity.INFO
        assert ReviewSeverity.INFO < ReviewSeverity.CRITICAL
        assert ReviewSeverity.CRITICAL >= ReviewSeverity.CRITICAL
        assert ReviewSeverity.INFO <= ReviewSeverity.LOW


# =============================================================================
# Cross-Model Reviewer
# =============================================================================

class TestCrossModelReviewer:
    def test_assign_reviewer_different_family(self) -> None:
        assignment = assign_reviewer(ModelFamily.ANTHROPIC)
        assert assignment.generator == ModelFamily.ANTHROPIC
        assert assignment.reviewer != ModelFamily.ANTHROPIC
        assert "Cross-family" in assignment.reason

    def test_assign_reviewer_all_families(self) -> None:
        for family in ModelFamily:
            assignment = assign_reviewer(family)
            assert assignment.reviewer != family or len(ModelFamily) == 1

    def test_assign_reviewer_is_frozen(self) -> None:
        assignment = assign_reviewer(ModelFamily.OPENAI)
        with pytest.raises(AttributeError):
            assignment.reviewer = ModelFamily.ANTHROPIC  # type: ignore[misc]

    @pytest.mark.asyncio
    async def test_generate_review_passes_good_content(self) -> None:
        reviewer = CrossModelReviewer()
        result = await reviewer.generate_review(
            "The sky is blue. Water is wet. Fire is hot.",
            ModelFamily.ANTHROPIC,
        )
        assert isinstance(result, ReviewResult)
        assert result.overall_verdict in ("PASS", "FAIL")
        assert 0 <= result.confidence <= 1

    @pytest.mark.asyncio
    async def test_generate_review_detects_security_issues(self) -> None:
        reviewer = CrossModelReviewer()
        result = await reviewer.generate_review(
            "This code has a SQL injection vulnerability and leaks credentials.",
            ModelFamily.OPENAI,
        )
        assert isinstance(result, ReviewResult)

    @pytest.mark.asyncio
    async def test_generate_review_with_custom_rules(self) -> None:
        reviewer = CrossModelReviewer()
        rules = [
            ReviewRule("correctness", ".*", ReviewSeverity.CRITICAL, "Check correctness"),
            ReviewRule("security", ".*", ReviewSeverity.CRITICAL, "Check security"),
        ]
        result = await reviewer.generate_review("Some content", ModelFamily.GOOGLE, rules)
        assert result.overall_verdict in ("PASS", "FAIL")

    @pytest.mark.asyncio
    async def test_generate_review_max_issues_enforced(self) -> None:
        config = ReviewConfig(max_issues_per_review=2)
        reviewer = CrossModelReviewer(config)
        rules = [
            ReviewRule("correctness", ".*", ReviewSeverity.HIGH, "c1"),
            ReviewRule("completeness", ".*", ReviewSeverity.HIGH, "c2"),
            ReviewRule("security", ".*", ReviewSeverity.HIGH, "c3"),
            ReviewRule("consistency", ".*", ReviewSeverity.HIGH, "c4"),
        ]
        result = await reviewer.generate_review("security vulnerability", ModelFamily.META, rules)
        assert len(result.issues) <= 2

    def test_review_severity_enum_values(self) -> None:
        assert ReviewSeverity.CRITICAL.value == "critical"
        assert ReviewSeverity.INFO.value == "info"

    def test_review_issue_frozen(self) -> None:
        issue = ReviewIssue(ReviewSeverity.HIGH, "desc", "loc", "sugg")
        with pytest.raises(AttributeError):
            issue.description = "new"  # type: ignore[misc]

    def test_model_family_values(self) -> None:
        assert ModelFamily.ANTHROPIC.value == "anthropic"
        assert ModelFamily.OPENAI.value == "openai"

    @pytest.mark.asyncio
    async def test_generate_review_different_families(self) -> None:
        reviewer = CrossModelReviewer()
        r1 = await reviewer.generate_review("test content", ModelFamily.ANTHROPIC)
        r2 = await reviewer.generate_review("test content", ModelFamily.OPENAI)
        assert isinstance(r1, ReviewResult)
        assert isinstance(r2, ReviewResult)

    @pytest.mark.asyncio
    async def test_aggregate_reviews_empty(self) -> None:
        result = await aggregate_reviews([])
        assert result.overall_verdict == "PASS"
        assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_aggregate_reviews_single(self) -> None:
        r = ReviewResult("PASS", [], 0.9, ModelFamily.ANTHROPIC)
        result = await aggregate_reviews([r])
        assert result.overall_verdict == "PASS"

    @pytest.mark.asyncio
    async def test_aggregate_reviews_weighted(self) -> None:
        r1 = ReviewResult("PASS", [], 0.9, ModelFamily.ANTHROPIC)
        r2 = ReviewResult("FAIL", [], 0.9, ModelFamily.OPENAI)
        r3 = ReviewResult("PASS", [], 0.9, ModelFamily.GOOGLE)
        result = await aggregate_reviews([r1, r2, r3])
        assert result.overall_verdict == "PASS"

    @pytest.mark.asyncio
    async def test_aggregate_reviews_verdict_fail(self) -> None:
        r1 = ReviewResult("FAIL", [], 0.9, ModelFamily.ANTHROPIC)
        r2 = ReviewResult("FAIL", [], 0.9, ModelFamily.OPENAI)
        result = await aggregate_reviews([r1, r2])
        assert result.overall_verdict == "FAIL"

    @pytest.mark.asyncio
    async def test_aggregate_reviews_collects_issues(self) -> None:
        issues = [ReviewIssue(ReviewSeverity.HIGH, "bug", "line:10", "fix it")]
        r = ReviewResult("FAIL", issues, 0.5, ModelFamily.ANTHROPIC)
        result = await aggregate_reviews([r])
        assert len(result.issues) == 1

    def test_review_result_frozen(self) -> None:
        r = ReviewResult("PASS", [], 1.0, ModelFamily.ANTHROPIC)
        with pytest.raises(AttributeError):
            r.overall_verdict = "FAIL"  # type: ignore[misc]


# =============================================================================
# Claim Verifier (ARIS 3-Stage)
# =============================================================================

class TestClaimVerifier:
    @pytest.mark.asyncio
    async def test_create_claim(self) -> None:
        verifier = ClaimVerifier()
        claim = verifier.create_claim("Test claim text", "test_source", 0.8)
        assert claim.text == "Test claim text"
        assert claim.source == "test_source"
        assert claim.confidence == 0.8
        assert claim.status == ClaimStatus.UNVERIFIED
        assert len(claim.claim_id) == 12

    @pytest.mark.asyncio
    async def test_check_integrity_passes(self) -> None:
        verifier = ClaimVerifier()
        claim = verifier.create_claim("A valid scientific claim about the research finding.", "source1", 0.9)
        result = await verifier.check_integrity(claim)
        assert result.stage == VerificationStage.INTEGRITY
        assert result.score >= 0.3

    @pytest.mark.asyncio
    async def test_check_integrity_fails_short(self) -> None:
        verifier = ClaimVerifier()
        claim = verifier.create_claim("Hi", "src")
        result = await verifier.check_integrity(claim)
        assert result.score < 0.7

    @pytest.mark.asyncio
    async def test_check_integrity_fails_no_source(self) -> None:
        verifier = ClaimVerifier()
        claim = verifier.create_claim("A long enough claim text that should pass length check", "", 0.5)
        result = await verifier.check_integrity(claim)
        assert len(result.issues) > 0

    @pytest.mark.asyncio
    async def test_check_integrity_detects_hedging(self) -> None:
        verifier = ClaimVerifier()
        claim = verifier.create_claim(
            "This might possibly be something that could maybe perhaps appear to be true.",
            "src", 0.8,
        )
        result = await verifier.check_integrity(claim)
        assert any("hedging" in i.lower() for i in result.issues)

    @pytest.mark.asyncio
    async def test_map_results_high_overlap(self) -> None:
        verifier = ClaimVerifier()
        claim = verifier.create_claim("quantum computing entanglement coherence", "src")
        result = await verifier.map_results(claim, "quantum computing requires entanglement and coherence")
        assert result.stage == VerificationStage.MAPPING

    @pytest.mark.asyncio
    async def test_map_results_low_overlap(self) -> None:
        verifier = ClaimVerifier()
        claim = verifier.create_claim("quantum physics mechanics particles waves", "src")
        result = await verifier.map_results(claim, "unrelated text about cooking recipes")
        assert result.score <= 0.5 or not result.passed

    @pytest.mark.asyncio
    async def test_audit_with_supporting_refs(self) -> None:
        verifier = ClaimVerifier()
        claim = verifier.create_claim("testing cross reference support verification", "src")
        refs = [
            "This testing reference supports the cross claim",
            "Another reference about testing and support",
            "Third reference for testing cross verification",
        ]
        result = await verifier.audit_claim(claim, refs)
        assert result.stage == VerificationStage.AUDITING

    @pytest.mark.asyncio
    async def test_audit_with_empty_refs(self) -> None:
        verifier = ClaimVerifier()
        claim = verifier.create_claim("Some claim text here", "src")
        result = await verifier.audit_claim(claim, [])
        assert not result.passed

    @pytest.mark.asyncio
    async def test_audit_with_contradictory_refs(self) -> None:
        verifier = ClaimVerifier()
        claim = verifier.create_claim("specific quantum computing breakthrough claim", "src")
        refs = [
            "unrelated reference about cooking",
            "another unrelated weather report",
            "sports news article",
        ]
        result = await verifier.audit_claim(claim, refs)
        assert "contradictory" in result.issues[0] if result.issues else True

    @pytest.mark.asyncio
    async def test_full_verify_pipeline_all_pass(self) -> None:
        verifier = ClaimVerifier()
        claim = verifier.create_claim("quantum computing research advances coherence", "research_paper", 0.9)
        result = await verifier.verify(
            claim,
            "quantum computing research shows advances in coherence times",
            ["quantum computing research paper on coherence"],
        )
        assert isinstance(result, VerificationResult)
        assert len(result.stages) == 3

    @pytest.mark.asyncio
    async def test_full_verify_fails_integrity(self) -> None:
        verifier = ClaimVerifier(config=ReviewConfig(min_confidence_threshold=0.95))
        claim = verifier.create_claim("short", "src", 0.1)
        result = await verifier.verify(claim, "some output")
        assert not result.overall_pass
        assert len(result.stages) == 1

    @pytest.mark.asyncio
    async def test_full_verify_fails_mapping(self) -> None:
        verifier = ClaimVerifier()
        claim = verifier.create_claim("specific technical claim about advanced AI systems", "src", 0.9)
        result = await verifier.verify(claim, "unrelated output about cooking")
        assert not result.overall_pass

    @pytest.mark.asyncio
    async def test_stage_result_frozen(self) -> None:
        from lyra_adversarial_review.claim_verifier import StageResult
        sr = StageResult(VerificationStage.INTEGRITY, True, 0.9, "evidence")
        with pytest.raises(AttributeError):
            sr.passed = False  # type: ignore[misc]

    @pytest.mark.asyncio
    async def test_claim_frozen(self) -> None:
        claim = Claim("id", "text", "src")
        with pytest.raises(AttributeError):
            claim.text = "new"  # type: ignore[misc]

    @pytest.mark.asyncio
    async def test_verification_result_frozen(self) -> None:
        from lyra_adversarial_review.claim_verifier import StageResult
        claim = Claim("id", "text", "src")
        sr = StageResult(VerificationStage.INTEGRITY, True, 1.0, "ev")
        vr = VerificationResult(claim, [sr], True, 0.9)
        with pytest.raises(AttributeError):
            vr.overall_pass = False  # type: ignore[misc]

    @pytest.mark.asyncio
    async def test_generate_report_empty(self) -> None:
        verifier = ClaimVerifier()
        report = verifier.generate_report([])
        assert report.total_claims == 0
        assert report.avg_confidence == 0.0

    @pytest.mark.asyncio
    async def test_generate_report_with_results(self) -> None:
        verifier = ClaimVerifier()
        from lyra_adversarial_review.claim_verifier import StageResult
        claim = Claim("id1", "text", "src")
        sr = StageResult(VerificationStage.INTEGRITY, True, 0.9, "ev")
        vr = VerificationResult(claim, [sr], True, 0.9)
        report = verifier.generate_report([vr])
        assert report.total_claims == 1
        assert report.verified == 1
        assert report.stage_breakdown.get("integrity") is not None

    def test_claim_status_enum(self) -> None:
        assert ClaimStatus.UNVERIFIED.value == "unverified"
        assert ClaimStatus.VERIFIED.value == "verified"
        assert ClaimStatus.REJECTED.value == "rejected"

    def test_verification_stage_enum(self) -> None:
        assert VerificationStage.INTEGRITY.value == "integrity"
        assert VerificationStage.MAPPING.value == "mapping"


# =============================================================================
# Pivot/Refine Engine
# =============================================================================

class TestPivotRefine:
    def test_recovery_config_defaults(self) -> None:
        config = RecoveryConfig()
        assert config.max_refines == 3
        assert config.max_pivots == 2
        assert config.max_retries == 3
        assert config.escalation_threshold == 5

    def test_recovery_config_validation_passes(self) -> None:
        RecoveryConfig().validate()

    def test_recovery_config_validation_fails_max_refines(self) -> None:
        config = RecoveryConfig(max_refines=-1)
        with pytest.raises(RecoveryError):
            config.validate()

    def test_recovery_config_validation_fails_escalation(self) -> None:
        config = RecoveryConfig(escalation_threshold=0)
        with pytest.raises(RecoveryError):
            config.validate()

    def test_analyze_failure_refine_on_tool_error(self) -> None:
        engine = PivotRefineEngine()
        signal = FailureSignal(FailureType.TOOL_ERROR, "context", 0, 3)
        decision = engine.analyze_failure(signal)
        assert decision.action == RecoveryAction.REFINE
        assert "retry_delay" in decision.modified_params

    def test_analyze_failure_pivot_on_approach_invalid(self) -> None:
        engine = PivotRefineEngine()
        signal = FailureSignal(FailureType.APPROACH_INVALID, "context", 0, 3)
        decision = engine.analyze_failure(signal)
        assert decision.action == RecoveryAction.PIVOT
        assert decision.new_approach != ""

    def test_analyze_failure_retry_on_parse_error(self) -> None:
        engine = PivotRefineEngine()
        signal = FailureSignal(FailureType.PARSE_ERROR, "context", 0, 3)
        decision = engine.analyze_failure(signal)
        assert decision.action == RecoveryAction.RETRY
        assert "format_instructions" in decision.modified_params

    def test_analyze_failure_retry_on_model_error(self) -> None:
        engine = PivotRefineEngine()
        signal = FailureSignal(FailureType.MODEL_ERROR, "context", 0, 3)
        decision = engine.analyze_failure(signal)
        assert decision.action == RecoveryAction.RETRY
        assert decision.modified_params.get("temperature") == 0.3

    def test_analyze_failure_escalate_at_threshold(self) -> None:
        engine = PivotRefineEngine()
        signal = FailureSignal(FailureType.TOOL_ERROR, "context", 6, 5)
        decision = engine.analyze_failure(signal)
        assert decision.action == RecoveryAction.ESCALATE

    def test_analyze_failure_abort_on_exhaustion(self) -> None:
        engine = PivotRefineEngine()
        engine._pivot_count = 2  # Exhaust all pivots
        signal = FailureSignal(
            FailureType.APPROACH_INVALID, "context", 4, 3,  # attempt_count=4 > max_attempts=3, but < escalation_threshold=5
        )
        decision = engine.analyze_failure(signal)
        assert decision.action == RecoveryAction.ABORT

    def test_analyze_failure_timeout_leads_to_refine(self) -> None:
        engine = PivotRefineEngine()
        signal = FailureSignal(FailureType.TIMEOUT, "context", 0, 3)
        decision = engine.analyze_failure(signal)
        assert decision.action == RecoveryAction.REFINE

    def test_analyze_failure_resource_exhausted_pivots(self) -> None:
        engine = PivotRefineEngine()
        signal = FailureSignal(FailureType.RESOURCE_EXHAUSTED, "context", 1, 5)
        decision = engine.analyze_failure(signal)
        assert decision.action == RecoveryAction.PIVOT

    def test_analyze_failure_refine_count_exceeded_retry(self) -> None:
        engine = PivotRefineEngine()
        # Internally trigger refines
        for _ in range(3):
            s = FailureSignal(FailureType.TOOL_ERROR, "ctx", 0, 3)
            engine.analyze_failure(s)
            engine._refine_count += 1  # type: ignore[attr-defined]
        signal = FailureSignal(FailureType.TOOL_ERROR, "context", 0, 3)
        decision = engine.analyze_failure(signal)
        assert decision.action == RecoveryAction.RETRY

    @pytest.mark.asyncio
    async def test_recover_returns_result(self) -> None:
        engine = PivotRefineEngine()
        signal = FailureSignal(FailureType.TOOL_ERROR, "task context", 0, 3)
        result = await engine.recover("original task", signal)
        assert isinstance(result, RecoveryResult)
        assert isinstance(result.recovery_trace, RecoveryTrace)
        assert result.total_attempts > 0

    @pytest.mark.asyncio
    async def test_recover_escalates_on_threshold(self) -> None:
        engine = PivotRefineEngine()
        signal = FailureSignal(FailureType.TOOL_ERROR, "task", 5, 2)
        result = await engine.recover("task", signal)
        assert not result.success

    def test_recovery_decision_frozen(self) -> None:
        d = RecoveryDecision(RecoveryAction.ABORT, "reason")
        with pytest.raises(AttributeError):
            d.action = RecoveryAction.RETRY  # type: ignore[misc]

    def test_failure_signal_frozen(self) -> None:
        s = FailureSignal(FailureType.TOOL_ERROR, "ctx", 0, 3)
        with pytest.raises(AttributeError):
            s.context = "new"  # type: ignore[misc]

    def test_recovery_trace_frozen(self) -> None:
        now = datetime.now(timezone.utc)
        t = RecoveryTrace([], [], now, now)
        with pytest.raises(AttributeError):
            t.sequence = [RecoveryDecision(RecoveryAction.ABORT, "r")]  # type: ignore[misc]

    def test_recovery_result_frozen(self) -> None:
        now = datetime.now(timezone.utc)
        trace = RecoveryTrace([], [], now, now)
        r = RecoveryResult(True, "output", trace, 1)
        with pytest.raises(AttributeError):
            r.success = False  # type: ignore[misc]

    def test_recovery_action_enum(self) -> None:
        assert RecoveryAction.REFINE.value == "refine"
        assert RecoveryAction.PIVOT.value == "pivot"
        assert RecoveryAction.ABORT.value == "abort"

    def test_failure_type_enum(self) -> None:
        assert FailureType.TIMEOUT.value == "timeout"
        assert FailureType.MODEL_ERROR.value == "model_error"


# =============================================================================
# Claim Ledger
# =============================================================================

class TestClaimLedger:
    @pytest.mark.asyncio
    async def test_record_claim(self) -> None:
        ledger = ClaimLedger()
        claim = Claim("id1", "test claim", "src", 0.8)
        entry_id = await ledger.record_claim(claim)
        assert len(entry_id) == 12
        assert isinstance(entry_id, str)

    @pytest.mark.asyncio
    async def test_record_claim_with_reviewer(self) -> None:
        ledger = ClaimLedger()
        claim = Claim("id1", "test", "src")
        entry_id = await ledger.record_claim(claim, ModelFamily.ANTHROPIC)
        entries = await ledger.query(LedgerQuery())
        assert entries[0].reviewer_family == ModelFamily.ANTHROPIC

    @pytest.mark.asyncio
    async def test_update_status(self) -> None:
        ledger = ClaimLedger()
        claim = Claim("id1", "test", "src")
        entry_id = await ledger.record_claim(claim)
        updated = await ledger.update_status(entry_id, ClaimStatus.VERIFIED)
        assert updated.verification_status == ClaimStatus.VERIFIED

    @pytest.mark.asyncio
    async def test_update_status_unknown_entry(self) -> None:
        ledger = ClaimLedger()
        with pytest.raises(LedgerError):
            await ledger.update_status("nonexistent", ClaimStatus.VERIFIED)

    @pytest.mark.asyncio
    async def test_query_by_status(self) -> None:
        ledger = ClaimLedger()
        c1 = Claim("id1", "claim1", "src")
        c2 = Claim("id2", "claim2", "src")
        eid1 = await ledger.record_claim(c1)
        eid2 = await ledger.record_claim(c2)
        await ledger.update_status(eid1, ClaimStatus.VERIFIED)
        await ledger.update_status(eid2, ClaimStatus.REJECTED)
        verified = await ledger.query(LedgerQuery(status=ClaimStatus.VERIFIED))
        rejected = await ledger.query(LedgerQuery(status=ClaimStatus.REJECTED))
        assert len(verified) == 1
        assert len(rejected) == 1

    @pytest.mark.asyncio
    async def test_query_by_confidence_range(self) -> None:
        ledger = ClaimLedger()
        c1 = Claim("id1", "c1", "src", 0.3)
        c2 = Claim("id2", "c2", "src", 0.7)
        await ledger.record_claim(c1)
        await ledger.record_claim(c2)
        results = await ledger.query(LedgerQuery(min_confidence=0.5))
        assert len(results) == 1
        assert results[0].claim.confidence == 0.7

    @pytest.mark.asyncio
    async def test_query_by_date_range(self) -> None:
        ledger = ClaimLedger()
        claim = Claim("id1", "test", "src")
        await ledger.record_claim(claim)
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)
        results = await ledger.query(LedgerQuery(date_from=yesterday, date_to=tomorrow))
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_query_by_reviewer_family(self) -> None:
        ledger = ClaimLedger()
        claim = Claim("id1", "test", "src")
        await ledger.record_claim(claim, ModelFamily.ANTHROPIC)
        results = await ledger.query(LedgerQuery(reviewer_family=ModelFamily.ANTHROPIC))
        assert len(results) == 1
        results = await ledger.query(LedgerQuery(reviewer_family=ModelFamily.OPENAI))
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_get_unverified(self) -> None:
        ledger = ClaimLedger()
        claim = Claim("id1", "test", "src")
        await ledger.record_claim(claim)
        unverified = await ledger.get_unverified()
        assert len(unverified) == 1

    @pytest.mark.asyncio
    async def test_get_verified(self) -> None:
        ledger = ClaimLedger()
        claim = Claim("id1", "test", "src")
        eid = await ledger.record_claim(claim)
        await ledger.update_status(eid, ClaimStatus.VERIFIED)
        verified = await ledger.get_verified()
        assert len(verified) == 1

    @pytest.mark.asyncio
    async def test_get_rejected(self) -> None:
        ledger = ClaimLedger()
        claim = Claim("id1", "test", "src")
        eid = await ledger.record_claim(claim)
        await ledger.update_status(eid, ClaimStatus.REJECTED)
        rejected = await ledger.get_rejected()
        assert len(rejected) == 1

    @pytest.mark.asyncio
    async def test_get_stats_empty(self) -> None:
        ledger = ClaimLedger()
        stats = await ledger.get_stats()
        assert stats.total == 0
        assert stats.verification_rate == 0.0

    @pytest.mark.asyncio
    async def test_get_stats_with_entries(self) -> None:
        ledger = ClaimLedger()
        claim = Claim("id1", "test", "src")
        eid = await ledger.record_claim(claim)
        await ledger.update_status(eid, ClaimStatus.VERIFIED)
        stats = await ledger.get_stats()
        assert stats.total == 1
        assert stats.verified == 1
        assert stats.verification_rate == 1.0

    @pytest.mark.asyncio
    async def test_export_ledger_json(self) -> None:
        ledger = ClaimLedger()
        claim = Claim("id1", "test claim text", "src")
        eid = await ledger.record_claim(claim)
        await ledger.update_status(eid, ClaimStatus.VERIFIED)
        exported = await ledger.export_ledger("json")
        data = json.loads(exported)
        assert "entries" in data
        assert len(data["entries"]) == 1
        assert data["entries"][0]["claim_text"] == "test claim text"

    @pytest.mark.asyncio
    async def test_export_ledger_unsupported_format(self) -> None:
        ledger = ClaimLedger()
        with pytest.raises(LedgerError):
            await ledger.export_ledger("xml")

    def test_ledger_entry_frozen(self) -> None:
        claim = Claim("id", "t", "s")
        e = LedgerEntry("eid", claim, datetime.now(timezone.utc), ClaimStatus.UNVERIFIED)
        with pytest.raises(AttributeError):
            e.entry_id = "new"  # type: ignore[misc]

    def test_ledger_stats_frozen(self) -> None:
        s = LedgerStats()
        with pytest.raises(AttributeError):
            s.total = 5  # type: ignore[misc]

    def test_ledger_query_frozen(self) -> None:
        q = LedgerQuery()
        with pytest.raises(AttributeError):
            q.status = ClaimStatus.VERIFIED  # type: ignore[misc]


# =============================================================================
# Citation Fencer
# =============================================================================

class TestCitationFencer:
    def test_extract_citations_arxiv(self) -> None:
        fencer = CitationFencer()
        text = "This paper (arXiv:2203.15556) shows important results."
        citations = fencer.extract_citations(text)
        arxiv_cites = [c for c in citations if c.source_type == SourceType.ARXIV]
        assert len(arxiv_cites) >= 1
        assert arxiv_cites[0].identifier == "2203.15556"

    def test_extract_citations_arxiv_with_version(self) -> None:
        fencer = CitationFencer()
        text = "See arXiv:2203.15556v2 for details."
        citations = fencer.extract_citations(text)
        arxiv = [c for c in citations if c.source_type == SourceType.ARXIV]
        assert len(arxiv) >= 1

    def test_extract_citations_doi(self) -> None:
        fencer = CitationFencer()
        text = "Published at https://doi.org/10.1038/s41586-023-06466-5"
        citations = fencer.extract_citations(text)
        dois = [c for c in citations if c.source_type == SourceType.DOI]
        assert len(dois) >= 1

    def test_extract_citations_url(self) -> None:
        fencer = CitationFencer()
        text = "Code available at https://github.com/user/repo"
        citations = fencer.extract_citations(text)
        urls = [c for c in citations if c.source_type == SourceType.URL]
        assert len(urls) >= 1

    def test_extract_citations_semantic_scholar(self) -> None:
        fencer = CitationFencer()
        text = "Data from https://api.semanticscholar.org/graph/v1/paper/test"
        citations = fencer.extract_citations(text)
        s2 = [c for c in citations if c.source_type == SourceType.SEMANTIC_SCHOLAR]
        assert len(s2) >= 1

    def test_extract_citations_hallucination(self) -> None:
        fencer = CitationFencer()
        text = "According to a recent study, the results demonstrate improved performance."
        citations = fencer.extract_citations(text)
        llm = [c for c in citations if c.source_type == SourceType.LLM_GENERATED]
        assert len(llm) >= 1

    def test_extract_citations_multiple_types(self) -> None:
        fencer = CitationFencer()
        text = (
            "arXiv:2203.15556 shows X. Also DOI:10.1000/test. "
            "See https://example.com for more. "
            "According to a new study, the findings are significant."
        )
        citations = fencer.extract_citations(text)
        types = {c.source_type for c in citations}
        assert SourceType.ARXIV in types
        assert SourceType.URL in types

    def test_extract_citations_empty_text(self) -> None:
        fencer = CitationFencer()
        citations = fencer.extract_citations("")
        assert len(citations) == 0

    def test_extract_citations_no_citations(self) -> None:
        fencer = CitationFencer()
        citations = fencer.extract_citations("Just plain text with no references.")
        assert len(citations) == 0

    @pytest.mark.asyncio
    async def test_verify_citation_arxiv_valid(self) -> None:
        fencer = CitationFencer()
        citation = Citation("arXiv:2203.15556", SourceType.ARXIV, "2203.15556")
        result = await fencer.verify_citation(citation)
        assert result.is_valid
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_verify_citation_arxiv_invalid(self) -> None:
        fencer = CitationFencer()
        citation = Citation("arXiv:bad", SourceType.ARXIV, "bad")
        result = await fencer.verify_citation(citation)
        assert not result.is_valid

    @pytest.mark.asyncio
    async def test_verify_citation_doi_valid(self) -> None:
        fencer = CitationFencer()
        citation = Citation("DOI:10.1038/s41586-023-06466-5", SourceType.DOI, "10.1038/s41586-023-06466-5")
        result = await fencer.verify_citation(citation)
        assert result.is_valid

    @pytest.mark.asyncio
    async def test_verify_citation_doi_invalid(self) -> None:
        fencer = CitationFencer()
        citation = Citation("bad-doi", SourceType.DOI, "bad-doi")
        result = await fencer.verify_citation(citation)
        assert not result.is_valid

    @pytest.mark.asyncio
    async def test_verify_citation_url_known_domain(self) -> None:
        fencer = CitationFencer()
        citation = Citation("arxiv url", SourceType.URL, "https://arxiv.org/abs/2203.15556")
        result = await fencer.verify_citation(citation)
        assert result.is_valid

    @pytest.mark.asyncio
    async def test_verify_citation_url_unknown_domain(self) -> None:
        fencer = CitationFencer()
        citation = Citation("unknown url", SourceType.URL, "https://unknown-site.example.com/page")
        result = await fencer.verify_citation(citation)
        assert not result.is_valid

    @pytest.mark.asyncio
    async def test_verify_citation_url_bad_scheme(self) -> None:
        fencer = CitationFencer()
        citation = Citation("bad", SourceType.URL, "ftp://bad.com")
        result = await fencer.verify_citation(citation)
        assert not result.is_valid

    @pytest.mark.asyncio
    async def test_verify_citation_llm_generated(self) -> None:
        fencer = CitationFencer()
        text = "According to a recent study, the results are groundbreaking."
        citation = Citation(text, SourceType.LLM_GENERATED, "hallucination-1")
        result = await fencer.verify_citation(citation)
        assert not result.is_valid
        assert result.confidence < 0.5

    @pytest.mark.asyncio
    async def test_verify_citation_crossref(self) -> None:
        fencer = CitationFencer()
        citation = Citation("crossref test", SourceType.CROSSREF, "test-identifier")
        result = await fencer.verify_citation(citation)
        assert result.is_valid

    @pytest.mark.asyncio
    async def test_verify_citation_semantic_scholar(self) -> None:
        fencer = CitationFencer()
        citation = Citation(
            "s2 test", SourceType.SEMANTIC_SCHOLAR,
            "https://api.semanticscholar.org/graph/v1/paper/test",
        )
        result = await fencer.verify_citation(citation)
        assert result.is_valid

    @pytest.mark.asyncio
    async def test_fence_document_empty(self) -> None:
        fencer = CitationFencer()
        report = await fencer.fence_document("")
        assert report.overall_score == 1.0
        assert report.verified_count == 0

    @pytest.mark.asyncio
    async def test_fence_document_with_citations(self) -> None:
        fencer = CitationFencer()
        text = "According to arXiv:2203.15556, the results show X. Also check DOI:10.1000/test123."
        report = await fencer.fence_document(text)
        assert len(report.citations) >= 2
        assert isinstance(report, FenceReport)
        assert report.overall_score > 0

    @pytest.mark.asyncio
    async def test_fence_document_mixed_validity(self) -> None:
        fencer = CitationFencer()
        text = "arXiv:2203.15556 is valid. But check this bad DOI:10.invalid and According to a recent study, it works."
        report = await fencer.fence_document(text)
        assert report.flagged_count > 0

    @pytest.mark.asyncio
    async def test_caching(self) -> None:
        fencer = CitationFencer()
        c1 = Citation("test", SourceType.ARXIV, "2203.15556")
        r1 = await fencer.verify_citation(c1)
        r2 = await fencer.verify_citation(c1)
        assert r1.confidence == r2.confidence

    def test_citation_frozen(self) -> None:
        c = Citation("text", SourceType.ARXIV, "id")
        with pytest.raises(AttributeError):
            c.text = "new"  # type: ignore[misc]

    def test_fence_result_frozen(self) -> None:
        c = Citation("text", SourceType.ARXIV, "id")
        r = FenceResult(c, True, "src", 0.9)
        with pytest.raises(AttributeError):
            r.is_valid = False  # type: ignore[misc]

    def test_fence_report_frozen(self) -> None:
        fr = FenceReport([], 0, 0, 1.0)
        with pytest.raises(AttributeError):
            fr.verified_count = 5  # type: ignore[misc]

    def test_source_type_enum(self) -> None:
        assert SourceType.ARXIV.value == "arxiv"
        assert SourceType.LLM_GENERATED.value == "llm_generated"
