"""Tests for UnifiedResearchState — Phase 21 Architecture Upgrade Module 1/4."""
from datetime import datetime

from lyra_research.research_state import (
    ResearchPhase,
    SessionStatus,
    UnifiedResearchState,
)


class TestResearchPhase:
    def test_all_phases_present(self):
        assert len(list(ResearchPhase)) == 10
        assert ResearchPhase.CLARIFY.value == "clarify"
        assert ResearchPhase.SEARCH.value == "search"
        assert ResearchPhase.MEMORIZE.value == "memorize"

    def test_phase_ordering(self):
        phases = list(ResearchPhase)
        assert phases[0] == ResearchPhase.CLARIFY
        assert phases[-1] == ResearchPhase.MEMORIZE


class TestSessionStatus:
    def test_all_statuses(self):
        statuses = list(SessionStatus)
        assert SessionStatus.CREATED in statuses
        assert SessionStatus.RUNNING in statuses
        assert SessionStatus.COMPLETED in statuses
        assert SessionStatus.FAILED in statuses


class TestUnifiedResearchStateDefaults:
    def test_default_initialization(self):
        state = UnifiedResearchState()
        assert state.current_phase == ResearchPhase.CLARIFY
        assert state.status == SessionStatus.CREATED
        assert state.depth == "standard"
        assert state.phase_index == 0
        assert isinstance(state.started_at, datetime)
        assert state.completed_at is None

    def test_custom_topic_and_depth(self):
        state = UnifiedResearchState(
            topic="Quantum Computing",
            depth="deep",
        )
        assert state.topic == "Quantum Computing"
        assert state.depth == "deep"

    def test_session_id_unique(self):
        s1 = UnifiedResearchState()
        s2 = UnifiedResearchState()
        assert s1.session_id != s2.session_id


class TestAdvancePhase:
    def test_advance_to_specific_phase(self):
        state = UnifiedResearchState()
        state.advance_phase(ResearchPhase.SEARCH)
        assert state.current_phase == ResearchPhase.SEARCH
        assert state.phase_index == 1

    def test_advance_auto_sequence(self):
        state = UnifiedResearchState()
        state.advance_phase()  # clarify → plan
        assert state.current_phase == ResearchPhase.PLAN
        state.advance_phase()  # plan → search
        assert state.current_phase == ResearchPhase.SEARCH

    def test_advance_through_all_phases(self):
        state = UnifiedResearchState()
        for _ in range(9):  # Already at clarify, 9 advances to memorize
            state.advance_phase()
        assert state.current_phase == ResearchPhase.MEMORIZE

    def test_advance_at_end_does_not_wrap(self):
        state = UnifiedResearchState(current_phase=ResearchPhase.MEMORIZE)
        state.advance_phase()
        assert state.current_phase == ResearchPhase.MEMORIZE

    def test_advance_records_history(self):
        state = UnifiedResearchState()
        state.advance_phase(ResearchPhase.PLAN)
        state.advance_phase(ResearchPhase.SEARCH)
        assert len(state.phase_history) == 2
        assert state.phase_history[0]["phase"] == "clarify"
        assert state.phase_history[1]["phase"] == "plan"


class TestErrorRecording:
    def test_record_error_with_current_phase(self):
        state = UnifiedResearchState()
        state.record_error("Something went wrong")
        assert len(state.errors) == 1
        assert state.errors[0]["message"] == "Something went wrong"
        assert state.errors[0]["phase"] == "clarify"

    def test_record_error_with_explicit_phase(self):
        state = UnifiedResearchState()
        state.record_error("Search failed", phase="search")
        assert state.errors[0]["phase"] == "search"

    def test_multiple_errors(self):
        state = UnifiedResearchState()
        state.record_error("Error 1")
        state.record_error("Error 2")
        state.record_error("Error 3")
        assert len(state.errors) == 3


class TestMarkCompleted:
    def test_mark_completed(self):
        state = UnifiedResearchState()
        state.mark_completed()
        assert state.status == SessionStatus.COMPLETED
        assert isinstance(state.completed_at, datetime)

    def test_mark_failed(self):
        state = UnifiedResearchState()
        state.mark_failed("Critical error occurred")
        assert state.status == SessionStatus.FAILED
        assert isinstance(state.completed_at, datetime)
        assert len(state.errors) == 1
        assert state.errors[0]["message"] == "Critical error occurred"


class TestProgress:
    def test_get_progress_pct_initial(self):
        state = UnifiedResearchState()
        assert state.get_progress_pct() == 0.0

    def test_get_progress_pct_midway(self):
        state = UnifiedResearchState()
        for _ in range(5):
            state.advance_phase()
        pct = state.get_progress_pct()
        assert pct > 0.0
        assert pct < 100.0

    def test_get_progress_pct_complete(self):
        state = UnifiedResearchState(phase_index=10)
        assert state.get_progress_pct() >= 100.0


class TestSerialization:
    def test_to_dict_contains_keys(self):
        state = UnifiedResearchState(topic="Test")
        data = state.to_dict()
        assert data["topic"] == "Test"
        assert data["current_phase"] == "clarify"
        assert data["status"] == "created"
        assert isinstance(data["started_at"], str)

    def test_to_dict_with_completed_at(self):
        state = UnifiedResearchState()
        state.mark_completed()
        data = state.to_dict()
        assert data["completed_at"] is not None
        assert isinstance(data["completed_at"], str)

    def test_roundtrip(self):
        state = UnifiedResearchState(
            topic="Roundtrip Test",
            depth="deep",
            sources_found=42,
            papers_analyzed=15,
        )
        state.advance_phase(ResearchPhase.SEARCH)
        state.advance_phase(ResearchPhase.ANALYZE)
        state.record_error("Test error")

        data = state.to_dict()
        restored = UnifiedResearchState.from_dict(data)

        assert restored.topic == state.topic
        assert restored.depth == state.depth
        assert restored.current_phase == state.current_phase
        assert restored.sources_found == state.sources_found
        assert restored.papers_analyzed == state.papers_analyzed
        assert restored.status == state.status
        assert len(restored.errors) == len(state.errors)

    def test_from_dict_preserves_datetime(self):
        data = UnifiedResearchState(topic="DT Test").to_dict()
        restored = UnifiedResearchState.from_dict(data)
        assert isinstance(restored.started_at, datetime)


class TestMetrics:
    def test_quality_metrics_default_zero(self):
        state = UnifiedResearchState()
        assert state.verification_rate == 0.0
        assert state.citation_fidelity == 0.0
        assert state.overall_quality_score == 0.0

    def test_model_usage_tracking(self):
        state = UnifiedResearchState()
        state.model_calls["sonnet"] = 5
        state.total_tokens = 10000
        state.estimated_cost_usd = 0.15
        assert state.model_calls["sonnet"] == 5
        assert state.total_tokens == 10000
        assert state.estimated_cost_usd == 0.15

    def test_discovery_progress(self):
        state = UnifiedResearchState(
            sources_found=100,
            sources_filtered=30,
            sources_fetched=70,
        )
        assert state.sources_found == 100
        assert state.sources_filtered == 30
        assert state.sources_fetched == 70

    def test_analysis_progress(self):
        state = UnifiedResearchState(
            papers_analyzed=25,
            repos_analyzed=10,
            claims_verified=18,
            claims_falsified=7,
        )
        assert state.papers_analyzed == 25
        assert state.repos_analyzed == 10
        assert state.claims_verified == 18

    def test_gap_detection(self):
        state = UnifiedResearchState(
            gaps_found=5,
            gaps_by_severity={"critical": 1, "high": 2, "medium": 2},
        )
        assert state.gaps_found == 5
        assert state.gaps_by_severity["critical"] == 1


class TestGateResults:
    def test_gate_results(self):
        state = UnifiedResearchState()
        state.gate_results = {
            "quality_gate": True,
            "safety_gate": True,
            "compliance_gate": False,
        }
        assert state.gate_results["quality_gate"] is True
        assert state.gate_results["compliance_gate"] is False

    def test_intermediate_results(self):
        state = UnifiedResearchState()
        state.raw_discovery_results = [{"source": "arxiv", "count": 20}]
        state.ranked_sources = [{"title": "Paper A", "rank": 1}]
        assert len(state.raw_discovery_results) == 1
        assert len(state.ranked_sources) == 1
