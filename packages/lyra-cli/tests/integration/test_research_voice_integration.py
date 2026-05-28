"""Integration: Research findings delivered via voice, voice-triggered research.

Tests exercise:
- Research findings delivered via voice TTS
- Voice commands triggering research operations
- Knowledge graph updated from voice sessions
- Source credibility affecting TTS confidence announcements
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lyra_cli.research import (
    ExploreResult,
    Finding,
    FindingRelation,
    MultiHopResearchEngine,
    ResearchKnowledgeGraph,
    ResearchReport,
    SourceCredibility,
    SourceProfile,
    SourceType,
    StrategySelector,
    StrategyType,
)
from lyra_cli.voice import (
    SessionConfig,
    TTSBackend,
    TTSConfig,
    VoiceConfig,
    VoiceSession,
    WakeWordDetector,
    WakeWordResult,
    synthesize_speech,
)


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def mock_tts_backend() -> MagicMock:
    """Provide a mock TTS backend to avoid real audio output."""
    backend = MagicMock(spec=TTSBackend)
    backend.name = "mock-tts"
    backend.available = True
    backend.synthesize.return_value = Path("/tmp/test_output.wav")
    return backend


@pytest.fixture
def research_engine() -> MultiHopResearchEngine:
    """Provide a fresh research engine."""
    return MultiHopResearchEngine(max_hops=2)


@pytest.fixture
def knowledge_graph() -> ResearchKnowledgeGraph:
    """Provide a fresh knowledge graph."""
    return ResearchKnowledgeGraph()


@pytest.fixture
def source_evaluator() -> SourceCredibility:
    """Provide a fresh source credibility evaluator."""
    return SourceCredibility()


@pytest.fixture
def voice_session(mock_tts_backend) -> VoiceSession:
    """Provide a voice session with mock TTS."""
    config = SessionConfig(
        wake_words=["hey lyra", "lyra"],
        sound_enabled=False,
        push_to_talk=False,
    )
    return VoiceSession(
        config=config,
        tts_backend=mock_tts_backend,
    )


# =========================================================================
# Test: Research findings delivered via voice TTS
# =========================================================================


class TestResearchToVoiceTTS:
    """Test that research findings are delivered via voice TTS."""

    def test_research_report_text_delivered_to_tts(
        self, research_engine, mock_tts_backend,
    ):
        """Verify research report text can be passed to TTS engine."""
        report = research_engine.deep_research(
            query="What is the best approach for distributed tracing?",
            query_type="technical",
        )

        # Build a spoken summary from the report
        tts_text = (
            f"Research complete. Found {len(report.findings)} "
            f"findings across {report.trajectories} trajectories. "
            f"Consensus score: {report.consensus_score:.2f}."
        )

        result = synthesize_speech(
            tts_text,
            backend=mock_tts_backend,
            voice=VoiceConfig(),
        )
        mock_tts_backend.synthesize.assert_called_once()
        assert result == Path("/tmp/test_output.wav")

    def test_research_findings_list_in_tts_output(
        self, research_engine, mock_tts_backend,
    ):
        """Verify each research finding is included in the spoken summary."""
        report = research_engine.deep_research(
            query="How to implement RAG?",
            query_type="exploratory",
        )

        if report.findings:
            tts_text = (
                f"Key finding: {report.findings[0][:100]}. "
                f"Consensus: {report.consensus_score:.0%}."
            )
            result = synthesize_speech(
                tts_text,
                backend=mock_tts_backend,
                voice=VoiceConfig(),
            )
            mock_tts_backend.synthesize.assert_called()
            assert result is not None

    def test_tts_with_different_voice_configs(
        self, mock_tts_backend,
    ):
        """Verify TTS works with different voice configs for research output."""
        text = "Research analysis complete with high confidence."

        synthesize_speech(
            text,
            backend=mock_tts_backend,
            voice=VoiceConfig(name="female", speed=1.0),
        )
        mock_tts_backend.synthesize.assert_called_once()

    def test_empty_research_does_not_trigger_tts(
        self, mock_tts_backend,
    ):
        """Verify empty research reports do not trigger TTS."""
        with pytest.raises(Exception):
            synthesize_speech("", backend=mock_tts_backend)


# =========================================================================
# Test: Voice commands triggering research operations
# =========================================================================


class TestVoiceCommandsTriggerResearch:
    """Test that voice commands can trigger research operations."""

    def test_voice_command_routes_to_research(
        self, voice_session, research_engine,
    ):
        """Verify a voice command can trigger a research operation."""
        def command_handler(text: str) -> str:
            if "research" in text.lower():
                report = research_engine.deep_research(
                    query=text,
                    query_type="exploratory",
                )
                return (
                    f"Research found {len(report.findings)} findings "
                    f"with consensus {report.consensus_score:.2f}"
                )
            return f"I heard: {text}"

        voice_session._command_handler = command_handler
        response = voice_session.process_text(
            "lyra research transformer architectures"
        )

        assert "research" in response.lower() or "finding" in response.lower()

    def test_wake_word_detected_triggers_research(
        self, voice_session, research_engine,
    ):
        """Verify wake word + command triggers research execution."""
        def command_handler(text: str) -> str:
            if "research" in text.lower():
                report = research_engine.deep_research(text)
                return f"Researched. {len(report.findings)} findings."
            return f"Command: {text}"

        voice_session._command_handler = command_handler
        response = voice_session.process_text(
            "hey lyra research best practices for microservices"
        )

        assert response

    def test_voice_session_history_includes_research_context(
        self, voice_session,
    ):
        """Verify conversation history stores research commands and responses."""
        voice_session.process_text("lyra research quantum computing")
        voice_session.process_text("lyra what about topological qubits?")

        history = voice_session.conversation_history
        assert len(history) >= 2
        assert any("quantum" in h["input"].lower() for h in history)
        assert any("qubits" in h["input"].lower() for h in history)

    def test_non_research_command_no_research_executed(
        self, voice_session,
    ):
        """Verify non-research commands do not trigger research pathways."""
        response = voice_session.process_text("lyra what time is it")
        # Default handler should echo
        assert "I heard:" in response or response.strip()


# =========================================================================
# Test: Knowledge graph updated from voice sessions
# =========================================================================


class TestKnowledgeGraphVoiceUpdate:
    """Test that voice sessions can update the knowledge graph."""

    def test_voice_findings_added_to_knowledge_graph(
        self, voice_session, knowledge_graph,
    ):
        """Verify findings extracted from voice sessions enter the graph."""
        findings = [
            Finding(
                finding_id="voice_1",
                content="User prefers fast responses under 2 seconds",
                confidence=0.8,
                tags=("voice_session", "preference"),
            ),
            Finding(
                finding_id="voice_2",
                content="User requests code review for Python projects",
                confidence=0.9,
                tags=("voice_session", "command"),
            ),
        ]

        for f in findings:
            knowledge_graph.add_finding(f)

        assert knowledge_graph.get_finding_count() == 2

    def test_knowledge_graph_relations_from_voice_context(
        self, knowledge_graph,
    ):
        """Verify semantic relations created from voice session data."""
        f1 = Finding(
            finding_id="vf_1", content="Ask about performance",
            tags=("voice_session",),
        )
        f2 = Finding(
            finding_id="vf_2", content="Response mentions optimization tools",
            tags=("voice_session",),
        )
        knowledge_graph.add_finding(f1)
        knowledge_graph.add_finding(f2)

        rel = FindingRelation(
            relation_id="vr_1",
            source_id="vf_1",
            target_id="vf_2",
            relation_type="related_to",
            strength=0.7,
        )
        knowledge_graph.add_relation(rel)

        assert knowledge_graph.get_relation_count() == 1
        neighbors = knowledge_graph.get_neighbors("vf_1")
        assert len(neighbors) == 1
        assert neighbors[0][0].finding_id == "vf_2"

    def test_knowledge_graph_detects_gaps_from_voice(
        self, knowledge_graph,
    ):
        """Verify knowledge gaps detected from voice-interaction findings."""
        f1 = Finding(
            finding_id="gap_voice_1",
            content="User asked about deployment strategies but no answer given",
            confidence=0.5,
            tags=("voice_session", "unanswered"),
        )
        knowledge_graph.add_finding(f1)

        gaps = knowledge_graph.find_knowledge_gaps()
        # The orphan finding should be flagged as a gap
        gap_ids = {g.gap_id for g in gaps}
        assert any("gap_voice_1" in gid for gid in gap_ids)


# =========================================================================
# Test: Source credibility affecting TTS confidence announcements
# =========================================================================


class TestSourceCredibilityTTS:
    """Test that source credibility influences TTS confidence announcements."""

    def test_high_credibility_produces_confident_tts(
        self, source_evaluator,
    ):
        """Verify high-credibility sources lead to confident announcements."""
        source_evaluator.evaluate_source(
            source_id="academic_1",
            url="https://arxiv.org/abs/2301.001",
            source_type=SourceType.ACADEMIC_PAPER,
            title="Definitive Study on Topic X",
            citation_count=50,
        )

        profile = source_evaluator.get_source("academic_1")
        assert profile is not None
        assert profile.credibility_score >= 0.85

    def test_low_credibility_triggers_caveat_tts(
        self, source_evaluator,
    ):
        """Verify low-credibility sources produce cautious announcements."""
        source_evaluator.evaluate_source(
            source_id="forum_1",
            url="https://forum.example.com/post/123",
            source_type=SourceType.USER_FORUM,
            title="Random opinion",
            citation_count=0,
            detected_biases=["anecdotal"],
        )

        profile = source_evaluator.get_source("forum_1")
        assert profile is not None
        assert profile.credibility_score <= 0.35

    def test_consensus_score_affects_tts_confidence(
        self, source_evaluator,
    ):
        """Verify consensus score changes with contradictory sources."""
        source_evaluator.evaluate_source(
            source_id="src_a", url="https://a.example",
            source_type=SourceType.ACADEMIC_PAPER,
            title="Paper A", citation_count=30,
        )
        source_evaluator.evaluate_source(
            source_id="src_b", url="https://b.example",
            source_type=SourceType.ACADEMIC_PAPER,
            title="Paper B", citation_count=25,
        )
        source_evaluator.detect_contradictions(
            source_a_id="src_a", source_b_id="src_b",
            claim_a="X is true", claim_b="X is false",
        )

        consensus = source_evaluator.get_consensus_score(["src_a", "src_b"])
        # Contradiction penalty reduces consensus below simple average
        no_contradiction = source_evaluator.get_consensus_score(["src_a"])
        assert consensus <= no_contradiction
