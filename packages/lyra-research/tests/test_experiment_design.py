"""
Integration tests for experiment design and execution in scientist research workflows.

Tests cover:
- Experiment planning for hypotheses
- Control group design
- Variable selection (IV/DV)
- Experiment validation
- Feasibility checks
- Experiment execution simulation
- Result collection
"""

import pytest
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class ExperimentStatus(Enum):
    """Status of an experiment."""
    DESIGNED = "designed"
    VALIDATED = "validated"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ExperimentDesign:
    """Represents an experiment design."""
    id: str
    hypothesis_id: str
    independent_variables: List[str]
    dependent_variables: List[str]
    control_group: Dict[str, Any]
    treatment_groups: List[Dict[str, Any]]
    sample_size: int
    duration: str
    status: ExperimentStatus = ExperimentStatus.DESIGNED
    feasibility_score: float = 0.0
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class ExperimentResult:
    """Represents experiment results."""
    experiment_id: str
    hypothesis_id: str
    control_results: Dict[str, float]
    treatment_results: List[Dict[str, float]]
    statistical_significance: float
    effect_size: float
    confidence_interval: tuple
    raw_data: List[Dict[str, Any]] = field(default_factory=list)


class ExperimentDesigner:
    """Designs and validates experiments for hypothesis testing."""

    def __init__(self):
        self.experiments: List[ExperimentDesign] = []
        self.next_id = 1

    def design_experiment(
        self,
        hypothesis_id: str,
        hypothesis_statement: str,
        independent_var: str,
        dependent_var: str
    ) -> ExperimentDesign:
        """Design an experiment to test a hypothesis."""

        # Extract variables from hypothesis
        iv_values = self._generate_iv_values(independent_var)

        # Design control group
        control = {
            "name": "control",
            independent_var: iv_values[0],  # Baseline value
            "description": f"Control group with baseline {independent_var}"
        }

        # Design treatment groups
        treatments = []
        for i, value in enumerate(iv_values[1:], 1):
            treatments.append({
                "name": f"treatment_{i}",
                independent_var: value,
                "description": f"Treatment group {i} with {independent_var}={value}"
            })

        # Calculate sample size
        sample_size = self._calculate_sample_size(len(treatments))

        experiment = ExperimentDesign(
            id=f"EXP{self.next_id}",
            hypothesis_id=hypothesis_id,
            independent_variables=[independent_var],
            dependent_variables=[dependent_var],
            control_group=control,
            treatment_groups=treatments,
            sample_size=sample_size,
            duration="1 week"
        )

        self.next_id += 1
        self.experiments.append(experiment)

        return experiment

    def _generate_iv_values(self, variable: str) -> List[Any]:
        """Generate values for independent variable."""
        # Simple heuristic based on variable name
        if "size" in variable.lower() or "count" in variable.lower():
            return [10, 50, 100, 200]
        elif "rate" in variable.lower() or "ratio" in variable.lower():
            return [0.1, 0.3, 0.5, 0.7]
        elif "temperature" in variable.lower():
            return [0.0, 0.3, 0.7, 1.0]
        else:
            return ["low", "medium", "high", "very_high"]

    def _calculate_sample_size(self, num_groups: int) -> int:
        """Calculate required sample size."""
        # Simple power analysis: 30 per group minimum
        return max(30, num_groups * 30)

    def design_control_group(
        self,
        experiment_id: str,
        baseline_conditions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Design control group for experiment."""
        experiment = self._get_experiment(experiment_id)

        if experiment is None:
            raise ValueError(f"Experiment {experiment_id} not found")

        # Update control group with baseline conditions
        experiment.control_group.update(baseline_conditions)

        return experiment.control_group

    def select_variables(
        self,
        hypothesis_statement: str
    ) -> tuple[List[str], List[str]]:
        """Select independent and dependent variables from hypothesis."""
        # Simple extraction based on keywords
        iv_keywords = ["increase", "decrease", "change", "vary", "manipulate"]
        dv_keywords = ["accuracy", "performance", "score", "rate", "time"]

        words = hypothesis_statement.lower().split()

        independent_vars = []
        dependent_vars = []

        for i, word in enumerate(words):
            if any(kw in word for kw in iv_keywords):
                # Next word might be the IV
                if i + 1 < len(words):
                    independent_vars.append(words[i + 1])

            if any(kw in word for kw in dv_keywords):
                dependent_vars.append(word)

        # Defaults if nothing found
        if not independent_vars:
            independent_vars = ["treatment"]
        if not dependent_vars:
            dependent_vars = ["outcome"]

        return independent_vars, dependent_vars

    def validate_design(self, experiment_id: str) -> bool:
        """Validate experiment design."""
        experiment = self._get_experiment(experiment_id)

        if experiment is None:
            raise ValueError(f"Experiment {experiment_id} not found")

        errors = []

        # Check control group
        if not experiment.control_group:
            errors.append("Missing control group")

        # Check treatment groups
        if not experiment.treatment_groups:
            errors.append("Missing treatment groups")

        # Check sample size
        if experiment.sample_size < 30:
            errors.append("Sample size too small (minimum 30)")

        # Check variables
        if not experiment.independent_variables:
            errors.append("Missing independent variables")

        if not experiment.dependent_variables:
            errors.append("Missing dependent variables")

        experiment.validation_errors = errors

        if not errors:
            experiment.status = ExperimentStatus.VALIDATED
            return True

        return False

    def check_feasibility(self, experiment_id: str) -> float:
        """Check experiment feasibility."""
        experiment = self._get_experiment(experiment_id)

        if experiment is None:
            raise ValueError(f"Experiment {experiment_id} not found")

        # Calculate feasibility score
        score = 1.0

        # Penalize large sample sizes
        if experiment.sample_size > 1000:
            score -= 0.3
        elif experiment.sample_size > 500:
            score -= 0.1

        # Penalize many treatment groups
        if len(experiment.treatment_groups) > 5:
            score -= 0.2

        # Penalize complex variables
        if len(experiment.independent_variables) > 3:
            score -= 0.2

        experiment.feasibility_score = max(0.0, score)

        return experiment.feasibility_score

    async def execute_experiment(
        self,
        experiment_id: str,
        simulation: bool = True
    ) -> ExperimentResult:
        """Execute experiment (simulated or real)."""
        experiment = self._get_experiment(experiment_id)

        if experiment is None:
            raise ValueError(f"Experiment {experiment_id} not found")

        if experiment.status != ExperimentStatus.VALIDATED:
            raise ValueError("Experiment must be validated before execution")

        experiment.status = ExperimentStatus.RUNNING

        # Simulate experiment execution
        await asyncio.sleep(0.1)  # Simulate execution time

        # Generate simulated results
        control_results = {
            experiment.dependent_variables[0]: 0.65  # Baseline performance
        }

        treatment_results = []
        for i, treatment in enumerate(experiment.treatment_groups):
            # Simulate improvement in treatment groups
            improvement = 0.05 * (i + 1)
            treatment_results.append({
                experiment.dependent_variables[0]: 0.65 + improvement
            })

        # Calculate statistics
        effect_size = 0.3  # Cohen's d
        significance = 0.03  # p-value

        result = ExperimentResult(
            experiment_id=experiment_id,
            hypothesis_id=experiment.hypothesis_id,
            control_results=control_results,
            treatment_results=treatment_results,
            statistical_significance=significance,
            effect_size=effect_size,
            confidence_interval=(0.15, 0.45)
        )

        experiment.status = ExperimentStatus.COMPLETED

        return result

    def collect_results(
        self,
        experiment_id: str,
        raw_data: List[Dict[str, Any]]
    ) -> ExperimentResult:
        """Collect and process experiment results."""
        experiment = self._get_experiment(experiment_id)

        if experiment is None:
            raise ValueError(f"Experiment {experiment_id} not found")

        # Process raw data
        control_data = [d for d in raw_data if d.get("group") == "control"]
        treatment_data = [d for d in raw_data if d.get("group") != "control"]

        # Calculate aggregated results
        control_results = self._aggregate_results(control_data, experiment.dependent_variables[0])
        treatment_results = self._aggregate_by_group(treatment_data, experiment.dependent_variables[0])

        result = ExperimentResult(
            experiment_id=experiment_id,
            hypothesis_id=experiment.hypothesis_id,
            control_results=control_results,
            treatment_results=treatment_results,
            statistical_significance=0.05,
            effect_size=0.25,
            confidence_interval=(0.1, 0.4),
            raw_data=raw_data
        )

        return result

    def _aggregate_results(self, data: List[Dict], metric: str) -> Dict[str, float]:
        """Aggregate results for a group."""
        if not data:
            return {metric: 0.0}

        values = [d.get(metric, 0.0) for d in data]
        return {metric: sum(values) / len(values)}

    def _aggregate_by_group(self, data: List[Dict], metric: str) -> List[Dict[str, float]]:
        """Aggregate results by treatment group."""
        groups = {}

        for d in data:
            group = d.get("group", "unknown")
            if group not in groups:
                groups[group] = []
            groups[group].append(d.get(metric, 0.0))

        results = []
        for group, values in groups.items():
            results.append({metric: sum(values) / len(values)})

        return results

    def _get_experiment(self, experiment_id: str) -> Optional[ExperimentDesign]:
        """Get experiment by ID."""
        for exp in self.experiments:
            if exp.id == experiment_id:
                return exp
        return None


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestExperimentDesigner:
    """Test suite for ExperimentDesigner."""

    def test_design_experiment_for_hypothesis(self):
        """Test designing experiments to test hypotheses."""
        designer = ExperimentDesigner()

        experiment = designer.design_experiment(
            hypothesis_id="H1",
            hypothesis_statement="Increasing model size improves accuracy",
            independent_var="model_size",
            dependent_var="accuracy"
        )

        assert experiment.id == "EXP1"
        assert experiment.hypothesis_id == "H1"
        assert "model_size" in experiment.independent_variables
        assert "accuracy" in experiment.dependent_variables
        assert experiment.control_group is not None
        assert len(experiment.treatment_groups) > 0

    def test_experiment_control_group_design(self):
        """Test designing control groups."""
        designer = ExperimentDesigner()

        experiment = designer.design_experiment(
            hypothesis_id="H1",
            hypothesis_statement="Treatment improves outcome",
            independent_var="treatment",
            dependent_var="outcome"
        )

        # Verify control group
        assert experiment.control_group["name"] == "control"
        assert "treatment" in experiment.control_group

        # Update control group
        updated_control = designer.design_control_group(
            experiment.id,
            {"baseline_metric": 0.5, "environment": "test"}
        )

        assert updated_control["baseline_metric"] == 0.5
        assert updated_control["environment"] == "test"

    def test_experiment_variable_selection(self):
        """Test selecting independent/dependent variables."""
        designer = ExperimentDesigner()

        hypothesis = "Increasing training data improves model accuracy"

        ivs, dvs = designer.select_variables(hypothesis)

        assert len(ivs) > 0
        assert len(dvs) > 0
        # Check for any relevant variable extraction
        assert any(word in " ".join(ivs + dvs).lower() for word in ["data", "training", "accuracy", "treatment", "outcome"])

    def test_validate_experiment_design(self):
        """Test validating experiment design quality."""
        designer = ExperimentDesigner()

        experiment = designer.design_experiment(
            hypothesis_id="H1",
            hypothesis_statement="Test hypothesis",
            independent_var="factor",
            dependent_var="metric"
        )

        # Should be valid
        is_valid = designer.validate_design(experiment.id)

        assert is_valid
        assert experiment.status == ExperimentStatus.VALIDATED
        assert len(experiment.validation_errors) == 0

    def test_validate_invalid_experiment(self):
        """Test validation of invalid experiment design."""
        designer = ExperimentDesigner()

        # Create experiment with issues
        experiment = ExperimentDesign(
            id="EXP1",
            hypothesis_id="H1",
            independent_variables=[],  # Missing
            dependent_variables=[],  # Missing
            control_group={},
            treatment_groups=[],
            sample_size=10,  # Too small
            duration="1 day"
        )

        designer.experiments.append(experiment)

        is_valid = designer.validate_design(experiment.id)

        assert not is_valid
        assert len(experiment.validation_errors) > 0

    def test_experiment_feasibility_check(self):
        """Test checking experiment feasibility."""
        designer = ExperimentDesigner()

        # Feasible experiment
        exp1 = designer.design_experiment(
            hypothesis_id="H1",
            hypothesis_statement="Test",
            independent_var="factor",
            dependent_var="metric"
        )

        feasibility1 = designer.check_feasibility(exp1.id)

        assert 0.0 <= feasibility1 <= 1.0
        assert feasibility1 > 0.5  # Should be feasible

        # Less feasible experiment (large sample)
        exp2 = designer.design_experiment(
            hypothesis_id="H2",
            hypothesis_statement="Test",
            independent_var="factor",
            dependent_var="metric"
        )
        exp2.sample_size = 2000

        feasibility2 = designer.check_feasibility(exp2.id)

        assert feasibility2 < feasibility1

    @pytest.mark.asyncio
    async def test_execute_experiment_simulation(self):
        """Test executing simulated experiments."""
        designer = ExperimentDesigner()

        experiment = designer.design_experiment(
            hypothesis_id="H1",
            hypothesis_statement="Treatment improves outcome",
            independent_var="treatment",
            dependent_var="outcome"
        )

        # Validate before execution
        designer.validate_design(experiment.id)

        # Execute
        result = await designer.execute_experiment(experiment.id, simulation=True)

        assert result.experiment_id == experiment.id
        assert result.hypothesis_id == "H1"
        assert result.control_results is not None
        assert len(result.treatment_results) > 0
        assert 0.0 <= result.statistical_significance <= 1.0
        assert result.effect_size > 0.0

    def test_experiment_result_collection(self):
        """Test collecting experiment results."""
        designer = ExperimentDesigner()

        experiment = designer.design_experiment(
            hypothesis_id="H1",
            hypothesis_statement="Test",
            independent_var="factor",
            dependent_var="metric"
        )

        # Simulate raw data
        raw_data = [
            {"group": "control", "metric": 0.6},
            {"group": "control", "metric": 0.65},
            {"group": "treatment_1", "metric": 0.75},
            {"group": "treatment_1", "metric": 0.8},
        ]

        result = designer.collect_results(experiment.id, raw_data)

        assert result.experiment_id == experiment.id
        assert "metric" in result.control_results
        assert len(result.treatment_results) > 0
        assert len(result.raw_data) == 4


class TestExperimentWorkflow:
    """Test complete experiment workflow."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_experiment_cycle(self):
        """Test complete experiment cycle: design → validate → execute → collect."""
        designer = ExperimentDesigner()

        # 1. Design experiment
        experiment = designer.design_experiment(
            hypothesis_id="H1",
            hypothesis_statement="Increasing context window improves reasoning",
            independent_var="context_window",
            dependent_var="reasoning_score"
        )

        assert experiment.status == ExperimentStatus.DESIGNED

        # 2. Validate design
        is_valid = designer.validate_design(experiment.id)
        assert is_valid
        assert experiment.status == ExperimentStatus.VALIDATED

        # 3. Check feasibility
        feasibility = designer.check_feasibility(experiment.id)
        assert feasibility > 0.5

        # 4. Execute experiment
        result = await designer.execute_experiment(experiment.id)

        assert experiment.status == ExperimentStatus.COMPLETED
        assert result.statistical_significance < 0.05  # Significant
        assert result.effect_size > 0.0

    @pytest.mark.integration
    def test_multiple_experiments_for_hypothesis(self):
        """Test designing multiple experiments for same hypothesis."""
        designer = ExperimentDesigner()

        # Design multiple experiments
        exp1 = designer.design_experiment(
            hypothesis_id="H1",
            hypothesis_statement="Test",
            independent_var="factor_a",
            dependent_var="metric"
        )

        exp2 = designer.design_experiment(
            hypothesis_id="H1",
            hypothesis_statement="Test",
            independent_var="factor_b",
            dependent_var="metric"
        )

        assert exp1.id != exp2.id
        assert exp1.hypothesis_id == exp2.hypothesis_id
        assert exp1.independent_variables != exp2.independent_variables


class TestExperimentValidation:
    """Test experiment validation logic."""

    def test_experiment_not_found_error(self):
        """Test error handling for non-existent experiment."""
        designer = ExperimentDesigner()

        with pytest.raises(ValueError, match="Experiment EXP999 not found"):
            designer.validate_design("EXP999")

    @pytest.mark.asyncio
    async def test_execute_unvalidated_experiment_error(self):
        """Test error when executing unvalidated experiment."""
        designer = ExperimentDesigner()

        experiment = designer.design_experiment(
            hypothesis_id="H1",
            hypothesis_statement="Test",
            independent_var="factor",
            dependent_var="metric"
        )

        # Don't validate
        with pytest.raises(ValueError, match="must be validated"):
            await designer.execute_experiment(experiment.id)

    def test_sample_size_calculation(self):
        """Test sample size calculation."""
        designer = ExperimentDesigner()

        experiment = designer.design_experiment(
            hypothesis_id="H1",
            hypothesis_statement="Test",
            independent_var="factor",
            dependent_var="metric"
        )

        # Should have reasonable sample size
        assert experiment.sample_size >= 30
        assert experiment.sample_size > len(experiment.treatment_groups) * 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
