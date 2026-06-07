"""
A-MAC: Adaptive Memory Admission Control.

Implements the 5-factor memory admission gate from the MemAgent Workshop
(A-MAC paper, arXiv 2603.04549). Content-type classification alone provides
63% of the admission gain — the single most powerful heuristic.

References
----------
- A-MAC: Adaptive Memory Admission Control for LLM Agents
  Workday Research, ICLR 2026 MemAgent Workshop, arXiv 2603.04549v1
- Cost-Sensitive Store Routing for Memory-Augmented Agents
  Gaikwad et al., ICLR 2026 MemAgent Workshop, arXiv 2603.15658v1
- CraniMem: Cranial Inspired Gated Bounded Memory
  ICLR 2026 MemAgent Workshop, arXiv 2603.15642v1
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ContentType(str, Enum):
    """Content type classification for memory admission.

    Type Prior is the single most powerful admission heuristic (63% of gain
    in A-MAC experiments on LoCoMo). Different content types have different
    baseline admission probabilities.
    """

    CODE = "code"
    FACT = "fact"
    CONVERSATION = "conversation"
    DECISION = "decision"
    PREFERENCE = "preference"
    PLAN = "plan"
    ERROR_LOG = "error_log"
    UNKNOWN = "unknown"


# Baseline admission probabilities per content type (from A-MAC §4.2)
_TYPE_PRIORS: dict[ContentType, float] = {
    ContentType.CODE: 0.35,           # Code ages fast; admit conservatively
    ContentType.FACT: 0.85,           # Facts are durable; admit liberally
    ContentType.CONVERSATION: 0.40,   # Conversations are transient
    ContentType.DECISION: 0.75,       # Decisions are important to remember
    ContentType.PREFERENCE: 0.80,     # User preferences are critical
    ContentType.PLAN: 0.60,           # Plans become stale but useful for context
    ContentType.ERROR_LOG: 0.70,      # Errors are learning opportunities
    ContentType.UNKNOWN: 0.50,        # Conservative default
}


@dataclass(frozen=True)
class AdmissionScore:
    """Result of the 5-factor admission scoring.

    Attributes:
        utility: Predicted future utility (0-1). How useful will this be later?
        confidence: Confidence in the fact/observation (0-1). Low confidence
            → less likely to admit (avoid polluting memory with uncertain facts).
        novelty: How novel is this relative to existing memories (0-1)?
            Duplicate information should not be re-admitted.
        recency: Time decay factor (0-1). Recent items score higher.
        type_prior: Baseline probability from content type classification (0-1).
        combined: Weighted combination of all five factors (0-1).
        admit: Whether the combined score exceeds the threshold.
    """

    utility: float
    confidence: float
    novelty: float
    recency: float
    type_prior: float
    combined: float
    admit: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "utility": round(self.utility, 4),
            "confidence": round(self.confidence, 4),
            "novelty": round(self.novelty, 4),
            "recency": round(self.recency, 4),
            "type_prior": round(self.type_prior, 4),
            "combined": round(self.combined, 4),
            "admit": self.admit,
        }


class AdmissionController:
    """5-factor memory admission gate.

    Weights from A-MAC §4.2 ablation study. Type Prior dominates (63% of
    total gain), followed by Future Utility (18%), then Confidence (10%),
    Novelty (6%), and Recency (3%).

    Usage::

        ctrl = AdmissionController(threshold=0.45)
        score = ctrl.evaluate(
            content="The user prefers dark mode",
            content_type=ContentType.PREFERENCE,
            confidence=0.95,
        )
        if score.admit:
            memory_store.add(memory)
    """

    # Default weights from A-MAC §4.2 (normalized to sum to 1.0)
    _DEFAULT_WEIGHTS: dict[str, float] = {
        "utility": 0.18,
        "confidence": 0.10,
        "novelty": 0.06,
        "recency": 0.03,
        "type_prior": 0.63,
    }

    def __init__(
        self,
        threshold: float = 0.45,
        weights: dict[str, float] | None = None,
    ) -> None:
        self._threshold = threshold
        self._weights = weights or dict(self._DEFAULT_WEIGHTS)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        content: str,
        content_type: ContentType = ContentType.UNKNOWN,
        confidence: float = 0.8,
        existing_memories: list[str] | None = None,
        age_seconds: float = 0.0,
    ) -> AdmissionScore:
        """Score a memory candidate for admission.

        Args:
            content: The memory content text.
            content_type: Classified content type.
            confidence: Estimated confidence in the fact/observation (0-1).
            existing_memories: Optional list of existing memory texts for novelty.
            age_seconds: Age of the memory in seconds (0 = just created).

        Returns:
            AdmissionScore with all factor scores and admit decision.
        """
        utility = self._estimate_utility(content, content_type)
        conf = self._clamp(confidence)
        novelty = self._estimate_novelty(content, existing_memories or [])
        recency = self._compute_recency(age_seconds)
        type_prior = _TYPE_PRIORS.get(content_type, 0.50)

        combined = (
            self._weights["utility"] * utility
            + self._weights["confidence"] * conf
            + self._weights["novelty"] * novelty
            + self._weights["recency"] * recency
            + self._weights["type_prior"] * type_prior
        )

        return AdmissionScore(
            utility=utility,
            confidence=conf,
            novelty=novelty,
            recency=recency,
            type_prior=type_prior,
            combined=combined,
            admit=combined >= self._threshold,
        )

    def classify_content_type(self, text: str) -> ContentType:
        """Heuristic content type classifier.

        Uses keyword matching for fast classification. For production, replace
        with a lightweight LLM call (Haiku-class, ~500 input tokens).

        Args:
            text: The content text to classify.

        Returns:
            Best-guess ContentType.
        """
        text_lower = text.lower()

        # Code patterns — require multiple indicators or strong signals
        code_strong = {"```", "def ", "class ", "import ", "const ", "let ", "var "}
        code_weak = {"=>", "async ", "await ", "function", "return "}
        strong_hits = sum(1 for ind in code_strong if ind in text_lower)
        weak_hits = sum(1 for ind in code_weak if ind in text_lower)
        if strong_hits >= 1 or weak_hits >= 2:
            return ContentType.CODE

        # Decision patterns
        decision_indicators = {
            "decided to", "chose to", "opted for", "selected",
            "approved", "rejected", "merged", "deployed",
        }
        if any(ind in text_lower for ind in decision_indicators):
            return ContentType.DECISION

        # Preference patterns
        preference_indicators = {
            "prefer", "like", "don't like", "favorite",
            "always use", "never use", "my setup",
        }
        if any(ind in text_lower for ind in preference_indicators):
            return ContentType.PREFERENCE

        # Plan patterns — check BEFORE error (TODO: fix error = plan, not error log)
        plan_indicators = {
            "plan to", "will implement", "next step", "todo:",
            "roadmap", "milestone", "sprint",
        }
        if any(ind in text_lower for ind in plan_indicators):
            return ContentType.PLAN

        # Error patterns
        error_indicators = {
            "error:", "exception:", "traceback",
            "failed with", "crash", "timeout",
        }
        if any(ind in text_lower for ind in error_indicators):
            return ContentType.ERROR_LOG

        # Conversation patterns (questions, acknowledgments) — check BEFORE fact
        if "?" in text or any(
            phrase in text_lower
            for phrase in ("thanks", "ok", "got it", "understood", "let me know")
        ):
            return ContentType.CONVERSATION

        # Fact patterns (declarative statements) — check LAST as catch-all
        if any(
            phrase in text_lower
            for phrase in ("is a", "was a", "it has", "there are")
        ):
            return ContentType.FACT

        return ContentType.UNKNOWN

    # ------------------------------------------------------------------
    # Factor estimators
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_utility(content: str, content_type: ContentType) -> float:
        """Heuristic future utility based on content type + length.

        Longer, structured content tends to be more useful. Decisions and
        preferences have higher baseline utility.
        """
        base = _TYPE_PRIORS.get(content_type, 0.50)
        # Length bonus: longer content often contains more signal
        length_bonus = min(math.log(len(content) + 1) / 10.0, 0.15)
        return AdmissionController._clamp(base + length_bonus)

    @staticmethod
    def _estimate_novelty(
        content: str, existing_memories: list[str]
    ) -> float:
        """Estimate novelty via simple lexical overlap.

        For production, replace with embedding cosine similarity against
        the top-K nearest existing memories.

        Args:
            content: Candidate memory text.
            existing_memories: Existing memory texts to compare against.

        Returns:
            Novelty score (1.0 = completely novel, 0.0 = duplicate).
        """
        if not existing_memories:
            return 1.0

        content_words = set(content.lower().split())
        if not content_words:
            return 1.0

        max_overlap = 0.0
        for existing in existing_memories[:50]:  # Check top 50 for performance
            existing_words = set(existing.lower().split())
            if not existing_words:
                continue
            overlap = len(content_words & existing_words) / len(content_words)
            max_overlap = max(max_overlap, overlap)

        return 1.0 - max_overlap

    @staticmethod
    def _compute_recency(age_seconds: float) -> float:
        """Ebbinghaus-style exponential decay.

        Half-life of ~24 hours for memory importance. Memories older than
        7 days approach zero recency score.

        Args:
            age_seconds: Age in seconds (0 = just created).

        Returns:
            Recency score (1.0 = brand new, →0 = very old).
        """
        if age_seconds <= 0:
            return 1.0
        half_life = 86400.0  # 24 hours in seconds
        return math.exp(-math.log(2) * age_seconds / half_life)

    @staticmethod
    def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, value))

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    @property
    def threshold(self) -> float:
        return self._threshold

    def set_threshold(self, value: float) -> None:
        """Dynamically adjust the admission threshold."""
        self._threshold = self._clamp(value)

    @property
    def weights(self) -> dict[str, float]:
        return dict(self._weights)
