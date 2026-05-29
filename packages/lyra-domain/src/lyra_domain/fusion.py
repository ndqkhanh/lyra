"""
Cross-Domain Fusion Engine (SAGE-inspired).

Enables knowledge transfer between domain experts by identifying analogies,
adapting concepts across domain boundaries, and computing fusion confidence
scores. This is Layer 5 of the omni-domain architecture.

Design principles:
  - Knowledge transfers preserve source-domain rigor
  - Analogies are flagged with confidence, never presented as exact matches
  - Fusion is opt-in: always verify adapted knowledge in the target domain
"""

from __future__ import annotations

import logging
from typing import Any

from lyra_domain.models import (
    DomainType,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Built-in cross-domain analogy catalog
# ---------------------------------------------------------------------------

# Structure: (source_domain, target_domain) -> list of (source_concept,
# target_concept, confidence, explanation)
_ANALOGY_DB: dict[tuple[DomainType, DomainType], list[tuple[str, str, float, str]]] = {
    (DomainType.CODING, DomainType.ENGINEERING): [
        ("modular design", "system architecture decomposition", 0.85,
         "Both decompose complex systems into manageable, composable units"),
        ("unit testing", "finite element analysis", 0.7,
         "Both verify individual components before system integration"),
        ("version control", "revision management", 0.8,
         "Both track changes, enable rollback, and manage concurrent work"),
        ("type safety", "safety factor", 0.6,
         "Both prevent runtime errors through compile-time (design-time) constraints"),
    ],
    (DomainType.ENGINEERING, DomainType.CODING): [
        ("safety factor", "type safety / defensive programming", 0.6,
         "Both provide design-time safety margins against failure"),
        ("tolerance stack-up", "error propagation", 0.75,
         "Individual tolerances compound just as floating-point errors do"),
    ],
    (DomainType.FINANCE, DomainType.BUSINESS): [
        ("diversification", "market segment diversification", 0.85,
         "Both reduce concentration risk across independent exposures"),
        ("risk-adjusted return", "risk-adjusted strategic value", 0.8,
         "Both evaluate returns relative to the risk taken"),
        ("portfolio rebalancing", "resource reallocation", 0.75,
         "Periodic adjustment to maintain target allocations"),
    ],
    (DomainType.MEDICAL, DomainType.SCIENTIFIC): [
        ("differential diagnosis", "hypothesis testing", 0.9,
         "Both systematically narrow possibilities through evidence collection"),
        ("clinical trial", "controlled experiment", 0.85,
         "Both use control groups, blinding, and statistical analysis"),
        ("evidence hierarchy", "scientific evidence pyramid", 0.8,
         "Both rank evidence quality from anecdote to meta-analysis"),
    ],
    (DomainType.LEGAL, DomainType.BUSINESS): [
        ("precedent", "case study analysis", 0.75,
         "Both learn from past examples to guide current decisions"),
        ("due diligence", "risk assessment", 0.8,
         "Both investigate thoroughly before committing resources"),
        ("jurisdiction", "market segment", 0.6,
         "Both define the scope of authority / applicability"),
    ],
    (DomainType.EDUCATION, DomainType.CREATIVE): [
        ("scaffolding", "creative constraints", 0.7,
         "Both provide structure that enables skill development"),
        ("formative assessment", "iterative critique", 0.8,
         "Both provide ongoing feedback for improvement"),
        ("learning objective", "creative brief", 0.75,
         "Both define clear goals and constraints for the process"),
    ],
    (DomainType.SCIENTIFIC, DomainType.CODING): [
        ("hypothesis", "specification", 0.7,
         "Both define expected behavior before implementation"),
        ("peer review", "code review", 0.8,
         "Both involve expert evaluation before acceptance"),
        ("reproducibility", "deterministic build", 0.75,
         "Both ensure consistent results from the same inputs"),
    ],
    (DomainType.FINANCE, DomainType.ENGINEERING): [
        ("option pricing", "real options valuation", 0.8,
         "Both value flexibility in decision-making under uncertainty"),
        ("risk parity", "load balancing", 0.7,
         "Both distribute exposure proportionally to capacity"),
    ],
    (DomainType.CREATIVE, DomainType.EDUCATION): [
        ("storytelling", "narrative learning", 0.8,
         "Both use narrative structure to engage and communicate"),
        ("visual design", "visual learning aids", 0.75,
         "Both use visual elements to convey information effectively"),
    ],
}

# Domain similarity matrix (symmetric, values in [0, 1])
# Higher values indicate more inherent similarity between domains.
_DOMAIN_SIMILARITY: dict[tuple[DomainType, DomainType], float] = {
    (DomainType.CODING, DomainType.ENGINEERING): 0.7,
    (DomainType.FINANCE, DomainType.BUSINESS): 0.75,
    (DomainType.MEDICAL, DomainType.SCIENTIFIC): 0.8,
    (DomainType.LEGAL, DomainType.BUSINESS): 0.6,
    (DomainType.SCIENTIFIC, DomainType.CODING): 0.5,
    (DomainType.EDUCATION, DomainType.CREATIVE): 0.55,
    (DomainType.FINANCE, DomainType.ENGINEERING): 0.4,
    (DomainType.EDUCATION, DomainType.SCIENTIFIC): 0.6,
    (DomainType.CREATIVE, DomainType.BUSINESS): 0.35,
    (DomainType.CODING, DomainType.SCIENTIFIC): 0.5,
    (DomainType.MEDICAL, DomainType.LEGAL): 0.3,  # bioethics
    (DomainType.LEGAL, DomainType.ENGINEERING): 0.45,  # standards & compliance
}

# Default similarity for unlisted pairs
_DEFAULT_SIMILARITY: float = 0.2


# ---------------------------------------------------------------------------
# Cross-Domain Fusion Engine
# ---------------------------------------------------------------------------


class CrossDomainFusion:
    """Cross-domain knowledge fusion engine (SAGE-inspired).

    Transfers knowledge between specialized domains by identifying relevant
    analogies, adapting concepts, and computing fusion reliability.
    """

    def __init__(self) -> None:
        self._analogy_db: dict[tuple[DomainType, DomainType], list[tuple[str, str, float, str]]]
        self._analogy_db = dict(_ANALOGY_DB)
        self._similarity: dict[tuple[DomainType, DomainType], float] = dict(_DOMAIN_SIMILARITY)
        logger.info("CrossDomainFusion initialized with %d analogy pairs and %d similarity entries",
                     sum(len(v) for v in _ANALOGY_DB.values()),
                     len(_DOMAIN_SIMILARITY))

    # ------------------------------------------------------------------
    # Core fusion operations
    # ------------------------------------------------------------------

    def fuse_expertise(
        self,
        source_domain: DomainType,
        target_domain: DomainType,
        task: str,
    ) -> dict[str, Any]:
        """Generate an augmented approach by fusing expertise from source into target domain.

        Returns a structured fusion result with adapted concepts,
        analogies, confidence score, and recommended strategy.
        """
        if source_domain == target_domain:
            return {
                "source_domain": source_domain.value,
                "target_domain": target_domain.value,
                "fusion_confidence": 1.0,
                "analogies": [],
                "adapted_approaches": [],
                "strategy": "same_domain_no_fusion_needed",
                "note": "Source and target domains are identical; no fusion required",
            }

        analogies = self.identify_analogies(source_domain, target_domain)

        # Build adapted approaches from analogies
        adapted: list[dict[str, Any]] = []
        for source_concept, target_concept, confidence, explanation in analogies:
            adapted.append({
                "source_concept": source_concept,
                "adapted_concept": target_concept,
                "confidence": confidence,
                "explanation": explanation,
                "task_relevance": self._compute_task_relevance(task, source_concept,
                                                                target_concept),
            })

        fusion_confidence = self.compute_fusion_confidence(source_domain, target_domain)

        return {
            "source_domain": source_domain.value,
            "target_domain": target_domain.value,
            "fusion_confidence": fusion_confidence,
            "analogies": [a[1] for a in analogies],
            "adapted_approaches": adapted,
            "strategy": self._recommend_strategy(fusion_confidence),
        }

    def transfer_knowledge(
        self,
        source: DomainType,
        target: DomainType,
        concept: str,
    ) -> dict[str, Any]:
        """Adapt a concept from source domain to be applicable in target domain.

        Returns the adapted concept, adaptation steps, and confidence.
        """
        if source == target:
            return {
                "original_concept": concept,
                "adapted_concept": concept,
                "adaptation_steps": [],
                "preservation_level": 1.0,
                "confidence": 1.0,
            }

        # Find relevant analogies for this concept
        analogies = self.identify_analogies(source, target)

        relevant = [a for a in analogies if concept.lower() in a[0].lower()
                    or a[1].lower() in concept.lower()]

        if relevant:
            best = relevant[0]
            return {
                "original_concept": concept,
                "adapted_concept": best[1],
                "adaptation_steps": [
                    f"Map {concept} to {best[1]} based on domain analogy",
                    f"Apply {best[3]}",
                ],
                "preservation_level": best[2],
                "confidence": best[2],
            }

        # Generic adaptation fallback
        similarity = self._get_similarity(source, target)
        return {
            "original_concept": concept,
            "adapted_concept": concept,
            "adaptation_steps": [
                f"Review concept in context of {target.value} domain standards",
                "Verify applicability through domain-specific validation",
            ],
            "preservation_level": similarity,
            "confidence": similarity * 0.7,
        }

    def identify_analogies(
        self,
        domain_a: DomainType,
        domain_b: DomainType,
    ) -> list[tuple[str, str, float, str]]:
        """Identify cross-domain analogies between two domains.

        Returns list of (source_concept, target_concept, confidence, explanation).
        """
        direct = self._analogy_db.get((domain_a, domain_b), [])
        reverse = self._analogy_db.get((domain_b, domain_a), [])

        # For reverse entries, swap source/target
        swapped: list[tuple[str, str, float, str]] = [
            (target, source, conf, f"Reverse: {expl}")
            for source, target, conf, expl in reverse
        ]

        all_analogies = direct + swapped
        # Sort by confidence descending
        all_analogies.sort(key=lambda x: x[2], reverse=True)
        return all_analogies

    def compute_fusion_confidence(self, a: DomainType, b: DomainType) -> float:
        """Compute reliability of cross-domain knowledge transfer.

        Uses the domain similarity matrix, analogy density, and a diminishing
        returns factor for distant domains.
        """
        if a == b:
            return 1.0

        similarity = self._get_similarity(a, b)

        # Analogy richness bonus
        analogies = self.identify_analogies(a, b)
        analogy_count = len(analogies)
        avg_analogy_confidence = (
            sum(a[2] for a in analogies) / analogy_count if analogy_count > 0 else 0.0
        )

        analogy_factor = min(analogy_count / 5.0, 1.0)  # max 5 analogies saturate
        weighted = (similarity * 0.6) + (avg_analogy_confidence * analogy_factor * 0.4)

        # Distant domain penalty
        if similarity < 0.3:
            weighted *= 0.8

        return round(min(weighted, 0.95), 4)

    # ------------------------------------------------------------------
    # Customization
    # ------------------------------------------------------------------

    def add_analogy(
        self,
        source: DomainType,
        target: DomainType,
        source_concept: str,
        target_concept: str,
        confidence: float,
        explanation: str = "",
    ) -> None:
        """Register a new cross-domain analogy."""
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {confidence}")
        key = (source, target)
        if key not in self._analogy_db:
            self._analogy_db[key] = []
        self._analogy_db[key].append((source_concept, target_concept, confidence, explanation))
        logger.info("Added analogy: %s -> %s (confidence=%.2f)",
                     source_concept, target_concept, confidence)

    def set_similarity(self, a: DomainType, b: DomainType, value: float) -> None:
        """Set or update the similarity between two domains."""
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"similarity must be in [0, 1], got {value}")
        self._similarity[(a, b)] = value
        self._similarity[(b, a)] = value

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_similarity(self, a: DomainType, b: DomainType) -> float:
        """Get the domain similarity, with symmetry and default fallback."""
        if (a, b) in self._similarity:
            return self._similarity[(a, b)]
        if (b, a) in self._similarity:
            return self._similarity[(b, a)]
        return _DEFAULT_SIMILARITY

    @staticmethod
    def _compute_task_relevance(task: str, source_concept: str, target_concept: str) -> float:
        """Estimate how relevant a fused concept is to the given task."""
        task_lower = task.lower()
        relevance = 0.0
        for word in source_concept.lower().split():
            if word in task_lower:
                relevance += 0.2
        for word in target_concept.lower().split():
            if word in task_lower:
                relevance += 0.15
        return min(relevance, 1.0)

    @staticmethod
    def _recommend_strategy(confidence: float) -> str:
        """Recommend a fusion strategy based on confidence."""
        if confidence >= 0.8:
            return "direct_transfer"
        if confidence >= 0.6:
            return "guided_adaptation"
        if confidence >= 0.4:
            return "supervised_fusion"
        return "independent_validation"
