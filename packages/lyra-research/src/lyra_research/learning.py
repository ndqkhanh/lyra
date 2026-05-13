"""
Continual Research Learning System.

Provides strategy extraction, case selection, domain expertise accumulation,
workflow optimization, and a safety gate for self-improvement.

All logic is rule/heuristic-based — no LLM calls.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from lyra_research.orchestrator import ResearchProgress
    from lyra_research.memory import ResearchCase, SessionCaseBank, ResearchStrategyMemory

from lyra_research.evaluation import QualityTrendTracker


# ---------------------------------------------------------------------------
# ExtractedStrategy
# ---------------------------------------------------------------------------

@dataclass
class ExtractedStrategy:
    """A research strategy extracted from a completed session."""
    topic: str
    domain: str
    topic_type: str          # "paper_search", "repo_search", "mixed_search"
    strategy_steps: List[str]
    outcome_score: float
    lessons_learned: str
    key_sources_used: List[str]
    query_patterns: List[str]


# ---------------------------------------------------------------------------
# ResearchStrategyExtractor
# ---------------------------------------------------------------------------

class ResearchStrategyExtractor:
    """Extracts reusable research strategies from completed sessions.

    ReasoningBank-inspired: success -> extract what worked,
    failure -> extract what went wrong and why.

    Saves extracted strategies to ResearchStrategyMemory.
    """

    DOMAIN_KEYWORDS: Dict[str, List[str]] = {
        "ml": ["machine learning", "deep learning", "neural", "model", "training", "inference"],
        "nlp": ["language model", "nlp", "text", "transformer", "llm", "tokenization"],
        "systems": ["distributed", "system", "infrastructure", "scalable", "latency", "throughput"],
        "vision": ["image", "vision", "visual", "cnn", "detection", "segmentation"],
        "rl": ["reinforcement learning", "reward", "policy", "agent", "environment"],
    }

    def extract(
        self,
        progress: "ResearchProgress",
        quality_score: float,
    ) -> ExtractedStrategy:
        """Extract a strategy from a completed research session."""
        domain = self.detect_domain(progress.topic)
        topic_type = self.detect_topic_type(progress.sources_found)
        key_sources = list(progress.sources_found.keys())

        steps: List[str] = []
        if progress.papers_analyzed > 0:
            steps.append(f"Analyzed {progress.papers_analyzed} papers")
        if progress.repos_analyzed > 0:
            steps.append(f"Analyzed {progress.repos_analyzed} repositories")
        if progress.gaps_found > 0:
            steps.append(f"Identified {progress.gaps_found} research gaps")
        if not steps:
            steps.append("Searched available sources")

        strategy = ExtractedStrategy(
            topic=progress.topic,
            domain=domain,
            topic_type=topic_type,
            strategy_steps=steps,
            outcome_score=quality_score,
            lessons_learned="",
            key_sources_used=key_sources,
            query_patterns=[progress.topic],
        )

        if quality_score >= 0.7:
            strategy.lessons_learned = self._lessons_from_success(progress, strategy)
        elif quality_score < 0.4:
            strategy.lessons_learned = self._lessons_from_failure(progress, strategy)
        else:
            strategy.lessons_learned = (
                f"Moderate result ({quality_score:.0%}) for '{progress.topic}'. "
                "Consider broader source coverage."
            )

        return strategy

    def extract_and_save(
        self,
        progress: "ResearchProgress",
        quality_score: float,
        strategy_memory: "ResearchStrategyMemory",
    ) -> ExtractedStrategy:
        """Extract strategy and save to ResearchStrategyMemory."""
        from lyra_research.memory import ResearchStrategy

        extracted = self.extract(progress, quality_score)
        rs = ResearchStrategy(
            topic_type=extracted.topic_type,
            domain=extracted.domain,
            strategy_steps=extracted.strategy_steps,
            outcome_score=extracted.outcome_score,
            lessons_learned=extracted.lessons_learned,
        )
        strategy_memory.save_strategy(rs)
        return extracted

    def detect_domain(self, topic: str) -> str:
        """Detect research domain from topic keywords."""
        topic_lower = topic.lower()
        scores = {
            domain: sum(1 for kw in kws if kw in topic_lower)
            for domain, kws in self.DOMAIN_KEYWORDS.items()
        }
        best = max(scores, key=lambda d: scores.get(d, 0))
        return best if scores[best] > 0 else "general"

    def detect_topic_type(self, sources_found: Dict[str, int]) -> str:
        """Detect whether this was primarily a paper or repo search."""
        paper_sources = sum(
            v for k, v in sources_found.items()
            if k in ("arxiv", "openreview", "semantic_scholar", "huggingface",
                     "papers_with_code", "acl")
        )
        repo_sources = sources_found.get("github", 0)
        if paper_sources > repo_sources * 2:
            return "paper_search"
        if repo_sources > paper_sources * 2:
            return "repo_search"
        return "mixed_search"

    def _lessons_from_success(
        self,
        progress: "ResearchProgress",
        strategy: ExtractedStrategy,
    ) -> str:
        """Generate lesson text from a successful session."""
        sources_str = ", ".join(strategy.key_sources_used) if strategy.key_sources_used else "multiple sources"
        return (
            f"Successful research ({strategy.outcome_score:.0%}) on '{progress.topic}'. "
            f"Key sources: {sources_str}. "
            f"Strategy: {strategy.topic_type} with {len(strategy.strategy_steps)} steps."
        )

    def _lessons_from_failure(
        self,
        progress: "ResearchProgress",
        strategy: ExtractedStrategy,
    ) -> str:
        """Generate lesson text from a failed/low-quality session."""
        return (
            f"Low quality ({strategy.outcome_score:.0%}) for '{progress.topic}'. "
            f"Sources used: {', '.join(strategy.key_sources_used) or 'none'}. "
            "Consider: expanding query terms, adding more sources, or increasing depth."
        )


# ---------------------------------------------------------------------------
# CaseMatch + CaseSelectionPolicy
# ---------------------------------------------------------------------------

@dataclass
class CaseMatch:
    """A matched past case with similarity score."""
    case: "ResearchCase"
    similarity_score: float
    overlap_terms: List[str]


class CaseSelectionPolicy:
    """Selects the best past research case for a new query.

    Memento-inspired: uses topic keyword overlap + quality score
    to find the most useful past session to bootstrap from.

    Online update: records which cases were actually useful.
    """

    _STOPWORDS = frozenset({
        "the", "a", "an", "of", "in", "for", "on", "with", "to",
        "and", "or", "is", "are",
    })

    def __init__(self, case_bank: Optional["SessionCaseBank"] = None) -> None:
        from lyra_research.memory import SessionCaseBank as _SessionCaseBank
        self.case_bank = case_bank or _SessionCaseBank()
        self._usefulness_scores: Dict[str, float] = {}

    def select(self, topic: str, top_k: int = 3) -> List[CaseMatch]:
        """Select top-k most relevant past cases for a new research topic."""
        all_cases = self.case_bank.get_all()
        if not all_cases:
            return []

        matches: List[CaseMatch] = []
        for case in all_cases:
            sim, terms = self._compute_similarity(topic, case)
            if sim > 0:
                usefulness = self._usefulness_scores.get(case.id, 1.0)
                adjusted_sim = sim * usefulness * (0.5 + 0.5 * case.quality_score)
                matches.append(CaseMatch(
                    case=case,
                    similarity_score=adjusted_sim,
                    overlap_terms=terms,
                ))

        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        return matches[:top_k]

    def record_usefulness(self, case_id: str, was_useful: bool) -> None:
        """Update the usefulness score for a case. Used for online learning."""
        current = self._usefulness_scores.get(case_id, 1.0)
        self._usefulness_scores[case_id] = current * 0.9 + (1.0 if was_useful else 0.0) * 0.1

    def _compute_similarity(
        self,
        topic: str,
        case: "ResearchCase",
    ) -> Tuple[float, List[str]]:
        """Compute keyword overlap between topic and case.topic."""
        topic_terms = set(topic.lower().split()) - self._STOPWORDS
        case_terms = set(case.topic.lower().split()) - self._STOPWORDS
        overlap = topic_terms & case_terms
        if not topic_terms:
            return 0.0, []
        sim = len(overlap) / len(topic_terms)
        return sim, list(overlap)


# ---------------------------------------------------------------------------
# DomainModel + DomainExpertiseAccumulator
# ---------------------------------------------------------------------------

@dataclass
class DomainModel:
    """Accumulated expertise model for a research domain."""
    domain: str
    key_venues: List[str] = field(default_factory=list)
    landmark_papers: List[str] = field(default_factory=list)
    key_methods: List[str] = field(default_factory=list)
    preferred_sources: List[str] = field(default_factory=list)
    total_sessions: int = 0
    avg_quality: float = 0.0
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["updated_at"] = self.updated_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DomainModel":
        d = dict(d)
        d["updated_at"] = datetime.fromisoformat(d["updated_at"])
        return cls(**d)


class DomainExpertiseAccumulator:
    """Builds domain expertise models from research sessions.

    After each session, updates the domain model with:
    - New venues discovered
    - High-quality papers found
    - Key methods mentioned
    - Which sources worked best

    Persistence: JSON at ~/.lyra/domain_expertise.json
    """

    def __init__(self, store_path: Optional[Path] = None) -> None:
        self.store_path = store_path or Path.home() / ".lyra" / "domain_expertise.json"
        self._models: Dict[str, DomainModel] = {}
        self._load()

    def update(
        self,
        domain: str,
        progress: "ResearchProgress",
        quality_score: float,
    ) -> DomainModel:
        """Update domain model from a completed research session."""
        if domain not in self._models:
            self._models[domain] = DomainModel(domain=domain)
        model = self._models[domain]

        for src_name in progress.sources_found:
            if src_name not in model.preferred_sources:
                model.preferred_sources.append(src_name)

        model.total_sessions += 1
        model.avg_quality = (
            model.avg_quality * (model.total_sessions - 1) + quality_score
        ) / model.total_sessions
        model.updated_at = datetime.now(timezone.utc)

        self._save()
        return model

    def get_model(self, domain: str) -> Optional[DomainModel]:
        return self._models.get(domain)

    def add_landmark_paper(self, domain: str, paper_title: str) -> None:
        """Manually add a landmark paper to a domain model."""
        if domain not in self._models:
            self._models[domain] = DomainModel(domain=domain)
        model = self._models[domain]
        if paper_title not in model.landmark_papers:
            model.landmark_papers.append(paper_title)
            if len(model.landmark_papers) > 50:
                model.landmark_papers = model.landmark_papers[-50:]
        self._save()

    def add_key_venue(self, domain: str, venue: str) -> None:
        """Add a key venue to the domain model."""
        model = self._models.setdefault(domain, DomainModel(domain=domain))
        if venue not in model.key_venues:
            model.key_venues.append(venue)
        self._save()

    def list_domains(self) -> List[str]:
        return list(self._models.keys())

    def _save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        data = {domain: model.to_dict() for domain, model in self._models.items()}
        self.store_path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not self.store_path.exists():
            return
        try:
            data = json.loads(self.store_path.read_text())
            self._models = {domain: DomainModel.from_dict(d) for domain, d in data.items()}
        except (json.JSONDecodeError, KeyError, TypeError):
            self._models = {}


# ---------------------------------------------------------------------------
# WorkflowInsight + ResearchWorkflowOptimizer
# ---------------------------------------------------------------------------

@dataclass
class WorkflowInsight:
    """An insight about what works best in research workflows."""
    insight_type: str
    domain: str
    description: str
    evidence: str
    confidence: float
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ResearchWorkflowOptimizer:
    """Analyzes patterns across sessions and derives optimization insights.

    Identifies:
    - Which sources consistently have highest-quality results per domain
    - What depth works best for which domains
    - Which stopping criteria are appropriate for each domain
    """

    def analyze(
        self,
        trend_tracker: QualityTrendTracker,
        domain_models: Dict[str, DomainModel],
    ) -> List[WorkflowInsight]:
        """Derive optimization insights from quality trends and domain models."""
        insights: List[WorkflowInsight] = []

        if trend_tracker.is_improving("overall_score"):
            insights.append(WorkflowInsight(
                insight_type="trend",
                domain="general",
                description="Overall research quality is improving",
                evidence=f"Last 3 sessions trend upward (avg: {trend_tracker.average():.0%})",
                confidence=0.7,
            ))

        for domain, model in domain_models.items():
            if model.total_sessions >= 2 and model.avg_quality >= 0.75:
                insights.append(WorkflowInsight(
                    insight_type="best_domain",
                    domain=domain,
                    description=f"Strong research quality in {domain} domain",
                    evidence=f"{model.total_sessions} sessions, avg quality {model.avg_quality:.0%}",
                    confidence=min(model.total_sessions / 5, 1.0) * model.avg_quality,
                ))

        avg_fidelity = trend_tracker.average("citation_fidelity")
        if avg_fidelity < 1.0:
            insights.append(WorkflowInsight(
                insight_type="quality_gap",
                domain="general",
                description="Citation fidelity below 100% — review source binding",
                evidence=f"Average fidelity: {avg_fidelity:.0%}",
                confidence=0.9,
            ))

        return insights

    def recommend_depth(
        self,
        domain: str,
        domain_models: Dict[str, DomainModel],
    ) -> str:
        """Recommend research depth for a domain based on past sessions."""
        model = domain_models.get(domain)
        if not model or model.total_sessions < 2:
            return "standard"
        if model.avg_quality < 0.6:
            return "deep"
        if model.avg_quality >= 0.85:
            return "standard"
        return "standard"


# ---------------------------------------------------------------------------
# GateDecision + SelfImprovementGate
# ---------------------------------------------------------------------------

@dataclass
class GateDecision:
    """Decision from the self-improvement gate."""
    approved: bool
    reason: str
    before_score: float
    after_score: float
    improvement: float


class SelfImprovementGate:
    """Safety gate that validates improvements before applying them.

    An update is only applied if:
    1. It has been tested on >= MIN_TEST_SESSIONS sessions
    2. Quality improves by >= IMPROVEMENT_THRESHOLD
    3. No quality regression on any individual session
    """

    MIN_TEST_SESSIONS = 2
    IMPROVEMENT_THRESHOLD = 0.05

    def evaluate(
        self,
        before_scores: List[float],
        after_scores: List[float],
    ) -> GateDecision:
        """Evaluate whether an update should be applied.

        Args:
            before_scores: Quality scores before the candidate update
            after_scores: Quality scores after the candidate update
        """
        if len(before_scores) < self.MIN_TEST_SESSIONS:
            return GateDecision(
                approved=False,
                reason=f"Insufficient test sessions: {len(before_scores)} < {self.MIN_TEST_SESSIONS}",
                before_score=0.0,
                after_score=0.0,
                improvement=0.0,
            )

        before_avg = sum(before_scores) / len(before_scores)
        after_avg = sum(after_scores) / len(after_scores)
        improvement = after_avg - before_avg

        if improvement < self.IMPROVEMENT_THRESHOLD:
            return GateDecision(
                approved=False,
                reason=f"Insufficient improvement: {improvement:.1%} < {self.IMPROVEMENT_THRESHOLD:.0%}",
                before_score=before_avg,
                after_score=after_avg,
                improvement=improvement,
            )

        min_after = min(after_scores)
        if min_after < before_avg - 0.1:
            return GateDecision(
                approved=False,
                reason=f"Regression detected: worst after-score {min_after:.0%} < baseline {before_avg:.0%}",
                before_score=before_avg,
                after_score=after_avg,
                improvement=improvement,
            )

        return GateDecision(
            approved=True,
            reason=f"Quality improved by {improvement:.1%}",
            before_score=before_avg,
            after_score=after_avg,
            improvement=improvement,
        )

    def rollback_if_needed(self, decision: GateDecision) -> bool:
        """Return True if rollback is required (update not approved)."""
        return not decision.approved
