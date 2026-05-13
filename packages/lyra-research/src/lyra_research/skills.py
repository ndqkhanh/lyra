"""
Research Skills Library.

Implements callable research skills with interface, verifier, and lineage
following the 7-tuple formalism from Doc 320.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from lyra_research.strategies import SearchStrategy


# ---------------------------------------------------------------------------
# ResearchSkill (7-tuple skill formalism)
# ---------------------------------------------------------------------------

@dataclass
class ResearchSkill:
    """A callable research skill with interface, verifier, and lineage.

    Models the 7-tuple from Doc 320: applicability, policy, termination,
    interface, edit_operator, verification, lineage.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""                  # e.g. "ml_paper_search"
    domain: str = ""                # e.g. "ml", "nlp", "systems", "general"
    description: str = ""          # When to use this skill

    # Policy: what the skill does
    preferred_sources: List[str] = field(default_factory=list)  # ["arxiv", "openreview", "semantic_scholar"]
    preferred_venues: List[str] = field(default_factory=list)   # ["NeurIPS", "ICLR", "ICML"]
    query_expansions: List[str] = field(default_factory=list)   # Extra terms to add
    max_results_per_source: int = 30
    recency_bias: float = 0.5       # 0.0=all-time, 1.0=very-recent-only

    # Termination: when is the search good enough
    min_papers: int = 5
    min_repos: int = 3

    # Verifier: what makes a result high quality
    min_quality_score: float = 0.5

    # Lineage
    version: int = 1
    parent_skill_id: Optional[str] = None
    performance_history: List[float] = field(default_factory=list)  # outcome scores
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def average_performance(self) -> float:
        """Average outcome score across uses."""
        return sum(self.performance_history) / len(self.performance_history) if self.performance_history else 0.0

    def record_performance(self, score: float) -> None:
        """Record an outcome score (clamped to 0.0-1.0)."""
        self.performance_history.append(max(0.0, min(1.0, score)))


def _skill_to_dict(skill: ResearchSkill) -> dict:
    d = asdict(skill)
    d["created_at"] = skill.created_at.isoformat()
    return d


def _dict_to_skill(d: dict) -> ResearchSkill:
    d = dict(d)
    d["created_at"] = datetime.fromisoformat(d["created_at"])
    return ResearchSkill(**d)


# ---------------------------------------------------------------------------
# ResearchSkillStore
# ---------------------------------------------------------------------------

class ResearchSkillStore:
    """Stores and retrieves ResearchSkills.

    Persistence: JSON at ~/.lyra/research_skills.json
    Pre-populated with built-in domain skills on first load.
    """

    BUILTIN_SKILLS = [
        ResearchSkill(
            name="ml_paper_search",
            domain="ml",
            description="Search for machine learning papers. Prefers ICLR/NeurIPS/ICML/COLM.",
            preferred_sources=["arxiv", "openreview", "semantic_scholar", "papers_with_code"],
            preferred_venues=["NeurIPS", "ICLR", "ICML", "COLM", "AAAI", "JMLR"],
            query_expansions=["deep learning", "neural network", "benchmark"],
            recency_bias=0.6,
            min_papers=10,
            min_repos=3,
        ),
        ResearchSkill(
            name="nlp_paper_search",
            domain="nlp",
            description="Search for NLP/LLM papers. Prefers ACL/EMNLP/NAACL/ICLR.",
            preferred_sources=["arxiv", "acl", "openreview", "semantic_scholar"],
            preferred_venues=["ACL", "EMNLP", "NAACL", "ICLR", "NeurIPS"],
            query_expansions=["language model", "NLP", "text", "transformer"],
            recency_bias=0.7,
            min_papers=10,
            min_repos=3,
        ),
        ResearchSkill(
            name="systems_paper_search",
            domain="systems",
            description="Search for systems/infrastructure papers. Prefers SOSP/OSDI/USENIX.",
            preferred_sources=["arxiv", "semantic_scholar", "github"],
            preferred_venues=["SOSP", "OSDI", "USENIX", "EuroSys", "NSDI"],
            query_expansions=["distributed system", "infrastructure", "performance"],
            recency_bias=0.4,
            min_papers=5,
            min_repos=5,
        ),
        ResearchSkill(
            name="general_research",
            domain="general",
            description="Fallback skill for any research topic.",
            preferred_sources=["arxiv", "semantic_scholar", "github", "huggingface"],
            preferred_venues=[],
            query_expansions=[],
            recency_bias=0.5,
            min_papers=5,
            min_repos=3,
        ),
    ]

    def __init__(self, store_path: Optional[Path] = None):
        self.store_path = store_path or Path.home() / ".lyra" / "research_skills.json"
        self._skills: Dict[str, ResearchSkill] = {}
        self._load()
        self._ensure_builtins()

    def get_for_domain(self, domain: str) -> Optional[ResearchSkill]:
        """Get the best skill for a domain (highest average_performance)."""
        candidates = [
            s for s in self._skills.values()
            if s.domain.lower() == domain.lower()
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda s: s.average_performance())

    def get_by_name(self, name: str) -> Optional[ResearchSkill]:
        """Get a skill by its name."""
        for skill in self._skills.values():
            if skill.name == name:
                return skill
        return None

    def list_all(self) -> List[ResearchSkill]:
        """List all stored skills."""
        return list(self._skills.values())

    def save_skill(self, skill: ResearchSkill) -> ResearchSkill:
        """Persist a skill to the store."""
        self._skills[skill.id] = skill
        self._save()
        return skill

    def record_performance(self, skill_name: str, score: float) -> None:
        """Record an outcome score for a named skill."""
        skill = self.get_by_name(skill_name)
        if not skill:
            return
        skill.record_performance(score)
        self._save()

    def _ensure_builtins(self) -> None:
        """Add built-in skills if not already present by name."""
        existing_names = {s.name for s in self._skills.values()}
        for builtin in self.BUILTIN_SKILLS:
            if builtin.name not in existing_names:
                self._skills[builtin.id] = builtin
        self._save()

    def _save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        data = {sid: _skill_to_dict(s) for sid, s in self._skills.items()}
        self.store_path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not self.store_path.exists():
            return
        try:
            data = json.loads(self.store_path.read_text())
            self._skills = {sid: _dict_to_skill(d) for sid, d in data.items()}
        except (json.JSONDecodeError, KeyError, TypeError):
            self._skills = {}


# ---------------------------------------------------------------------------
# QueryRefinementSkill
# ---------------------------------------------------------------------------

@dataclass
class RefinementSuggestion:
    """Suggested query refinement with reason and confidence."""
    original_query: str
    refined_query: str
    reason: str             # "too_broad", "too_narrow", "add_year", "add_domain"
    confidence: float       # 0.0-1.0


class QueryRefinementSkill:
    """Refines research queries based on initial result quality.

    Rule-based: detects overly broad/narrow queries and suggests improvements.
    """

    # Signals that a query is too broad
    BROAD_SIGNALS = ["AI", "machine learning", "deep learning", "neural network", "model"]

    # Domain-specific sharpening suffixes
    DOMAIN_SUFFIXES = {
        "ml": "2024 2025 benchmark evaluation",
        "nlp": "language model transformer 2024",
        "systems": "distributed scalable production",
        "general": "survey 2024 2025",
    }

    # Broad result count threshold
    BROAD_THRESHOLD = 200

    # Narrow result count threshold
    NARROW_THRESHOLD = 5

    def refine(self, query: str, result_count: int, domain: str = "general") -> RefinementSuggestion:
        """Suggest a refined query based on query text and result count."""
        if self.is_too_broad(query, result_count):
            suffix = self.DOMAIN_SUFFIXES.get(domain, self.DOMAIN_SUFFIXES["general"])
            refined = f"{query} {suffix}"
            return RefinementSuggestion(
                original_query=query,
                refined_query=refined,
                reason="too_broad",
                confidence=0.8,
            )

        if self.is_too_narrow(query, result_count):
            # Strip trailing words to broaden
            words = query.strip().split()
            refined = " ".join(words[:-1]) if len(words) > 1 else query
            return RefinementSuggestion(
                original_query=query,
                refined_query=refined,
                reason="too_narrow",
                confidence=0.7,
            )

        # Check if recency should be added
        query_lower = query.lower()
        has_year = any(str(y) in query for y in range(2018, 2027))
        if not has_year and domain in ("ml", "nlp"):
            refined = self.add_recency(query)
            return RefinementSuggestion(
                original_query=query,
                refined_query=refined,
                reason="add_year",
                confidence=0.6,
            )

        # Add domain suffix if query matches broad signals
        for signal in self.BROAD_SIGNALS:
            if signal.lower() in query_lower:
                suffix = self.DOMAIN_SUFFIXES.get(domain, self.DOMAIN_SUFFIXES["general"])
                refined = f"{query} {suffix}"
                return RefinementSuggestion(
                    original_query=query,
                    refined_query=refined,
                    reason="add_domain",
                    confidence=0.5,
                )

        return RefinementSuggestion(
            original_query=query,
            refined_query=query,
            reason="add_domain",
            confidence=0.3,
        )

    def is_too_broad(self, _query: str, result_count: int) -> bool:
        """True if result count exceeds broad threshold."""
        return result_count > self.BROAD_THRESHOLD

    def is_too_narrow(self, _query: str, result_count: int) -> bool:
        """True if result count is below narrow threshold."""
        return result_count < self.NARROW_THRESHOLD

    def add_recency(self, query: str) -> str:
        """Append current year range to query."""
        current_year = datetime.now(timezone.utc).year
        return f"{query} {current_year - 1} {current_year}"


# ---------------------------------------------------------------------------
# StrategyAdaptationSkill
# ---------------------------------------------------------------------------

class StrategyAdaptationSkill:
    """Selects and switches search strategies based on topic and source density.

    Reads from ResearchStrategyMemory for domain expertise.
    """

    # Strategy selection rules
    STRATEGY_RULES: Dict[str, SearchStrategy] = {
        "survey": SearchStrategy.BREADTH_FIRST,
        "overview": SearchStrategy.BREADTH_FIRST,
        "review": SearchStrategy.BREADTH_FIRST,
        "mechanism": SearchStrategy.DEPTH_FIRST,
        "how does": SearchStrategy.DEPTH_FIRST,
        "why": SearchStrategy.DEPTH_FIRST,
        "related": SearchStrategy.SNOWBALL,
        "related work": SearchStrategy.SNOWBALL,
        "building on": SearchStrategy.SNOWBALL,
        "systematic": SearchStrategy.SYSTEMATIC,
        "comprehensive": SearchStrategy.SYSTEMATIC,
    }

    # Thresholds for strategy switching
    SWITCH_HIGH_PAPERS = 50
    SWITCH_LOW_QUALITY = 0.4
    SWITCH_LOW_PAPERS = 5

    def select_strategy(self, topic: str, _domain: str = "general") -> SearchStrategy:
        """Select best strategy based on topic keywords (longest match wins)."""
        topic_lower = topic.lower()
        # Sort by keyword length descending so more specific phrases match first
        for keyword in sorted(self.STRATEGY_RULES, key=len, reverse=True):
            if keyword in topic_lower:
                return self.STRATEGY_RULES[keyword]
        return SearchStrategy.BREADTH_FIRST

    def should_switch(
        self,
        current_strategy: SearchStrategy,
        papers_found: int,
        repos_found: int,
        quality_scores: List[float],
    ) -> Optional[SearchStrategy]:
        """Decide if strategy should switch mid-research.

        Returns new strategy if switch needed, None to continue current.
        - BREADTH -> DEPTH if papers_found > 50 and avg quality < 0.4
        - DEPTH -> BREADTH if papers_found < 5 after 2 search iterations
        """
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

        if (
            current_strategy == SearchStrategy.BREADTH_FIRST
            and papers_found > self.SWITCH_HIGH_PAPERS
            and avg_quality < self.SWITCH_LOW_QUALITY
        ):
            return SearchStrategy.DEPTH_FIRST

        if (
            current_strategy == SearchStrategy.DEPTH_FIRST
            and papers_found < self.SWITCH_LOW_PAPERS
        ):
            return SearchStrategy.BREADTH_FIRST

        return None


# ---------------------------------------------------------------------------
# SkillEvolutionTracker
# ---------------------------------------------------------------------------

@dataclass
class SkillEvolutionRecord:
    """Record of a skill performance measurement."""
    skill_name: str
    session_topic: str
    outcome_score: float
    notes: str
    measured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def _record_to_dict(r: SkillEvolutionRecord) -> dict:
    return {
        "skill_name": r.skill_name,
        "session_topic": r.session_topic,
        "outcome_score": r.outcome_score,
        "notes": r.notes,
        "measured_at": r.measured_at.isoformat(),
    }


def _dict_to_record(d: dict) -> SkillEvolutionRecord:
    d = dict(d)
    d["measured_at"] = datetime.fromisoformat(d["measured_at"])
    return SkillEvolutionRecord(**d)


class SkillEvolutionTracker:
    """Tracks skill performance over time and proposes refinements.

    After N sessions, proposes skill refinement suggestions.
    """

    MIN_SESSIONS_FOR_PROPOSAL = 3  # Need at least 3 data points
    IMPROVEMENT_THRESHOLD = 0.1    # Must improve by 10% to accept

    def __init__(self, store_path: Optional[Path] = None):
        self.store_path = store_path or Path.home() / ".lyra" / "skill_evolution.json"
        self._records: List[SkillEvolutionRecord] = []
        self._load()

    def record(self, skill_name: str, topic: str, score: float, notes: str = "") -> None:
        """Record a skill performance measurement."""
        rec = SkillEvolutionRecord(
            skill_name=skill_name,
            session_topic=topic,
            outcome_score=max(0.0, min(1.0, score)),
            notes=notes,
        )
        self._records.append(rec)
        self._save()

    def get_trend(self, skill_name: str, last_n: int = 5) -> List[float]:
        """Get last N outcome scores for a skill (most recent last)."""
        skill_records = [
            r for r in self._records
            if r.skill_name == skill_name
        ]
        return [r.outcome_score for r in skill_records[-last_n:]]

    def propose_refinements(self, skill_name: str) -> List[str]:
        """Propose skill refinements based on performance history.

        Returns list of human-readable suggestions.
        """
        skill_records = [r for r in self._records if r.skill_name == skill_name]
        if len(skill_records) < self.MIN_SESSIONS_FOR_PROPOSAL:
            return []

        scores = [r.outcome_score for r in skill_records]
        avg_score = sum(scores) / len(scores)
        suggestions = []

        if avg_score < 0.5:
            suggestions.append("Add 'benchmark' to query_expansions (improves coverage)")
            suggestions.append("Increase max_results_per_source to 50 (more sources found)")

        if avg_score < 0.4:
            suggestions.append("Consider switching to a more specific domain skill")

        trend = self.get_trend(skill_name, last_n=3)
        if len(trend) >= 2 and trend[-1] < trend[0]:
            suggestions.append("Recent performance declining: review preferred_venues list")

        if not suggestions:
            suggestions.append("Performance is satisfactory; no changes needed")

        return suggestions

    def is_improving(self, skill_name: str, window: int = 3) -> bool:
        """True if last `window` scores trend upward."""
        trend = self.get_trend(skill_name, last_n=window)
        if len(trend) < 2:
            return False
        return trend[-1] > trend[0]

    def _save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        data = [_record_to_dict(r) for r in self._records]
        self.store_path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not self.store_path.exists():
            return
        try:
            data = json.loads(self.store_path.read_text())
            self._records = [_dict_to_record(d) for d in data]
        except (json.JSONDecodeError, KeyError, TypeError):
            self._records = []
