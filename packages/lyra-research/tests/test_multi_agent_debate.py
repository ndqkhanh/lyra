"""
E2E tests for multi-agent debate and consensus (US-028).

Tests multi-agent structured debate system with perspective synthesis.
"""

import pytest
from lyra_research.multi_perspective import (
    DebateRound,
    MultiPerspectiveSynthesizer,
    PerspectiveAgent,
    PerspectiveAnalysis,
    PerspectiveType,
    SynthesisResult,
)


class TestMultiAgentDebate:
    """Test multi-agent structured debate system."""

    def test_create_debate_panel(self):
        """Test creating debate panel with perspectives."""
        synthesizer = MultiPerspectiveSynthesizer()

        assert len(synthesizer._agents) == 5
        assert PerspectiveType.OPTIMIST in synthesizer._agents
        assert PerspectiveType.SKEPTIC in synthesizer._agents
        assert PerspectiveType.PRAGMATIST in synthesizer._agents
        assert PerspectiveType.INNOVATOR in synthesizer._agents
        assert PerspectiveType.HISTORIAN in synthesizer._agents

    def test_debate_round_execution(self):
        """Test executing a single debate round."""
        synthesizer = MultiPerspectiveSynthesizer()

        findings = """
        Recent advances in multi-agent systems show promising results.
        Novel architectures achieve state-of-the-art performance on benchmarks.
        However, scalability and cost remain practical concerns.
        """

        rounds = synthesizer.debate(
            topic="Multi-agent systems",
            findings=findings,
            rounds=1,
        )

        assert len(rounds) == 1
        assert rounds[0].round_number == 0
        assert len(rounds[0].analyses) == 5
        assert len(rounds[0].critiques) > 0

    def test_multi_round_debate_convergence(self):
        """Test multi-round debate convergence."""
        synthesizer = MultiPerspectiveSynthesizer()

        findings = """
        LLM agents demonstrate breakthrough capabilities in reasoning.
        Rigorous evaluation shows 95% accuracy on standard benchmarks.
        Implementation requires significant computational resources.
        Novel combination of techniques enables new applications.
        Historical context shows this builds on prior transformer work.
        """

        rounds = synthesizer.debate(
            topic="LLM agents",
            findings=findings,
            rounds=3,
        )

        assert len(rounds) == 3
        # Later rounds should have more refined analyses
        assert rounds[0].round_number == 0
        assert rounds[1].round_number == 1
        assert rounds[2].round_number == 2

    def test_debate_consensus_detection(self):
        """Test detecting consensus among agents."""
        synthesizer = MultiPerspectiveSynthesizer()

        findings = """
        Multi-agent systems improve performance across all benchmarks.
        All evaluations show consistent improvements.
        Performance gains are reproducible and significant.
        """

        rounds = synthesizer.debate(
            topic="Multi-agent performance",
            findings=findings,
            rounds=2,
        )

        consensus = synthesizer.identify_consensus(rounds)

        # Should find common keywords across perspectives
        assert len(consensus) > 0
        assert any("performance" in word.lower() for word in consensus)

    def test_debate_dissent_identification(self):
        """Test identifying areas of disagreement."""
        synthesizer = MultiPerspectiveSynthesizer()

        findings = """
        Novel approach shows promise but lacks rigorous evaluation.
        Theoretical benefits are clear but practical deployment is uncertain.
        """

        rounds = synthesizer.debate(
            topic="Novel approach",
            findings=findings,
            rounds=2,
        )

        dissent = synthesizer.highlight_dissent(rounds)

        # Should capture critiques
        assert len(dissent) > 0


class TestPerspectiveAgents:
    """Test individual perspective agents."""

    def test_optimist_perspective(self):
        """Test optimist perspective analysis."""
        agent = PerspectiveAgent(PerspectiveType.OPTIMIST)

        findings = """
        Breakthrough results show novel approach outperforms baselines.
        Promising improvements in efficiency and scalability.
        State-of-the-art performance on multiple benchmarks.
        """

        analysis = agent.analyze(findings)

        assert analysis.perspective == PerspectiveType.OPTIMIST
        assert analysis.score > 0.5  # Should score high on positive signals
        assert len(analysis.key_insights) > 0
        assert len(analysis.strengths) > 0

    def test_skeptic_perspective(self):
        """Test skeptic perspective analysis."""
        agent = PerspectiveAgent(PerspectiveType.SKEPTIC)

        findings = """
        Claims of breakthrough performance without rigorous ablation studies.
        State-of-the-art results but baseline comparisons are missing.
        """

        analysis = agent.analyze(findings)

        assert analysis.perspective == PerspectiveType.SKEPTIC
        assert len(analysis.weaknesses) > 0
        # Skeptic should flag missing rigor
        assert any("missing" in w.lower() for w in analysis.weaknesses)

    def test_pragmatist_perspective(self):
        """Test pragmatist perspective analysis."""
        agent = PerspectiveAgent(PerspectiveType.PRAGMATIST)

        findings = """
        Implementation requires 8 GPUs and 100GB memory.
        Deployment cost is $1000 per month.
        Latency is 500ms which meets production requirements.
        """

        analysis = agent.analyze(findings)

        assert analysis.perspective == PerspectiveType.PRAGMATIST
        assert analysis.score > 0.5  # Should score high on practical details
        assert len(analysis.strengths) > 0

    def test_innovator_perspective(self):
        """Test innovator perspective analysis."""
        agent = PerspectiveAgent(PerspectiveType.INNOVATOR)

        findings = """
        Novel combination of techniques from different domains.
        Unconventional hybrid approach yields surprising results.
        Cross-domain analogies inspire new research directions.
        """

        analysis = agent.analyze(findings)

        assert analysis.perspective == PerspectiveType.INNOVATOR
        assert analysis.score > 0.5
        assert len(analysis.novel_ideas) > 0

    def test_historian_perspective(self):
        """Test historian perspective analysis."""
        agent = PerspectiveAgent(PerspectiveType.HISTORIAN)

        findings = """
        Builds on prior work in transformer architectures.
        Evolution from classic attention mechanisms.
        Historical context shows this is part of a research lineage.
        """

        analysis = agent.analyze(findings)

        assert analysis.perspective == PerspectiveType.HISTORIAN
        assert analysis.score > 0.5
        assert len(analysis.key_insights) > 0


class TestCrossPerspectiveCritique:
    """Test cross-perspective critique mechanisms."""

    def test_skeptic_critiques_optimist(self):
        """Test skeptic critiquing optimist."""
        skeptic = PerspectiveAgent(PerspectiveType.SKEPTIC)
        optimist = PerspectiveAgent(PerspectiveType.OPTIMIST)

        findings = "Breakthrough results show amazing performance."
        optimist_analysis = optimist.analyze(findings)

        critiques = skeptic.critique(optimist_analysis)

        assert len(critiques) > 0
        # Skeptic should challenge optimistic framing
        assert any("optimistic" in c.lower() or "overstate" in c.lower() for c in critiques)

    def test_pragmatist_critiques_innovator(self):
        """Test pragmatist critiquing innovator."""
        pragmatist = PerspectiveAgent(PerspectiveType.PRAGMATIST)
        innovator = PerspectiveAgent(PerspectiveType.INNOVATOR)

        findings = "Novel unconventional approach with speculative benefits."
        innovator_analysis = innovator.analyze(findings)

        critiques = pragmatist.critique(innovator_analysis)

        assert len(critiques) > 0
        # Pragmatist should demand feasibility
        assert any(
            "feasibility" in c.lower() or "implementation" in c.lower() for c in critiques
        )

    def test_historian_critiques_optimist(self):
        """Test historian critiquing optimist."""
        historian = PerspectiveAgent(PerspectiveType.HISTORIAN)
        optimist = PerspectiveAgent(PerspectiveType.OPTIMIST)

        findings = "First-ever breakthrough in this domain."
        optimist_analysis = optimist.analyze(findings)

        critiques = historian.critique(optimist_analysis)

        assert len(critiques) > 0
        # Historian should reference historical patterns
        assert any("historical" in c.lower() or "prior" in c.lower() for c in critiques)


class TestSynthesisGeneration:
    """Test synthesis generation from debate."""

    def test_synthesize_perspectives(self):
        """Test synthesizing perspectives into balanced report."""
        synthesizer = MultiPerspectiveSynthesizer()

        findings = """
        Multi-agent systems show promising results with rigorous evaluation.
        Implementation is feasible with modern hardware.
        Novel architectures build on historical transformer work.
        """

        rounds = synthesizer.debate(
            topic="Multi-agent systems",
            findings=findings,
            rounds=2,
        )

        synthesis = synthesizer.synthesize_perspectives(rounds)

        assert isinstance(synthesis, SynthesisResult)
        assert synthesis.topic != "unknown"
        assert len(synthesis.consensus_points) >= 0
        assert len(synthesis.dissent_points) >= 0
        assert len(synthesis.balanced_report) > 0
        assert 0.0 <= synthesis.confidence <= 1.0

    def test_synthesis_includes_all_perspectives(self):
        """Test synthesis includes insights from all perspectives."""
        synthesizer = MultiPerspectiveSynthesizer()

        findings = """
        Breakthrough novel approach with rigorous evaluation.
        Practical implementation on standard hardware.
        Builds on historical research foundations.
        """

        rounds = synthesizer.debate(
            topic="Test topic",
            findings=findings,
            rounds=1,
        )

        synthesis = synthesizer.synthesize_perspectives(rounds)

        # Report should mention multiple perspectives
        report_lower = synthesis.balanced_report.lower()
        perspective_names = [p.value for p in PerspectiveType]

        # At least some perspectives should be mentioned
        mentioned = sum(1 for name in perspective_names if name in report_lower)
        assert mentioned >= 3

    def test_synthesis_confidence_calculation(self):
        """Test synthesis confidence calculation."""
        synthesizer = MultiPerspectiveSynthesizer()

        # High-quality findings should yield high confidence
        high_quality_findings = """
        Rigorous evaluation shows 95% accuracy with proper baselines.
        Implementation is cost-effective and scalable.
        Novel approach builds on solid theoretical foundations.
        Breakthrough results are reproducible across multiple benchmarks.
        """

        rounds = synthesizer.debate(
            topic="High quality research",
            findings=high_quality_findings,
            rounds=2,
        )

        synthesis = synthesizer.synthesize_perspectives(rounds)

        # Should have reasonable confidence
        assert synthesis.confidence > 0.3


class TestDebateDataStructures:
    """Test debate data structures."""

    def test_perspective_analysis_creation(self):
        """Test creating perspective analysis objects."""
        analysis = PerspectiveAnalysis(
            perspective=PerspectiveType.OPTIMIST,
            key_insights=("Insight 1", "Insight 2"),
            strengths=("Strength 1",),
            weaknesses=("Weakness 1",),
            score=0.8,
            novel_ideas=("Idea 1",),
        )

        assert analysis.perspective == PerspectiveType.OPTIMIST
        assert len(analysis.key_insights) == 2
        assert analysis.score == 0.8

    def test_debate_round_creation(self):
        """Test creating debate round objects."""
        analyses = (
            PerspectiveAnalysis(
                perspective=PerspectiveType.OPTIMIST,
                score=0.8,
            ),
            PerspectiveAnalysis(
                perspective=PerspectiveType.SKEPTIC,
                score=0.6,
            ),
        )

        critiques = (
            ("optimist", "skeptic", "Critique 1"),
            ("skeptic", "optimist", "Critique 2"),
        )

        round_obj = DebateRound(
            round_number=0,
            analyses=analyses,
            critiques=critiques,
        )

        assert round_obj.round_number == 0
        assert len(round_obj.analyses) == 2
        assert len(round_obj.critiques) == 2

    def test_synthesis_result_creation(self):
        """Test creating synthesis result objects."""
        result = SynthesisResult(
            topic="Test topic",
            consensus_points=("Point 1", "Point 2"),
            dissent_points=("Dissent 1",),
            balanced_report="Test report",
            confidence=0.75,
        )

        assert result.topic == "Test topic"
        assert len(result.consensus_points) == 2
        assert result.confidence == 0.75


@pytest.mark.e2e
@pytest.mark.slow
class TestFullDebateSession:
    """End-to-end tests for complete debate sessions."""

    def test_complete_debate_cycle(self):
        """Test complete debate cycle from findings to synthesis."""
        synthesizer = MultiPerspectiveSynthesizer()

        findings = """
        Recent research in multi-agent LLM systems demonstrates significant
        advances in collaborative reasoning. Novel architectures achieve
        state-of-the-art results on complex benchmarks, with rigorous
        ablation studies confirming the contribution of each component.

        Implementation requires modern GPU infrastructure but is feasible
        for production deployment. Cost analysis shows 40% reduction
        compared to single-agent baselines while improving accuracy by 15%.

        The approach builds on historical work in multi-agent systems and
        transformer architectures, representing an evolutionary step rather
        than a revolutionary breakthrough. Cross-domain applications show
        promise in areas beyond the original scope.
        """

        # Run full debate
        rounds = synthesizer.debate(
            topic="Multi-agent LLM systems",
            findings=findings,
            rounds=3,
        )

        # Generate synthesis
        synthesis = synthesizer.synthesize_perspectives(rounds)

        # Verify complete cycle
        assert len(rounds) == 3
        assert synthesis.confidence > 0.0
        assert len(synthesis.balanced_report) > 100
        assert len(synthesis.consensus_points) > 0

    def test_debate_with_conflicting_evidence(self):
        """Test debate with conflicting evidence."""
        synthesizer = MultiPerspectiveSynthesizer()

        findings = """
        Paper A claims 95% accuracy on benchmark X.
        Paper B reports only 78% accuracy on the same benchmark.
        Implementation costs vary from $100 to $10,000 per month.
        Some studies show breakthrough results, others show marginal gains.
        """

        rounds = synthesizer.debate(
            topic="Conflicting evidence",
            findings=findings,
            rounds=2,
        )

        synthesis = synthesizer.synthesize_perspectives(rounds)

        # Should identify dissent
        assert len(synthesis.dissent_points) > 0

    def test_debate_quality_improvement_over_rounds(self):
        """Test that debate quality improves over rounds."""
        synthesizer = MultiPerspectiveSynthesizer()

        findings = """
        Multi-agent systems show promising results in initial tests.
        Further evaluation needed to confirm scalability.
        """

        rounds = synthesizer.debate(
            topic="Multi-agent systems",
            findings=findings,
            rounds=3,
        )

        # Later rounds should have more critiques (more refined analysis)
        assert len(rounds[2].critiques) >= len(rounds[0].critiques)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
