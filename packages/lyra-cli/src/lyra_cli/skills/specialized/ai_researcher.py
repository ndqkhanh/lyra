"""
AI Researcher Skill - AI research methodology planning.

Given a research question, produces:
- Literature review structure
- Experiment design
- Hypothesis formulation
- Evaluation methodology
- Related work mapping

Outputs structured research plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ResearchType(StrEnum):
    """Types of AI research."""

    EMPIRICAL = "empirical"  # Experimental evaluation
    THEORETICAL = "theoretical"  # Mathematical analysis
    APPLIED = "applied"  # Application/system building
    SURVEY = "survey"  # Literature review
    REPRODUCTION = "reproduction"  # Reproduction study


class EvaluationMetric(StrEnum):
    """Common AI evaluation metrics."""

    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1 = "f1"
    AUC_ROC = "auc_roc"
    PERPLEXITY = "perplexity"
    BLEU = "bleu"
    ROUGE = "rouge"
    METEOR = "meteor"
    CIDEr = "cider"
    MSE = "mean_squared_error"
    MAE = "mean_absolute_error"
    LATENCY = "latency"
    THROUGHPUT = "throughput"


@dataclass(frozen=True)
class ResearchQuestion:
    """The primary research question and sub-questions."""

    primary_question: str
    sub_questions: tuple[str, ...]
    null_hypothesis: str
    alternative_hypothesis: str
    scope_boundaries: tuple[str, ...]


@dataclass(frozen=True)
class LiteratureSection:
    """A section in the literature review."""

    title: str
    description: str
    key_papers: tuple[str, ...]
    identified_gaps: tuple[str, ...]


@dataclass(frozen=True)
class ExperimentDesign:
    """Design of a single experiment."""

    name: str
    purpose: str
    independent_variables: tuple[str, ...]
    dependent_variables: tuple[str, ...]
    control_conditions: tuple[str, ...]
    treatment_conditions: tuple[str, ...]
    sample_size_estimate: str
    statistical_test: str


@dataclass(frozen=True)
class EvaluationPlan:
    """Evaluation methodology plan."""

    primary_metrics: tuple[EvaluationMetric, ...]
    secondary_metrics: tuple[EvaluationMetric, ...]
    baseline_methods: tuple[str, ...]
    ablation_studies: tuple[str, ...]
    cross_validation: str
    significance_level: str
    error_analysis_method: str


@dataclass(frozen=True)
class RelatedWorkCluster:
    """A cluster of related work."""

    cluster_name: str
    key_approaches: tuple[str, ...]
    representative_papers: tuple[str, ...]
    relation_to_this_work: str


@dataclass(frozen=True)
class ResearchPlan:
    """Complete research plan."""

    title: str
    research_type: ResearchType
    question: ResearchQuestion
    literature_review: tuple[LiteratureSection, ...]
    experiments: tuple[ExperimentDesign, ...]
    evaluation: EvaluationPlan
    related_work: tuple[RelatedWorkCluster, ...]
    timeline: tuple[tuple[str, str], ...]
    compute_requirements: str


class AIResearcher:
    """AI research skill producing structured research plans."""

    def run(self, input_data: dict) -> dict:
        """Run AI research planning.

        Args:
            input_data: Dictionary with keys:
                - research_question: The primary research question
                - research_type: Optional research type (default "empirical")
                - domain: Optional research domain (default "machine learning")

        Returns:
            Dictionary with research plan data.
        """
        question_text = input_data.get("research_question", "")
        if not question_text:
            return {"error": "No research question provided"}

        domain = input_data.get("domain", "machine learning")
        type_str = input_data.get("research_type", "empirical").lower()
        try:
            research_type = ResearchType(type_str)
        except ValueError:
            research_type = ResearchType.EMPIRICAL

        question = self._formulate_question(question_text, domain)
        lit_review = self._build_literature_review(question_text, domain)
        experiments = self._design_experiments(question_text, domain)
        evaluation = self._build_evaluation_plan()
        related_work = self._map_related_work(question_text, domain)
        timeline = self._build_timeline()
        compute = self._estimate_compute(domain)

        return ResearchPlan(
            title=question_text[:80] + ("..." if len(question_text) > 80 else ""),
            research_type=research_type,
            question=question,
            literature_review=tuple(lit_review),
            experiments=tuple(experiments),
            evaluation=evaluation,
            related_work=tuple(related_work),
            timeline=tuple(timeline),
            compute_requirements=compute,
        ).__dict__ | {
            "question": question.__dict__,
            "literature_review": [s.__dict__ for s in lit_review],
            "experiments": [e.__dict__ for e in experiments],
            "evaluation": evaluation.__dict__,
            "related_work": [r.__dict__ for r in related_work],
        }

    @staticmethod
    def _formulate_question(
        question_text: str, domain: str
    ) -> ResearchQuestion:
        return ResearchQuestion(
            primary_question=question_text,
            sub_questions=(
                f"What is the current state-of-the-art for {question_text.lower().rstrip('?')}?",
                f"What are the key limitations of existing approaches to this problem?",
                f"How does computational budget affect the proposed approach?",
                f"How does the approach generalize across different {domain} benchmarks?",
            ),
            null_hypothesis=(
                f"The proposed method shows no statistically significant improvement over "
                f"existing baselines for the stated problem."
            ),
            alternative_hypothesis=(
                f"The proposed method achieves statistically significant improvement over "
                f"existing baselines across multiple evaluation metrics."
            ),
            scope_boundaries=(
                f"Limited to {domain} tasks and benchmarks",
                "Does not address real-time / production deployment constraints",
                "Assumes standard compute environment (single GPU node or small cluster)",
            ),
        )

    @staticmethod
    def _build_literature_review(
        question_text: str, domain: str
    ) -> list[LiteratureSection]:
        domain_name = domain.capitalize()
        return [
            LiteratureSection(
                title="Foundational Work",
                description=(
                    f"Seminal papers and established methods in {domain} that form "
                    f"the basis for current approaches"
                ),
                key_papers=(
                    f"Key papers in {domain}: TBD based on literature search",
                    "Survey papers covering the field comprehensively",
                ),
                identified_gaps=(
                    "Limited coverage of recent advances (last 2 years)",
                    "May lack domain-specific adaptations",
                ),
            ),
            LiteratureSection(
                title="Current State-of-the-Art",
                description=(
                    f"Latest methods and benchmarks that represent the current "
                    f"best performance on relevant tasks"
                ),
                key_papers=(
                    f"Top-performing methods on {domain} benchmarks",
                    "Recent preprints from major conferences (NeurIPS, ICML, ICLR)",
                ),
                identified_gaps=(
                    "SOTA methods often require extensive compute",
                    "Reproducibility concerns for complex methods",
                ),
            ),
            LiteratureSection(
                title="Related Methodologies",
                description=(
                    "Alternative approaches and adjacent techniques that could "
                    "inform or complement the proposed research"
                ),
                key_papers=(
                    "Methods from adjacent domains with potential transferability",
                    "Theoretical analyses relevant to the problem",
                ),
                identified_gaps=(
                    "Limited cross-pollination between sub-fields",
                    "Few comprehensive comparison studies",
                ),
            ),
            LiteratureSection(
                title="Evaluation & Benchmarks",
                description=(
                    "Standard evaluation protocols, datasets, and metrics used in the field"
                ),
                key_papers=(
                    "Established benchmarks and leaderboards",
                    "Critical analyses of existing evaluation practices",
                ),
                identified_gaps=(
                    "Benchmark saturation: many datasets may be saturated",
                    "Limited coverage of real-world scenarios",
                ),
            ),
        ]

    @staticmethod
    def _design_experiments(
        question_text: str, domain: str
    ) -> list[ExperimentDesign]:
        return [
            ExperimentDesign(
                name="Main Comparison Experiment",
                purpose=(
                    f"Compare proposed method against established baselines on "
                    f"standard benchmarks"
                ),
                independent_variables=("Method variant (proposed vs baselines)",
                                       "Hyperparameter configuration"),
                dependent_variables=("Task performance metrics",
                                     "Computational cost (FLOPs, runtime)"),
                control_conditions=("Fixed train/val/test split",
                                    "Same compute environment",
                                    "Fixed random seed"),
                treatment_conditions=("Proposed method with default hyperparameters",
                                      "Proposed method with tuned hyperparameters"),
                sample_size_estimate="5 runs with different seeds per condition",
                statistical_test="Paired bootstrap test or Wilcoxon signed-rank",
            ),
            ExperimentDesign(
                name="Ablation Study",
                purpose=(
                    "Isolate the contribution of each component in the proposed method"
                ),
                independent_variables=("Component presence/absence",
                                       "Component configuration"),
                dependent_variables=("Performance degradation when component removed",),
                control_conditions=("Full model performance as baseline",),
                treatment_conditions=("Remove component A", "Remove component B",
                                      "Remove components A+B"),
                sample_size_estimate="3-5 runs per ablation condition",
                statistical_test="McNemar's test or bootstrapped confidence intervals",
            ),
            ExperimentDesign(
                name="Generalization Study",
                purpose=(
                    "Evaluate how well the method transfers to different datasets "
                    "and settings"
                ),
                independent_variables=("Dataset", "Domain shift magnitude"),
                dependent_variables=("Cross-domain performance",
                                     "Fine-tuning efficiency"),
                control_conditions=("In-domain performance as reference",),
                treatment_conditions=("Out-of-domain dataset A",
                                      "Out-of-domain dataset B",
                                      "Low-resource setting"),
                sample_size_estimate="3 runs per dataset",
                statistical_test="Confidence interval overlap analysis",
            ),
            ExperimentDesign(
                name="Robustness Analysis",
                purpose="Test sensitivity to hyperparameters and random initialization",
                independent_variables=("Learning rate", "Weight initialization seed",
                                       "Training data subset"),
                dependent_variables=("Final performance variance",
                                     "Convergence stability"),
                control_conditions=("Recommended hyperparameters",),
                treatment_conditions=("LR x0.1", "LR x10", "Different seeds 1-10"),
                sample_size_estimate="10 runs with varied seeds",
                statistical_test="Variance analysis (F-test)",
            ),
        ]

    @staticmethod
    def _build_evaluation_plan() -> EvaluationPlan:
        return EvaluationPlan(
            primary_metrics=(
                EvaluationMetric.ACCURACY,
                EvaluationMetric.F1,
                EvaluationMetric.AUC_ROC,
            ),
            secondary_metrics=(
                EvaluationMetric.PRECISION,
                EvaluationMetric.RECALL,
                EvaluationMetric.LATENCY,
                EvaluationMetric.THROUGHPUT,
            ),
            baseline_methods=(
                "Random baseline",
                "Majority class baseline",
                "Previous SOTA method (reproduced)",
                "Simplified variant of proposed method",
            ),
            ablation_studies=(
                "Remove each component independently",
                "Vary key hyperparameters",
                "Test with different backbone architectures",
            ),
            cross_validation="5-fold cross-validation on all datasets",
            significance_level="p < 0.05",
            error_analysis_method=(
                "Confusion matrix analysis + per-category breakdown + "
                "qualitative error review"
            ),
        )

    @staticmethod
    def _map_related_work(
        question_text: str, domain: str
    ) -> list[RelatedWorkCluster]:
        return [
            RelatedWorkCluster(
                cluster_name=f"Core {domain} Methods",
                key_approaches=(
                    "Deep learning approaches",
                    "Classical ML methods",
                    "Hybrid approaches",
                ),
                representative_papers=(
                    "Key papers in this cluster: TBD",
                ),
                relation_to_this_work="Provides direct baselines and motivation",
            ),
            RelatedWorkCluster(
                cluster_name="Efficiency & Scalability",
                key_approaches=(
                    "Model compression",
                    "Knowledge distillation",
                    "Efficient architectures",
                ),
                representative_papers=(
                    "Key papers on efficiency: TBD",
                ),
                relation_to_this_work="Relevant for practical deployment considerations",
            ),
            RelatedWorkCluster(
                cluster_name="Robustness & Reliability",
                key_approaches=(
                    "Adversarial robustness",
                    "Distribution shift",
                    "Uncertainty estimation",
                ),
                representative_papers=(
                    "Key papers on robustness: TBD",
                ),
                relation_to_this_work="Provides evaluation methodology and stress tests",
            ),
        ]

    @staticmethod
    def _build_timeline() -> list[tuple[str, str]]:
        return [
            ("Month 1-2", "Literature review and problem formalization"),
            ("Month 2-3", "Baseline implementation and reproduction"),
            ("Month 3-5", "Proposed method implementation"),
            ("Month 5-7", "Experiments, ablation studies, and analysis"),
            ("Month 7-8", "Paper writing and figure preparation"),
            ("Month 8-9", "Revision, supplementary materials, and submission"),
        ]

    @staticmethod
    def _estimate_compute(domain: str) -> str:
        return (
            f"Estimated {150 if 'language' in domain or 'nlp' in domain else 300} "
            f"GPU-hours (single A100 80GB). "
            f"Recommended: 1-4 GPUs for development, 8+ GPUs for final experiments. "
            f"Storage: ~500 GB for datasets and checkpoints."
        )
