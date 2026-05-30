"""
Tests for scientific method workflow: iterative refinement and peer review simulation.

Tests cover:
- Iterative hypothesis refinement
- Experimental design iteration
- Result-driven hypothesis updates
- Peer review simulation
- Reproducibility checks
- Scientific rigor validation
"""

import pytest
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum

# Import from other test modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from test_hypothesis_generation import Hypothesis, HypothesisGenerator, HypothesisStatus
from test_experiment_design import ExperimentDesigner, ExperimentResult
from test_scientist_e2e import ResultAnalyzer, ConclusionType, ScientificConclusion


class ReviewStatus(Enum):
    """Peer review status."""
    PENDING = "pending"
    APPROVED = "approved"
    REVISIONS_REQUIRED = "revisions_required"
    REJECTED = "rejected"


@dataclass
class PeerReview:
    """Represents a peer review."""
    reviewer_id: str
    hypothesis_id: str
    status: ReviewStatus
    comments: List[str]
    methodology_score: float
    statistical_rigor_score: float
    reproducibility_score: float
    overall_score: float


class PeerReviewSimulator:
    """Simulates peer review process for scientific research."""

    def __init__(self):
        self.reviews: List[PeerReview] = []

    def review_hypothesis(
        self,
        hypothesis: Hypothesis,
        experiment_design: Any,
        results: ExperimentResult
    ) -> PeerReview:
        """Conduct peer review of hypothesis and experimental work."""

        comments = []
        methodology_score = 0.0
        statistical_rigor_score = 0.0
        reproducibility_score = 0.0

        # Review methodology
        if experiment_design.control_group:
            methodology_score += 0.3
        else:
            comments.append("Missing control group")

        if len(experiment_design.treatment_groups) >= 2:
            methodology_score += 0.3
        else:
            comments.append("Insufficient treatment groups")

        if experiment_design.sample_size >= 30:
            methodology_score += 0.4
        else:
            comments.append("Sample size too small")

        # Review statistical rigor
        if results.statistical_significance < 0.05:
            statistical_rigor_score += 0.5
        else:
            comments.append("Statistical significance not achieved")

        if results.effect_size > 0.2:
            statistical_rigor_score += 0.3
        else:
            comments.append("Effect size too small")

        if results.confidence_interval[0] > 0:
            statistical_rigor_score += 0.2
        else:
            comments.append("Confidence interval includes zero")

        # Review reproducibility
        if experiment_design.independent_variables:
            reproducibility_score += 0.3

        if experiment_design.dependent_variables:
            reproducibility_score += 0.3

        if len(experiment_design.validation_errors) == 0:
            reproducibility_score += 0.4
        else:
            comments.append("Validation errors present")

        # Calculate overall score
        overall_score = (
            0.4 * methodology_score +
            0.4 * statistical_rigor_score +
            0.2 * reproducibility_score
        )

        # Determine status
        if overall_score >= 0.7:
            status = ReviewStatus.APPROVED
        elif overall_score >= 0.5:
            status = ReviewStatus.REVISIONS_REQUIRED
            comments.append("Revisions required to improve rigor")
        else:
            status = ReviewStatus.REJECTED
            comments.append("Insufficient scientific rigor")

        review = PeerReview(
            reviewer_id="reviewer_1",
            hypothesis_id=hypothesis.id,
            status=status,
            comments=comments,
            methodology_score=methodology_score,
            statistical_rigor_score=statistical_rigor_score,
            reproducibility_score=reproducibility_score,
            overall_score=overall_score
        )

        self.reviews.append(review)
        return review

    def multi_reviewer_consensus(
        self,
        reviews: List[PeerReview]
    ) -> ReviewStatus:
        """Determine consensus from multiple reviews."""
        if not reviews:
            return ReviewStatus.PENDING

        approved = sum(1 for r in reviews if r.status == ReviewStatus.APPROVED)
        rejected = sum(1 for r in reviews if r.status == ReviewStatus.REJECTED)

        if approved > len(reviews) / 2:
            return ReviewStatus.APPROVED
        elif rejected > len(reviews) / 2:
            return ReviewStatus.REJECTED
        else:
            return ReviewStatus.REVISIONS_REQUIRED


class IterativeRefinementEngine:
    """Manages iterative hypothesis refinement based on experimental results."""

    def __init__(self):
        self.hypothesis_generator = HypothesisGenerator()
        self.experiment_designer = ExperimentDesigner()
        self.result_analyzer = ResultAnalyzer()
        self.iteration_history: List[Dict[str, Any]] = []

    async def refine_iteratively(
        self,
        initial_hypothesis: Hypothesis,
        max_iterations: int = 5,
        convergence_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """Iteratively refine hypothesis until convergence or max iterations."""

        current_hypothesis = initial_hypothesis
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Design experiment
            experiment = self.experiment_designer.design_experiment(
                hypothesis_id=current_hypothesis.id,
                hypothesis_statement=current_hypothesis.statement,
                independent_var=current_hypothesis.independent_variable,
                dependent_var=current_hypothesis.dependent_variable
            )

            # Validate and execute
            self.experiment_designer.validate_design(experiment.id)
            result = await self.experiment_designer.execute_experiment(experiment.id)

            # Analyze results
            conclusion = self.result_analyzer.analyze_results(result, current_hypothesis)

            # Record iteration
            self.iteration_history.append({
                "iteration": iteration,
                "hypothesis": current_hypothesis,
                "experiment": experiment,
                "result": result,
                "conclusion": conclusion
            })

            # Check convergence
            if conclusion.confidence >= convergence_threshold:
                if conclusion.conclusion_type == ConclusionType.SUPPORTED:
                    break

            # Refine hypothesis based on results
            if conclusion.conclusion_type == ConclusionType.INCONCLUSIVE:
                # Refine hypothesis
                self.hypothesis_generator.refine_hypothesis(
                    current_hypothesis.id,
                    [f"Iteration {iteration}: {conclusion.evidence_summary}"]
                )

            elif conclusion.conclusion_type == ConclusionType.NOT_SUPPORTED:
                # Generate alternative hypothesis
                new_hypotheses = self.hypothesis_generator.generate_from_observations(
                    [f"Alternative to: {current_hypothesis.statement}"],
                    domain="refined"
                )
                if new_hypotheses:
                    current_hypothesis = new_hypotheses[0]

        return {
            "final_hypothesis": current_hypothesis,
            "total_iterations": iteration,
            "converged": iteration < max_iterations,
            "iteration_history": self.iteration_history
        }

    def analyze_convergence(self) -> Dict[str, Any]:
        """Analyze convergence pattern across iterations."""
        if not self.iteration_history:
            return {"converged": False, "pattern": "no_data"}

        confidences = [h["conclusion"].confidence for h in self.iteration_history]

        # Check if confidence is increasing
        increasing = all(
            confidences[i] <= confidences[i + 1]
            for i in range(len(confidences) - 1)
        )

        # Calculate convergence rate
        if len(confidences) > 1:
            convergence_rate = (confidences[-1] - confidences[0]) / len(confidences)
        else:
            convergence_rate = 0.0

        return {
            "converged": confidences[-1] >= 0.8,
            "pattern": "increasing" if increasing else "fluctuating",
            "convergence_rate": convergence_rate,
            "final_confidence": confidences[-1],
            "iterations_required": len(confidences)
        }


# ============================================================================
# UNIT TESTS
# ============================================================================

class TestPeerReviewSimulator:
    """Test peer review simulation."""

    def test_review_high_quality_research(self):
        """Test reviewing high-quality research."""
        reviewer = PeerReviewSimulator()

        hypothesis = Hypothesis(
            id="H1",
            statement="High quality hypothesis",
            independent_variable="iv",
            dependent_variable="dv",
            expected_effect="positive"
        )

        # Create high-quality experiment design
        designer = ExperimentDesigner()
        experiment = designer.design_experiment(
            hypothesis_id="H1",
            hypothesis_statement=hypothesis.statement,
            independent_var="iv",
            dependent_var="dv"
        )
        designer.validate_design(experiment.id)

        # Create strong results
        result = ExperimentResult(
            experiment_id=experiment.id,
            hypothesis_id="H1",
            control_results={"dv": 0.5},
            treatment_results=[{"dv": 0.7}, {"dv": 0.75}],
            statistical_significance=0.01,
            effect_size=0.5,
            confidence_interval=(0.3, 0.7)
        )

        review = reviewer.review_hypothesis(hypothesis, experiment, result)

        assert review.status == ReviewStatus.APPROVED
        assert review.overall_score >= 0.7
        assert review.methodology_score > 0.5
        assert review.statistical_rigor_score > 0.5

    def test_review_low_quality_research(self):
        """Test reviewing low-quality research."""
        reviewer = PeerReviewSimulator()

        hypothesis = Hypothesis(
            id="H1",
            statement="Low quality hypothesis",
            independent_variable="iv",
            dependent_variable="dv",
            expected_effect="positive"
        )

        # Create poor experiment design
        from test_experiment_design import ExperimentDesign, ExperimentStatus
        experiment = ExperimentDesign(
            id="EXP1",
            hypothesis_id="H1",
            independent_variables=[],
            dependent_variables=[],
            control_group={},
            treatment_groups=[],
            sample_size=10,
            duration="1 day",
            status=ExperimentStatus.DESIGNED
        )

        # Create weak results
        result = ExperimentResult(
            experiment_id="EXP1",
            hypothesis_id="H1",
            control_results={"dv": 0.5},
            treatment_results=[{"dv": 0.51}],
            statistical_significance=0.15,
            effect_size=0.05,
            confidence_interval=(-0.1, 0.2)
        )

        review = reviewer.review_hypothesis(hypothesis, experiment, result)

        assert review.status in [ReviewStatus.REJECTED, ReviewStatus.REVISIONS_REQUIRED]
        assert review.overall_score < 0.7
        assert len(review.comments) > 0

    def test_multi_reviewer_consensus(self):
        """Test consensus from multiple reviewers."""
        reviewer = PeerReviewSimulator()

        # Create multiple reviews
        reviews = [
            PeerReview(
                reviewer_id="R1",
                hypothesis_id="H1",
                status=ReviewStatus.APPROVED,
                comments=[],
                methodology_score=0.8,
                statistical_rigor_score=0.9,
                reproducibility_score=0.8,
                overall_score=0.85
            ),
            PeerReview(
                reviewer_id="R2",
                hypothesis_id="H1",
                status=ReviewStatus.APPROVED,
                comments=[],
                methodology_score=0.7,
                statistical_rigor_score=0.8,
                reproducibility_score=0.7,
                overall_score=0.75
            ),
            PeerReview(
                reviewer_id="R3",
                hypothesis_id="H1",
                status=ReviewStatus.REVISIONS_REQUIRED,
                comments=["Minor revisions needed"],
                methodology_score=0.6,
                statistical_rigor_score=0.7,
                reproducibility_score=0.6,
                overall_score=0.65
            )
        ]

        consensus = reviewer.multi_reviewer_consensus(reviews)

        assert consensus == ReviewStatus.APPROVED  # Majority approved


class TestIterativeRefinement:
    """Test iterative hypothesis refinement."""

    @pytest.mark.asyncio
    async def test_iterative_refinement_convergence(self):
        """Test iterative refinement converges."""
        engine = IterativeRefinementEngine()

        initial_hypothesis = Hypothesis(
            id="H1",
            statement="Initial hypothesis about performance",
            independent_variable="factor",
            dependent_variable="performance",
            expected_effect="positive"
        )

        result = await engine.refine_iteratively(
            initial_hypothesis,
            max_iterations=3,
            convergence_threshold=0.7
        )

        assert result["total_iterations"] <= 3
        assert len(result["iteration_history"]) > 0
        assert result["final_hypothesis"] is not None

    @pytest.mark.asyncio
    async def test_refinement_improves_confidence(self):
        """Test that refinement improves confidence over iterations."""
        engine = IterativeRefinementEngine()

        initial_hypothesis = Hypothesis(
            id="H1",
            statement="Hypothesis to refine",
            independent_variable="iv",
            dependent_variable="dv",
            expected_effect="positive",
            confidence=0.3
        )

        result = await engine.refine_iteratively(
            initial_hypothesis,
            max_iterations=3
        )

        # Check if confidence improved
        if len(result["iteration_history"]) > 1:
            first_confidence = result["iteration_history"][0]["conclusion"].confidence
            last_confidence = result["iteration_history"][-1]["conclusion"].confidence

            # Confidence should not decrease significantly
            assert last_confidence >= first_confidence - 0.1

    @pytest.mark.asyncio
    async def test_convergence_analysis(self):
        """Test convergence pattern analysis."""
        engine = IterativeRefinementEngine()

        initial_hypothesis = Hypothesis(
            id="H1",
            statement="Test hypothesis",
            independent_variable="iv",
            dependent_variable="dv",
            expected_effect="positive"
        )

        await engine.refine_iteratively(initial_hypothesis, max_iterations=3)

        analysis = engine.analyze_convergence()

        assert "converged" in analysis
        assert "pattern" in analysis
        assert "convergence_rate" in analysis
        assert "final_confidence" in analysis
        assert "iterations_required" in analysis


class TestScientificRigor:
    """Test scientific rigor validation."""

    def test_reproducibility_check(self):
        """Test reproducibility validation."""
        designer = ExperimentDesigner()

        experiment = designer.design_experiment(
            hypothesis_id="H1",
            hypothesis_statement="Test",
            independent_var="iv",
            dependent_var="dv"
        )

        # Validate design
        is_valid = designer.validate_design(experiment.id)

        # Check reproducibility criteria
        reproducible = (
            is_valid and
            len(experiment.independent_variables) > 0 and
            len(experiment.dependent_variables) > 0 and
            experiment.sample_size >= 30
        )

        assert reproducible

    def test_statistical_power_validation(self):
        """Test statistical power validation."""
        designer = ExperimentDesigner()

        experiment = designer.design_experiment(
            hypothesis_id="H1",
            hypothesis_statement="Test",
            independent_var="iv",
            dependent_var="dv"
        )

        # Check sample size for adequate power
        # Rule of thumb: 30+ per group
        min_required = len(experiment.treatment_groups) * 30

        assert experiment.sample_size >= min_required

    def test_control_group_requirement(self):
        """Test control group requirement."""
        designer = ExperimentDesigner()

        experiment = designer.design_experiment(
            hypothesis_id="H1",
            hypothesis_statement="Test",
            independent_var="iv",
            dependent_var="dv"
        )

        # Must have control group
        assert experiment.control_group is not None
        assert "name" in experiment.control_group
        assert experiment.control_group["name"] == "control"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestScientificMethodIntegration:
    """Integration tests for complete scientific method workflow."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_scientific_method_cycle(self):
        """Test complete scientific method cycle with peer review."""
        # 1. Generate hypothesis
        generator = HypothesisGenerator()
        hypotheses = generator.generate_from_observations([
            "Observation about system behavior"
        ])
        hypothesis = hypotheses[0]

        # 2. Design experiment
        designer = ExperimentDesigner()
        experiment = designer.design_experiment(
            hypothesis_id=hypothesis.id,
            hypothesis_statement=hypothesis.statement,
            independent_var=hypothesis.independent_variable,
            dependent_var=hypothesis.dependent_variable
        )

        # 3. Validate design
        is_valid = designer.validate_design(experiment.id)
        assert is_valid

        # 4. Execute experiment
        result = await designer.execute_experiment(experiment.id)

        # 5. Analyze results
        analyzer = ResultAnalyzer()
        conclusion = analyzer.analyze_results(result, hypothesis)

        # 6. Peer review
        reviewer = PeerReviewSimulator()
        review = reviewer.review_hypothesis(hypothesis, experiment, result)

        # Verify complete cycle
        assert hypothesis is not None
        assert experiment is not None
        assert result is not None
        assert conclusion is not None
        assert review is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_iterative_refinement_with_peer_review(self):
        """Test iterative refinement with peer review at each iteration."""
        engine = IterativeRefinementEngine()
        reviewer = PeerReviewSimulator()

        initial_hypothesis = Hypothesis(
            id="H1",
            statement="Initial hypothesis",
            independent_variable="iv",
            dependent_variable="dv",
            expected_effect="positive"
        )

        # Run refinement
        result = await engine.refine_iteratively(
            initial_hypothesis,
            max_iterations=2
        )

        # Review each iteration
        reviews = []
        for iteration_data in result["iteration_history"]:
            review = reviewer.review_hypothesis(
                iteration_data["hypothesis"],
                iteration_data["experiment"],
                iteration_data["result"]
            )
            reviews.append(review)

        # At least one review should exist
        assert len(reviews) > 0

        # Check if quality improved over iterations
        if len(reviews) > 1:
            first_score = reviews[0].overall_score
            last_score = reviews[-1].overall_score

            # Quality should not decrease significantly
            assert last_score >= first_score - 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
