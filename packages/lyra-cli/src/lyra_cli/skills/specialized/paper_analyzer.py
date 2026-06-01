"""
Paper Analyzer Skill - AI research paper analysis and summarization.

Given a research paper (abstract/content), produces:
- Key contributions summary
- Methodology analysis
- Results interpretation
- Limitations identification
- Future work suggestions

Outputs structured paper analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PaperType(StrEnum):
    """Types of research papers."""

    EMPIRICAL = "empirical"
    THEORETICAL = "theoretical"
    SURVEY = "survey"
    POSITION = "position"
    REPRODUCTION = "reproduction"
    WORKSHOP = "workshop"


class ContributionType(StrEnum):
    """Types of research contributions."""

    NOVEL_METHOD = "novel_method"
    NOVEL_DATASET = "novel_dataset"
    NOVEL_BENCHMARK = "novel_benchmark"
    THEORETICAL_ANALYSIS = "theoretical_analysis"
    EMPIRICAL_FINDING = "empirical_finding"
    SURVEY_SYNTHESIS = "survey_synthesis"


@dataclass(frozen=True)
class KeyContribution:
    """A key contribution from the paper."""

    type: ContributionType
    description: str
    significance: str
    novelty_score: str


@dataclass(frozen=True)
class MethodologyAnalysis:
    """Analysis of the paper's methodology."""

    approach: str
    datasets_used: tuple[str, ...]
    baselines: tuple[str, ...]
    evaluation_metrics: tuple[str, ...]
    experimental_setup: str
    reproducibility_score: str


@dataclass(frozen=True)
class ResultSummary:
    """Summary of key results."""

    main_findings: tuple[str, ...]
    performance_improvements: tuple[str, ...]
    statistical_significance: str
    ablation_insights: tuple[str, ...]


@dataclass(frozen=True)
class Limitation:
    """A limitation of the work."""

    category: str
    description: str
    severity: str
    potential_impact: str


@dataclass(frozen=True)
class FutureDirection:
    """A suggested future research direction."""

    direction: str
    rationale: str
    difficulty: str
    potential_impact: str


@dataclass(frozen=True)
class PaperAnalysis:
    """Complete paper analysis."""

    title: str
    paper_type: PaperType
    contributions: tuple[KeyContribution, ...]
    methodology: MethodologyAnalysis
    results: ResultSummary
    limitations: tuple[Limitation, ...]
    future_work: tuple[FutureDirection, ...]
    overall_assessment: str
    citation_recommendation: str


class PaperAnalyzer:
    """Paper analysis skill producing structured analyses."""

    def run(self, input_data: dict) -> dict:
        """Run paper analysis.

        Args:
            input_data: Dictionary with keys:
                - paper_content: Paper abstract or full text
                - title: Optional paper title (default "Untitled Paper")
                - paper_type: Optional paper type (default "empirical")

        Returns:
            Dictionary with paper analysis data.
        """
        content = input_data.get("paper_content", "")
        if not content:
            return {"error": "No paper content provided"}

        title = input_data.get("title", "Untitled Paper")
        type_str = input_data.get("paper_type", "empirical").lower()
        try:
            paper_type = PaperType(type_str)
        except ValueError:
            paper_type = PaperType.EMPIRICAL

        content_lower = content.lower()

        contributions = self._extract_contributions(content_lower)
        methodology = self._analyze_methodology(content_lower)
        results = self._summarize_results(content_lower)
        limitations = self._identify_limitations(content_lower)
        future_work = self._suggest_future_work(content_lower)
        assessment = self._assess_overall(contributions, methodology, results)
        citation = self._recommend_citation(contributions, results)

        return PaperAnalysis(
            title=title,
            paper_type=paper_type,
            contributions=tuple(contributions),
            methodology=methodology,
            results=results,
            limitations=tuple(limitations),
            future_work=tuple(future_work),
            overall_assessment=assessment,
            citation_recommendation=citation,
        ).__dict__ | {
            "contributions": [c.__dict__ for c in contributions],
            "methodology": methodology.__dict__,
            "results": results.__dict__,
            "limitations": [l.__dict__ for l in limitations],
            "future_work": [f.__dict__ for f in future_work],
        }

    @staticmethod
    def _extract_contributions(content: str) -> list[KeyContribution]:
        contributions: list[KeyContribution] = []

        if "novel" in content or "new method" in content or "propose" in content:
            contributions.append(
                KeyContribution(
                    type=ContributionType.NOVEL_METHOD,
                    description="Proposes a novel method/architecture for the task",
                    significance="Advances state-of-the-art on key benchmarks",
                    novelty_score="HIGH",
                )
            )

        if "dataset" in content or "benchmark" in content:
            contributions.append(
                KeyContribution(
                    type=ContributionType.NOVEL_DATASET,
                    description="Introduces new dataset or benchmark for evaluation",
                    significance="Enables future research in this area",
                    novelty_score="MEDIUM",
                )
            )

        if "theoretical" in content or "proof" in content or "analysis" in content:
            contributions.append(
                KeyContribution(
                    type=ContributionType.THEORETICAL_ANALYSIS,
                    description="Provides theoretical analysis or formal guarantees",
                    significance="Deepens understanding of the problem",
                    novelty_score="MEDIUM",
                )
            )

        if "empirical" in content or "experiment" in content:
            contributions.append(
                KeyContribution(
                    type=ContributionType.EMPIRICAL_FINDING,
                    description="Reports empirical findings from extensive experiments",
                    significance="Validates hypotheses and provides insights",
                    novelty_score="MEDIUM",
                )
            )

        if not contributions:
            contributions.append(
                KeyContribution(
                    type=ContributionType.EMPIRICAL_FINDING,
                    description="General research contribution (details in paper)",
                    significance="TBD based on full paper review",
                    novelty_score="TBD",
                )
            )

        return contributions

    @staticmethod
    def _analyze_methodology(content: str) -> MethodologyAnalysis:
        datasets = []
        if "imagenet" in content:
            datasets.append("ImageNet")
        if "coco" in content:
            datasets.append("COCO")
        if "squad" in content:
            datasets.append("SQuAD")
        if "glue" in content:
            datasets.append("GLUE")
        if not datasets:
            datasets.append("Standard benchmarks (see paper)")

        baselines = []
        if "baseline" in content:
            baselines.append("Standard baselines")
        if "sota" in content or "state-of-the-art" in content:
            baselines.append("Previous SOTA methods")
        if not baselines:
            baselines.append("Comparative baselines (see paper)")

        metrics = []
        if "accuracy" in content:
            metrics.append("Accuracy")
        if "f1" in content:
            metrics.append("F1 Score")
        if "bleu" in content:
            metrics.append("BLEU")
        if "rouge" in content:
            metrics.append("ROUGE")
        if not metrics:
            metrics.append("Standard metrics (see paper)")

        reproducibility = "MEDIUM"
        if "code" in content or "github" in content or "open source" in content:
            reproducibility = "HIGH"
        elif "proprietary" in content or "closed" in content:
            reproducibility = "LOW"

        return MethodologyAnalysis(
            approach="Described in paper methodology section",
            datasets_used=tuple(datasets),
            baselines=tuple(baselines),
            evaluation_metrics=tuple(metrics),
            experimental_setup="See paper for detailed experimental setup",
            reproducibility_score=reproducibility,
        )

    @staticmethod
    def _summarize_results(content: str) -> ResultSummary:
        findings = [
            "Main findings reported in results section",
            "Performance compared against baselines",
        ]

        improvements = []
        if "improve" in content or "better" in content or "outperform" in content:
            improvements.append("Outperforms baseline methods")
        if "sota" in content or "state-of-the-art" in content:
            improvements.append("Achieves new state-of-the-art")
        if not improvements:
            improvements.append("Performance improvements detailed in paper")

        significance = "p < 0.05"
        if "significant" in content:
            significance = "Statistically significant (see paper)"
        elif "not significant" in content:
            significance = "Not statistically significant"

        ablations = [
            "Ablation studies validate component contributions",
            "See paper for detailed ablation analysis",
        ]

        return ResultSummary(
            main_findings=tuple(findings),
            performance_improvements=tuple(improvements),
            statistical_significance=significance,
            ablation_insights=tuple(ablations),
        )

    @staticmethod
    def _identify_limitations(content: str) -> list[Limitation]:
        limitations: list[Limitation] = [
            Limitation(
                category="Computational",
                description="High computational cost for training/inference",
                severity="MEDIUM",
                potential_impact="Limits accessibility for resource-constrained researchers",
            ),
            Limitation(
                category="Generalization",
                description="Evaluation limited to specific benchmarks",
                severity="MEDIUM",
                potential_impact="Unclear how well method generalizes to other domains",
            ),
        ]

        if "limitation" in content or "future work" in content:
            limitations.append(
                Limitation(
                    category="Scope",
                    description="Limitations explicitly discussed in paper",
                    severity="LOW",
                    potential_impact="Authors acknowledge scope boundaries",
                )
            )

        return limitations

    @staticmethod
    def _suggest_future_work(content: str) -> list[FutureDirection]:
        return [
            FutureDirection(
                direction="Extend to additional domains and tasks",
                rationale="Validate generalization beyond current benchmarks",
                difficulty="MEDIUM",
                potential_impact="HIGH",
            ),
            FutureDirection(
                direction="Improve computational efficiency",
                rationale="Make method more accessible and practical",
                difficulty="MEDIUM",
                potential_impact="MEDIUM",
            ),
            FutureDirection(
                direction="Theoretical analysis of method properties",
                rationale="Deepen understanding of why method works",
                difficulty="HIGH",
                potential_impact="MEDIUM",
            ),
        ]

    @staticmethod
    def _assess_overall(
        contributions: list[KeyContribution],
        methodology: MethodologyAnalysis,
        results: ResultSummary,
    ) -> str:
        novelty = sum(1 for c in contributions if c.novelty_score == "HIGH")
        reproducibility = methodology.reproducibility_score

        if novelty >= 2 and reproducibility == "HIGH":
            return "STRONG: High novelty with reproducible methodology"
        if novelty >= 1 and reproducibility in ("HIGH", "MEDIUM"):
            return "GOOD: Solid contribution with reasonable reproducibility"
        return "ACCEPTABLE: Incremental contribution, standard methodology"

    @staticmethod
    def _recommend_citation(
        contributions: list[KeyContribution], results: ResultSummary
    ) -> str:
        high_novelty = any(c.novelty_score == "HIGH" for c in contributions)
        has_improvements = len(results.performance_improvements) > 0

        if high_novelty and has_improvements:
            return "HIGHLY RECOMMENDED: Cite for novel method and strong results"
        if high_novelty:
            return "RECOMMENDED: Cite for novel contribution"
        if has_improvements:
            return "RECOMMENDED: Cite for empirical results"
        return "OPTIONAL: Cite if directly relevant to your work"
