from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from lyra_adversarial_review.exceptions import ConfigurationError


class ReviewSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    def __lt__(self, other: ReviewSeverity) -> bool:
        order = list(ReviewSeverity)
        return order.index(self) > order.index(other)

    def __le__(self, other: ReviewSeverity) -> bool:
        order = list(ReviewSeverity)
        return order.index(self) >= order.index(other)

    def __gt__(self, other: ReviewSeverity) -> bool:
        order = list(ReviewSeverity)
        return order.index(self) < order.index(other)

    def __ge__(self, other: ReviewSeverity) -> bool:
        order = list(ReviewSeverity)
        return order.index(self) <= order.index(other)


@dataclass(frozen=True)
class SeverityThresholds:
    critical: float = 0.9
    high: float = 0.7
    medium: float = 0.5
    low: float = 0.3


@dataclass(frozen=True)
class ReviewRule:
    name: str
    pattern: str
    severity: ReviewSeverity
    description: str


@dataclass(frozen=True)
class ReviewRuleSet:
    name: str
    rules: Sequence[ReviewRule]
    description: str


@dataclass(frozen=True)
class ReviewConfig:
    max_issues_per_review: int = 50
    min_confidence_threshold: float = 0.3
    severity_thresholds: SeverityThresholds = SeverityThresholds()
    require_cross_family: bool = True
    max_reviewers_per_content: int = 3
    enable_aggregation: bool = True

    def validate(self) -> None:
        if self.max_issues_per_review < 1:
            raise ConfigurationError("max_issues_per_review must be >= 1")
        if self.min_confidence_threshold < 0 or self.min_confidence_threshold > 1:
            raise ConfigurationError("min_confidence_threshold must be in [0, 1]")
        if self.max_reviewers_per_content < 1:
            raise ConfigurationError("max_reviewers_per_content must be >= 1")


DEFAULT_RULES: ReviewRuleSet = ReviewRuleSet(
    name="default",
    description="Standard review rules for general content verification",
    rules=[
        ReviewRule(
            "correctness",
            ".*",
            ReviewSeverity.CRITICAL,
            "Verify factual and logical correctness of claims",
        ),
        ReviewRule(
            "completeness", ".*", ReviewSeverity.HIGH, "Ensure all required aspects are covered"
        ),
        ReviewRule("consistency", ".*", ReviewSeverity.MEDIUM, "Check for internal contradictions"),
        ReviewRule(
            "citation_accuracy",
            ".*",
            ReviewSeverity.HIGH,
            "Validate that citations support their claims",
        ),
    ],
)

SECURITY_RULES: ReviewRuleSet = ReviewRuleSet(
    name="security",
    description="Security-focused review rules",
    rules=[
        ReviewRule(
            "injection_prevention",
            ".*",
            ReviewSeverity.CRITICAL,
            "Detect injection vulnerabilities",
        ),
        ReviewRule(
            "authentication", ".*", ReviewSeverity.CRITICAL, "Verify authentication correctness"
        ),
        ReviewRule("authorization", ".*", ReviewSeverity.HIGH, "Verify authorization boundaries"),
        ReviewRule(
            "data_exposure", ".*", ReviewSeverity.CRITICAL, "Check for sensitive data leaks"
        ),
        ReviewRule("input_validation", ".*", ReviewSeverity.HIGH, "Verify input sanitization"),
    ],
)

RESEARCH_RULES: ReviewRuleSet = ReviewRuleSet(
    name="research",
    description="Academic research verification rules",
    rules=[
        ReviewRule("methodology", ".*", ReviewSeverity.CRITICAL, "Verify research methodology"),
        ReviewRule(
            "statistical_validity", ".*", ReviewSeverity.CRITICAL, "Check statistical claims"
        ),
        ReviewRule("citation_accuracy", ".*", ReviewSeverity.HIGH, "Validate citation support"),
        ReviewRule("reproducibility", ".*", ReviewSeverity.HIGH, "Ensure claims are reproducible"),
        ReviewRule("bias_assessment", ".*", ReviewSeverity.MEDIUM, "Check for systematic bias"),
    ],
)

CODE_REVIEW_RULES: ReviewRuleSet = ReviewRuleSet(
    name="code_review",
    description="Code review rules",
    rules=[
        ReviewRule("correctness", ".*", ReviewSeverity.CRITICAL, "Verify code correctness"),
        ReviewRule("security", ".*", ReviewSeverity.CRITICAL, "Check for security vulnerabilities"),
        ReviewRule("performance", ".*", ReviewSeverity.MEDIUM, "Evaluate performance implications"),
        ReviewRule("style", ".*", ReviewSeverity.LOW, "Check code style consistency"),
        ReviewRule("test_coverage", ".*", ReviewSeverity.HIGH, "Ensure adequate test coverage"),
    ],
)

_PREDEFINED_SETS: dict[str, ReviewRuleSet] = {
    "default": DEFAULT_RULES,
    "security": SECURITY_RULES,
    "research": RESEARCH_RULES,
    "code_review": CODE_REVIEW_RULES,
}


def get_ruleset(name: str) -> ReviewRuleSet:
    if name not in _PREDEFINED_SETS:
        raise ConfigurationError(f"Unknown ruleset: {name!r}. Available: {list(_PREDEFINED_SETS)}")
    return _PREDEFINED_SETS[name]
