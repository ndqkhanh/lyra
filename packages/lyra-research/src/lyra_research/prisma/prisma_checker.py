"""
PRISMA Compliance Checker

Implements PRISMA-trAIce 17-item compliance for systematic reviews.
Based on PRISMA 2020 guidelines and Academic Research Skills repository.
"""

from dataclasses import dataclass
from typing import Dict, Any, List
from enum import Enum


class PRISMAItem(Enum):
    """PRISMA-trAIce 17 items"""
    TITLE_IDENTIFICATION = "title_identification"
    ABSTRACT_STRUCTURED = "abstract_structured"
    RATIONALE = "rationale"
    OBJECTIVES = "objectives"
    ELIGIBILITY_CRITERIA = "eligibility_criteria"
    INFORMATION_SOURCES = "information_sources"
    SEARCH_STRATEGY = "search_strategy"
    SELECTION_PROCESS = "selection_process"
    DATA_COLLECTION = "data_collection"
    DATA_ITEMS = "data_items"
    RISK_OF_BIAS = "risk_of_bias"
    EFFECT_MEASURES = "effect_measures"
    SYNTHESIS_METHODS = "synthesis_methods"
    REPORTING_BIAS = "reporting_bias"
    CERTAINTY_ASSESSMENT = "certainty_assessment"
    STUDY_CHARACTERISTICS = "study_characteristics"
    RESULTS_SYNTHESIS = "results_synthesis"


@dataclass
class PRISMAItemResult:
    """Result for a single PRISMA item"""
    item: PRISMAItem
    passed: bool
    reason: str
    evidence: str = ""


@dataclass
class PRISMAResult:
    """Overall PRISMA compliance result"""
    compliance_rate: float
    items: Dict[PRISMAItem, PRISMAItemResult]
    passed: bool
    missing_items: List[PRISMAItem]


class PRISMAComplianceChecker:
    """
    17-item PRISMA-trAIce compliance checker for systematic reviews

    Validates research reports against PRISMA 2020 guidelines.
    """

    def __init__(self, min_compliance: float = 0.85):
        """
        Initialize PRISMA checker

        Args:
            min_compliance: Minimum compliance rate (default 85%)
        """
        self.min_compliance = min_compliance

    def check_compliance(self, report: Dict[str, Any]) -> PRISMAResult:
        """
        Check all 17 PRISMA items

        Args:
            report: Research report to validate

        Returns:
            PRISMAResult with compliance details
        """
        results = {}

        # Check each PRISMA item
        for item in PRISMAItem:
            checker_method = getattr(self, f"check_{item.value}")
            results[item] = checker_method(report)

        # Calculate compliance rate
        passed_count = sum(1 for r in results.values() if r.passed)
        compliance_rate = passed_count / len(results)

        # Identify missing items
        missing_items = [item for item, result in results.items() if not result.passed]

        return PRISMAResult(
            compliance_rate=compliance_rate,
            items=results,
            passed=compliance_rate >= self.min_compliance,
            missing_items=missing_items
        )

    def check_title_identification(self, report: Dict[str, Any]) -> PRISMAItemResult:
        """Check if title identifies the report as a systematic review"""
        title = report.get("title", "").lower()
        keywords = ["systematic review", "meta-analysis", "systematic literature review"]

        passed = any(keyword in title for keyword in keywords)

        return PRISMAItemResult(
            item=PRISMAItem.TITLE_IDENTIFICATION,
            passed=passed,
            reason="Title identifies as systematic review" if passed else "Title does not identify as systematic review",
            evidence=report.get("title", "")
        )

    def check_abstract_structured(self, report: Dict[str, Any]) -> PRISMAItemResult:
        """Check if abstract is structured with required sections"""
        abstract = report.get("abstract", {})
        required_sections = ["background", "methods", "results", "conclusions"]

        if isinstance(abstract, str):
            # Check if sections are present in text
            passed = all(section in abstract.lower() for section in required_sections)
        else:
            # Check if sections exist as keys
            passed = all(section in abstract for section in required_sections)

        return PRISMAItemResult(
            item=PRISMAItem.ABSTRACT_STRUCTURED,
            passed=passed,
            reason="Abstract has all required sections" if passed else f"Abstract missing sections: {[s for s in required_sections if s not in str(abstract).lower()]}"
        )

    def check_rationale(self, report: Dict[str, Any]) -> PRISMAItemResult:
        """Check if rationale for the review is provided"""
        rationale = report.get("rationale", "")
        passed = len(rationale) > 50  # At least 50 characters

        return PRISMAItemResult(
            item=PRISMAItem.RATIONALE,
            passed=passed,
            reason="Rationale provided" if passed else "Rationale missing or too short"
        )

    def check_objectives(self, report: Dict[str, Any]) -> PRISMAItemResult:
        """Check if explicit objectives are stated"""
        objectives = report.get("objectives", "")
        passed = len(objectives) > 30

        return PRISMAItemResult(
            item=PRISMAItem.OBJECTIVES,
            passed=passed,
            reason="Objectives stated" if passed else "Objectives missing or unclear"
        )

    def check_eligibility_criteria(self, report: Dict[str, Any]) -> PRISMAItemResult:
        """Check if eligibility criteria are specified"""
        criteria = report.get("eligibility_criteria", {})
        required = ["inclusion", "exclusion"]

        if isinstance(criteria, dict):
            passed = all(key in criteria for key in required)
        else:
            passed = len(str(criteria)) > 50

        return PRISMAItemResult(
            item=PRISMAItem.ELIGIBILITY_CRITERIA,
            passed=passed,
            reason="Eligibility criteria specified" if passed else "Eligibility criteria missing"
        )

    def check_information_sources(self, report: Dict[str, Any]) -> PRISMAItemResult:
        """Check if information sources are described"""
        sources = report.get("information_sources", [])
        passed = len(sources) >= 3  # At least 3 sources

        return PRISMAItemResult(
            item=PRISMAItem.INFORMATION_SOURCES,
            passed=passed,
            reason=f"{len(sources)} information sources described" if passed else "Insufficient information sources"
        )

    def check_search_strategy(self, report: Dict[str, Any]) -> PRISMAItemResult:
        """Check if search strategy is documented"""
        strategy = report.get("search_strategy", "")
        passed = len(strategy) > 100  # Detailed strategy

        return PRISMAItemResult(
            item=PRISMAItem.SEARCH_STRATEGY,
            passed=passed,
            reason="Search strategy documented" if passed else "Search strategy missing or incomplete"
        )

    def check_selection_process(self, report: Dict[str, Any]) -> PRISMAItemResult:
        """Check if selection process is described"""
        process = report.get("selection_process", "")
        passed = len(process) > 50

        return PRISMAItemResult(
            item=PRISMAItem.SELECTION_PROCESS,
            passed=passed,
            reason="Selection process described" if passed else "Selection process missing"
        )

    def check_data_collection(self, report: Dict[str, Any]) -> PRISMAItemResult:
        """Check if data collection process is described"""
        collection = report.get("data_collection", "")
        passed = len(collection) > 50

        return PRISMAItemResult(
            item=PRISMAItem.DATA_COLLECTION,
            passed=passed,
            reason="Data collection described" if passed else "Data collection missing"
        )

    def check_data_items(self, report: Dict[str, Any]) -> PRISMAItemResult:
        """Check if data items are defined"""
        items = report.get("data_items", [])
        passed = len(items) >= 3

        return PRISMAItemResult(
            item=PRISMAItem.DATA_ITEMS,
            passed=passed,
            reason=f"{len(items)} data items defined" if passed else "Insufficient data items"
        )

    def check_risk_of_bias(self, report: Dict[str, Any]) -> PRISMAItemResult:
        """Check if risk of bias assessment is included"""
        bias_assessment = report.get("risk_of_bias", {})
        passed = len(bias_assessment) > 0

        return PRISMAItemResult(
            item=PRISMAItem.RISK_OF_BIAS,
            passed=passed,
            reason="Risk of bias assessed" if passed else "Risk of bias assessment missing"
        )

    def check_effect_measures(self, report: Dict[str, Any]) -> PRISMAItemResult:
        """Check if effect measures are specified"""
        measures = report.get("effect_measures", "")
        passed = len(measures) > 30

        return PRISMAItemResult(
            item=PRISMAItem.EFFECT_MEASURES,
            passed=passed,
            reason="Effect measures specified" if passed else "Effect measures missing"
        )

    def check_synthesis_methods(self, report: Dict[str, Any]) -> PRISMAItemResult:
        """Check if synthesis methods are described"""
        methods = report.get("synthesis_methods", "")
        passed = len(methods) > 50

        return PRISMAItemResult(
            item=PRISMAItem.SYNTHESIS_METHODS,
            passed=passed,
            reason="Synthesis methods described" if passed else "Synthesis methods missing"
        )

    def check_reporting_bias(self, report: Dict[str, Any]) -> PRISMAItemResult:
        """Check if reporting bias is assessed"""
        bias = report.get("reporting_bias", "")
        passed = len(bias) > 30

        return PRISMAItemResult(
            item=PRISMAItem.REPORTING_BIAS,
            passed=passed,
            reason="Reporting bias assessed" if passed else "Reporting bias assessment missing"
        )

    def check_certainty_assessment(self, report: Dict[str, Any]) -> PRISMAItemResult:
        """Check if certainty of evidence is assessed"""
        certainty = report.get("certainty_assessment", "")
        passed = len(certainty) > 30

        return PRISMAItemResult(
            item=PRISMAItem.CERTAINTY_ASSESSMENT,
            passed=passed,
            reason="Certainty assessed" if passed else "Certainty assessment missing"
        )

    def check_study_characteristics(self, report: Dict[str, Any]) -> PRISMAItemResult:
        """Check if study characteristics are presented"""
        characteristics = report.get("study_characteristics", [])
        passed = len(characteristics) > 0

        return PRISMAItemResult(
            item=PRISMAItem.STUDY_CHARACTERISTICS,
            passed=passed,
            reason="Study characteristics presented" if passed else "Study characteristics missing"
        )

    def check_results_synthesis(self, report: Dict[str, Any]) -> PRISMAItemResult:
        """Check if results of synthesis are presented"""
        synthesis = report.get("results_synthesis", "")
        passed = len(synthesis) > 100

        return PRISMAItemResult(
            item=PRISMAItem.RESULTS_SYNTHESIS,
            passed=passed,
            reason="Results synthesis presented" if passed else "Results synthesis missing or incomplete"
        )
