"""
Burstiness Analyzer

Analyzes sentence length variation (burstiness) in text.
Low burstiness indicates AI-like uniformity.
"""

from dataclasses import dataclass
from typing import List
import re
import statistics


@dataclass
class BurstinessResult:
    """Result from burstiness analysis"""
    burstiness_score: float  # 0.0 to 1.0+
    mean_sentence_length: float
    std_dev: float
    coefficient_of_variation: float
    sentence_lengths: List[int]
    is_uniform: bool  # True if burstiness < 0.3


class BurstinessAnalyzer:
    """
    Analyze sentence length variation (burstiness)

    Human writing tends to have high burstiness (varied sentence lengths).
    AI writing tends to have low burstiness (uniform sentence lengths).
    """

    def __init__(self, uniformity_threshold: float = 0.3):
        """
        Initialize burstiness analyzer

        Args:
            uniformity_threshold: Threshold below which text is considered uniform
        """
        self.uniformity_threshold = uniformity_threshold

    def analyze(self, text: str) -> BurstinessResult:
        """
        Analyze text burstiness

        Args:
            text: Text to analyze

        Returns:
            BurstinessResult with analysis
        """
        # Split into sentences
        sentences = self.split_sentences(text)

        if len(sentences) < 2:
            # Not enough data
            return BurstinessResult(
                burstiness_score=0.5,
                mean_sentence_length=0.0,
                std_dev=0.0,
                coefficient_of_variation=0.0,
                sentence_lengths=[],
                is_uniform=False
            )

        # Calculate sentence lengths (in words)
        lengths = [len(s.split()) for s in sentences]

        # Calculate statistics
        mean = statistics.mean(lengths)
        std_dev = statistics.stdev(lengths) if len(lengths) > 1 else 0.0

        # Calculate coefficient of variation (CV = std / mean)
        cv = std_dev / mean if mean > 0 else 0.0

        # Normalize to 0-1 range (CV > 0.5 is high burstiness)
        burstiness = min(cv / 0.5, 1.0)

        # Determine if uniform
        is_uniform = burstiness < self.uniformity_threshold

        return BurstinessResult(
            burstiness_score=burstiness,
            mean_sentence_length=mean,
            std_dev=std_dev,
            coefficient_of_variation=cv,
            sentence_lengths=lengths,
            is_uniform=is_uniform
        )

    def split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Split on sentence terminators
        sentences = re.split(r'[.!?]+', text)

        # Clean and filter
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def is_ai_like(self, text: str) -> bool:
        """
        Check if text has AI-like uniformity

        Args:
            text: Text to check

        Returns:
            True if text appears AI-generated based on burstiness
        """
        result = self.analyze(text)
        return result.is_uniform

    def get_burstiness_score(self, text: str) -> float:
        """
        Get burstiness score for text

        Args:
            text: Text to analyze

        Returns:
            Burstiness score (0.0 to 1.0+)
        """
        result = self.analyze(text)
        return result.burstiness_score
