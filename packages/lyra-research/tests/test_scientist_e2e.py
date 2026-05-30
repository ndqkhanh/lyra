"""
End-to-end tests for complete scientist research workflows.

Tests cover:
- Complete hypothesis → experiment → conclusion workflow
- Multi-hypothesis comparison
- Iterative scientific discovery
- Result analysis and synthesis
- Peer review simulation
"""

import pytest
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum


# Import from other test modules
import sys
from pathlib import Path

# Add tests directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from test_hypothesis_generation import (
    Hypothesis,
    HypothesisGenerator,
    HypothesisStatus
)
from test_experiment_design import (
    ExperimentDesigner,
    ExperimentResult,
    ExperimentStatus
)


class ConclusionType(Enum):
    """Type of scientific conclusion."""
    SUPPORTED = "supported"
    NOT_SUPPORTED = "not_supported"
    INCONCLUSIVE = "inconclusive"
    REQUIRES_FURTHER_STUDY = "requires_further_study"


@dataclass
class ScientificConclusion:
    """Represents a scientific conclusion."""
    hypothesis_id: str
    conclusion_type: ConclusionType
    confidence: float
    evidence_summary: str
    limitations: List[str]
    future_work: List[str]
    statistical_support: Dict[str, float]


class ResultAnalyzer:
    """Analyzes experiment results and draws conclusions."""

    def analyze_results(
        self,
        result: ExperimentResult,
        hypothesis: Hypothesis
    ) -> ScientificConclusion:
        """Analyze experiment results and draw conclusions."""

        # Determine conclusion type based on statistical significance
        if result.statistical_significance < 0.05:
            if result.effect_size > 0.2:
                conclusion_type = ConclusionType.SUPPORTED
                confidence = 0.9
            else:
                conclusion_type = ConclusionType.SUPPORTED
                confidence = 0.7
        elif result.statistical_significance < 0.1:
            conclusion_type = ConclusionType.INCONCLUSIVE
            confidence = 0.5
        else:
            conclusion_type = ConclusionType.NOT_SUPPORTED
            confidence = 0.3

        # Generate evidence summary
        evidence_summary = self._generate_evidence_summary(result, hypothesis)

        # Identify limitations
        limitations = self._identify_limitations(result)

        # Suggest future work
        future_work = self._suggest_future_work(result, conclusion_type)

        return ScientificConclusion(
            hypothesis_id=hypothesis.id,
            conclusion_type=conclusion_type,
            confidence=confidence,
            evidence_summary=evidence_summary,
            limitations=limitations,
            future_work=future_work,
            statistical_support={
                "p_value": result.statistical_significance,
                "effect_size": result.effect_size,
                "ci_lower": result.confidence_interval[0],
                "ci_upper": result.confidence_interval[1]
            }
        )

    def _generate_evidence_summary(
        self,
        result: ExperimentResult,
        hypothesis: Hypothesis
    ) -> str:
        """Generate evidence summary."""
        control_value = list(result.control_results.values())[0]
        treatment_values = [list(t.values())[0] for t in result.treatment_results]
        avg_treatment = sum(treatment_values) / len(treatment_values)

        improvement = ((avg_treatment - control_value) / control_value) * 100

        return (
            f"Hypothesis {hypothesis.id}: {hypothesis.statement}. "
            f"Results show {improvement:.1f}% improvement in treatment groups "
            f"(p={result.statistical_significance:.3f}, d={result.effect_size:.2f})."
        )

    def _identify_limitations(self, result: ExperimentResult) -> List[str]:
        """Identify study limitations."""
        limitations = []

        if result.effect_size < 0.3:
            limitations.append("Small effect size may limit practical significance")

        if result.statistical_significance > 0.01:
            limitations.append("Moderate statistical significance suggests need for replication")

        if not result.raw_data:
            limitations.append("Limited raw data available for detailed analysis")

        return limitations

    def _suggest_future_work(
        self,
        result: ExperimentResult,
        conclusion_type: ConclusionType
    ) -> List[str]:
        """Suggest future research directions."""
        suggestions = []

        if conclusion_type == ConclusionType.SUPPORTED:
            suggestions.append("Replicate study with larger sample size")
            suggestions.append("Test generalization to different domains")

        elif conclusion_type == ConclusionType.INCONCLUSIVE:
            suggestions.append("Increase statistical power with larger sample")
            suggestions.append("Refine experimental design to reduce variance")

        else:
            suggestions.append("Explore alternative hypotheses")
            suggestions.append("Investigate confounding variables")

        return suggestions

    def synthesize_conclusions(
        self,
        conclusions: List[ScientificConclusion]
    ) -> Dict[str, Any]:
        """Synthesize multiple conclusions into overall findings."""
        if not conclusions:
            return {
                "total_hypotheses": 0,
                "supported": 0,
                "not_supported": 0,
                "inconclusive": 0,
                "average_confidence": 0.0,
                "key_findings": [],
                "limitations": [],
                "future_directions": []
            }

        supported = [c for c in conclusions if c.conclusion_type == ConclusionType.SUPPORTED]
        not_supported = [c for c in conclusions if c.conclusion_type == ConclusionType.NOT_SUPPORTED]
        inconclusive = [c for c in conclusions if c.conclusion_type == ConclusionType.INCONCLUSIVE]

        avg_confidence = sum(c.confidence for c in conclusions) / len(conclusions)

        return {
            "total_hypotheses": len(conclusions),
            "supported": len(supported),
            "not_supported": len(not_supported),
            "inconclusive": len(inconclusive),
            "average_confidence": avg_confidence,
            "key_findings": [c.evidence_summary for c in supported],
            "limitations": list(set(lim for c in conclusions for lim in c.limitations)),
            "future_directions": list(set(fw for c in conclusions for fw in c.future_work))
        }


class ScientistWorkflow:
    """Orchestrates complete scientist research workflow."""

    def __init__(self):
        self.hypothesis_generator = HypothesisGenerator()
        self.experiment_designer = ExperimentDesigner()
        self.result_analyzer = ResultAnalyzer()

    async def run_complete_workflow(
        self,
        observations: List[str],
        domain: str = "general"
    ) -> Dict[str, Any]:
        """Run complete scientific workflow from observations to conclusions."""

        # 1. Generate hypotheses
        hypotheses = self.hypothesis_generator.generate_from_observations(
            observations, domain
        )

        # 2. Design experiments
        experiments = []
        for h in hypotheses:
            exp = self.experiment_designer.design_experiment(
                hypothesis_id=h.id,
                hypothesis_statement=h.statement,
                independent_var=h.independent_variable,
                dependent_var=h.dependent_variable
            )
            experiments.append(exp)

        # 3. Validate and execute experiments
        results = []
        for exp in experiments:
            self.experiment_designer.validate_design(exp.id)
            result = await self.experiment_designer.execute_experiment(exp.id)
            results.append(result)

        # 4. Analyze results and draw conclusions
        conclusions = []
        for result, hypothesis in zip(results, hypotheses):
            conclusion = self.result_analyzer.analyze_results(result, hypothesis)
            conclusions.append(conclusion)

        # 5. Synthesize overall findings
        synthesis = self.result_analyzer.synthesize_conclusions(conclusions)

        return {
            "hypotheses": hypotheses,
            "experiments": experiments,
            "results": results,
            "conclusions": conclusions,
            "synthesis": synthesis
        }

    async def iterative_refinement(
        self,
        initial_hypothesis: Hypothesis,
        max_iterations: int = 3
    ) -> List[ScientificConclusion]:
        """Iteratively refine hypothesis based on experimental results."""

        conclusions = []
        current_hypothesis = initial_hypothesis

        for iteration in range(max_iterations):
            # Design and execute experiment
            exp = self.experiment_designer.design_experiment(
                hypothesis_id=current_hypothesis.id,
                hypothesis_statement=current_hypothesis.statement,
                independent_var=current_hypothesis.independent_variable,
                dependent_var=current_hypothesis.dependent_variable
            )

            self.experiment_designer.validate_design(exp.id)
            result = await self.experiment_designer.execute_experiment(exp.id)

            # Analyze results
            conclusion = self.result_analyzer.analyze_results(result, current_hypothesis)
            conclusions.append(conclusion)

            # Refine hypothesis if needed
            if conclusion.conclusion_type == ConclusionType.INCONCLUSIVE:
                # Refine hypothesis based on results
                self.hypothesis_generator.refine_hypothesis(
                    current_hypothesis.id,
                    [f"Iteration {iteration + 1} results"]
                )
            elif conclusion.conclusion_type == ConclusionType.SUPPORTED:
                # Hypothesis confirmed, stop iteration
                break

        return conclusions


# ============================================================================
# E2E TESTS
# ============================================================================

class TestScientistE2EWorkflow:
    """End-to-end tests for complete scientist research workflows."""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_hypothesis_to_conclusion_workflow(self):
        """Test complete hypothesis → experiment → conclusion workflow."""
        workflow = ScientistWorkflow()

        observations = [
            "Increasing model size improves accuracy on benchmarks",
            "Multi-agent systems reduce task completion time"
        ]

        results = await workflow.run_complete_workflow(observations, domain="AI")

        # Verify all stages completed
        assert len(results["hypotheses"]) == 2
        assert len(results["experiments"]) == 2
        assert len(results["results"]) == 2
        assert len(results["conclusions"]) == 2

        # Verify synthesis
        synthesis = results["synthesis"]
        assert synthesis["total_hypotheses"] == 2
        assert synthesis["average_confidence"] > 0.0
        assert len(synthesis["key_findings"]) > 0

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_multi_hypothesis_comparison(self):
        """Test comparing multiple competing hypotheses."""
        workflow = ScientistWorkflow()

        observations = [
            "Method A improves accuracy by 10%",
            "Method B improves accuracy by 15%",
            "Method C improves accuracy by 5%"
        ]

        results = await workflow.run_complete_workflow(observations, domain="ML")

        # All hypotheses should be tested
        assert len(results["hypotheses"]) == 3

        # Compare conclusions
        conclusions = results["conclusions"]
        supported = [c for c in conclusions if c.conclusion_type == ConclusionType.SUPPORTED]

        # At least some should be supported
        assert len(supported) > 0

        # Verify synthesis identifies best approach
        synthesis = results["synthesis"]
        assert synthesis["supported"] > 0

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_iterative_scientific_discovery(self):
        """Test iterative scientific discovery process."""
        workflow = ScientistWorkflow()

        # Initial hypothesis
        initial_hypothesis = Hypothesis(
            id="H1",
            statement="Increasing training data improves model performance",
            independent_variable="training_data_size",
            dependent_variable="model_performance",
            expected_effect="positive"
        )

        # Run iterative refinement
        conclusions = await workflow.iterative_refinement(
            initial_hypothesis,
            max_iterations=3
        )

        # Should have at least one conclusion
        assert len(conclusions) > 0

        # Should converge or reach max iterations
        assert len(conclusions) <= 3

        # Final conclusion should have high confidence if supported
        final_conclusion = conclusions[-1]
        if final_conclusion.conclusion_type == ConclusionType.SUPPORTED:
            assert final_conclusion.confidence > 0.6

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_result_analysis_and_synthesis(self):
        """Test comprehensive result analysis and synthesis."""
        analyzer = ResultAnalyzer()

        # Create mock results
        result1 = ExperimentResult(
            experiment_id="EXP1",
            hypothesis_id="H1",
            control_results={"accuracy": 0.65},
            treatment_results=[{"accuracy": 0.75}, {"accuracy": 0.80}],
            statistical_significance=0.02,
            effect_size=0.35,
            confidence_interval=(0.20, 0.50)
        )

        result2 = ExperimentResult(
            experiment_id="EXP2",
            hypothesis_id="H2",
            control_results={"latency": 100.0},
            treatment_results=[{"latency": 90.0}, {"latency": 85.0}],
            statistical_significance=0.01,
            effect_size=0.45,
            confidence_interval=(0.30, 0.60)
        )

        hypothesis1 = Hypothesis(
            id="H1",
            statement="Treatment improves accuracy",
            independent_variable="treatment",
            dependent_variable="accuracy",
            expected_effect="positive"
        )

        hypothesis2 = Hypothesis(
            id="H2",
            statement="Optimization reduces latency",
            independent_variable="optimization",
            dependent_variable="latency",
            expected_effect="negative"
        )

        # Analyze results
        conclusion1 = analyzer.analyze_results(result1, hypothesis1)
        conclusion2 = analyzer.analyze_results(result2, hypothesis2)

        # Both should be supported
        assert conclusion1.conclusion_type == ConclusionType.SUPPORTED
        assert conclusion2.conclusion_type == ConclusionType.SUPPORTED

        # Synthesize
        synthesis = analyzer.synthesize_conclusions([conclusion1, conclusion2])

        assert synthesis["total_hypotheses"] == 2
        assert synthesis["supported"] == 2
        assert synthesis["average_confidence"] > 0.7

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_peer_review_simulation(self):
        """Test peer review simulation workflow."""
        workflow = ScientistWorkflow()

        observations = [
            "Novel architecture improves performance"
        ]

        results = await workflow.run_complete_workflow(observations)

        # Extract conclusion
        conclusion = results["conclusions"][0]

        # Simulate peer review checks
        peer_review_passed = True

        # Check 1: Statistical significance
        if conclusion.statistical_support["p_value"] > 0.05:
            peer_review_passed = False

        # Check 2: Effect size
        if conclusion.statistical_support["effect_size"] < 0.2:
            peer_review_passed = False

        # Check 3: Confidence
        if conclusion.confidence < 0.6:
            peer_review_passed = False

        # Check 4: Limitations acknowledged
        if len(conclusion.limitations) == 0:
            peer_review_passed = False

        # Should pass basic peer review
        assert peer_review_passed or conclusion.conclusion_type != ConclusionType.SUPPORTED


class TestScientificMethodWorkflow:
    """Test scientific method workflow components."""

    @pytest.mark.e2e
    def test_hypothesis_generation_quality(self):
        """Test quality of generated hypotheses."""
        generator = HypothesisGenerator()

        observations = [
            "Larger models with more parameters achieve higher accuracy on benchmarks",
            "Fine-tuning on domain-specific data improves task performance"
        ]

        hypotheses = generator.generate_from_observations(observations, domain="ML")

        # All hypotheses should be testable
        assert all(h.testability_score > 0.3 for h in hypotheses)

        # Should have reasonable novelty
        assert all(h.novelty_score > 0.2 for h in hypotheses)

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_experiment_execution_reliability(self):
        """Test reliability of experiment execution."""
        designer = ExperimentDesigner()

        # Execute multiple times with fresh experiments
        results = []
        for i in range(3):
            # Design experiment
            exp = designer.design_experiment(
                hypothesis_id=f"H{i+1}",
                hypothesis_statement="Test hypothesis",
                independent_var="factor",
                dependent_var="metric"
            )

            designer.validate_design(exp.id)
            result = await designer.execute_experiment(exp.id)
            results.append(result)

        # All executions should complete
        assert len(results) == 3

        # Results should be consistent (simulated)
        assert all(r.statistical_significance < 0.1 for r in results)

    @pytest.mark.e2e
    def test_conclusion_synthesis_completeness(self):
        """Test completeness of conclusion synthesis."""
        analyzer = ResultAnalyzer()

        # Create diverse conclusions
        conclusions = [
            ScientificConclusion(
                hypothesis_id="H1",
                conclusion_type=ConclusionType.SUPPORTED,
                confidence=0.9,
                evidence_summary="Strong evidence",
                limitations=["Limited sample"],
                future_work=["Replicate study"],
                statistical_support={"p_value": 0.01, "effect_size": 0.5}
            ),
            ScientificConclusion(
                hypothesis_id="H2",
                conclusion_type=ConclusionType.NOT_SUPPORTED,
                confidence=0.3,
                evidence_summary="Weak evidence",
                limitations=["High variance"],
                future_work=["Explore alternatives"],
                statistical_support={"p_value": 0.15, "effect_size": 0.1}
            ),
            ScientificConclusion(
                hypothesis_id="H3",
                conclusion_type=ConclusionType.INCONCLUSIVE,
                confidence=0.5,
                evidence_summary="Mixed evidence",
                limitations=["Small effect"],
                future_work=["Increase power"],
                statistical_support={"p_value": 0.08, "effect_size": 0.2}
            )
        ]

        synthesis = analyzer.synthesize_conclusions(conclusions)

        # Should have all required fields
        assert "total_hypotheses" in synthesis
        assert "supported" in synthesis
        assert "not_supported" in synthesis
        assert "inconclusive" in synthesis
        assert "average_confidence" in synthesis
        assert "key_findings" in synthesis
        assert "limitations" in synthesis
        assert "future_directions" in synthesis

        # Counts should be correct
        assert synthesis["total_hypotheses"] == 3
        assert synthesis["supported"] == 1
        assert synthesis["not_supported"] == 1
        assert synthesis["inconclusive"] == 1


class TestScientistWorkflowEdgeCases:
    """Test edge cases in scientist workflows."""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_no_observations(self):
        """Test workflow with no observations."""
        workflow = ScientistWorkflow()

        results = await workflow.run_complete_workflow([])

        assert len(results["hypotheses"]) == 0
        assert len(results["experiments"]) == 0

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_single_observation(self):
        """Test workflow with single observation."""
        workflow = ScientistWorkflow()

        results = await workflow.run_complete_workflow(
            ["Single observation about performance"]
        )

        assert len(results["hypotheses"]) == 1
        assert len(results["experiments"]) == 1
        assert len(results["conclusions"]) == 1

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_inconclusive_results_handling(self):
        """Test handling of inconclusive experimental results."""
        analyzer = ResultAnalyzer()

        # Create inconclusive result
        result = ExperimentResult(
            experiment_id="EXP1",
            hypothesis_id="H1",
            control_results={"metric": 0.5},
            treatment_results=[{"metric": 0.52}],
            statistical_significance=0.08,  # Not significant
            effect_size=0.1,  # Small effect
            confidence_interval=(0.0, 0.2)
        )

        hypothesis = Hypothesis(
            id="H1",
            statement="Test hypothesis",
            independent_variable="iv",
            dependent_variable="dv",
            expected_effect="positive"
        )

        conclusion = analyzer.analyze_results(result, hypothesis)

        assert conclusion.conclusion_type == ConclusionType.INCONCLUSIVE
        assert len(conclusion.future_work) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
