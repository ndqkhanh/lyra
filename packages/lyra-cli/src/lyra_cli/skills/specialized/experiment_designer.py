"""
Experiment Designer Skill - AI/ML experiment design and planning.

Given a research hypothesis, produces:
- Experiment protocol
- Variable definitions (IV/DV/CV)
- Sample size calculations
- Statistical test selection
- Data collection plan

Outputs structured experiment design.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ExperimentType(StrEnum):
    """Types of experiments."""

    AB_TEST = "ab_test"
    FACTORIAL = "factorial"
    RANDOMIZED_CONTROLLED = "randomized_controlled"
    QUASI_EXPERIMENTAL = "quasi_experimental"
    OBSERVATIONAL = "observational"
    ABLATION = "ablation"


class VariableType(StrEnum):
    """Types of variables."""

    INDEPENDENT = "independent"
    DEPENDENT = "dependent"
    CONTROL = "control"
    CONFOUNDING = "confounding"


class StatisticalTest(StrEnum):
    """Statistical tests."""

    T_TEST = "t_test"
    ANOVA = "anova"
    CHI_SQUARE = "chi_square"
    MANN_WHITNEY = "mann_whitney"
    WILCOXON = "wilcoxon"
    BOOTSTRAP = "bootstrap"
    PERMUTATION = "permutation"


@dataclass(frozen=True)
class Variable:
    """An experimental variable."""

    name: str
    type: VariableType
    description: str
    measurement_method: str
    levels: tuple[str, ...]


@dataclass(frozen=True)
class Hypothesis:
    """Experimental hypothesis."""

    null_hypothesis: str
    alternative_hypothesis: str
    directional: bool
    rationale: str


@dataclass(frozen=True)
class SampleSize:
    """Sample size calculation."""

    recommended_size: int
    power: str
    effect_size: str
    alpha: str
    rationale: str


@dataclass(frozen=True)
class DataCollectionPlan:
    """Data collection protocol."""

    data_sources: tuple[str, ...]
    collection_method: str
    sampling_strategy: str
    quality_checks: tuple[str, ...]
    storage_format: str


@dataclass(frozen=True)
class AnalysisPlan:
    """Statistical analysis plan."""

    primary_test: StatisticalTest
    secondary_tests: tuple[StatisticalTest, ...]
    significance_level: str
    multiple_comparison_correction: str
    sensitivity_analysis: tuple[str, ...]


@dataclass(frozen=True)
class ExperimentDesign:
    """Complete experiment design."""

    title: str
    experiment_type: ExperimentType
    hypothesis: Hypothesis
    variables: tuple[Variable, ...]
    sample_size: SampleSize
    data_collection: DataCollectionPlan
    analysis_plan: AnalysisPlan
    timeline: tuple[tuple[str, str], ...]
    ethical_considerations: tuple[str, ...]
    limitations: tuple[str, ...]


class ExperimentDesigner:
    """Experiment design skill producing structured designs."""

    def run(self, input_data: dict) -> dict:
        """Run experiment design.

        Args:
            input_data: Dictionary with keys:
                - research_question: The research question or hypothesis
                - experiment_type: Optional experiment type (default "ab_test")
                - domain: Optional domain (default "machine learning")

        Returns:
            Dictionary with experiment design data.
        """
        question = input_data.get("research_question", "")
        if not question:
            return {"error": "No research question provided"}

        title = question[:80] + ("..." if len(question) > 80 else "")
        type_str = input_data.get("experiment_type", "ab_test").lower()
        domain = input_data.get("domain", "machine learning")

        try:
            exp_type = ExperimentType(type_str)
        except ValueError:
            exp_type = ExperimentType.AB_TEST

        question_lower = question.lower()

        hypothesis = self._formulate_hypothesis(question)
        variables = self._define_variables(question_lower, domain)
        sample_size = self._calculate_sample_size(exp_type)
        data_collection = self._plan_data_collection(question_lower, domain)
        analysis = self._plan_analysis(exp_type, len(variables))
        timeline = self._build_timeline(exp_type)
        ethical = self._identify_ethical_considerations(question_lower, domain)
        limitations = self._identify_limitations(exp_type)

        return ExperimentDesign(
            title=title,
            experiment_type=exp_type,
            hypothesis=hypothesis,
            variables=tuple(variables),
            sample_size=sample_size,
            data_collection=data_collection,
            analysis_plan=analysis,
            timeline=tuple(timeline),
            ethical_considerations=tuple(ethical),
            limitations=tuple(limitations),
        ).__dict__ | {
            "hypothesis": hypothesis.__dict__,
            "variables": [v.__dict__ for v in variables],
            "sample_size": sample_size.__dict__,
            "data_collection": data_collection.__dict__,
            "analysis_plan": analysis.__dict__,
        }

    @staticmethod
    def _formulate_hypothesis(question: str) -> Hypothesis:
        return Hypothesis(
            null_hypothesis=(
                "There is no statistically significant difference between "
                "the treatment and control conditions"
            ),
            alternative_hypothesis=(
                "The treatment condition shows statistically significant "
                "improvement over the control condition"
            ),
            directional=True,
            rationale=f"Based on research question: {question[:100]}",
        )

    @staticmethod
    def _define_variables(question: str, domain: str) -> list[Variable]:
        variables: list[Variable] = [
            Variable(
                name="Treatment Condition",
                type=VariableType.INDEPENDENT,
                description="The experimental manipulation being tested",
                measurement_method="Categorical assignment (treatment vs control)",
                levels=("Control", "Treatment"),
            ),
            Variable(
                name="Primary Outcome",
                type=VariableType.DEPENDENT,
                description="The main outcome metric of interest",
                measurement_method="Quantitative measurement (see protocol)",
                levels=("Continuous scale",),
            ),
            Variable(
                name="Random Seed",
                type=VariableType.CONTROL,
                description="Random initialization for reproducibility",
                measurement_method="Fixed seed value",
                levels=("Fixed across all runs",),
            ),
        ]

        if "model" in question or "algorithm" in question:
            variables.append(
                Variable(
                    name="Model Architecture",
                    type=VariableType.CONTROL,
                    description="Neural network architecture or algorithm variant",
                    measurement_method="Categorical (fixed architecture)",
                    levels=("Standard architecture",),
                )
            )

        if "data" in question or "dataset" in question:
            variables.append(
                Variable(
                    name="Dataset Split",
                    type=VariableType.CONTROL,
                    description="Train/validation/test split",
                    measurement_method="Fixed split ratio",
                    levels=("70/15/15 split",),
                )
            )

        return variables

    @staticmethod
    def _calculate_sample_size(exp_type: ExperimentType) -> SampleSize:
        if exp_type == ExperimentType.AB_TEST:
            return SampleSize(
                recommended_size=100,
                power="0.80",
                effect_size="0.5 (medium)",
                alpha="0.05",
                rationale="Based on standard power analysis for medium effect size",
            )
        elif exp_type == ExperimentType.FACTORIAL:
            return SampleSize(
                recommended_size=200,
                power="0.80",
                effect_size="0.5 (medium)",
                alpha="0.05",
                rationale="Larger sample needed for factorial design with multiple factors",
            )
        else:
            return SampleSize(
                recommended_size=150,
                power="0.80",
                effect_size="0.5 (medium)",
                alpha="0.05",
                rationale="Standard sample size for experimental design",
            )

    @staticmethod
    def _plan_data_collection(question: str, domain: str) -> DataCollectionPlan:
        sources = ["Primary data collection", "Existing benchmark datasets"]
        if "user" in question:
            sources.append("User study participants")
        if "simulation" in question:
            sources.append("Simulated data")

        return DataCollectionPlan(
            data_sources=tuple(sources),
            collection_method="Automated data collection with manual validation",
            sampling_strategy="Random sampling with stratification",
            quality_checks=(
                "Data completeness check",
                "Outlier detection",
                "Distribution validation",
                "Missing value analysis",
            ),
            storage_format="Structured format (CSV/JSON) with metadata",
        )

    @staticmethod
    def _plan_analysis(exp_type: ExperimentType, num_variables: int) -> AnalysisPlan:
        if exp_type == ExperimentType.AB_TEST:
            primary = StatisticalTest.T_TEST
            secondary = (StatisticalTest.MANN_WHITNEY, StatisticalTest.BOOTSTRAP)
        elif exp_type == ExperimentType.FACTORIAL:
            primary = StatisticalTest.ANOVA
            secondary = (StatisticalTest.T_TEST, StatisticalTest.BOOTSTRAP)
        else:
            primary = StatisticalTest.BOOTSTRAP
            secondary = (StatisticalTest.PERMUTATION, StatisticalTest.WILCOXON)

        correction = "Bonferroni" if num_variables > 3 else "None (single comparison)"

        return AnalysisPlan(
            primary_test=primary,
            secondary_tests=secondary,
            significance_level="0.05",
            multiple_comparison_correction=correction,
            sensitivity_analysis=(
                "Vary significance threshold (0.01, 0.05, 0.10)",
                "Exclude outliers and re-analyze",
                "Subsample analysis for robustness",
            ),
        )

    @staticmethod
    def _build_timeline(exp_type: ExperimentType) -> list[tuple[str, str]]:
        base_timeline = [
            ("Week 1", "Finalize experiment protocol and obtain approvals"),
            ("Week 2-3", "Set up data collection infrastructure"),
            ("Week 4-6", "Pilot study and protocol refinement"),
        ]

        if exp_type == ExperimentType.FACTORIAL:
            base_timeline.extend([
                ("Week 7-12", "Main data collection (factorial design)"),
                ("Week 13-14", "Data cleaning and validation"),
                ("Week 15-16", "Statistical analysis and interpretation"),
            ])
        else:
            base_timeline.extend([
                ("Week 7-10", "Main data collection"),
                ("Week 11-12", "Data cleaning and validation"),
                ("Week 13-14", "Statistical analysis and interpretation"),
            ])

        return base_timeline

    @staticmethod
    def _identify_ethical_considerations(question: str, domain: str) -> list[str]:
        considerations = [
            "Informed consent: Ensure all participants understand the study",
            "Data privacy: Protect participant data and maintain confidentiality",
            "Minimal risk: Ensure experiment poses minimal risk to participants",
        ]

        if "user" in question or "human" in question:
            considerations.append(
                "IRB approval: Obtain institutional review board approval for human subjects"
            )

        if "bias" in question or "fairness" in question:
            considerations.append(
                "Fairness: Ensure experiment does not perpetuate or amplify biases"
            )

        return considerations

    @staticmethod
    def _identify_limitations(exp_type: ExperimentType) -> list[str]:
        limitations = [
            "External validity: Results may not generalize beyond experimental setting",
            "Sample size: Limited by computational/time constraints",
            "Confounding variables: Potential unmeasured confounders",
        ]

        if exp_type == ExperimentType.OBSERVATIONAL:
            limitations.append(
                "Causality: Observational design limits causal inference"
            )

        if exp_type == ExperimentType.QUASI_EXPERIMENTAL:
            limitations.append(
                "Selection bias: Non-random assignment may introduce bias"
            )

        return limitations
