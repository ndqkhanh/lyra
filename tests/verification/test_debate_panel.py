"""Tests for AnonymousDebatePanel core convene flow and helpers."""

from __future__ import annotations

import pytest

from lyra.verification.debate_panel import (
    AnonymousDebatePanel,
    Argument,
    Ballot,
    DebateResult,
    Perspective,
)
from lyra.verification.panel import AdversarialPanel, Lens, ReviewerVote


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def panel_with_sync_speaker() -> AnonymousDebatePanel:
    """Panel using a synchronous argument function."""

    def speaker(topic: str, perspective: Perspective, prior: list[Argument]) -> str:
        return f"Argument from {perspective.value} perspective on: {topic[:30]}."

    return AnonymousDebatePanel(argument_fn=speaker)


@pytest.fixture
def panel_with_async_speaker() -> AnonymousDebatePanel:
    """Panel using an async argument function."""

    async def speaker(topic: str, perspective: Perspective, prior: list[Argument]) -> str:
        return f"Async argument from {perspective.value}."

    return AnonymousDebatePanel(async_argument_fn=speaker)


@pytest.fixture
def minimal_perspectives() -> list[Perspective]:
    return [Perspective.SUPPORTER, Perspective.SKEPTIC, Perspective.DOMAIN_EXPERT]


# ---------------------------------------------------------------------------
# Tests: convene flow
# ---------------------------------------------------------------------------


class TestConvene:
    @pytest.mark.asyncio
    async def test_basic_convene(self, panel_with_async_speaker, minimal_perspectives):
        result = await panel_with_async_speaker.convene(
            topic="Rust is safer than C",
            perspectives=minimal_perspectives,
            rounds=1,
        )
        assert isinstance(result, DebateResult)
        assert result.topic == "Rust is safer than C"
        assert result.passed is not None
        # 3 perspectives + 1 from diversity quotas (ADVERSARIAL) = 4
        assert len(result.arguments) == 4
        assert result.total_rounds == 1
        assert result.consensus is not None
        assert result.consensus_confidence >= 0

    @pytest.mark.asyncio
    async def test_convene_multiple_rounds(self, panel_with_async_speaker, minimal_perspectives):
        result = await panel_with_async_speaker.convene(
            topic="Test topic",
            perspectives=minimal_perspectives,
            rounds=2,
        )
        # 4 panelists (3+1 from quotas) x 2 rounds
        assert len(result.arguments) == 8
        assert len(result.voting_record) == 4

    @pytest.mark.asyncio
    async def test_convene_without_explicit_perspectives_defaults_all(
        self, panel_with_async_speaker,
    ):
        """When perspectives omitted, defaults to all 6."""
        result = await panel_with_async_speaker.convene(
            topic="Test", rounds=1,
        )
        assert len(result.arguments) == 6
        assert len(result.panelist_perspectives) == 6

    @pytest.mark.asyncio
    async def test_convene_with_sync_fn(self, panel_with_sync_speaker, minimal_perspectives):
        result = await panel_with_sync_speaker.convene(
            topic="Sync test",
            perspectives=minimal_perspectives,
            rounds=1,
        )
        assert result.passed is not None

    @pytest.mark.asyncio
    async def test_convene_auto_adds_minority(self):
        """If no minority perspective in list, MINORITY_REPRESENTATIVE is added."""

        async def speaker(topic, perspective, prior):
            return f"Arg from {perspective.value}."

        panel = AnonymousDebatePanel(async_argument_fn=speaker)
        # Only supporter + domain_expert + ethics (no minority perspectives)
        result = await panel.convene(
            topic="Test",
            perspectives=[
                Perspective.SUPPORTER,
                Perspective.DOMAIN_EXPERT,
                Perspective.ETHICS_REVIEWER,
            ],
            rounds=1,
        )
        perspectives_in_use = {p for _, p in result.panelist_perspectives.items()}
        assert Perspective.MINORITY_REPRESENTATIVE in perspectives_in_use

    @pytest.mark.asyncio
    async def test_convene_with_verification_panel(self, panel_with_async_speaker, minimal_perspectives):
        """Optional AdversarialPanel verification should not raise."""

        async def reviewer(subject, lens):
            return ReviewerVote(lens=lens, passed=True, reason="ok")

        vp = AdversarialPanel(async_reviewer_fn=reviewer)

        result = await panel_with_async_speaker.convene(
            topic="Test claim",
            perspectives=minimal_perspectives,
            rounds=1,
            verification_panel=vp,
        )
        assert result.passed is not None

    @pytest.mark.asyncio
    async def test_convene_rounds_out_of_range(self, panel_with_async_speaker, minimal_perspectives):
        with pytest.raises(ValueError, match="rounds must be between 1 and 5"):
            await panel_with_async_speaker.convene(
                topic="T", perspectives=minimal_perspectives, rounds=0,
            )
        with pytest.raises(ValueError, match="rounds must be between 1 and 5"):
            await panel_with_async_speaker.convene(
                topic="T", perspectives=minimal_perspectives, rounds=6,
            )

    @pytest.mark.asyncio
    async def test_convene_fewer_than_3_perspectives(self, panel_with_async_speaker):
        with pytest.raises(ValueError, match="At least 3 perspectives"):
            await panel_with_async_speaker.convene(
                topic="T",
                perspectives=[Perspective.SUPPORTER, Perspective.SKEPTIC],
                rounds=1,
            )

    @pytest.mark.asyncio
    async def test_convene_panelist_ids_unique(self, panel_with_async_speaker, minimal_perspectives):
        result = await panel_with_async_speaker.convene(
            topic="Test", perspectives=minimal_perspectives, rounds=1,
        )
        anon_ids = [a.anonymous_id for a in result.arguments]
        assert len(set(anon_ids)) == 4  # 4 panelists (3+1 from quotas)

    @pytest.mark.asyncio
    async def test_convene_argument_structure(self, panel_with_async_speaker, minimal_perspectives):
        result = await panel_with_async_speaker.convene(
            topic="Test topic here", perspectives=minimal_perspectives, rounds=1,
        )
        for arg in result.arguments:
            assert arg.round_number == 1
            assert arg.anonymous_id is not None
            assert arg.perspective in list(Perspective)
            assert len(arg.content) > 0


# ---------------------------------------------------------------------------
# Tests: Voting
# ---------------------------------------------------------------------------


class TestVoting:
    @pytest.mark.asyncio
    async def test_voting_record_produced(self, panel_with_async_speaker, minimal_perspectives):
        result = await panel_with_async_speaker.convene(
            topic="Test", perspectives=minimal_perspectives, rounds=1,
        )
        assert len(result.voting_record) == 4
        for ballot in result.voting_record:
            assert isinstance(ballot.approve, bool)
            assert 0.0 <= ballot.confidence <= 1.0
            assert len(ballot.rationale) > 0

    def test_parse_vote_approve(self):
        assert AnonymousDebatePanel._parse_vote("I approve this claim.") is True
        assert AnonymousDebatePanel._parse_vote("I support this.") is True
        assert AnonymousDebatePanel._parse_vote("This is correct and valid.") is True

    def test_parse_vote_reject(self):
        assert AnonymousDebatePanel._parse_vote("I reject this claim.") is False
        assert AnonymousDebatePanel._parse_vote("This is flawed and incorrect.") is False
        assert AnonymousDebatePanel._parse_vote("I refute this statement.") is False

    def test_parse_vote_ambiguous_defaults_to_score(self):
        """When approve and reject keywords both present or absent, use score."""
        # More approve keywords than reject
        assert AnonymousDebatePanel._parse_vote("approve support correct invalid") is True
        # More reject keywords
        assert AnonymousDebatePanel._parse_vote("reject oppose invalid correct") is False

    def test_estimate_confidence(self):
        high = AnonymousDebatePanel._estimate_confidence("I am definitely certain this is correct.")
        low = AnonymousDebatePanel._estimate_confidence("maybe this is possibly correct, uncertain.")
        assert high > low

    def test_estimate_confidence_default(self):
        mid = AnonymousDebatePanel._estimate_confidence("neutral statement here.")
        assert mid == 0.5


# ---------------------------------------------------------------------------
# Tests: Minority report
# ---------------------------------------------------------------------------


class TestMinorityReport:
    def test_minority_report_from_rejecting_voters(self):
        panel = AnonymousDebatePanel()
        args = [
            Argument(1, "a", Perspective.SUPPORTER, "This is great."),
            Argument(1, "b", Perspective.SKEPTIC, "I disagree."),
            Argument(2, "b", Perspective.SKEPTIC, "Still disagree."),
        ]
        ballots = [
            Ballot("a", True, 0.9, "Approve"),
            Ballot("b", False, 0.8, "Reject"),
        ]
        report = panel._generate_minority_report(args, ballots, passed=True)
        # Should return the last argument from a rejecting voter (b)
        assert "Still disagree" in report

    def test_minority_report_from_approving_when_not_passed(self):
        panel = AnonymousDebatePanel()
        args = [
            Argument(1, "a", Perspective.SUPPORTER, "Good."),
            Argument(1, "b", Perspective.SKEPTIC, "Bad."),
        ]
        ballots = [
            Ballot("a", True, 0.9, "A"),
            Ballot("b", False, 0.8, "R"),
        ]
        report = panel._generate_minority_report(args, ballots, passed=False)
        # Not passed -> minority = approving voters (a)
        assert "Good" in report

    def test_minority_report_unanimous_falls_back_to_minority_perspective(self):
        panel = AnonymousDebatePanel()
        args = [
            Argument(1, "a", Perspective.SUPPORTER, "Support A."),
            Argument(1, "b", Perspective.DOMAIN_EXPERT, "Expert says yes."),
            Argument(1, "c", Perspective.SKEPTIC, "Skeptic says no."),
        ]
        ballots = [
            Ballot("a", True, 0.9, "A"),
            Ballot("b", True, 0.8, "E"),
            Ballot("c", True, 0.7, "S"),
        ]
        report = panel._generate_minority_report(args, ballots, passed=True)
        # All approve, so no rejecting IDs. Falls back to MINORITY_PERSPECTIVES -> skeptic
        assert "Skeptic says no" in report

    def test_minority_report_empty_args(self):
        panel = AnonymousDebatePanel()
        report = panel._generate_minority_report([], [], True)
        assert report == "No minority report generated."


# ---------------------------------------------------------------------------
# Tests: Helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_render_transcript(self):
        args = [
            Argument(1, "a", Perspective.SUPPORTER, "Content A."),
            Argument(1, "b", Perspective.SKEPTIC, "Content B."),
        ]
        transcript = AnonymousDebatePanel._render_transcript(args)
        assert "Round 1" in transcript
        assert "supporter" in transcript.lower()
        assert "skeptic" in transcript.lower()
        assert "Content A" in transcript

    def test_build_prior_excludes_own(self):
        args = [
            Argument(1, "a", Perspective.SUPPORTER, "A1"),
            Argument(1, "b", Perspective.SKEPTIC, "B1"),
            Argument(1, "c", Perspective.DOMAIN_EXPERT, "C1"),
        ]
        panel = AnonymousDebatePanel()
        prior = panel._build_prior_for_panelist(args, "a")
        assert len(prior) == 2
        assert all(a.anonymous_id != "a" for a in prior)

    def test_build_prior_with_comm_graph(self):
        from lyra.verification.debate_panel import CommunicationGraph, CommunicationTopology

        args = [
            Argument(1, "a", Perspective.SUPPORTER, "A1"),
            Argument(1, "b", Perspective.SKEPTIC, "B1"),
            Argument(1, "c", Perspective.DOMAIN_EXPERT, "C1"),
        ]
        panel = AnonymousDebatePanel()
        graph = CommunicationGraph(
            topology=CommunicationTopology.STAR,
            edges=[("b", "a"), ("c", "a")],
            round_number=1,
        )
        prior = panel._build_prior_for_panelist(args, "a", graph)
        assert len(prior) == 2
        assert all(a.anonymous_id in ("b", "c") for a in prior)

    def test_build_prior_empty_graph(self):
        args = [Argument(1, "a", Perspective.SUPPORTER, "A1")]
        panel = AnonymousDebatePanel()
        from lyra.verification.debate_panel import CommunicationGraph, CommunicationTopology

        graph = CommunicationGraph(
            topology=CommunicationTopology.FULL_MESH,
            edges=[],
            round_number=1,
        )
        prior = panel._build_prior_for_panelist(args, "a", graph)
        assert prior == []  # Empty edges => no visible args

    def test_synthesize_consensus_approve(self):
        args = [Argument(1, "a", Perspective.SUPPORTER, "A")]
        consensus = AnonymousDebatePanel._synthesize_consensus("Test claim", args, approve=True)
        assert "Claim validated" in consensus
        assert "Test claim" in consensus

    def test_synthesize_consensus_reject(self):
        consensus = AnonymousDebatePanel._synthesize_consensus("Bad claim", [], approve=False)
        assert "Claim rejected" in consensus

    def test_seed_randomness(self):
        panel = AnonymousDebatePanel()
        panel.seed_randomness(42)
        import random

        val1 = random.randint(0, 1000)
        panel.seed_randomness(42)
        val2 = random.randint(0, 1000)
        assert val1 == val2

    def test_default_constructor(self):
        """Panel created with no args should still work."""
        panel = AnonymousDebatePanel()
        assert panel._voting_threshold == 2.0 / 3.0
        assert panel._forced_disagreement_rounds is True
        assert panel._evidence_anchoring is True
        assert panel._randomized_topology_per_round is True

    def test_quality_history_after_convene(self, panel_with_async_speaker, minimal_perspectives):
        """convene should record quality metrics."""
        import asyncio

        result = asyncio.run(
            panel_with_async_speaker.convene(
                topic="Test", perspectives=minimal_perspectives, rounds=1,
            )
        )
        history = panel_with_async_speaker.get_quality_history()
        assert len(history) >= 1

    def test_get_communication_graphs(self, panel_with_async_speaker, minimal_perspectives):
        """convene should accumulate communication graphs."""
        import asyncio

        result = asyncio.run(
            panel_with_async_speaker.convene(
                topic="Test", perspectives=minimal_perspectives, rounds=2,
            )
        )
        graphs = panel_with_async_speaker.get_communication_graphs()
        assert len(graphs) == 2

    @pytest.mark.asyncio
    async def test_convene_forced_disagreement_off(self, minimal_perspectives):
        async def speaker(t, p, prior):
            return f"Arg from {p.value}."

        panel = AnonymousDebatePanel(async_argument_fn=speaker, forced_disagreement_rounds=False)
        result = await panel.convene(
            topic="Test", perspectives=minimal_perspectives, rounds=1,
        )
        assert result.passed is not None


# ---------------------------------------------------------------------------
# Tests: Evidence anchoring helpers
# ---------------------------------------------------------------------------


class TestEvidenceAnchoring:
    def test_anchor_adds_citation(self):
        content = "This approach is correct."
        anchored = AnonymousDebatePanel._anchor_evidence(content, "Claim X")
        assert "[Evidence required:" in anchored

    def test_anchor_already_present(self):
        content = "According to arXiv:2401.12345, this is correct."
        anchored = AnonymousDebatePanel._anchor_evidence(content, "Claim X")
        assert anchored == content

    def test_anchor_url(self):
        content = "Per https://example.com/spec, this is correct."
        anchored = AnonymousDebatePanel._anchor_evidence(content, "Claim X")
        assert "[Evidence required:" not in anchored

    def test_extract_citations_arxiv(self):
        citations = AnonymousDebatePanel.extract_citations("See arXiv:2401.12345")
        assert len(citations) >= 1
        assert "2401.12345" in citations[0].source

    def test_extract_citations_doi(self):
        citations = AnonymousDebatePanel.extract_citations("doi:10.1000/xyz123")
        assert len(citations) >= 1

    def test_extract_citations_url(self):
        citations = AnonymousDebatePanel.extract_citations("See https://example.com/doc")
        assert len(citations) >= 1
        assert "https://example.com/doc" in citations[0].source

    def test_extract_citations_according_to(self):
        citations = AnonymousDebatePanel.extract_citations(
            "According to the IEEE standard, this is correct."
        )
        assert len(citations) >= 1
        assert "IEEE standard" in citations[0].source

    def test_extract_citations_empty(self):
        assert AnonymousDebatePanel.extract_citations("Just an opinion.") == []
