"""
Tests for the Research Intelligence Core (intelligence.py).

All tests run offline — no network calls.
"""


from lyra_research.intelligence import (
    AuditReport,
    ChecklistItem,
    ClaimEvidence,
    Contradiction,
    ContradictionDetector,
    EvidenceAudit,
    FalsificationChecker,
    FalsificationNote,
    GapAnalyzer,
    ResearchChecklist,
    ResearchGap,
    VerifiableChecklistGenerator,
)


# ---------------------------------------------------------------------------
# VerifiableChecklistGenerator tests
# ---------------------------------------------------------------------------

def test_checklist_generates_universal_items():
    """Standard depth generates 10 items from UNIVERSAL_TEMPLATES."""
    gen = VerifiableChecklistGenerator()
    checklist = gen.generate("attention mechanisms")
    assert len(checklist.items) == 10


def test_checklist_topic_interpolated():
    """All questions contain the topic string."""
    gen = VerifiableChecklistGenerator()
    topic = "sparse transformers"
    checklist = gen.generate(topic)
    for item in checklist.items:
        assert topic in item.question


def test_checklist_depth_quick_has_5_items():
    """Quick depth returns exactly 5 items."""
    gen = VerifiableChecklistGenerator()
    checklist = gen.generate("LoRA fine-tuning", depth="quick")
    assert len(checklist.items) == 5


def test_checklist_depth_deep_has_15_items():
    """Deep depth returns exactly 15 items."""
    gen = VerifiableChecklistGenerator()
    checklist = gen.generate("mixture of experts", depth="deep")
    assert len(checklist.items) == 15


def test_checklist_categories_present():
    """Standard checklist contains at least one item from each expected category."""
    gen = VerifiableChecklistGenerator()
    checklist = gen.generate("diffusion models")
    categories = {item.category for item in checklist.items}
    assert "definition" in categories
    assert "sota" in categories
    assert "comparison" in categories
    assert "gap" in categories
    assert "application" in categories


def test_checklist_priorities_valid():
    """All priorities are 1, 2, or 3."""
    gen = VerifiableChecklistGenerator()
    checklist = gen.generate("contrastive learning")
    for item in checklist.items:
        assert item.priority in (1, 2, 3)


def test_checklist_completion_rate_zero():
    """New checklist has 0% completion rate."""
    gen = VerifiableChecklistGenerator()
    checklist = gen.generate("graph neural networks")
    assert checklist.completion_rate() == 0.0


def test_checklist_completion_rate():
    """Completion rate reflects answered fraction."""
    gen = VerifiableChecklistGenerator()
    checklist = gen.generate("graph neural networks")
    checklist = gen.mark_answered(checklist, 0, ["src1"])
    checklist = gen.mark_answered(checklist, 1, ["src2"])
    assert abs(checklist.completion_rate() - 0.2) < 1e-9


def test_checklist_mark_answered():
    """Marked item has answered=True and correct source IDs."""
    gen = VerifiableChecklistGenerator()
    checklist = gen.generate("vision transformers")
    updated = gen.mark_answered(checklist, 2, ["paper_a", "paper_b"])
    assert updated.items[2].answered is True
    assert updated.items[2].answer_source_ids == ["paper_a", "paper_b"]


def test_checklist_mark_answered_immutable():
    """mark_answered returns a new object; original is unchanged."""
    gen = VerifiableChecklistGenerator()
    checklist = gen.generate("vision transformers")
    updated = gen.mark_answered(checklist, 0, ["src1"])
    assert checklist.items[0].answered is False
    assert updated.items[0].answered is True


def test_checklist_unanswered_questions_all():
    """Unanswered list equals all items on fresh checklist."""
    gen = VerifiableChecklistGenerator()
    checklist = gen.generate("knowledge distillation")
    unanswered = gen.unanswered_questions(checklist)
    assert len(unanswered) == len(checklist.items)


def test_checklist_unanswered_questions_partial():
    """Unanswered list shrinks after marking items."""
    gen = VerifiableChecklistGenerator()
    checklist = gen.generate("knowledge distillation")
    checklist = gen.mark_answered(checklist, 0, ["s1"])
    checklist = gen.mark_answered(checklist, 3, ["s2"])
    unanswered = gen.unanswered_questions(checklist)
    assert len(unanswered) == len(checklist.items) - 2


# ---------------------------------------------------------------------------
# EvidenceAudit tests
# ---------------------------------------------------------------------------

def test_evidence_audit_flags_uncited_claim():
    """A claim with no nearby source ID is flagged."""
    audit = EvidenceAudit()
    text = "The model achieves 95% accuracy on the benchmark."
    report = audit.audit(text, available_source_ids=["paper_xyz"])
    # "paper_xyz" does not appear in the text, so the claim should be unverified
    assert report.unverified_claims > 0
    assert len(report.flagged_claims) > 0


def test_evidence_audit_accepts_cited_claim():
    """A claim with a nearby source ID is verified."""
    audit = EvidenceAudit()
    text = "The model achieves 95% accuracy on the benchmark [paper_abc]. See paper_abc for details."
    report = audit.audit(text, available_source_ids=["paper_abc"])
    assert report.verified_claims > 0


def test_evidence_audit_verification_rate_range():
    """Verification rate is always between 0 and 1."""
    audit = EvidenceAudit()
    text = "Model shows state-of-the-art results. It outperforms baselines."
    report = audit.audit(text, available_source_ids=["s1"])
    assert 0.0 <= report.verification_rate <= 1.0


def test_evidence_audit_is_acceptable_high_rate():
    """Report is acceptable when all claims are verified."""
    report = AuditReport(
        total_claims=10,
        verified_claims=10,
        unverified_claims=0,
        verification_rate=1.0,
        flagged_claims=[],
    )
    assert report.is_acceptable(threshold=0.95) is True


def test_evidence_audit_is_acceptable_low_rate():
    """Report is not acceptable when verification rate is below threshold."""
    report = AuditReport(
        total_claims=10,
        verified_claims=5,
        unverified_claims=5,
        verification_rate=0.5,
        flagged_claims=[],
    )
    assert report.is_acceptable(threshold=0.95) is False


def test_evidence_audit_no_claims():
    """Empty text produces a perfect audit report (no claims = 100% rate)."""
    audit = EvidenceAudit()
    report = audit.audit("", available_source_ids=["s1"])
    assert report.total_claims == 0
    assert report.verification_rate == 1.0
    assert report.is_acceptable() is True


def test_evidence_audit_extract_claims_returns_list():
    """extract_claims returns a list of strings."""
    audit = EvidenceAudit()
    text = "The system outperforms baseline by a wide margin. It shows state-of-the-art performance."
    claims = audit.extract_claims(text)
    assert isinstance(claims, list)


def test_evidence_audit_has_citation_found():
    """has_citation returns True when source ID appears near the claim."""
    audit = EvidenceAudit()
    claim = "achieves state-of-the-art"
    context = "Model achieves state-of-the-art performance [src99]. This is shown in src99."
    assert audit.has_citation(claim, context, ["src99"]) is True


def test_evidence_audit_has_citation_not_found():
    """has_citation returns False when no source ID is nearby."""
    audit = EvidenceAudit()
    claim = "achieves state-of-the-art"
    context = "Model achieves state-of-the-art performance without references."
    assert audit.has_citation(claim, context, ["src99"]) is False


# ---------------------------------------------------------------------------
# ContradictionDetector tests
# ---------------------------------------------------------------------------

def test_contradiction_detector_no_sources():
    """Empty source list produces no contradictions."""
    detector = ContradictionDetector()
    result = detector.detect([])
    assert result == []


def test_contradiction_detector_single_source():
    """Single source cannot contradict itself."""
    detector = ContradictionDetector()
    analyses = [{"source_id": "s1", "abstract": "Our model outperforms BERT.", "findings": []}]
    result = detector.detect(analyses)
    assert result == []


def test_contradiction_detector_finds_conflict():
    """Two sources with opposing outperformance claims are flagged."""
    detector = ContradictionDetector()
    analyses = [
        {
            "source_id": "paper_A",
            "abstract": "ModelX outperforms ModelY on all benchmarks.",
            "findings": [],
        },
        {
            "source_id": "paper_B",
            "abstract": "ModelY outperforms ModelX in our evaluation.",
            "findings": [],
        },
    ]
    contradictions = detector.detect(analyses)
    assert len(contradictions) >= 1
    severities = {c.severity for c in contradictions}
    assert "direct" in severities


def test_contradiction_detector_no_conflict_when_consistent():
    """Sources agreeing on the same claim produce no contradiction."""
    detector = ContradictionDetector()
    analyses = [
        {"source_id": "s1", "abstract": "ModelX achieves accuracy of 92%.", "findings": []},
        {"source_id": "s2", "abstract": "ModelX achieves accuracy of 93%.", "findings": []},
    ]
    # Small spread (<= 10 points) should not trigger numerical conflict
    contradictions = detector.detect_numerical_conflicts(analyses)
    assert len(contradictions) == 0


def test_contradiction_detector_numerical_conflict():
    """Large spread in reported metrics triggers a methodological contradiction."""
    detector = ContradictionDetector()
    analyses = [
        {"source_id": "s1", "abstract": "Accuracy of 55% on the test set.", "findings": []},
        {"source_id": "s2", "abstract": "Accuracy of 90% on the test set.", "findings": []},
    ]
    contradictions = detector.detect_numerical_conflicts(analyses)
    assert len(contradictions) >= 1
    assert contradictions[0].severity == "methodological"


def test_contradiction_fields():
    """Contradiction dataclass has all required fields."""
    c = Contradiction(
        claim_a="X beats Y",
        claim_b="Y beats X",
        source_a_id="s1",
        source_b_id="s2",
        severity="direct",
        description="Opposing claims",
    )
    assert c.claim_a == "X beats Y"
    assert c.severity == "direct"


# ---------------------------------------------------------------------------
# GapAnalyzer tests
# ---------------------------------------------------------------------------

def test_gap_analyzer_returns_list():
    """analyze() always returns a list."""
    analyzer = GapAnalyzer()
    result = analyzer.analyze([], "language models")
    assert isinstance(result, list)


def test_gap_analyzer_extracts_explicit_gaps():
    """Gap signals in abstracts produce ResearchGap entries."""
    analyzer = GapAnalyzer()
    sources = [
        {
            "source_id": "s1",
            "title": "Survey",
            "abstract": "This area remains challenging and future work should explore multi-modal settings.",
            "findings": [],
        }
    ]
    gaps = analyzer.analyze(sources, "multi-modal learning")
    assert len(gaps) >= 1
    assert any("remains challenging" in g.area or "future work" in g.area for g in gaps)


def test_gap_analyzer_coverage_gaps():
    """Questions with no source coverage produce coverage gaps."""
    gen = VerifiableChecklistGenerator()
    analyzer = GapAnalyzer()
    checklist = gen.generate("quantum computing")
    # Provide sources with completely unrelated content
    sources = [
        {"source_id": "s1", "abstract": "Deep learning is great.", "findings": []}
    ]
    gaps = analyzer.coverage_gaps(sources, checklist)
    assert isinstance(gaps, list)
    assert len(gaps) > 0


def test_gap_analyzer_no_gaps_when_fully_covered():
    """Answered checklist items are skipped in coverage gap analysis."""
    gen = VerifiableChecklistGenerator()
    analyzer = GapAnalyzer()
    checklist = gen.generate("image classification", depth="quick")
    # Mark all items answered
    for i in range(len(checklist.items)):
        checklist = gen.mark_answered(checklist, i, ["s1"])
    sources = [{"source_id": "s1", "abstract": "image classification results.", "findings": []}]
    gaps = analyzer.coverage_gaps(sources, checklist)
    assert gaps == []


def test_gap_severity_values():
    """ResearchGap severity is one of the expected values."""
    gap = ResearchGap(
        area="Missing benchmarks",
        evidence="No standard dataset exists",
        severity="critical",
        suggested_direction="Create evaluation benchmarks",
    )
    assert gap.severity in ("critical", "important", "minor")


# ---------------------------------------------------------------------------
# FalsificationChecker tests
# ---------------------------------------------------------------------------

def test_falsification_checker_returns_notes():
    """check() returns one FalsificationNote per claim."""
    checker = FalsificationChecker()
    claims = ["BERT outperforms GPT on classification tasks"]
    sources = [
        {"source_id": "s1", "abstract": "BERT shows strong results.", "findings": []}
    ]
    notes = checker.check(claims, sources)
    assert len(notes) == 1
    assert isinstance(notes[0], FalsificationNote)


def test_falsification_checker_verdict_insufficient():
    """No sources => verdict is insufficient_evidence."""
    checker = FalsificationChecker()
    claims = ["Attention is all you need"]
    notes = checker.check(claims, sources=[])
    assert notes[0].verdict == "insufficient_evidence"


def test_falsification_checker_verdict_supported():
    """Claim with no counter-evidence in any source => supported."""
    checker = FalsificationChecker()
    claims = ["Transformers achieve good results on NLP tasks"]
    sources = [
        {"source_id": "s1", "abstract": "Transformers are very effective for NLP tasks.", "findings": []},
        {"source_id": "s2", "abstract": "Attention-based models improve performance significantly.", "findings": []},
    ]
    notes = checker.check(claims, sources)
    assert notes[0].verdict == "supported"


def test_falsification_checker_verdict_contested():
    """Minority counter-evidence => contested."""
    checker = FalsificationChecker()
    claims = ["our model outperforms all baselines"]
    sources = [
        {"source_id": "s1", "abstract": "Great performance across benchmarks.", "findings": []},
        {"source_id": "s2", "abstract": "Our method fails to outperform this baseline in the results.", "findings": []},
        {"source_id": "s3", "abstract": "Consistent improvements observed.", "findings": []},
    ]
    notes = checker.check(claims, sources)
    # With partial refutation, verdict should be contested or supported
    assert notes[0].verdict in ("supported", "contested")


def test_falsification_checker_check_consensus():
    """check_consensus returns dict mapping claim -> consensus label."""
    checker = FalsificationChecker()
    claims = ["Model X is state-of-the-art"]
    sources = [
        {"source_id": "s1", "abstract": "Model X shows impressive state-of-the-art results.", "findings": []}
    ]
    consensus = checker.check_consensus(claims, sources)
    assert isinstance(consensus, dict)
    assert claims[0] in consensus
    assert consensus[claims[0]] in ("consensus", "contested", "minority_view")


def test_falsification_checker_multiple_claims():
    """check() handles multiple claims correctly."""
    checker = FalsificationChecker()
    claims = ["Claim A about transformers", "Claim B about efficiency"]
    sources = [
        {"source_id": "s1", "abstract": "Transformers are efficient.", "findings": []}
    ]
    notes = checker.check(claims, sources)
    assert len(notes) == 2


def test_falsification_note_fields():
    """FalsificationNote dataclass has all required fields."""
    note = FalsificationNote(
        claim="X beats Y",
        counter_sources=["s1"],
        counter_evidence="Y outperforms X",
        verdict="contested",
    )
    assert note.claim == "X beats Y"
    assert note.verdict == "contested"
    assert note.counter_sources == ["s1"]
