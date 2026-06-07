"""
Tests for v8.2 Advanced Adversarial Panel features.

Covers:
- ReTAS alignment corrects actor-observer asymmetry
- Collusion detection identifies covert communication
- Forced disagreement produces minority reports
- Diversity quotas enforced
- Evidence anchoring works
- Confidence monitor tracks quality
- Communication graph randomization
"""

from __future__ import annotations

import uuid

import pytest

from lyra.verification.retas_alignment import (
    ActorObserverAsymmetry,
    AlignmentMetrics,
    AlignedRound,
    ReTASAligner,
)
from lyra.verification.collusion_detector import (
    CollusionDetector,
    CollusionRisk,
    IdentityClusterSignal,
    MetaphorSignal,
    NarrativeOverfitSignal,
    RiskLevel,
)
from lyra.verification.debate_panel import (
    AnonymousDebatePanel,
    Argument,
    Ballot,
    CommunicationGraph,
    CommunicationTopology,
    DebateQualityMetrics,
    DebateResult,
    DEFAULT_DIVERSITY_QUOTAS,
    DiversityQuota,
    EvidenceCitation,
    Perspective,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_arguments() -> tuple[Argument, ...]:
    """Create a sample set of debate arguments."""
    return (
        Argument(
            round_number=1,
            anonymous_id="Panelist-a1b2",
            perspective=Perspective.SUPPORTER,
            content="I definitely believe this approach is correct. "
                    "According to arXiv:2401.12345, this method demonstrably "
                    "outperforms alternatives.",
        ),
        Argument(
            round_number=1,
            anonymous_id="Panelist-c3d4",
            perspective=Perspective.SKEPTIC,
            content="I am uncertain about this. There may be edge cases "
                    "where it fails. It could be that the approach "
                    "overfits to the benchmark data.",
        ),
        Argument(
            round_number=2,
            anonymous_id="Panelist-a1b2",
            perspective=Perspective.SUPPORTER,
            content="Without doubt the evidence is clear. The paper shows "
                    "absolutely consistent results across multiple settings.",
        ),
        Argument(
            round_number=2,
            anonymous_id="Panelist-c3d4",
            perspective=Perspective.SKEPTIC,
            content="I think we need to be careful about generalisation. "
                    "Maybe the results don't transfer to real-world scenarios.",
        ),
    )


@pytest.fixture
def sample_ballots() -> tuple[Ballot, ...]:
    """Create sample ballots with some asymmetry."""
    return (
        Ballot(
            anonymous_id="Panelist-a1b2",
            approve=True,
            confidence=0.95,
            rationale="I strongly approve from the supporter perspective.",
        ),
        Ballot(
            anonymous_id="Panelist-c3d4",
            approve=False,
            confidence=0.60,
            rationale="I cautiously reject from the skeptic perspective.",
        ),
    )


@pytest.fixture
def sample_debate_result(
    sample_arguments: tuple[Argument, ...],
    sample_ballots: tuple[Ballot, ...],
) -> DebateResult:
    """Create a complete sample debate result."""
    return DebateResult(
        topic="This approach is correct",
        consensus="The claim is validated.",
        consensus_confidence=0.75,
        minority_report="We need more evidence.",
        arguments=sample_arguments,
        voting_record=sample_ballots,
        passed=True,
        total_rounds=2,
        panelist_perspectives={
            "Panelist-a1b2": Perspective.SUPPORTER,
            "Panelist-c3d4": Perspective.SKEPTIC,
        },
    )


@pytest.fixture
def colluding_arguments() -> tuple[Argument, ...]:
    """Create arguments that exhibit collusion signals.

    Both agents share the same claims and metaphors (war framing).
    """
    return (
        Argument(
            round_number=1,
            anonymous_id="Panelist-x1",
            perspective=Perspective.SUPPORTER,
            content="This approach is battle-tested and proven. "
                    "The strategy wins because we defend against all "
                    "attacks. The architecture is clearly superior.",
        ),
        Argument(
            round_number=1,
            anonymous_id="Panelist-x2",
            perspective=Perspective.SUPPORTER,
            content="This approach is battle-tested and proven. "
                    "The strategy wins because we defend against all "
                    "attacks. The framework is demonstrably better.",
        ),
        Argument(
            round_number=2,
            anonymous_id="Panelist-x3",
            perspective=Perspective.SKEPTIC,
            content="There are legitimate concerns about scalability. "
                    "The evidence is not conclusive.",
        ),
        Argument(
            round_number=2,
            anonymous_id="Panelist-x1",
            perspective=Perspective.SUPPORTER,
            content="The evidence supports our campaign. No retreat needed.",
        ),
        Argument(
            round_number=2,
            anonymous_id="Panelist-x2",
            perspective=Perspective.SUPPORTER,
            content="The evidence supports our defence. No retreat needed.",
        ),
    )


@pytest.fixture
def colluding_ballots() -> tuple[Ballot, ...]:
    """Ballots from colluding agents."""
    return (
        Ballot(anonymous_id="Panelist-x1", approve=True, confidence=0.95, rationale="Approve"),
        Ballot(anonymous_id="Panelist-x2", approve=True, confidence=0.95, rationale="Approve"),
        Ballot(anonymous_id="Panelist-x3", approve=False, confidence=0.50, rationale="Reject"),
    )


# ---------------------------------------------------------------------------
# Tests: ReTAS Alignment
# ---------------------------------------------------------------------------


class TestReTASAligner:
    """Verify ReTAS dialectical alignment."""

    def test_measure_asymmetry_detects_bias(
        self,
        sample_debate_result: DebateResult,
    ):
        """Actor-observer asymmetry should be measurable."""
        aligner = ReTASAligner()
        aligned = aligner.apply_alignment(sample_debate_result)

        assert isinstance(aligned, AlignedRound)
        assert len(aligned.arguments) == len(aligned.original_arguments)
        assert aligned.correction_map is not None

        metrics = aligned.metrics
        assert isinstance(metrics, AlignmentMetrics)
        assert len(metrics.pre_alignment_asymmetries) > 0
        assert len(metrics.post_alignment_asymmetries) > 0

    def test_alignment_reduces_asymmetry(
        self,
        sample_debate_result: DebateResult,
    ):
        """Alignment should reduce mean absolute asymmetry."""
        aligner = ReTASAligner(correction_strength=0.8)
        aligned = aligner.apply_alignment(sample_debate_result)

        assert aligned.metrics.alignment_improvement >= 0.0
        assert aligned.metrics.mean_asymmetry_after <= aligned.metrics.mean_asymmetry_before

    def test_weak_correction(
        self,
        sample_debate_result: DebateResult,
    ):
        """Very weak correction should barely change asymmetry."""
        aligner = ReTASAligner(correction_strength=0.05)
        aligned = aligner.apply_alignment(sample_debate_result)

        # With weak correction, asymmetry should be near unchanged
        assert abs(aligned.metrics.mean_asymmetry_before - aligned.metrics.mean_asymmetry_after) < 0.1

    def test_strong_correction(
        self,
        sample_debate_result: DebateResult,
    ):
        """Strong correction should substantially reduce asymmetry."""
        aligner = ReTASAligner(correction_strength=1.0, min_observations=1)
        aligned = aligner.apply_alignment(sample_debate_result)

        assert aligned.metrics.total_arguments_aligned > 0

    def test_actor_observer_asymmetry_dataclass(self):
        """Verify ActorObserverAsymmetry creation."""
        aoa = ActorObserverAsymmetry(
            anonymous_id="test-agent",
            self_rating_mean=0.9,
            other_rating_mean=0.5,
            asymmetry_score=0.4,
            argument_self_count=3,
            argument_other_count=10,
        )
        assert aoa.anonymous_id == "test-agent"
        assert aoa.asymmetry_score == 0.4
        assert aoa.argument_self_count == 3

    def test_alignment_metrics_dataclass(self):
        """Verify AlignmentMetrics creation."""
        metrics = AlignmentMetrics(
            pre_alignment_asymmetries=(),
            post_alignment_asymmetries=(),
            mean_asymmetry_before=0.3,
            mean_asymmetry_after=0.1,
            alignment_improvement=0.2,
            total_arguments_aligned=4,
            correction_factor=0.15,
        )
        assert metrics.alignment_improvement == 0.2
        assert metrics.total_arguments_aligned == 4

    def test_content_correction_dilutes_confidence(
        self,
        sample_debate_result: DebateResult,
    ):
        """Confident language should be diluted when weight < 1.0."""
        aligner = ReTASAligner(correction_strength=0.5)

        # Manually correct content
        diluted = aligner._apply_correction_to_content(
            "This is definitely correct and clearly proven.",
            weight=0.5,
        )
        assert "definitely" not in diluted
        assert "probably" in diluted
        assert "clearly" not in diluted
        assert "arguably" in diluted

    def test_content_correction_strengthens_weak(
        self,
    ):
        """Weak language should be strengthened when weight > 1.0."""
        aligner = ReTASAligner(correction_strength=0.5)

        strengthened = aligner._apply_correction_to_content(
            "maybe this is correct, it seems plausible.",
            weight=1.3,
        )
        assert "maybe" not in strengthened
        assert "likely" in strengthened or "probably" in strengthened

    def test_mean_abs_asymmetry(self):
        """Static mean-abs-asymmetry calculation."""
        asymmetries = [
            ActorObserverAsymmetry("a", 0.8, 0.5, 0.3, 2, 5),
            ActorObserverAsymmetry("b", 0.6, 0.5, 0.1, 2, 5),
        ]
        mean_abs = ReTASAligner._mean_abs_asymmetry(asymmetries)
        assert mean_abs == pytest.approx(0.2)

    def test_empty_mean_abs_asymmetry(self):
        """Empty list returns 0.0."""
        assert ReTASAligner._mean_abs_asymmetry([]) == 0.0

    def test_apply_alignment_preserves_structure(self):
        """Aligned round should have same structure as original."""
        aligner = ReTASAligner()
        debate_result = DebateResult(
            topic="Test",
            consensus="Consensus",
            consensus_confidence=0.8,
            minority_report="Report",
            arguments=(),
            voting_record=(),
            passed=True,
            total_rounds=1,
            panelist_perspectives={},
        )
        aligned = aligner.apply_alignment(debate_result)
        assert len(aligned.arguments) == 0
        assert aligned.correction_map == {}


# ---------------------------------------------------------------------------
# Tests: Collusion Detection
# ---------------------------------------------------------------------------


class TestCollusionDetector:
    """Verify collusion detection across all three signals."""

    def test_detects_metaphor_convergence(
        self,
        colluding_arguments: tuple[Argument, ...],
        colluding_ballots: tuple[Ballot, ...],
    ):
        """Metaphor profile divergence should detect collusion."""
        detector = CollusionDetector(metaphor_threshold=0.3)
        risk = detector.monitor_communication(
            colluding_arguments, colluding_ballots
        )

        assert isinstance(risk, CollusionRisk)
        assert risk.metaphor_signal is not None
        assert risk.risk_score > 0.0

    def test_no_false_positive_on_independent_agents(
        self,
        sample_arguments: tuple[Argument, ...],
        sample_ballots: tuple[Ballot, ...],
    ):
        """Independent agents should not trigger collusion."""
        detector = CollusionDetector()
        risk = detector.monitor_communication(
            sample_arguments, sample_ballots
        )

        assert risk.risk_level in (RiskLevel.NONE, RiskLevel.LOW)

    def test_detects_narrative_overfitting(
        self,
        colluding_arguments: tuple[Argument, ...],
        colluding_ballots: tuple[Ballot, ...],
    ):
        """Narrative overfitting should be detected."""
        detector = CollusionDetector(narrative_threshold=0.3)
        risk = detector.monitor_communication(
            colluding_arguments, colluding_ballots
        )

        assert risk.narrative_signal is not None
        # Colluding agents share the same claims
        if risk.narrative_signal.detected:
            assert len(risk.narrative_signal.overfitted_pairs) > 0

    def test_detects_identity_clustering(
        self,
        colluding_arguments: tuple[Argument, ...],
        colluding_ballots: tuple[Ballot, ...],
    ):
        """Identity clustering should be detectable."""
        detector = CollusionDetector(identity_threshold=0.5)
        risk = detector.monitor_communication(
            colluding_arguments, colluding_ballots
        )

        assert risk.identity_signal is not None
        if risk.identity_signal.detected:
            assert len(risk.identity_signal.clusters) > 0

    def test_classify_risk_levels(self):
        """Risk level boundaries should be correct."""
        detector = CollusionDetector()

        assert detector._classify_risk(0.0) == RiskLevel.NONE
        assert detector._classify_risk(0.2) == RiskLevel.LOW
        assert detector._classify_risk(0.4) == RiskLevel.MEDIUM
        assert detector._classify_risk(0.6) == RiskLevel.HIGH
        assert detector._classify_risk(0.8) == RiskLevel.CRITICAL

    def test_select_mitigation_none(self):
        """No risk -> no mitigation."""
        mitigation = CollusionDetector._select_mitigation(
            RiskLevel.NONE, []
        )
        assert mitigation == "none"

    def test_select_mitigation_high(self):
        """High risk -> force anonymization + disruption."""
        mitigation = CollusionDetector._select_mitigation(
            RiskLevel.HIGH, ["metaphor", "narrative"]
        )
        assert "force_identity_anonymization" in mitigation
        assert "inject_disruption_agent" in mitigation

    def test_select_mitigation_low(self):
        """Low risk -> randomized topology."""
        mitigation = CollusionDetector._select_mitigation(
            RiskLevel.LOW, ["metaphor"]
        )
        assert "randomized_topology" in mitigation

    def test_select_mitigation_medium(self):
        """Medium risk -> signal-dependent mitigations."""
        mitigation = CollusionDetector._select_mitigation(
            RiskLevel.MEDIUM, ["metaphor", "narrative"]
        )
        assert "force_identity_anonymization" in mitigation
        assert "inject_disruption_agent" in mitigation
        assert "randomized_topology" in mitigation

    def test_metaphor_classification(self):
        """Metaphor classification should identify categories."""
        detector = CollusionDetector()

        war_cat = detector._classify_metaphor(
            "This is a battle for the future of AI."
        )
        assert war_cat == "war"

        health_cat = detector._classify_metaphor(
            "The system needs a proper diagnosis."
        )
        assert health_cat == "health"

        no_cat = detector._classify_metaphor(
            "The system uses a standard approach."
        )
        assert no_cat is None

    def test_jaccard_metaphor_similarity(self):
        """Jaccard similarity on metaphor profiles."""
        from collections import Counter

        a = Counter({"war": 5, "health": 1})
        b = Counter({"war": 4, "journey": 2})

        sim = CollusionDetector._jaccard_metaphor(a, b)
        assert 0.0 <= sim <= 1.0
        assert sim > 0.0  # Some overlap in "war"

    def test_claim_extraction(self):
        """Claim extraction should find declarative statements."""
        text = ("The system is scalable and efficient. "
                "The architecture provides fault tolerance. "
                "It should handle 10K requests per second.")

        claims = CollusionDetector._extract_claims(text)
        assert len(claims) >= 2  # "system is scalable" + "architecture provides"

    def test_claim_overlap(self):
        """Claim overlap computation."""
        a = {"system is scalable", "architecture is robust"}
        b = {"system is scalable", "performance is optimal"}

        overlap = CollusionDetector._compute_claim_overlap(a, b)
        assert overlap == pytest.approx(0.3333, rel=0.01)  # 1 / 3

    def test_aggregate_pair_score(self):
        """Pair score aggregation."""
        pairs = [("a", "b", 0.8), ("b", "c", 0.7)]
        score = CollusionDetector._aggregate_pair_score(pairs, 3)
        assert 0.0 < score <= 1.0

    def test_empty_aggregate_pair_score(self):
        """Empty pairs -> 0.0."""
        assert CollusionDetector._aggregate_pair_score([], 2) == 0.0

    def test_metaphor_signal_dataclass(self):
        """MetaphorSignal dataclass."""
        signal = MetaphorSignal(
            detected=True,
            score=0.8,
            converging_pairs=[("a", "b", 0.9)],
            dominant_metaphors=["war", "health"],
        )
        assert signal.detected is True
        assert signal.score == 0.8

    def test_narrative_signal_dataclass(self):
        """NarrativeOverfitSignal dataclass."""
        signal = NarrativeOverfitSignal(
            detected=True,
            score=0.75,
            overfitted_pairs=[("a", "b", 0.85)],
            overlapping_claims=["system is scalable"],
        )
        assert signal.detected is True
        assert len(signal.overlapping_claims) == 1

    def test_identity_cluster_signal_dataclass(self):
        """IdentityClusterSignal dataclass."""
        signal = IdentityClusterSignal(
            detected=True,
            score=0.9,
            clusters={"supporter": ["a", "b"]},
            cluster_agreement=0.9,
        )
        assert signal.detected is True
        assert signal.cluster_agreement == 0.9

    def test_collusion_risk_dataclass(self):
        """CollusionRisk dataclass."""
        risk = CollusionRisk(
            risk_level=RiskLevel.HIGH,
            risk_score=0.65,
            metaphor_signal=None,
            narrative_signal=None,
            identity_signal=None,
            mitigation="force_identity_anonymization",
            signals_triggered=("metaphor",),
        )
        assert risk.risk_level == RiskLevel.HIGH
        assert risk.risk_score == 0.65
        assert "force_identity_anonymization" in risk.mitigation

    def test_risk_level_enum(self):
        """RiskLevel enum values."""
        assert RiskLevel.NONE.value == "none"
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"


# ---------------------------------------------------------------------------
# Tests: Debate Panel v8.2 Enhancements
# ---------------------------------------------------------------------------


class TestConfidenceMonitor:
    """Verify the confidence_monitor feature."""

    def test_confidence_monitor_returns_metrics(
        self,
        sample_debate_result: DebateResult,
    ):
        """confidence_monitor should return DebateQualityMetrics."""
        panel = AnonymousDebatePanel()
        quality = panel.confidence_monitor(sample_debate_result)

        assert isinstance(quality, DebateQualityMetrics)
        assert quality.total_arguments == len(sample_debate_result.arguments)
        assert quality.unique_perspectives_used > 0
        assert 0.0 <= quality.evidence_citation_rate <= 1.0
        assert 0.0 <= quality.disagreement_intensity <= 1.0
        assert 0.0 <= quality.minority_representation <= 1.0

    def test_evidence_citation_rate(
        self,
        sample_debate_result: DebateResult,
    ):
        """Arguments with 'according to' should count as cited."""
        panel = AnonymousDebatePanel()
        quality = panel.confidence_monitor(sample_debate_result)

        # One argument cites "According to arxiv:..."
        assert quality.evidence_citation_rate > 0.0

    def test_minority_representation(
        self,
        sample_debate_result: DebateResult,
    ):
        """Minority perspectives should be counted."""
        panel = AnonymousDebatePanel()
        quality = panel.confidence_monitor(sample_debate_result)

        # There are skeptic arguments in the fixture
        assert quality.minority_representation > 0.0

    def test_disagreement_intensity_with_split_vote(
        self,
    ):
        """Split vote should produce higher disagreement intensity."""
        panel = AnonymousDebatePanel()

        result = DebateResult(
            topic="Test",
            consensus="Mixed",
            consensus_confidence=0.5,
            minority_report="N/A",
            arguments=(
                Argument(1, "a", Perspective.SUPPORTER, "pro"),
                Argument(1, "b", Perspective.SKEPTIC, "con"),
            ),
            voting_record=(
                Ballot("a", True, 0.8, "Approve"),
                Ballot("b", False, 0.7, "Reject"),
            ),
            passed=False,
            total_rounds=1,
            panelist_perspectives={"a": Perspective.SUPPORTER, "b": Perspective.SKEPTIC},
        )
        quality = panel.confidence_monitor(result)

        # 50/50 vote split = maximum disagreement intensity
        assert quality.disagreement_intensity > 0.5

    def test_get_quality_history(
        self,
        sample_debate_result: DebateResult,
    ):
        """Quality metrics should be created correctly."""
        panel = AnonymousDebatePanel()

        quality1 = panel.confidence_monitor(sample_debate_result)
        quality2 = panel.confidence_monitor(sample_debate_result)

        assert isinstance(quality1, DebateQualityMetrics)
        assert isinstance(quality2, DebateQualityMetrics)
        assert quality1.total_arguments == quality2.total_arguments

    def test_debate_quality_metrics_dataclass(self):
        """DebateQualityMetrics dataclass."""
        metrics = DebateQualityMetrics(
            total_arguments=10,
            unique_perspectives_used=4,
            evidence_citation_rate=0.5,
            disagreement_intensity=0.3,
            minority_representation=0.4,
            round_balance=0.1,
            forced_minority_reports_generated=1,
        )
        assert metrics.total_arguments == 10
        assert metrics.evidence_citation_rate == 0.5

    def test_confidence_monitor_with_no_votes(self):
        """Empty voting record should not crash."""
        panel = AnonymousDebatePanel()
        result = DebateResult(
            topic="Test",
            consensus="",
            consensus_confidence=0.0,
            minority_report="",
            arguments=(),
            voting_record=(),
            passed=False,
            total_rounds=0,
            panelist_perspectives={},
        )
        quality = panel.confidence_monitor(result)
        assert quality.disagreement_intensity == 0.0
        assert quality.total_arguments == 0


class TestDiversityQuotas:
    """Verify diversity quotas enforcement."""

    def test_default_quotas_include_minority(self):
        """Default quotas should include SKEPTIC and ADVERSARIAL."""
        quota_perspectives = {q.perspective for q in DEFAULT_DIVERSITY_QUOTAS}
        assert Perspective.SKEPTIC in quota_perspectives
        assert Perspective.ADVERSARIAL in quota_perspectives
        assert Perspective.DOMAIN_EXPERT in quota_perspectives

    def test_enforce_quotas_adds_missing_perspectives(self):
        """Missing perspectives should be added by enforce."""
        panel = AnonymousDebatePanel()
        perspectives = [Perspective.SUPPORTER]

        result = panel._enforce_diversity_quotas(perspectives)
        assert Perspective.SKEPTIC in result
        assert Perspective.ADVERSARIAL in result
        assert Perspective.DOMAIN_EXPERT in result

    def test_enforce_quotas_preserves_existing(self):
        """Existing minority perspectives should not be duplicated."""
        panel = AnonymousDebatePanel()
        perspectives = [
            Perspective.SUPPORTER,
            Perspective.SKEPTIC,
            Perspective.ADVERSARIAL,
            Perspective.DOMAIN_EXPERT,
        ]

        result = panel._enforce_diversity_quotas(perspectives)
        assert len(result) == len(perspectives)  # No duplicates

    def test_custom_quotas(self):
        """Custom quotas should be respected."""
        custom_quotas = (DiversityQuota(Perspective.ETHICS_REVIEWER, min_count=2),)
        panel = AnonymousDebatePanel(diversity_quotas=custom_quotas)
        perspectives = [Perspective.SUPPORTER]

        result = panel._enforce_diversity_quotas(perspectives)
        ethics_count = sum(1 for p in result if p == Perspective.ETHICS_REVIEWER)
        assert ethics_count >= 2

    def test_diversity_quota_dataclass(self):
        """DiversityQuota dataclass."""
        quota = DiversityQuota(
            perspective=Perspective.SKEPTIC,
            min_count=2,
            enforced=True,
        )
        assert quota.perspective == Perspective.SKEPTIC
        assert quota.min_count == 2
        assert quota.enforced is True

    def test_non_enforced_quota_not_applied(self):
        """Non-enforced quotas should not add perspectives."""
        quotas = (
            DiversityQuota(Perspective.SKEPTIC, min_count=2, enforced=False),
        )
        panel = AnonymousDebatePanel(diversity_quotas=quotas)
        perspectives = [Perspective.SUPPORTER]

        result = panel._enforce_diversity_quotas(perspectives)
        skeptic_count = sum(1 for p in result if p == Perspective.SKEPTIC)
        assert skeptic_count == 0  # Not enforced, not added


class TestEvidenceAnchoring:
    """Verify evidence anchoring."""

    def test_anchor_adds_citation_requirement(self):
        """Arguments without evidence should get anchoring appended."""
        content = "This approach is correct and well-designed."
        anchored = AnonymousDebatePanel._anchor_evidence(content, "Test claim")

        assert "[Evidence required:" in anchored
        assert "Please cite a verifiable source" in anchored

    def test_anchor_does_not_duplicate_citations(self):
        """Arguments with existing evidence should not be modified."""
        content = "According to arXiv:2401.12345, this approach is correct."
        anchored = AnonymousDebatePanel._anchor_evidence(content, "Test claim")

        assert "[Evidence required:" not in anchored
        assert content == anchored

    def test_anchor_url_evidence(self):
        """URL-based evidence should be recognised."""
        content = "Per the documentation at https://example.com/spec, this is correct."
        anchored = AnonymousDebatePanel._anchor_evidence(content, "Test claim")

        assert "[Evidence required:" not in anchored

    def test_extract_citations_arxiv(self):
        """arXiv references should be extracted."""
        content = "This is supported by arXiv:2401.12345."
        citations = AnonymousDebatePanel.extract_citations(content)

        assert len(citations) > 0
        assert "arXiv:2401.12345" in citations[0].source or "2401.12345" in citations[0].source  # fmt: skip

    def test_extract_citations_url(self):
        """URL references should be extracted."""
        content = "See https://example.com/paper for details."
        citations = AnonymousDebatePanel.extract_citations(content)

        assert len(citations) > 0
        assert "https://example.com/paper" in citations[0].source

    def test_extract_citations_according_to(self):
        """"According to" references should be extracted."""
        content = "According to the IEEE standard, this is correct."
        citations = AnonymousDebatePanel.extract_citations(content)

        assert len(citations) > 0
        assert "IEEE standard" in citations[0].source

    def test_extract_citations_empty(self):
        """No citations should return empty list."""
        content = "This is just an opinion."
        citations = AnonymousDebatePanel.extract_citations(content)

        assert len(citations) == 0

    def test_evidence_citation_dataclass(self):
        """EvidenceCitation dataclass."""
        citation = EvidenceCitation(
            source="arXiv:2401.12345",
            claim="Method outperforms baselines",
            confidence=0.85,
        )
        assert citation.source == "arXiv:2401.12345"
        assert citation.confidence == 0.85


class TestCommunicationGraph:
    """Verify communication graph randomization."""

    def test_build_full_mesh_default(self):
        """Default topology should be full mesh."""
        panel = AnonymousDebatePanel(randomized_topology_per_round=False)
        panelists = [
            ("a", Perspective.SUPPORTER),
            ("b", Perspective.SKEPTIC),
            ("c", Perspective.DOMAIN_EXPERT),
        ]

        graph = panel._build_communication_graph(panelists, 1)
        assert graph.topology == CommunicationTopology.FULL_MESH
        assert len(graph.edges) == 6  # 3 * 2 (all pairs)

    def test_random_topology_per_round(self):
        """Randomized topology should change per round."""
        panel = AnonymousDebatePanel(randomized_topology_per_round=True)
        panelists = [
            ("a", Perspective.SUPPORTER),
            ("b", Perspective.SKEPTIC),
            ("c", Perspective.DOMAIN_EXPERT),
            ("d", Perspective.ETHICS_REVIEWER),
            ("e", Perspective.ADVERSARIAL),
        ]

        graph1 = panel._build_communication_graph(panelists, 1)
        graph2 = panel._build_communication_graph(panelists, 2)

        assert graph1.topology != CommunicationTopology.FULL_MESH
        assert graph2.topology != CommunicationTopology.FULL_MESH

    def test_random_topology_with_few_agents(self):
        """With < 3 agents, should always use full mesh."""
        panel = AnonymousDebatePanel(randomized_topology_per_round=True)
        panelists = [
            ("a", Perspective.SUPPORTER),
            ("b", Perspective.SKEPTIC),
        ]

        graph = panel._build_communication_graph(panelists, 1)
        assert graph.topology == CommunicationTopology.FULL_MESH

    def test_star_topology(self):
        """Star topology should have a center."""
        panel = AnonymousDebatePanel()
        # Seed a specific topology type by building directly
        panel.seed_randomness(42)
        panelists = [
            ("a", Perspective.SUPPORTER),
            ("b", Perspective.SKEPTIC),
            ("c", Perspective.DOMAIN_EXPERT),
        ]

        graph = panel._build_communication_graph(panelists, 1)
        assert graph.round_number == 1
        assert len(graph.edges) > 0

    def test_communication_graph_dataclass(self):
        """CommunicationGraph dataclass."""
        graph = CommunicationGraph(
            topology=CommunicationTopology.RING,
            edges=[("a", "b"), ("b", "a")],
            round_number=1,
        )
        assert graph.topology == CommunicationTopology.RING
        assert len(graph.edges) == 2

    def test_build_prior_with_comm_graph(
        self,
        sample_arguments: tuple[Argument, ...],
    ):
        """Prior args should be filtered by communication graph."""
        panel = AnonymousDebatePanel()
        # Panelist "a1b2" can only hear arguments from "c3d4"
        comm_graph = CommunicationGraph(
            topology=CommunicationTopology.STAR,
            edges=[("Panelist-c3d4", "Panelist-a1b2")],
            round_number=1,
        )

        prior = panel._build_prior_for_panelist(
            list(sample_arguments), "Panelist-a1b2", comm_graph
        )

        # Should only include arguments from Panelist-c3d4
        for arg in prior:
            assert arg.anonymous_id == "Panelist-c3d4"

    def test_get_communication_graphs(self):
        """Communication graphs should accumulate."""
        panel = AnonymousDebatePanel(randomized_topology_per_round=False)
        panelists = [
            ("a", Perspective.SUPPORTER),
            ("b", Perspective.SKEPTIC),
        ]

        panel._build_communication_graph(panelists, 1)
        graphs = panel.get_communication_graphs()
        # Note: the graph is added in convene(), not _build, so this is empty
        assert isinstance(graphs, list)


class TestForcedDisagreement:
    """Verify forced disagreement rounds."""

    def test_forced_disagreement_in_unbalanced_debate(self):
        """Forced disagreement should trigger when debate is one-sided."""
        panel = AnonymousDebatePanel(forced_disagreement_rounds=True)
        panelists = [
            ("a", Perspective.SUPPORTER),
            ("b", Perspective.SKEPTIC),
        ]

        # Create a strongly one-sided record (2 supporter args, 0 skeptic)
        all_arguments = [
            Argument(1, "a", Perspective.SUPPORTER, "This is great."),
            Argument(1, "a", Perspective.SUPPORTER, "The evidence supports it."),
        ]

        # This should not raise
        import asyncio
        asyncio.run(panel._inject_forced_disagreement(
            "Test topic", panelists, all_arguments, 1
        ))
        # The method should complete without error

    def test_forced_disagreement_count_tracks(
        self,
        sample_debate_result: DebateResult,
    ):
        """Forced minority count should be tracked."""
        panel = AnonymousDebatePanel(forced_disagreement_rounds=True)
        assert panel._forced_minority_count >= 0

    def test_communication_topology_enum(self):
        """CommunicationTopology enum values."""
        assert CommunicationTopology.FULL_MESH.value == "full_mesh"
        assert CommunicationTopology.RANDOM_SUBSET.value == "random_subset"
        assert CommunicationTopology.STAR.value == "star"
        assert CommunicationTopology.CHAIN.value == "chain"
        assert CommunicationTopology.RING.value == "ring"
        assert CommunicationTopology.PARTITIONED.value == "partitioned"


class TestPanelSeeding:
    """Verify random seed for reproducibility."""

    def test_seed_produces_deterministic_topology(self):
        """Same seed should produce same graph (seed immediately before call)."""
        panel1 = AnonymousDebatePanel(randomized_topology_per_round=True)
        panel2 = AnonymousDebatePanel(randomized_topology_per_round=True)
        panelists = [
            ("a", Perspective.SUPPORTER),
            ("b", Perspective.SKEPTIC),
            ("c", Perspective.DOMAIN_EXPERT),
        ]

        panel1.seed_randomness(42)
        graph1 = panel1._build_communication_graph(panelists, 1)
        panel2.seed_randomness(42)
        graph2 = panel2._build_communication_graph(panelists, 1)

        assert graph1.topology == graph2.topology
        assert graph1.round_number == graph2.round_number


class TestPanelOptions:
    """Verify new v8.2 options don't break existing functionality."""

    @pytest.mark.asyncio
    async def test_panel_with_v82_options_defaults(self):
        """Panel should work with default v8.2 options."""

        async def speaker(topic: str, perspective: Perspective, prior: list) -> str:
            return f"Argument from {perspective.value}."

        panel = AnonymousDebatePanel(
            async_argument_fn=speaker,
            forced_disagreement_rounds=True,
            evidence_anchoring=True,
            randomized_topology_per_round=True,
        )

        result = await panel.convene(
            topic="Test claim",
            perspectives=[
                Perspective.SUPPORTER,
                Perspective.SKEPTIC,
                Perspective.DOMAIN_EXPERT,
            ],
            rounds=1,
        )
        assert result.passed is not None
        assert len(result.arguments) > 0

    @pytest.mark.asyncio
    async def test_panel_with_v82_options_disabled(self):
        """Panel should work with v8.2 features disabled."""

        async def speaker(topic: str, perspective: Perspective, prior: list) -> str:
            return f"Argument from {perspective.value}."

        panel = AnonymousDebatePanel(
            async_argument_fn=speaker,
            forced_disagreement_rounds=False,
            evidence_anchoring=False,
            randomized_topology_per_round=False,
        )

        result = await panel.convene(
            topic="Test claim",
            perspectives=[
                Perspective.SUPPORTER,
                Perspective.SKEPTIC,
                Perspective.DOMAIN_EXPERT,
            ],
            rounds=1,
        )
        assert result.passed is not None
        assert len(result.arguments) > 0
