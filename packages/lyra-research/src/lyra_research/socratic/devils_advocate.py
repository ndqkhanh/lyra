"""
Devil's Advocate Protocol

Implements Concession Threshold Protocol with frame-lock detection.
"""

from dataclasses import dataclass
from typing import Optional


class ConcessionThreshold:
    """Concession threshold levels (1-5 scale)"""
    WEAK = 1
    MODERATE = 2
    GOOD = 3
    STRONG = 4
    COMPELLING = 5


@dataclass
class AdvocateResult:
    """Result from devil's advocate evaluation"""
    concede: bool
    score: int  # 1-5
    reason: str
    counter_rebuttal: Optional[str] = None


class DevilsAdvocateProtocol:
    """
    Concession Threshold Protocol with frame-lock detection

    Prevents consecutive concessions and detects frame-lock patterns.
    """

    def __init__(self, concession_threshold: int = 4):
        """
        Initialize devil's advocate protocol

        Args:
            concession_threshold: Minimum score to concede (default 4)
        """
        self.concession_threshold = concession_threshold
        self.consecutive_concessions = 0
        self.max_consecutive = 1  # No consecutive concessions allowed
        self.concession_history = []

    def evaluate_rebuttal(self, claim: str, rebuttal: str) -> AdvocateResult:
        """
        Score rebuttal strength (1-5) and decide whether to concede

        Args:
            claim: Original claim being challenged
            rebuttal: User's rebuttal to the challenge

        Returns:
            AdvocateResult with concession decision
        """
        # Score the rebuttal
        score = self.score_rebuttal(claim, rebuttal)

        # Check if score meets threshold
        if score >= self.concession_threshold:
            # Check for frame-lock (consecutive concessions)
            if self.consecutive_concessions >= self.max_consecutive:
                # Frame-lock detected: refuse concession
                self.consecutive_concessions = 0  # Reset
                return AdvocateResult(
                    concede=False,
                    score=score,
                    reason="Frame-lock detected: consecutive concessions not allowed",
                    counter_rebuttal=self.generate_counter(claim, rebuttal)
                )

            # Concede
            self.consecutive_concessions += 1
            self.concession_history.append({
                "claim": claim,
                "rebuttal": rebuttal,
                "score": score
            })

            return AdvocateResult(
                concede=True,
                score=score,
                reason=f"Strong rebuttal (score {score}/{ConcessionThreshold.COMPELLING})"
            )

        # Don't concede - generate counter-rebuttal
        self.consecutive_concessions = 0  # Reset counter
        return AdvocateResult(
            concede=False,
            score=score,
            reason=f"Rebuttal insufficient (score {score}/{self.concession_threshold} required)",
            counter_rebuttal=self.generate_counter(claim, rebuttal)
        )

    def score_rebuttal(self, claim: str, rebuttal: str) -> int:
        """
        Score rebuttal strength on 1-5 scale

        Args:
            claim: Original claim
            rebuttal: User's rebuttal

        Returns:
            Score (1-5)
        """
        score = 1  # Start with weak

        # Check for evidence
        evidence_keywords = ["study", "research", "data", "evidence", "paper", "source"]
        if any(kw in rebuttal.lower() for kw in evidence_keywords):
            score += 1

        # Check for logical reasoning
        reasoning_keywords = ["because", "therefore", "thus", "since", "given that"]
        if any(kw in rebuttal.lower() for kw in reasoning_keywords):
            score += 1

        # Check for counter-examples
        counter_keywords = ["however", "but", "counter-example", "alternatively"]
        if any(kw in rebuttal.lower() for kw in counter_keywords):
            score += 1

        # Check for length/detail (longer rebuttals tend to be more thorough)
        if len(rebuttal) > 200:
            score += 1

        # Cap at 5
        return min(score, 5)

    def generate_counter(self, claim: str, rebuttal: str) -> str:
        """
        Generate counter-rebuttal

        Args:
            claim: Original claim
            rebuttal: User's rebuttal

        Returns:
            Counter-rebuttal text
        """
        # In production, this would use LLM to generate sophisticated counter-arguments
        # For now, return a template
        return f"While your rebuttal addresses some aspects, consider: What evidence supports the alternative view? Have you accounted for potential confounding factors?"

    def detect_frame_lock(self) -> bool:
        """
        Detect if frame-lock pattern is occurring

        Returns:
            True if frame-lock detected
        """
        # Frame-lock: consecutive concessions without genuine progress
        return self.consecutive_concessions >= self.max_consecutive

    def reset(self):
        """Reset the protocol state"""
        self.consecutive_concessions = 0
        self.concession_history = []
