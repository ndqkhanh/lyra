"""Thinking/Non-Thinking Mode Switch — Qwen3-inspired compute allocation.

Dynamically toggles between thinking and non-thinking modes based on task
complexity. Allocates reasoning budget proportional to task difficulty so
that simple queries get fast responses while hard problems get full chain-of-
thought treatment. On easy tasks the reasoning tokens are saved; on hard
tasks they are spent.

Design
------
Heuristic complexity estimation (word count, domain keywords, structural
indicators) maps a task description to a 1-10 score. A decision table then
selects a mode and token budget. The gate function ``should_think`` provides
a fast yes/no check for the common case.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Enums                                                              #
# ------------------------------------------------------------------ #


class ThinkingMode(Enum):
    """Reasoning depth levels for agent inference.

    Levels progress from zero reasoning through to full extended chain-of-thought
    suitable for research-grade problems.
    """

    OFF = auto()
    """No reasoning tokens — direct answer suitable for trivial lookups."""

    FAST = auto()
    """Single pass of lightweight reasoning — adequate for simple generation."""

    DEEP = auto()
    """Full chain-of-thought with intermediate steps — standard for complex tasks."""

    EXTENDED = auto()
    """Maximum reasoning depth with self-critique and backtracking."""


class TaskCategory(Enum):
    """Taxonomy of task types recognised by the complexity estimator."""

    TRIVIAL = auto()
    LOOKUP = auto()
    GENERATION = auto()
    REFACTORING = auto()
    ARCHITECTURE = auto()
    RESEARCH = auto()


# ------------------------------------------------------------------ #
# Data containers (all immutable)                                     #
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class TaskComplexity:
    """Precise complexity measurement for a single task.

    Attributes
    ----------
    score : int
        Overall complexity on a 1-10 scale (1 = trivial, 10 = maximal).
    category : str
        Human-readable category label (e.g. ``"refactoring"``).
    factors : tuple[str, ...]
        Named factors that contributed to the score.
    estimated_tokens : int
        Rough upper-bound token budget derived from the score.
    """

    score: int
    category: str
    factors: tuple[str, ...]
    estimated_tokens: int


@dataclass(frozen=True)
class ModeDecision:
    """Result of the mode selection process.

    Attributes
    ----------
    mode : ThinkingMode
        The selected reasoning mode.
    budget_tokens : int
        Maximum tokens to allocate for reasoning.
    confidence : float
        Confidence in the decision (0.0 — 1.0).
    reasoning : str
        Short explanation of why this mode was chosen.
    """

    mode: ThinkingMode
    budget_tokens: int
    confidence: float
    reasoning: str


@dataclass(frozen=True)
class ComplexityEstimate:
    """Raw complexity estimate produced by the heuristic analyser.

    Attributes
    ----------
    task_description : str
        The original task text.
    complexity_score : int
        Heuristic score 1-10.
    factors : dict[str, float]
        Breakdown of individual factor contributions.
    """

    task_description: str
    complexity_score: int
    factors: dict[str, float]


# ------------------------------------------------------------------ #
# Default token budgets per mode                                      #
# ------------------------------------------------------------------ #

_MODE_BUDGETS: dict[ThinkingMode, tuple[int, int]] = {
    ThinkingMode.OFF: (0, 0),
    ThinkingMode.FAST: (256, 1024),
    ThinkingMode.DEEP: (2048, 8192),
    ThinkingMode.EXTENDED: (8192, 32000),
}
"""Maps each mode to (min_budget, max_budget) tuples."""

_CATEGORY_KEYWORDS: dict[str, set[str]] = {
    "trivial": {"typo", "greeting", "hello", "yes", "no", "thanks"},
    "lookup": {"find", "search", "lookup", "get", "fetch", "retrieve", "show me"},
    "generation": {"write", "create", "generate", "compose", "draft", "produce", "make"},
    "refactoring": {"refactor", "rename", "extract", "inline", "move", "restructure"},
    "architecture": {"design", "architecture", "plan", "system", "schema", "blueprint"},
    "research": {"research", "investigate", "why", "compare", "analyse", "analyze",
                 "evaluate", "understand", "explain", "root cause"},
}

# Weight contributions for each factor (normalised internally).
_FACTOR_WEIGHTS: dict[str, float] = {
    "length": 0.15,
    "ambiguity": 0.15,
    "files_touched": 0.15,
    "risk": 0.15,
    "novelty": 0.10,
    "structural": 0.30,
}

_COMPLEXITY_CATEGORY_MAP: dict[str, int] = {
    "trivial": 1,
    "lookup": 3,
    "generation": 4,
    "refactoring": 6,
    "architecture": 8,
    "research": 9,
}


# ------------------------------------------------------------------ #
# Main switch                                                        #
# ------------------------------------------------------------------ #


class ThinkingSwitch:
    """Qwen3-inspired thinking-mode selector with heuristic complexity estimation.

    The switch analyses a task description and produces a
    :class:`ModeDecision` that specifies *whether* to think, *how deeply* to
    think, and *how many tokens* to spend.

    Usage
    -----
    >>> switch = ThinkingSwitch()
    >>> decision = switch.select_mode(
    ...     switch.estimate_complexity("Refactor the routing layer", {}),
    ...     task_type="refactoring",
    ... )
    >>> print(decision.mode)
    ThinkingMode.DEEP
    """

    def __init__(self, token_budget_override: dict[ThinkingMode, tuple[int, int]] | None = None):
        self._budgets: dict[ThinkingMode, tuple[int, int]] = (
            token_budget_override if token_budget_override is not None
            else _MODE_BUDGETS
        )
        self._decision_history: list[ModeDecision] = []
        self._max_history: int = 1000

    # ── Public API ─────────────────────────────────────────────

    def estimate_complexity(
        self,
        task_description: str,
        context: dict[str, Any] | None = None,
    ) -> ComplexityEstimate:
        """Heuristic complexity estimation based on task text and context.

        Parameters
        ----------
        task_description : str
            Free-text description of the task to estimate.
        context : dict or None
            Optional context dictionary that may contain ``files_touched``,
            ``risk_level``, or ``novelty`` hints.

        Returns
        -------
        ComplexityEstimate
            Immutable estimate with per-factor breakdown.
        """
        context = context or {}
        factors: dict[str, float] = self._analyze_factors(task_description)

        # Incorporate hints from context when heuristic values are low.
        if factors.get("files_touched", 0) < 0.3:
            ctx_files = context.get("files_touched", 0)
            if isinstance(ctx_files, (int, float)) and ctx_files > 2:
                factors["files_touched"] = min(1.0, ctx_files / 10.0)

        if factors.get("risk", 0) < 0.3:
            ctx_risk = context.get("risk_level", 0.0)
            if isinstance(ctx_risk, (int, float)):
                factors["risk"] = min(1.0, ctx_risk)

        score = self._compute_score(factors)
        category = self._categorize_task(task_description)
        # Apply category bonus: architecture and research tasks get a boost
        # since they are cognitively demanding even when described concisely.
        category_bonus = _COMPLEXITY_CATEGORY_MAP.get(category, 0)
        # Blend: 70% heuristic score, 30% category baseline — this ensures
        # a concise "Design a distributed system" (few words, high category)
        # correctly scores higher than a verbose "print hello world".
        category_base = max(1, category_bonus - 1) / 9.0  # normalise to 0-1
        raw_normalised = (score - 1) / 9.0  # normalise to 0-1
        blended = raw_normalised * 0.7 + category_base * 0.3
        final_score = min(10, max(1, round(1 + blended * 9)))

        return ComplexityEstimate(
            task_description=task_description,
            complexity_score=final_score,
            factors=factors,
        )

    def select_mode(
        self,
        complexity: ComplexityEstimate,
        task_type: str,
    ) -> ModeDecision:
        """Map a complexity estimate to a mode + token budget.

        Parameters
        ----------
        complexity : ComplexityEstimate
            Pre-computed estimate from :meth:`estimate_complexity`.
        task_type : str
            Expected category label for cross-checking.

        Returns
        -------
        ModeDecision
            Selected mode, budget, confidence, and reasoning.
        """
        score = complexity.complexity_score
        base_category = self._categorize_task(complexity.task_description)

        mode = self._score_to_mode(score)
        budget = self.get_token_budget(mode, complexity)
        confidence = self._compute_confidence(score, base_category, task_type)
        reasoning = self._build_reasoning(score, mode, base_category, task_type)

        decision = ModeDecision(
            mode=mode,
            budget_tokens=budget,
            confidence=confidence,
            reasoning=reasoning,
        )
        self._decision_history.append(decision)
        if len(self._decision_history) > self._max_history:
            self._decision_history = self._decision_history[-self._max_history:]
        return decision

    def should_think(self, task_description: str) -> bool:
        """Quick yes/no gate — returns ``True`` if the task warrants reasoning.

        This is the cheapest possible check and is intended for hot-path
        callers that need a boolean answer without the full decision object.

        Parameters
        ----------
        task_description : str
            Free-text task description.

        Returns
        -------
        bool
            ``True`` when estimated complexity > 3.
        """
        estimate = self.estimate_complexity(task_description, None)
        return estimate.complexity_score > 3

    def get_token_budget(
        self,
        mode: ThinkingMode,
        complexity: ComplexityEstimate,
    ) -> int:
        """Compute token budget for a given mode and complexity.

        Budget is linearly interpolated between the mode's min and max
        based on the normalised complexity score.

        Parameters
        ----------
        mode : ThinkingMode
            The selected reasoning mode.
        complexity : ComplexityEstimate
            Complexity estimate to scale the budget.

        Returns
        -------
        int
            Recommended reasoning token budget.
        """
        min_budget, max_budget = self._budgets.get(mode, (0, 0))
        if max_budget == 0:
            return 0
        normalised = (complexity.complexity_score - 1) / 9.0  # 1-10 -> 0-1
        budget = int(min_budget + normalised * (max_budget - min_budget))
        # Round to nearest 64 for cleanliness.
        return max(0, (budget // 64) * 64)

    def estimate_tokens(self, complexity: ComplexityEstimate) -> int:
        """Convenience: get just the token estimate for a complexity.

        Parameters
        ----------
        complexity : ComplexityEstimate
            Pre-computed estimate.

        Returns
        -------
        int
            Estimated reasoning tokens.
        """
        return self.get_token_budget(self._score_to_mode(complexity.complexity_score), complexity)

    # ── Internal heuristics ────────────────────────────────────

    def _analyze_factors(self, task: str) -> dict[str, float]:
        """Decompose a task string into individual factor scores (0.0 — 1.0).

        Parameters
        ----------
        task : str
            The raw task description.

        Returns
        -------
        dict[str, float]
            Per-factor scores.
        """
        word_count = len(task.split())

        # Length score: sigmoid centred at 50 words.
        length_score = 1.0 / (1.0 + math.exp(-0.05 * (word_count - 50)))
        length_score = max(0.0, min(1.0, length_score))

        # Files touched: heuristic based on file-like mentions.
        file_matches = re.findall(r'\b[\w./-]+\.[a-z]{2,4}\b', task)
        files_score = min(1.0, len(file_matches) / 8.0)

        # Ambiguity: presence of uncertain or vague language.
        ambiguity_indicators = [
            "maybe", "possibly", "unclear", "unknown", "somehow",
            "not sure", "depends", "various", "might", "could be",
        ]
        ambiguity_count = sum(1 for w in ambiguity_indicators if w in task.lower())
        ambiguity_score = min(1.0, ambiguity_count / 4.0)

        # Risk: keywords suggesting high-stakes changes.
        risk_indicators = [
            "critical", "production", "breaking", "security", "safety",
            "irreversible", "data-loss", "rollback", "revert", "urgent",
        ]
        risk_count = sum(1 for w in risk_indicators if w in task.lower())
        risk_score = min(1.0, risk_count / 5.0)

        # Novelty: new concepts or unfamiliar territory.
        novelty_indicators = [
            "new", "unfamiliar", "first time", "never", "novel",
            "unknown territory", "pilot", "experimental", "explore",
        ]
        novelty_count = sum(1 for w in novelty_indicators if w in task.lower())
        novelty_score = min(1.0, novelty_count / 4.0)

        # Structural complexity: domain keywords that indicate multi-component
        # or cognitively demanding work.
        task_lower = task.lower()
        structural_indicators = [
            "design", "architecture", "system", "pipeline", "framework",
            "infrastructure", "orchestrat", "distributed", "scalable",
            "integration", "interface", "protocol", "multi-agent",
            "fault tolerant", "redundancy", "cluster", "deploy",
            "migrate", "transform", "refactor", "restructure",
            "implement", "build", "create", "develop",
            # Research and analysis
            "research", "investigate", "analyse", "analyze", "evaluate",
            "consensus", "algorithm", "protocol", "theory", "benchmark",
        ]
        structural_count = sum(1 for w in structural_indicators if w in task_lower)
        # Score scales with absolute keyword count + a density bonus for
        # concise descriptions that pack many domain terms into few words.
        structural_base = min(1.0, structural_count / 5.0)
        density = structural_count / max(1, word_count)
        density_bonus = min(0.3, density * 3.0)
        structural_score = min(1.0, structural_base + density_bonus)

        return {
            "length": round(length_score, 3),
            "files_touched": round(files_score, 3),
            "ambiguity": round(ambiguity_score, 3),
            "risk": round(risk_score, 3),
            "novelty": round(novelty_score, 3),
            "structural": round(structural_score, 3),
        }

    def _categorize_task(self, task: str) -> str:
        """Classify a task description into a category label.

        Parameters
        ----------
        task : str
            Raw task description.

        Returns
        -------
        str
            One of: ``"trivial"``, ``"lookup"``, ``"generation"``,
            ``"refactoring"``, ``"architecture"``, ``"research"``.
        """
        task_lower = task.lower()
        best_category = "generation"
        best_score = 0

        for category, keywords in _CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in task_lower)
            if score > best_score:
                best_score = score
                best_category = category

        return best_category

    def _compute_score(self, factors: dict[str, float]) -> int:
        """Convert per-factor scores to a 1-10 integer.

        Parameters
        ----------
        factors : dict[str, float]
            Per-factor scores from :meth:`_analyze_factors`.

        Returns
        -------
        int
            Complexity score 1-10.
        """
        weighted = 0.0
        for key, weight in _FACTOR_WEIGHTS.items():
            weighted += factors.get(key, 0.0) * weight
        # Scale from [0, 1] to [1, 10].
        raw = 1 + weighted * 9
        return min(10, max(1, round(raw)))

    def _score_to_mode(self, score: int) -> ThinkingMode:
        """Map a numeric complexity score to a thinking mode.

        Parameters
        ----------
        score : int
            Complexity score 1-10.

        Returns
        -------
        ThinkingMode
        """
        if score <= 2:
            return ThinkingMode.OFF
        elif score <= 4:
            return ThinkingMode.FAST
        elif score <= 7:
            return ThinkingMode.DEEP
        else:
            return ThinkingMode.EXTENDED

    def _compute_confidence(self, score: int, base_cat: str, expected_cat: str) -> float:
        """Decision confidence based on score extremity and category match.

        Parameters
        ----------
        score : int
            Computed complexity score.
        base_cat : str
            Heuristic category from task text.
        expected_cat : str
            Expected category provided by caller.

        Returns
        -------
        float
            Confidence 0.0 — 1.0.
        """
        # Very low and very high scores are more confident.
        score_confidence = 1.0 - abs(score - 5) / 5.0  # peak at 5, trough at extremes
        extreme_bonus = 0.2 if score <= 2 or score >= 9 else 0.0

        category_match = 0.3 if base_cat == expected_cat else 0.0

        return round(min(1.0, score_confidence * 0.5 + extreme_bonus + category_match), 3)

    def _build_reasoning(self, score: int, mode: ThinkingMode, base_cat: str, expected_cat: str) -> str:
        """Build a short human-readable explanation of the decision.

        Parameters
        ----------
        score : int
            Computed complexity score.
        mode : ThinkingMode
            Selected mode.
        base_cat : str
            Heuristic category.
        expected_cat : str
            Expected category from caller.

        Returns
        -------
        str
            Explanation string.
        """
        return (
            f"Complexity {score}/10 [{base_cat}] -> {mode.name}. "
            f"Expected '{expected_cat}'. "
            f"{'Category matches.' if base_cat == expected_cat else 'Category mismatch.'}"
        )

    def _estimate_tokens_from_score(self, score: int) -> int:
        """Rough upper-bound token estimate for a score.

        Parameters
        ----------
        score : int
            Complexity score 1-10.

        Returns
        -------
        int
            Estimated token budget.
        """
        mode = self._score_to_mode(score)
        _, max_budget = self._budgets.get(mode, (0, 0))
        return max_budget


__all__ = [
    "ThinkingMode",
    "TaskCategory",
    "TaskComplexity",
    "ModeDecision",
    "ComplexityEstimate",
    "ThinkingSwitch",
]
