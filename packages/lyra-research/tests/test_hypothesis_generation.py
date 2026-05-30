"""
Unit tests for hypothesis generation in scientist research workflows.

Tests cover:
- Hypothesis creation from observations
- Hypothesis novelty scoring
- Testability checks
- Hypothesis refinement
- Contradiction handling
- Hypothesis ranking and diversity
"""

import pytest
from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum


class HypothesisStatus(Enum):
    """Status of a hypothesis."""
    PROPOSED = "proposed"
    TESTING = "testing"
    CONFIRMED = "confirmed"
    REFUTED = "refuted"
    INCONCLUSIVE = "inconclusive"


@dataclass
class Hypothesis:
    """Represents a scientific hypothesis."""
    id: str
    statement: str
    independent_variable: str
    dependent_variable: str
    expected_effect: str
    novelty_score: float = 0.5
    testability_score: float = 0.5
    promise_score: float = 0.5
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    confidence: float = 0.5
    evidence: List[str] = None
    contradictions: List[str] = None

    def __post_init__(self):
        if self.evidence is None:
            self.evidence = []
        if self.contradictions is None:
            self.contradictions = []


class HypothesisGenerator:
    """Generates and manages scientific hypotheses."""

    def __init__(self):
        self.hypotheses: List[Hypothesis] = []
        self.next_id = 1

    def generate_from_observations(
        self,
        observations: List[str],
        domain: str = "general"
    ) -> List[Hypothesis]:
        """Generate hypotheses from observations."""
        hypotheses = []

        for obs in observations:
            # Extract variables from observation
            if "increases" in obs.lower() or "improves" in obs.lower():
                effect = "positive"
            elif "decreases" in obs.lower() or "reduces" in obs.lower():
                effect = "negative"
            else:
                effect = "neutral"

            # Create hypothesis
            h = Hypothesis(
                id=f"H{self.next_id}",
                statement=f"Hypothesis based on: {obs}",
                independent_variable="extracted_iv",
                dependent_variable="extracted_dv",
                expected_effect=effect,
                novelty_score=self._calculate_novelty(obs, domain),
                testability_score=self._calculate_testability(obs),
            )

            self.next_id += 1
            hypotheses.append(h)
            self.hypotheses.append(h)

        return hypotheses

    def _calculate_novelty(self, statement: str, domain: str) -> float:
        """Calculate novelty score for hypothesis."""
        # Simple heuristic: longer statements are more novel
        base_score = min(len(statement) / 200.0, 1.0)

        # Check against existing hypotheses
        similarity_penalty = 0.0
        for h in self.hypotheses:
            if self._similarity(statement, h.statement) > 0.7:
                similarity_penalty += 0.2

        return max(0.0, min(1.0, base_score - similarity_penalty))

    def _calculate_testability(self, statement: str) -> float:
        """Calculate testability score for hypothesis."""
        # Check for measurable variables
        measurable_keywords = ["measure", "count", "rate", "score", "accuracy", "performance"]
        score = 0.5

        for keyword in measurable_keywords:
            if keyword in statement.lower():
                score += 0.1

        return min(1.0, score)

    def _similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    def refine_hypothesis(
        self,
        hypothesis_id: str,
        new_evidence: List[str]
    ) -> Hypothesis:
        """Refine hypothesis based on new evidence."""
        h = self._get_hypothesis(hypothesis_id)

        if h is None:
            raise ValueError(f"Hypothesis {hypothesis_id} not found")

        # Add evidence
        h.evidence.extend(new_evidence)

        # Update confidence based on evidence
        h.confidence = min(1.0, h.confidence + 0.1 * len(new_evidence))

        return h

    def handle_contradiction(
        self,
        hypothesis_id: str,
        contradictory_evidence: str
    ) -> Hypothesis:
        """Handle contradictory evidence for hypothesis."""
        h = self._get_hypothesis(hypothesis_id)

        if h is None:
            raise ValueError(f"Hypothesis {hypothesis_id} not found")

        # Add contradiction
        h.contradictions.append(contradictory_evidence)

        # Reduce confidence
        h.confidence = max(0.0, h.confidence - 0.2)

        # If too many contradictions, mark as refuted
        if len(h.contradictions) >= 3:
            h.status = HypothesisStatus.REFUTED

        return h

    def rank_by_promise(self) -> List[Hypothesis]:
        """Rank hypotheses by promise score."""
        # Calculate promise score
        for h in self.hypotheses:
            h.promise_score = (
                0.3 * h.novelty_score +
                0.3 * h.testability_score +
                0.4 * h.confidence
            )

        # Sort by promise score
        return sorted(self.hypotheses, key=lambda h: h.promise_score, reverse=True)

    def maintain_diversity(self, max_similar: int = 2) -> List[Hypothesis]:
        """Maintain diversity in hypothesis pool."""
        diverse_hypotheses = []

        for h in self.hypotheses:
            # Check similarity with already selected hypotheses
            similar_count = 0
            for selected in diverse_hypotheses:
                if self._similarity(h.statement, selected.statement) > 0.6:
                    similar_count += 1

            # Add if not too similar to existing
            if similar_count < max_similar:
                diverse_hypotheses.append(h)

        return diverse_hypotheses

    def _get_hypothesis(self, hypothesis_id: str) -> Hypothesis:
        """Get hypothesis by ID."""
        for h in self.hypotheses:
            if h.id == hypothesis_id:
                return h
        return None


# ============================================================================
# UNIT TESTS
# ============================================================================

class TestHypothesisGenerator:
    """Test suite for HypothesisGenerator."""

    def test_generate_hypothesis_from_observations(self):
        """Test generating hypotheses from observations."""
        generator = HypothesisGenerator()

        observations = [
            "Increasing context window improves reasoning accuracy",
            "Multi-agent systems reduce task completion time",
        ]

        hypotheses = generator.generate_from_observations(observations)

        assert len(hypotheses) == 2
        assert all(h.id.startswith("H") for h in hypotheses)
        assert all(h.status == HypothesisStatus.PROPOSED for h in hypotheses)
        assert hypotheses[0].expected_effect == "positive"
        assert hypotheses[1].expected_effect == "negative" or hypotheses[1].expected_effect == "neutral"

    def test_hypothesis_novelty_scoring(self):
        """Test scoring hypothesis novelty."""
        generator = HypothesisGenerator()

        # First hypothesis should have reasonable novelty
        h1 = generator.generate_from_observations(
            ["This is a completely novel observation about AI systems"],
            domain="AI"
        )[0]

        # Similar hypothesis should have lower novelty
        h2 = generator.generate_from_observations(
            ["This is a novel observation about AI systems"],
            domain="AI"
        )[0]

        assert h1.novelty_score > 0.2
        assert h2.novelty_score < h1.novelty_score

    def test_hypothesis_testability_check(self):
        """Test checking if hypothesis is testable."""
        generator = HypothesisGenerator()

        # Testable hypothesis with measurable variables
        testable = generator.generate_from_observations([
            "Increasing model size improves accuracy score on benchmark"
        ])[0]

        # Less testable hypothesis
        less_testable = generator.generate_from_observations([
            "AI systems are better than humans"
        ])[0]

        assert testable.testability_score > less_testable.testability_score
        assert testable.testability_score > 0.5

    def test_refine_hypothesis_based_on_evidence(self):
        """Test refining hypotheses with new evidence."""
        generator = HypothesisGenerator()

        h = generator.generate_from_observations([
            "Multi-agent coordination improves performance"
        ])[0]

        initial_confidence = h.confidence

        # Refine with new evidence
        refined = generator.refine_hypothesis(
            h.id,
            ["Experiment 1 confirms hypothesis", "Experiment 2 confirms hypothesis"]
        )

        assert len(refined.evidence) == 2
        assert refined.confidence > initial_confidence

    def test_hypothesis_contradiction_handling(self):
        """Test handling contradictory evidence."""
        generator = HypothesisGenerator()

        h = generator.generate_from_observations([
            "Larger models always perform better"
        ])[0]

        initial_confidence = h.confidence

        # Add contradictory evidence
        updated = generator.handle_contradiction(
            h.id,
            "Small model outperformed large model on task X"
        )

        assert len(updated.contradictions) == 1
        assert updated.confidence < initial_confidence

    def test_hypothesis_refutation_on_multiple_contradictions(self):
        """Test hypothesis refutation with multiple contradictions."""
        generator = HypothesisGenerator()

        h = generator.generate_from_observations([
            "Method A is always superior to Method B"
        ])[0]

        # Add multiple contradictions
        for i in range(3):
            generator.handle_contradiction(h.id, f"Contradiction {i+1}")

        assert h.status == HypothesisStatus.REFUTED

    def test_rank_hypotheses_by_promise(self):
        """Test ranking hypotheses by promise score."""
        generator = HypothesisGenerator()

        # Generate multiple hypotheses
        generator.generate_from_observations([
            "High novelty and testability hypothesis with measurable accuracy",
            "Low novelty hypothesis",
            "Medium hypothesis with some measurable performance",
        ])

        # Manually adjust scores for testing
        generator.hypotheses[0].novelty_score = 0.9
        generator.hypotheses[0].testability_score = 0.9
        generator.hypotheses[0].confidence = 0.8

        generator.hypotheses[1].novelty_score = 0.3
        generator.hypotheses[1].testability_score = 0.3
        generator.hypotheses[1].confidence = 0.3

        ranked = generator.rank_by_promise()

        assert len(ranked) == 3
        assert ranked[0].promise_score > ranked[1].promise_score
        assert ranked[1].promise_score > ranked[2].promise_score

    def test_hypothesis_diversity_maintenance(self):
        """Test maintaining diverse hypothesis pool."""
        generator = HypothesisGenerator()

        # Generate similar hypotheses
        generator.generate_from_observations([
            "Multi-agent systems improve performance",
            "Multi-agent systems enhance performance",
            "Multi-agent systems boost performance",
            "Single-agent systems are effective",
        ])

        diverse = generator.maintain_diversity(max_similar=2)

        # Should filter out very similar hypotheses
        assert len(diverse) < len(generator.hypotheses)
        assert len(diverse) >= 2  # At least some diversity maintained


class TestHypothesisRefinement:
    """Test hypothesis refinement workflows."""

    def test_iterative_refinement(self):
        """Test iterative hypothesis refinement."""
        generator = HypothesisGenerator()

        h = generator.generate_from_observations([
            "Increasing training data improves model accuracy"
        ])[0]

        # Multiple refinement iterations
        for i in range(3):
            generator.refine_hypothesis(h.id, [f"Evidence {i+1}"])

        assert len(h.evidence) == 3
        assert h.confidence > 0.5

    def test_refinement_with_mixed_evidence(self):
        """Test refinement with both supporting and contradicting evidence."""
        generator = HypothesisGenerator()

        h = generator.generate_from_observations([
            "Method X outperforms Method Y"
        ])[0]

        # Add supporting evidence
        generator.refine_hypothesis(h.id, ["Experiment 1 supports"])
        confidence_after_support = h.confidence

        # Add contradictory evidence
        generator.handle_contradiction(h.id, "Experiment 2 contradicts")

        assert h.confidence < confidence_after_support
        assert len(h.evidence) == 1
        assert len(h.contradictions) == 1


class TestHypothesisValidation:
    """Test hypothesis validation logic."""

    def test_hypothesis_id_generation(self):
        """Test unique hypothesis ID generation."""
        generator = HypothesisGenerator()

        h1 = generator.generate_from_observations(["Observation 1"])[0]
        h2 = generator.generate_from_observations(["Observation 2"])[0]

        assert h1.id != h2.id
        assert h1.id == "H1"
        assert h2.id == "H2"

    def test_hypothesis_not_found_error(self):
        """Test error handling for non-existent hypothesis."""
        generator = HypothesisGenerator()

        with pytest.raises(ValueError, match="Hypothesis H999 not found"):
            generator.refine_hypothesis("H999", ["Evidence"])

    def test_empty_observations(self):
        """Test handling empty observations."""
        generator = HypothesisGenerator()

        hypotheses = generator.generate_from_observations([])

        assert len(hypotheses) == 0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestHypothesisGenerationIntegration:
    """Integration tests for hypothesis generation workflow."""

    @pytest.mark.integration
    def test_full_hypothesis_lifecycle(self):
        """Test complete hypothesis lifecycle."""
        generator = HypothesisGenerator()

        # 1. Generate hypothesis
        hypotheses = generator.generate_from_observations([
            "Increasing model parameters improves accuracy on benchmark"
        ])
        h = hypotheses[0]

        assert h.status == HypothesisStatus.PROPOSED

        # 2. Refine with evidence
        generator.refine_hypothesis(h.id, ["Experiment 1 confirms"])

        # 3. Rank by promise
        ranked = generator.rank_by_promise()
        assert h in ranked

        # 4. Check diversity
        diverse = generator.maintain_diversity()
        assert h in diverse

    @pytest.mark.integration
    def test_multiple_hypotheses_workflow(self):
        """Test workflow with multiple competing hypotheses."""
        generator = HypothesisGenerator()

        # Generate multiple hypotheses
        observations = [
            "Method A improves accuracy",
            "Method B reduces latency",
            "Method C balances accuracy and latency",
        ]

        hypotheses = generator.generate_from_observations(observations)

        assert len(hypotheses) == 3

        # Refine each with different evidence
        generator.refine_hypothesis(hypotheses[0].id, ["Strong evidence for A"])
        generator.refine_hypothesis(hypotheses[1].id, ["Weak evidence for B"])
        generator.handle_contradiction(hypotheses[2].id, "C fails on edge cases")

        # Rank and select best
        ranked = generator.rank_by_promise()

        assert ranked[0].confidence >= ranked[1].confidence
        assert ranked[1].confidence >= ranked[2].confidence


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
