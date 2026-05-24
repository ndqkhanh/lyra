"""
Domain Router — Layer 1 of the omni-domain architecture.

Classifies tasks into domain categories, routes to appropriate expert cards,
detects multi-domain tasks, and computes cross-domain insights.

Architecture:
  Layer 1: Domain Router — classifies task domain
  Layer 2: Expert Card System — loads domain-specific identity + knowledge
  Layer 3: Generalist Foundation — shared reasoning across domains
  Layer 4: Specialist Execution — domain-specific tools + validation
  Layer 5: Memory & Knowledge Transfer — cross-domain learning
"""

from __future__ import annotations

import logging
import re
from typing import Any

from lyra_domain.experts import ExpertRegistry
from lyra_domain.models import (
    ComplexityLevel,
    CrossDomainMapping,
    DomainClassification,
    DomainType,
    ExpertCard,
    MultiDomainResult,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword-based domain classification heuristics
# ---------------------------------------------------------------------------

# Maps domain types to sets of trigger keywords for naive classification.
# In production, this would be replaced by an ML classifier.
_DOMAIN_KEYWORDS: dict[DomainType, set[str]] = {
    DomainType.CODING: {
        "code", "function", "algorithm", "debug", "compile", "api",
        "software", "program", "class", "method", "variable", "import",
        "refactor", "typescript", "python", "react", "backend", "frontend",
        "database", "sql", "query", "endpoint", "middleware", "deploy",
    },
    DomainType.FINANCE: {
        "stock", "bond", "portfolio", "trading", "investment", "market",
        "option", "future", "derivative", "dividend", "earnings", "valuation",
        "risk", "hedge", "arbitrage", "asset", "equity", "yield",
        "sharpe", "volatility", "p&l", "balance sheet", "cash flow",
    },
    DomainType.MEDICAL: {
        "diagnosis", "symptom", "treatment", "patient", "disease", "therapy",
        "clinical", "drug", "dosage", "surgery", "prognosis", "infection",
        "chronic", "acute", "prescription", "screening", "vaccine",
    },
    DomainType.LEGAL: {
        "contract", "statute", "regulation", "lawsuit", "compliance",
        "liability", "negligence", "tort", "damages", "plaintiff",
        "defendant", "jurisdiction", "precedent", "appeal", "litigation",
        "arbitration", "intellectual property", "copyright", "patent",
    },
    DomainType.SCIENTIFIC: {
        "hypothesis", "experiment", "study", "research", "publication",
        "peer review", "methodology", "statistical", "significant",
        "correlation", "causation", "variable", "control group", "trial",
        "p-value", "reproducibility", "literature review", "meta-analysis",
    },
    DomainType.EDUCATION: {
        "lesson", "curriculum", "teach", "learn", "student", "tutor",
        "assessment", "grade", "homework", "exercise", "understand",
        "explain", "practice", "quiz", "exam", "study plan", "pedagogy",
        "learning objective", "syllabus",
    },
    DomainType.ENGINEERING: {
        "design", "cad", "simulation", "stress", "strain", "load",
        "tolerance", "fmea", "optimization", "prototype", "manufacturing",
        "material", "structural", "thermal", "fluid", "mechanical",
        "electrical", "circuit", "specification", "safety factor",
    },
    DomainType.CREATIVE: {
        "design", "art", "music", "video", "write", "story", "poem",
        "illustration", "animation", "composition", "creativity",
        "narrative", "visual", "aesthetic", "mood", "color", "typography",
        "brand", "campaign", "concept", "storyboard",
    },
    DomainType.BUSINESS: {
        "strategy", "market", "competitive", "revenue", "growth", "profit",
        "acquisition", "merger", "business model", "valuation", "pitch",
        "investor", "startup", "scale", "pivot", "go-to-market",
        "customer segment", "value proposition", "kpi", "okr",
    },
}

# Domain-specific stop words that should not trigger false positives.
# These are words shared across domains that would dilute classification.
_COMMON_WORDS: set[str] = {"design", "study", "research", "analysis", "model", "system"}


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase tokens for keyword matching."""
    return re.findall(r"[a-zA-Z_][a-zA-Z0-9_\-']*", text.lower())


def _score_domain(task: str, domain: DomainType) -> float:
    """Compute a raw keyword-match score for a task against a domain.

    Returns a float in [0, 1] representing the fraction of domain keywords
    that appeared in the task text.
    """
    keywords = _DOMAIN_KEYWORDS[domain]
    tokens = _tokenize(task)
    token_set = set(tokens)

    if not keywords:
        return 0.0

    matches = sum(1 for kw in keywords if kw in task.lower() or kw in token_set)
    return matches / len(keywords)


# ---------------------------------------------------------------------------
# Cross-domain mapping definitions
# ---------------------------------------------------------------------------

_CROSS_DOMAIN_MAPPINGS: list[CrossDomainMapping] = [
    CrossDomainMapping(
        source_domain=DomainType.CODING,
        target_domain=DomainType.ENGINEERING,
        transferable_knowledge="Algorithmic thinking, system decomposition, "
                               "modular design, and testing methodology",
        adaptation_required="Translate programming abstractions to physical "
                            "constraints and engineering tolerances",
        confidence=0.8,
        analogies=("Type system -> Material properties",
                   "Function composition -> Process pipeline",
                   "Unit test -> FEA validation"),
    ),
    CrossDomainMapping(
        source_domain=DomainType.FINANCE,
        target_domain=DomainType.BUSINESS,
        transferable_knowledge="Risk assessment frameworks, portfolio "
                               "diversification, and return optimization",
        adaptation_required="Financial metrics adapted to strategic KPIs "
                            "and non-financial value drivers",
        confidence=0.75,
        analogies=("Portfolio optimization -> Resource allocation",
                   "Hedging -> Risk mitigation strategy"),
    ),
    CrossDomainMapping(
        source_domain=DomainType.MEDICAL,
        target_domain=DomainType.SCIENTIFIC,
        transferable_knowledge="Clinical trial methodology, evidence "
                               "hierarchy, and diagnostic reasoning",
        adaptation_required="Apply clinical evidence standards to "
                            "broader scientific hypothesis testing",
        confidence=0.7,
        analogies=("Differential diagnosis -> Hypothesis testing",
                   "Treatment protocol -> Experimental procedure"),
    ),
    CrossDomainMapping(
        source_domain=DomainType.LEGAL,
        target_domain=DomainType.BUSINESS,
        transferable_knowledge="Contract analysis, compliance frameworks, "
                               "and precedent-based reasoning",
        adaptation_required="Legal reasoning adapted to business risk "
                            "assessment and strategic planning",
        confidence=0.65,
        analogies=("Case precedent -> Business case study",
                   "Statutory compliance -> Regulatory compliance"),
    ),
    CrossDomainMapping(
        source_domain=DomainType.SCIENTIFIC,
        target_domain=DomainType.CODING,
        transferable_knowledge="Hypothesis formulation, controlled "
                               "experiments, and statistical validation",
        adaptation_required="Apply experimental methodology to A/B testing "
                            "and software performance benchmarking",
        confidence=0.7,
        analogies=("Null hypothesis -> Baseline metric",
                   "Control group -> A/B test control"),
    ),
    CrossDomainMapping(
        source_domain=DomainType.EDUCATION,
        target_domain=DomainType.CREATIVE,
        transferable_knowledge="Scaffolding techniques, engagement "
                               "strategies, and assessment methods",
        adaptation_required="Pedagogical scaffolding adapted to "
                            "creative skill development",
        confidence=0.55,
        analogies=("Learning objective -> Creative brief",
                   "Formative assessment -> Iterative critique"),
    ),
]


# ---------------------------------------------------------------------------
# Domain Router
# ---------------------------------------------------------------------------


class DomainRouter:
    """Routes tasks to domain-specialized experts.

    Layer 1 of the 5-layer omni-domain architecture. Uses keyword-based
    heuristics for initial classification (replaceable with ML model).
    """

    def __init__(self, registry: ExpertRegistry | None = None) -> None:
        self._registry = registry or ExpertRegistry()
        if registry is None:
            self._registry.load_defaults()
        self._threshold: float = 0.02  # minimum score to consider a domain relevant

    # ------------------------------------------------------------------
    # Core routing
    # ------------------------------------------------------------------

    def classify(self, task: str) -> DomainClassification:
        """Classify a task into the most likely domain.

        Returns a DomainClassification with the best-matching domain,
        confidence score, detected subdomain, complexity estimate,
        and matching keywords.
        """
        if not task or not task.strip():
            return DomainClassification(
                domain_type=DomainType.CODING,
                confidence=0.3,
                complexity=ComplexityLevel.SIMPLE,
                reasoning="Empty or whitespace-only task, defaulting to CODING",
            )

        scores: dict[DomainType, float] = {
            d: _score_domain(task, d) for d in DomainType
        }

        best_domain = max(scores, key=scores.get)
        best_score = scores[best_domain]
        second_score = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0.0

        # Normalize confidence: scale score to [0, 1], cap at 0.95
        raw_confidence = min(best_score * 5.0, 0.95)

        # Detect if task truly spans multiple domains (close scores)
        if second_score > 0 and best_score > 0 and (second_score / best_score) > 0.7:
            raw_confidence = min(raw_confidence, 0.7)

        matched_keywords = [
            kw for kw in _DOMAIN_KEYWORDS.get(best_domain, set())
            if kw in task.lower()
        ]

        subdomain = self._detect_subdomain(task, best_domain)
        complexity = self._estimate_complexity(task, best_score)

        return DomainClassification(
            domain_type=best_domain,
            confidence=raw_confidence,
            subdomain=subdomain,
            complexity=complexity,
            reasoning=(
                f"Classified as {best_domain.value} "
                f"(score={best_score:.3f}, keywords={len(matched_keywords)} matches)"
            ),
            keywords=tuple(matched_keywords[:10]),
        )

    def route_to_expert(self, classification: DomainClassification) -> ExpertCard | None:
        """Get the ExpertCard for a classified domain."""
        return self._registry.get_expert(classification.domain_type)

    # ------------------------------------------------------------------
    # Multi-domain detection
    # ------------------------------------------------------------------

    def detect_multi_domain(self, task: str) -> MultiDomainResult:
        """Detect if a task spans multiple domains and return ranked results."""
        if not task or not task.strip():
            single = self.classify(task)
            return MultiDomainResult(
                primary=single,
                secondary=(),
                requires_fusion=False,
                fusion_strategy="none",
            )

        scores: dict[DomainType, float] = {
            d: _score_domain(task, d) for d in DomainType
        }

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        ranked = [(d, s) for d, s in ranked if s >= self._threshold]

        if not ranked:
            single = self.classify(task)
            return MultiDomainResult(
                primary=single,
                secondary=(),
                requires_fusion=False,
                fusion_strategy="none",
            )

        primary_domain, primary_score = ranked[0]
        primary_class = DomainClassification(
            domain_type=primary_domain,
            confidence=min(primary_score * 5.0, 0.95),
            keywords=tuple(
                kw for kw in _DOMAIN_KEYWORDS.get(primary_domain, set())
                if kw in task.lower()
            )[:10],
        )

        secondary: list[DomainClassification] = []
        for domain, score in ranked[1:]:
            if score >= self._threshold * 3:
                secondary.append(DomainClassification(
                    domain_type=domain,
                    confidence=min(score * 5.0, 0.8),
                ))

        requires_fusion = len(secondary) > 0 and secondary[0].confidence > 0.3
        fusion_strategy = "parallel" if requires_fusion else "sequential"

        return MultiDomainResult(
            primary=primary_class,
            secondary=tuple(secondary),
            requires_fusion=requires_fusion,
            fusion_strategy=fusion_strategy,
        )

    # ------------------------------------------------------------------
    # Cross-domain insights
    # ------------------------------------------------------------------

    def get_cross_domain_insights(
        self,
        source: DomainType,
        target: DomainType,
    ) -> list[CrossDomainMapping]:
        """Find transferable knowledge between two domains."""
        if source == target:
            return []

        results: list[CrossDomainMapping] = []
        for mapping in _CROSS_DOMAIN_MAPPINGS:
            if mapping.source_domain == source and mapping.target_domain == target:
                results.append(mapping)
            elif mapping.source_domain == target and mapping.target_domain == source:
                # Reverse direction: lower confidence by default
                results.append(CrossDomainMapping(
                    source_domain=source,
                    target_domain=target,
                    transferable_knowledge=mapping.transferable_knowledge,
                    adaptation_required=mapping.adaptation_required,
                    confidence=mapping.confidence * 0.85,
                    analogies=mapping.analogies,
                ))
        return results

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    @property
    def registry(self) -> ExpertRegistry:
        return self._registry

    def set_classification_threshold(self, threshold: float) -> None:
        """Set the minimum keyword-match fraction to consider a domain relevant."""
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"threshold must be in [0, 1], got {threshold}")
        self._threshold = threshold

    def to_dict(self) -> dict[str, Any]:
        return {
            "threshold": self._threshold,
            "registry": self._registry.to_dict(),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_subdomain(task: str, domain: DomainType) -> str:
        """Extract a subdomain hint from the task text."""
        subdomain_patterns: dict[DomainType, list[tuple[str, str]]] = {
            DomainType.CODING: [
                (r"\bbackend\b", "backend"),
                (r"\bfrontend\b", "frontend"),
                (r"\bdatabase\b|sql", "data"),
                (r"\bapi\b|endpoint", "api"),
                (r"\bsecurity\b", "security"),
                (r"\bmobile\b|ios|android", "mobile"),
                (r"\bml\b|machine.?learning|deep.?learning", "ml/ai"),
            ],
            DomainType.FINANCE: [
                (r"\btrading\b", "trading"),
                (r"\bportfolio\b", "portfolio"),
                (r"\brisk\b", "risk management"),
                (r"\bvaluation\b", "valuation"),
                (r"\boption\b", "derivatives"),
            ],
            DomainType.MEDICAL: [
                (r"\bcardio\b|heart", "cardiology"),
                (r"\bneuro\b|brain", "neurology"),
                (r"\bonco\b|cancer|tumor", "oncology"),
                (r"\bderma\b|skin", "dermatology"),
            ],
            DomainType.LEGAL: [
                (r"\bcontract\b", "contract law"),
                (r"\bip\b|intellectual.?property|copyright|patent", "intellectual property"),
                (r"\bcompliance\b|regulat", "regulatory"),
                (r"\btax\b", "tax law"),
            ],
            DomainType.SCIENTIFIC: [
                (r"\bbio\b|biology|dna|gene", "biology"),
                (r"\bchem\b|chemistry|molecule", "chemistry"),
                (r"\bphys\b|physics|quantum", "physics"),
                (r"\bneurosci\b", "neuroscience"),
            ],
        }

        patterns = subdomain_patterns.get(domain, [])
        task_lower = task.lower()
        for pattern, label in patterns:
            if re.search(pattern, task_lower):
                return label
        return ""

    @staticmethod
    def _estimate_complexity(task: str, score: float) -> ComplexityLevel:
        """Estimate task complexity based on length, depth, and domain score."""
        word_count = len(task.split())
        has_nested = bool(re.search(r"(if|when|for each|assuming|provided that)", task.lower()))

        if word_count < 10:
            return ComplexityLevel.TRIVIAL if score < 0.1 else ComplexityLevel.SIMPLE
        if word_count < 30:
            return ComplexityLevel.SIMPLE if not has_nested else ComplexityLevel.MODERATE
        if word_count < 80:
            return ComplexityLevel.MODERATE if not has_nested else ComplexityLevel.COMPLEX
        if word_count < 200:
            return ComplexityLevel.COMPLEX
        return ComplexityLevel.VERY_COMPLEX
