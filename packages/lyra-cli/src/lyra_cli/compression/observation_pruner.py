"""
Observation Pruning - FocusAgent-style goal-aware filtering.

Extracts goal-relevant lines from large observations before action model.
Achieves 95%+ compression (10,000 lines → 50 lines).
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import re


@dataclass
class PruningResult:
    """Result of observation pruning."""

    original_lines: int
    pruned_lines: int
    compression_ratio: float
    relevant_content: str
    filtered_keywords: List[str]


class ObservationPruner:
    """
    Goal-aware observation pruning.

    Uses lightweight heuristics to extract relevant lines.
    Can be enhanced with small model (Haiku-class) for better accuracy.
    """

    def __init__(
        self,
        max_output_lines: int = 50,
        relevance_threshold: float = 0.3,
    ):
        self.max_output_lines = max_output_lines
        self.relevance_threshold = relevance_threshold

        # Statistics
        self.total_pruned = 0
        self.total_original = 0

    def prune(
        self,
        observation: str,
        goal: str,
        context: Optional[Dict[str, Any]] = None
    ) -> PruningResult:
        """
        Prune observation to extract goal-relevant lines.

        Args:
            observation: Raw observation text
            goal: Current goal/task description
            context: Optional context for better relevance scoring

        Returns:
            PruningResult with compressed content
        """
        lines = observation.split('\n')
        original_count = len(lines)

        # Extract keywords from goal
        goal_keywords = self._extract_keywords(goal)

        # Score each line for relevance
        scored_lines = []
        for i, line in enumerate(lines):
            score = self._score_relevance(line, goal_keywords, context)
            if score >= self.relevance_threshold:
                scored_lines.append((score, i, line))

        # Sort by score and take top N
        scored_lines.sort(reverse=True, key=lambda x: x[0])
        top_lines = scored_lines[:self.max_output_lines]

        # Sort by original position to maintain order
        top_lines.sort(key=lambda x: x[1])

        # Extract content
        relevant_content = '\n'.join(line for _, _, line in top_lines)
        pruned_count = len(top_lines)

        # Update statistics
        self.total_original += original_count
        self.total_pruned += pruned_count

        # Calculate compression
        compression_ratio = (
            (original_count - pruned_count) / original_count
            if original_count > 0
            else 0.0
        )

        return PruningResult(
            original_lines=original_count,
            pruned_lines=pruned_count,
            compression_ratio=compression_ratio,
            relevant_content=relevant_content,
            filtered_keywords=goal_keywords,
        )

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text."""
        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
        }

        # Extract words
        words = re.findall(r'\b\w+\b', text.lower())

        # Filter stop words and short words
        keywords = [
            w for w in words
            if w not in stop_words and len(w) > 3
        ]

        # Return unique keywords
        return list(set(keywords))

    def _score_relevance(
        self,
        line: str,
        goal_keywords: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Score line relevance to goal.

        Returns score between 0.0 and 1.0.
        """
        if not line.strip():
            return 0.0

        line_lower = line.lower()
        score = 0.0

        # Keyword matching
        keyword_matches = sum(1 for kw in goal_keywords if kw in line_lower)
        if goal_keywords:
            score += (keyword_matches / len(goal_keywords)) * 0.5

        # Error/warning indicators (usually important)
        if any(indicator in line_lower for indicator in ['error', 'warning', 'fail', 'exception']):
            score += 0.3

        # Success indicators
        if any(indicator in line_lower for indicator in ['success', 'complete', 'done', 'pass']):
            score += 0.2

        # Numeric data (often important)
        if re.search(r'\d+', line):
            score += 0.1

        # File paths (often important)
        if '/' in line or '\\' in line:
            score += 0.1

        # Context-based scoring
        if context:
            # Boost score if line contains context keywords
            context_keywords = context.get('keywords', [])
            context_matches = sum(1 for kw in context_keywords if kw in line_lower)
            if context_keywords:
                score += (context_matches / len(context_keywords)) * 0.2

        # Cap at 1.0
        return min(score, 1.0)

    def get_stats(self) -> Dict[str, Any]:
        """Get pruning statistics."""
        overall_compression = (
            (self.total_original - self.total_pruned) / self.total_original
            if self.total_original > 0
            else 0.0
        )

        return {
            "total_original_lines": self.total_original,
            "total_pruned_lines": self.total_pruned,
            "overall_compression_ratio": overall_compression,
            "lines_saved": self.total_original - self.total_pruned,
        }

    def reset_stats(self):
        """Reset statistics."""
        self.total_pruned = 0
        self.total_original = 0


class SmartObservationPruner(ObservationPruner):
    """
    Enhanced pruner with small model support.

    Can use a small model (Haiku-class) for better relevance scoring.
    Falls back to heuristic scoring if model unavailable.
    """

    def __init__(
        self,
        max_output_lines: int = 50,
        relevance_threshold: float = 0.3,
        use_model: bool = False,
    ):
        super().__init__(max_output_lines, relevance_threshold)
        self.use_model = use_model

    def _score_relevance_with_model(
        self,
        line: str,
        goal: str,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Score relevance using small model.

        Placeholder for model-based scoring.
        In production, this would call a small model (Haiku) to score relevance.
        """
        # TODO: Implement model-based scoring
        # For now, fall back to heuristic scoring
        goal_keywords = self._extract_keywords(goal)
        return self._score_relevance(line, goal_keywords, context)

    def prune(
        self,
        observation: str,
        goal: str,
        context: Optional[Dict[str, Any]] = None
    ) -> PruningResult:
        """
        Prune with optional model-based scoring.
        """
        if self.use_model:
            # Use model-based scoring (placeholder)
            return super().prune(observation, goal, context)
        else:
            # Use heuristic scoring
            return super().prune(observation, goal, context)
