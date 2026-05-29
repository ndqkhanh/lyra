"""
AI Content Detector

Detects AI-generated content patterns including:
- 25 AI high-frequency terms
- Throat-clearing openers
- Punctuation patterns
- Burstiness (sentence length variation)
"""

import re
from dataclasses import dataclass
from enum import Enum


class AIPattern(Enum):
    """Types of AI patterns"""
    HIGH_FREQ_TERMS = "high_freq_terms"
    THROAT_CLEARING = "throat_clearing"
    LOW_BURSTINESS = "low_burstiness"
    AI_PUNCTUATION = "ai_punctuation"


@dataclass
class AIDetectionResult:
    """Result from AI content detection"""
    is_ai_generated: bool
    confidence: float  # 0.0 to 1.0
    issues: list[str]
    patterns_detected: dict[AIPattern, int]


class AIContentDetector:
    """
    Detect 25 AI high-frequency terms and patterns

    Identifies AI-generated content through linguistic patterns.
    """

    # 25 AI high-frequency terms
    AI_HIGH_FREQ_TERMS = [
        "delve", "leverage", "robust", "comprehensive", "facilitate",
        "utilize", "paradigm", "synergy", "holistic", "innovative",
        "cutting-edge", "state-of-the-art", "novel", "groundbreaking",
        "transformative", "revolutionary", "game-changing", "disruptive",
        "seamless", "scalable", "optimize", "streamline", "enhance",
        "empower", "unlock"
    ]

    # Throat-clearing openers
    THROAT_CLEARING_OPENERS = [
        "It is important to note that",
        "It should be emphasized that",
        "It is worth mentioning that",
        "As previously mentioned",
        "In this context",
        "It is worth noting that",
        "It should be noted that",
        "It is interesting to note that",
        "As we have seen",
        "In light of this",
    ]

    def __init__(self):
        """Initialize AI content detector"""
        pass

    def detect_ai_patterns(self, text: str) -> AIDetectionResult:
        """
        Detect AI-generated content patterns

        Args:
            text: Text to analyze

        Returns:
            AIDetectionResult with detection details
        """
        issues = []
        patterns = {}

        # Check high-frequency terms
        term_count = self.count_high_freq_terms(text)
        patterns[AIPattern.HIGH_FREQ_TERMS] = term_count
        if term_count > 5:
            issues.append(f"High AI term density: {term_count} terms found")

        # Check throat-clearing openers
        opener_count = self.count_throat_clearing(text)
        patterns[AIPattern.THROAT_CLEARING] = opener_count
        if opener_count > 2:
            issues.append(f"Throat-clearing openers: {opener_count} found")

        # Check burstiness (sentence length variation)
        burstiness = self.calculate_burstiness(text)
        if burstiness < 0.3:
            patterns[AIPattern.LOW_BURSTINESS] = 1
            issues.append(f"Low burstiness: {burstiness:.2f} (AI-like uniformity)")

        # Check punctuation patterns
        if self.detect_ai_punctuation(text):
            patterns[AIPattern.AI_PUNCTUATION] = 1
            issues.append("AI punctuation patterns detected")

        # Determine if AI-generated (2+ issues = likely AI)
        is_ai = len(issues) >= 2
        confidence = len(issues) / 4  # 4 possible issue types

        return AIDetectionResult(
            is_ai_generated=is_ai,
            confidence=confidence,
            issues=issues,
            patterns_detected=patterns
        )

    def count_high_freq_terms(self, text: str) -> int:
        """
        Count AI high-frequency terms

        Args:
            text: Text to analyze

        Returns:
            Count of high-frequency terms
        """
        text_lower = text.lower()
        count = sum(1 for term in self.AI_HIGH_FREQ_TERMS if term in text_lower)
        return count

    def count_throat_clearing(self, text: str) -> int:
        """
        Count throat-clearing openers

        Args:
            text: Text to analyze

        Returns:
            Count of throat-clearing phrases
        """
        count = sum(1 for opener in self.THROAT_CLEARING_OPENERS if opener in text)
        return count

    def calculate_burstiness(self, text: str) -> float:
        """
        Calculate burstiness (sentence length variation)

        Low burstiness indicates AI-like uniformity.

        Args:
            text: Text to analyze

        Returns:
            Burstiness score (0.0 to 1.0+)
        """
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) < 2:
            return 0.5  # Not enough data

        # Calculate sentence lengths
        lengths = [len(s.split()) for s in sentences]

        # Calculate coefficient of variation (std / mean)
        import statistics
        if statistics.mean(lengths) == 0:
            return 0.0

        std_dev = statistics.stdev(lengths) if len(lengths) > 1 else 0
        mean = statistics.mean(lengths)
        cv = std_dev / mean if mean > 0 else 0

        # Normalize to 0-1 range (CV > 0.5 is high burstiness)
        burstiness = min(cv / 0.5, 1.0)

        return burstiness

    def detect_ai_punctuation(self, text: str) -> bool:
        """
        Detect AI punctuation patterns

        AI tends to use consistent punctuation patterns.

        Args:
            text: Text to analyze

        Returns:
            True if AI punctuation patterns detected
        """
        # Check for excessive comma usage
        comma_ratio = text.count(',') / len(text.split()) if text.split() else 0
        if comma_ratio > 0.15:  # More than 15% of words followed by comma
            return True

        # Check for lack of semicolons (AI rarely uses them)
        semicolon_count = text.count(';')
        sentence_count = len(re.split(r'[.!?]+', text))
        if sentence_count > 10 and semicolon_count == 0:
            return True

        return False

    def get_high_freq_terms_found(self, text: str) -> list[str]:
        """
        Get list of high-frequency terms found in text

        Args:
            text: Text to analyze

        Returns:
            List of terms found
        """
        text_lower = text.lower()
        found = [term for term in self.AI_HIGH_FREQ_TERMS if term in text_lower]
        return found

    def get_throat_clearing_found(self, text: str) -> list[str]:
        """
        Get list of throat-clearing openers found in text

        Args:
            text: Text to analyze

        Returns:
            List of openers found
        """
        found = [opener for opener in self.THROAT_CLEARING_OPENERS if opener in text]
        return found
