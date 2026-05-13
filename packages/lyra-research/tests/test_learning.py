"""
Tests for the Continual Research Learning System (learning.py).
"""

import pytest
from unittest.mock import MagicMock

from lyra_research.learning import (
    ExtractedStrategy,
    ResearchStrategyExtractor,
    CaseMatch,
    CaseSelectionPolicy,
    DomainModel,
    DomainExpertiseAccumulator,
    ResearchWorkflowOptimizer,
    GateDecision,
    SelfImprovementGate,
)
from lyra_research.memory import ResearchCase, SessionCaseBank, ResearchStrategyMemory
from lyra_research.evaluation import QualityTrendTracker, ResearchQualityMetrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_progress(
    topic: str = "attention mechanisms",
    sources_found: dict | None = None,
    papers_analyzed: int = 5,
    repos_analyzed: int = 2,
    gaps_found: int = 3,
):
    """Create a mock ResearchProgress for testing."""
    progress = MagicMock()
    progress.topic = topic
    progress.session_id = "test-session"
    progress.sources_found = sources_found or {"arxiv": 10, "github": 5}
    progress.papers_analyzed = papers_analyzed
    progress.repos_analyzed = repos_analyzed
    progress.gaps_found = gaps_found
    progress.report = None
    return progress


def _make_metrics(
    session_id: str = "s1",
    topic: str = "test",
    overall_score: float = 0.8,
    citation_fidelity: float = 1.0,
) -> ResearchQualityMetrics:
    m = ResearchQualityMetrics(session_id=session_id, topic=topic)
    m.overall_score = overall_score
    m.citation_fidelity = citation_fidelity
    return m


# ---------------------------------------------------------------------------
# ResearchStrategyExtractor — domain detection
# ---------------------------------------------------------------------------

def test_strategy_extractor_detect_domain_ml():
    ext = ResearchStrategyExtractor()
    assert ext.detect_domain("deep learning for image classification") == "ml"


def test_strategy_extractor_detect_domain_nlp():
    ext = ResearchStrategyExtractor()
    assert ext.detect_domain("transformer tokenization for NLP text processing") == "nlp"


def test_strategy_extractor_detect_domain_systems():
    ext = ResearchStrategyExtractor()
    assert ext.detect_domain("distributed system latency optimization") == "systems"


def test_strategy_extractor_detect_domain_vision():
    ext = ResearchStrategyExtractor()
    assert ext.detect_domain("image segmentation with CNN") == "vision"


def test_strategy_extractor_detect_domain_rl():
    ext = ResearchStrategyExtractor()
    assert ext.detect_domain("reinforcement learning policy gradient") == "rl"


def test_strategy_extractor_detect_domain_unknown():
    ext = ResearchStrategyExtractor()
    assert ext.detect_domain("quantum computing applications") == "general"


# ---------------------------------------------------------------------------
# ResearchStrategyExtractor — topic type detection
# ---------------------------------------------------------------------------

def test_strategy_extractor_detect_topic_type_paper():
    ext = ResearchStrategyExtractor()
    sources = {"arxiv": 20, "semantic_scholar": 10, "github": 2}
    assert ext.detect_topic_type(sources) == "paper_search"


def test_strategy_extractor_detect_topic_type_repo():
    ext = ResearchStrategyExtractor()
    sources = {"github": 15, "arxiv": 1}
    assert ext.detect_topic_type(sources) == "repo_search"


def test_strategy_extractor_detect_topic_type_mixed():
    ext = ResearchStrategyExtractor()
    sources = {"arxiv": 5, "github": 5}
    assert ext.detect_topic_type(sources) == "mixed_search"


def test_strategy_extractor_detect_topic_type_empty():
    ext = ResearchStrategyExtractor()
    assert ext.detect_topic_type({}) == "mixed_search"


# ---------------------------------------------------------------------------
# ResearchStrategyExtractor — extract
# ---------------------------------------------------------------------------

def test_strategy_extractor_extract_creates_strategy():
    ext = ResearchStrategyExtractor()
    progress = _make_progress(
        topic="neural network training",
        sources_found={"arxiv": 15, "github": 3},
    )
    strategy = ext.extract(progress, quality_score=0.85)
    assert isinstance(strategy, ExtractedStrategy)
    assert strategy.topic == "neural network training"
    assert strategy.domain == "ml"
    assert strategy.outcome_score == 0.85
    assert len(strategy.strategy_steps) > 0
    assert "arxiv" in strategy.key_sources_used


def test_strategy_extractor_extract_success_lesson():
    ext = ResearchStrategyExtractor()
    progress = _make_progress(topic="transformer architecture", sources_found={"arxiv": 20})
    strategy = ext.extract(progress, quality_score=0.9)
    assert "Successful" in strategy.lessons_learned
    assert "90%" in strategy.lessons_learned


def test_strategy_extractor_extract_failure_lesson():
    ext = ResearchStrategyExtractor()
    progress = _make_progress(topic="obscure topic xyz", sources_found={"arxiv": 1})
    strategy = ext.extract(progress, quality_score=0.2)
    assert "Low quality" in strategy.lessons_learned
    assert "20%" in strategy.lessons_learned


def test_strategy_extractor_extract_moderate_lesson():
    ext = ResearchStrategyExtractor()
    progress = _make_progress(sources_found={"arxiv": 5, "github": 3})
    strategy = ext.extract(progress, quality_score=0.55)
    assert "Moderate" in strategy.lessons_learned


def test_strategy_extractor_extract_steps_include_papers():
    ext = ResearchStrategyExtractor()
    progress = _make_progress(papers_analyzed=8, repos_analyzed=0, gaps_found=0)
    strategy = ext.extract(progress, quality_score=0.7)
    assert any("paper" in s.lower() for s in strategy.strategy_steps)


def test_strategy_extractor_extract_steps_no_data():
    ext = ResearchStrategyExtractor()
    progress = _make_progress(papers_analyzed=0, repos_analyzed=0, gaps_found=0)
    strategy = ext.extract(progress, quality_score=0.5)
    assert len(strategy.strategy_steps) >= 1


def test_strategy_extractor_extract_and_save(tmp_path):
    ext = ResearchStrategyExtractor()
    store_path = tmp_path / "strategies.json"
    memory = ResearchStrategyMemory(store_path=store_path)
    progress = _make_progress(
        topic="machine learning optimization",
        sources_found={"arxiv": 10},
    )
    strategy = ext.extract_and_save(progress, quality_score=0.8, strategy_memory=memory)
    assert isinstance(strategy, ExtractedStrategy)
    saved = memory.get_best_for_domain("ml")
    assert len(saved) == 1
    assert saved[0].outcome_score == 0.8


# ---------------------------------------------------------------------------
# CaseSelectionPolicy
# ---------------------------------------------------------------------------

def test_case_selection_policy_empty_bank(tmp_path):
    bank = SessionCaseBank(store_path=tmp_path / "cases.json")
    policy = CaseSelectionPolicy(case_bank=bank)
    result = policy.select("attention mechanisms")
    assert result == []


def test_case_selection_policy_selects_related(tmp_path):
    bank = SessionCaseBank(store_path=tmp_path / "cases.json")
    case = ResearchCase(
        topic="attention mechanisms transformers",
        quality_score=0.9,
    )
    bank.save_case(case)
    policy = CaseSelectionPolicy(case_bank=bank)
    matches = policy.select("attention mechanisms")
    assert len(matches) >= 1
    assert isinstance(matches[0], CaseMatch)
    assert matches[0].similarity_score > 0


def test_case_selection_policy_ignores_unrelated(tmp_path):
    bank = SessionCaseBank(store_path=tmp_path / "cases.json")
    case = ResearchCase(topic="quantum computing entanglement", quality_score=0.9)
    bank.save_case(case)
    policy = CaseSelectionPolicy(case_bank=bank)
    matches = policy.select("deep learning neural network")
    assert matches == []


def test_case_selection_policy_top_k(tmp_path):
    bank = SessionCaseBank(store_path=tmp_path / "cases.json")
    for i in range(5):
        bank.save_case(ResearchCase(topic=f"neural network layer {i}", quality_score=0.8))
    policy = CaseSelectionPolicy(case_bank=bank)
    matches = policy.select("neural network training", top_k=2)
    assert len(matches) <= 2


def test_case_selection_policy_record_usefulness(tmp_path):
    bank = SessionCaseBank(store_path=tmp_path / "cases.json")
    case = ResearchCase(topic="machine learning model", quality_score=0.8)
    bank.save_case(case)
    policy = CaseSelectionPolicy(case_bank=bank)
    policy.record_usefulness(case.id, was_useful=True)
    score_after_useful = policy._usefulness_scores.get(case.id, 1.0)
    # Should be slightly below 1.0 (0.9 * 1.0 + 0.1 * 1.0 = 1.0)
    assert score_after_useful == pytest.approx(1.0, abs=1e-9)

    policy.record_usefulness(case.id, was_useful=False)
    score_after_not_useful = policy._usefulness_scores.get(case.id, 1.0)
    assert score_after_not_useful < 1.0


def test_case_selection_similarity_no_overlap():
    bank_mock = MagicMock()
    bank_mock.get_all.return_value = []
    policy = CaseSelectionPolicy(case_bank=bank_mock)
    case = ResearchCase(topic="quantum physics experiment")
    sim, terms = policy._compute_similarity("deep learning neural", case)
    assert sim == 0.0
    assert terms == []


def test_case_selection_similarity_full_overlap():
    bank_mock = MagicMock()
    bank_mock.get_all.return_value = []
    policy = CaseSelectionPolicy(case_bank=bank_mock)
    case = ResearchCase(topic="attention transformer model")
    sim, _ = policy._compute_similarity("attention transformer model", case)
    assert sim == pytest.approx(1.0, abs=1e-9)


def test_case_selection_stopwords_ignored(tmp_path):
    bank = SessionCaseBank(store_path=tmp_path / "cases.json")
    # Topic with only stopwords should not match
    case = ResearchCase(topic="the a an of in for on with to and", quality_score=0.9)
    bank.save_case(case)
    policy = CaseSelectionPolicy(case_bank=bank)
    # Query is only stopwords → topic_terms empty → 0.0 sim
    matches = policy.select("the a an of")
    assert matches == []


def test_case_selection_quality_score_influences_ranking(tmp_path):
    bank = SessionCaseBank(store_path=tmp_path / "cases.json")
    low = ResearchCase(topic="neural network training", quality_score=0.3)
    high = ResearchCase(topic="neural network training", quality_score=0.9)
    bank.save_case(low)
    bank.save_case(high)
    policy = CaseSelectionPolicy(case_bank=bank)
    matches = policy.select("neural network training", top_k=2)
    assert matches[0].similarity_score >= matches[1].similarity_score


# ---------------------------------------------------------------------------
# DomainExpertiseAccumulator
# ---------------------------------------------------------------------------

def test_domain_expertise_update(tmp_path):
    acc = DomainExpertiseAccumulator(store_path=tmp_path / "expertise.json")
    progress = _make_progress(sources_found={"arxiv": 10, "github": 3})
    model = acc.update("ml", progress, quality_score=0.8)
    assert model.domain == "ml"
    assert model.total_sessions == 1
    assert model.avg_quality == pytest.approx(0.8)
    assert "arxiv" in model.preferred_sources


def test_domain_expertise_update_rolling_average(tmp_path):
    acc = DomainExpertiseAccumulator(store_path=tmp_path / "expertise.json")
    progress = _make_progress(sources_found={"arxiv": 5})
    acc.update("ml", progress, quality_score=0.6)
    acc.update("ml", progress, quality_score=0.8)
    model = acc.get_model("ml")
    assert model.total_sessions == 2
    assert model.avg_quality == pytest.approx(0.7)


def test_domain_expertise_add_landmark(tmp_path):
    acc = DomainExpertiseAccumulator(store_path=tmp_path / "expertise.json")
    acc.add_landmark_paper("ml", "Attention Is All You Need")
    model = acc.get_model("ml")
    assert "Attention Is All You Need" in model.landmark_papers


def test_domain_expertise_landmark_cap(tmp_path):
    acc = DomainExpertiseAccumulator(store_path=tmp_path / "expertise.json")
    for i in range(55):
        acc.add_landmark_paper("ml", f"Paper {i}")
    model = acc.get_model("ml")
    assert len(model.landmark_papers) <= 50


def test_domain_expertise_add_venue(tmp_path):
    acc = DomainExpertiseAccumulator(store_path=tmp_path / "expertise.json")
    acc.add_key_venue("ml", "NeurIPS")
    model = acc.get_model("ml")
    assert "NeurIPS" in model.key_venues


def test_domain_expertise_add_venue_no_duplicates(tmp_path):
    acc = DomainExpertiseAccumulator(store_path=tmp_path / "expertise.json")
    acc.add_key_venue("ml", "NeurIPS")
    acc.add_key_venue("ml", "NeurIPS")
    model = acc.get_model("ml")
    assert model.key_venues.count("NeurIPS") == 1


def test_domain_expertise_persistence(tmp_path):
    store = tmp_path / "expertise.json"
    acc = DomainExpertiseAccumulator(store_path=store)
    progress = _make_progress(sources_found={"arxiv": 5})
    acc.update("nlp", progress, quality_score=0.75)
    acc.add_landmark_paper("nlp", "BERT")

    acc2 = DomainExpertiseAccumulator(store_path=store)
    model = acc2.get_model("nlp")
    assert model is not None
    assert model.total_sessions == 1
    assert "BERT" in model.landmark_papers


def test_domain_expertise_list_domains(tmp_path):
    acc = DomainExpertiseAccumulator(store_path=tmp_path / "expertise.json")
    progress = _make_progress(sources_found={})
    acc.update("ml", progress, 0.7)
    acc.update("nlp", progress, 0.8)
    domains = acc.list_domains()
    assert "ml" in domains
    assert "nlp" in domains


def test_domain_expertise_get_model_missing(tmp_path):
    acc = DomainExpertiseAccumulator(store_path=tmp_path / "expertise.json")
    assert acc.get_model("nonexistent") is None


def test_domain_model_to_from_dict():
    model = DomainModel(
        domain="ml",
        key_venues=["NeurIPS"],
        landmark_papers=["BERT"],
        total_sessions=5,
        avg_quality=0.75,
    )
    d = model.to_dict()
    restored = DomainModel.from_dict(d)
    assert restored.domain == "ml"
    assert restored.key_venues == ["NeurIPS"]
    assert restored.total_sessions == 5
    assert restored.avg_quality == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# ResearchWorkflowOptimizer
# ---------------------------------------------------------------------------

def _make_trend_tracker(tmp_path, scores, fidelity=1.0):
    tracker = QualityTrendTracker(store_path=tmp_path / "trends.json")
    for score in scores:
        m = _make_metrics(overall_score=score, citation_fidelity=fidelity)
        tracker.record(m)
    return tracker


def test_workflow_optimizer_improving_insight(tmp_path):
    tracker = _make_trend_tracker(tmp_path, [0.6, 0.7, 0.8])
    optimizer = ResearchWorkflowOptimizer()
    insights = optimizer.analyze(tracker, domain_models={})
    types = [i.insight_type for i in insights]
    assert "trend" in types


def test_workflow_optimizer_no_trend_insight_when_declining(tmp_path):
    tracker = _make_trend_tracker(tmp_path, [0.8, 0.7, 0.6])
    optimizer = ResearchWorkflowOptimizer()
    insights = optimizer.analyze(tracker, domain_models={})
    types = [i.insight_type for i in insights]
    assert "trend" not in types


def test_workflow_optimizer_fidelity_gap_insight(tmp_path):
    tracker = _make_trend_tracker(tmp_path, [0.7], fidelity=0.8)
    optimizer = ResearchWorkflowOptimizer()
    insights = optimizer.analyze(tracker, domain_models={})
    types = [i.insight_type for i in insights]
    assert "quality_gap" in types


def test_workflow_optimizer_no_fidelity_gap_when_perfect(tmp_path):
    tracker = _make_trend_tracker(tmp_path, [0.7], fidelity=1.0)
    optimizer = ResearchWorkflowOptimizer()
    insights = optimizer.analyze(tracker, domain_models={})
    types = [i.insight_type for i in insights]
    assert "quality_gap" not in types


def test_workflow_optimizer_best_domain_insight(tmp_path):
    tracker = _make_trend_tracker(tmp_path, [0.8])
    model = DomainModel(domain="ml", total_sessions=3, avg_quality=0.85)
    optimizer = ResearchWorkflowOptimizer()
    insights = optimizer.analyze(tracker, domain_models={"ml": model})
    types = [i.insight_type for i in insights]
    assert "best_domain" in types


def test_workflow_optimizer_no_best_domain_when_few_sessions(tmp_path):
    tracker = _make_trend_tracker(tmp_path, [0.8])
    model = DomainModel(domain="ml", total_sessions=1, avg_quality=0.9)
    optimizer = ResearchWorkflowOptimizer()
    insights = optimizer.analyze(tracker, domain_models={"ml": model})
    types = [i.insight_type for i in insights]
    assert "best_domain" not in types


def test_workflow_optimizer_recommend_depth_standard_unknown():
    optimizer = ResearchWorkflowOptimizer()
    result = optimizer.recommend_depth("unknown_domain", domain_models={})
    assert result == "standard"


def test_workflow_optimizer_recommend_depth_deep_low_quality():
    optimizer = ResearchWorkflowOptimizer()
    model = DomainModel(domain="ml", total_sessions=3, avg_quality=0.4)
    result = optimizer.recommend_depth("ml", domain_models={"ml": model})
    assert result == "deep"


def test_workflow_optimizer_recommend_depth_standard_high_quality():
    optimizer = ResearchWorkflowOptimizer()
    model = DomainModel(domain="ml", total_sessions=3, avg_quality=0.9)
    result = optimizer.recommend_depth("ml", domain_models={"ml": model})
    assert result == "standard"


def test_workflow_optimizer_recommend_depth_few_sessions():
    optimizer = ResearchWorkflowOptimizer()
    model = DomainModel(domain="ml", total_sessions=1, avg_quality=0.4)
    result = optimizer.recommend_depth("ml", domain_models={"ml": model})
    assert result == "standard"


# ---------------------------------------------------------------------------
# SelfImprovementGate
# ---------------------------------------------------------------------------

def test_improvement_gate_insufficient_sessions():
    gate = SelfImprovementGate()
    decision = gate.evaluate([0.7], [0.8])
    assert decision.approved is False
    assert "Insufficient test sessions" in decision.reason
    assert decision.before_score == 0.0


def test_improvement_gate_insufficient_improvement():
    gate = SelfImprovementGate()
    decision = gate.evaluate([0.7, 0.7], [0.72, 0.72])
    assert decision.approved is False
    assert "Insufficient improvement" in decision.reason
    assert decision.improvement == pytest.approx(0.02, abs=1e-9)


def test_improvement_gate_regression_detected():
    gate = SelfImprovementGate()
    # Avg before: 0.6, avg after: 0.725 (improvement=0.125 >= 0.05),
    # but min_after=0.5 < 0.6 - 0.1 = 0.5 → exactly at boundary, use 0.45
    decision = gate.evaluate([0.6, 0.6], [0.95, 0.45])
    assert decision.approved is False
    assert "Regression" in decision.reason


def test_improvement_gate_approves_good_improvement():
    gate = SelfImprovementGate()
    decision = gate.evaluate([0.6, 0.6], [0.7, 0.72])
    assert decision.approved is True
    assert "improved" in decision.reason
    assert decision.improvement > 0.05


def test_improvement_gate_approves_exact_threshold():
    gate = SelfImprovementGate()
    # improvement = 0.05 exactly — should approve
    decision = gate.evaluate([0.6, 0.6], [0.65, 0.65])
    assert decision.approved is True


def test_improvement_gate_rollback_if_needed_not_approved():
    gate = SelfImprovementGate()
    decision = GateDecision(
        approved=False, reason="test", before_score=0.6,
        after_score=0.62, improvement=0.02,
    )
    assert gate.rollback_if_needed(decision) is True


def test_improvement_gate_rollback_if_needed_approved():
    gate = SelfImprovementGate()
    decision = GateDecision(
        approved=True, reason="good", before_score=0.6,
        after_score=0.7, improvement=0.1,
    )
    assert gate.rollback_if_needed(decision) is False


def test_improvement_gate_scores_stored_in_decision():
    gate = SelfImprovementGate()
    decision = gate.evaluate([0.5, 0.6], [0.7, 0.8])
    assert decision.before_score == pytest.approx(0.55)
    assert decision.after_score == pytest.approx(0.75)
    assert decision.improvement == pytest.approx(0.2)


def test_improvement_gate_zero_sessions():
    gate = SelfImprovementGate()
    decision = gate.evaluate([], [0.8, 0.9])
    assert decision.approved is False
    assert "Insufficient test sessions: 0" in decision.reason


def test_improvement_gate_min_test_sessions_constant():
    gate = SelfImprovementGate()
    assert gate.MIN_TEST_SESSIONS == 2


def test_improvement_gate_improvement_threshold_constant():
    gate = SelfImprovementGate()
    assert gate.IMPROVEMENT_THRESHOLD == pytest.approx(0.05)
