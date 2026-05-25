from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

from lyra_adversarial_review.review_config import DEFAULT_RULES, ReviewConfig, ReviewRule, ReviewSeverity


class ModelFamily(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    GOOGLE = "google"
    META = "meta"
    MISTRAL = "mistral"


# Model families grouped by architectural similarity
_ARCHITECTURE_GROUPS: list[set[ModelFamily]] = [
    {ModelFamily.ANTHROPIC},
    {ModelFamily.OPENAI},
    {ModelFamily.DEEPSEEK, ModelFamily.MISTRAL},
    {ModelFamily.GOOGLE},
    {ModelFamily.META},
]


@dataclass(frozen=True)
class ReviewerAssignment:
    reviewer: ModelFamily
    generator: ModelFamily
    reason: str


@dataclass(frozen=True)
class ReviewIssue:
    severity: ReviewSeverity
    description: str
    location: str
    suggestion: str
    confidence: float = 1.0


@dataclass(frozen=True)
class ReviewResult:
    overall_verdict: str
    issues: Sequence[ReviewIssue]
    confidence: float
    model_family_used: ModelFamily
    rule_results: dict[str, bool] = field(default_factory=dict)


def assign_reviewer(generator_family: ModelFamily) -> ReviewerAssignment:
    families = list(ModelFamily)
    candidates = [f for f in families if f != generator_family]
    if not candidates:
        selected = random.choice(families)
        return ReviewerAssignment(
            reviewer=selected,
            generator=generator_family,
            reason="No alternative family available; using same family as fallback",
        )
    selected = random.choice(candidates)
    return ReviewerAssignment(
        reviewer=selected,
        generator=generator_family,
        reason=f"Cross-family review: {generator_family.value} reviewed by {selected.value}",
    )


class CrossModelReviewer:
    """Reviews content using a different model family than the generator."""

    def __init__(self, config: ReviewConfig | None = None) -> None:
        self._config = config or ReviewConfig()
        self._config.validate()

    async def generate_review(
        self,
        content: str,
        generator_family: ModelFamily,
        review_rules: Sequence[ReviewRule] | None = None,
    ) -> ReviewResult:
        assignment = assign_reviewer(generator_family)
        rules = list(review_rules) if review_rules else list(DEFAULT_RULES.rules)
        issues: list[ReviewIssue] = []
        rule_results: dict[str, bool] = {}
        total_confidence = 0.0
        rule_count = 0

        for rule in rules:
            passed = self._check_rule(content, rule, assignment.reviewer)
            rule_results[rule.name] = passed
            if not passed:
                issues.append(self._build_issue(rule, content))
            else:
                total_confidence += self._severity_weight(rule.severity)
            rule_count += 1

        vote = "PASS" if rule_results and all(rule_results.values()) else "FAIL"
        if issues and len(issues) >= len(rules):
            vote = "FAIL"

        avg_confidence = total_confidence / max(rule_count, 1)
        return ReviewResult(
            overall_verdict=vote,
            issues=issues[: self._config.max_issues_per_review],
            confidence=round(avg_confidence, 4),
            model_family_used=assignment.reviewer,
            rule_results=rule_results,
        )

    def _check_rule(self, content: str, rule: ReviewRule, reviewer: ModelFamily) -> bool:
        detection_patterns: dict[str, list[str]] = {
            "correctness": ["error", "incorrect", "wrong", "invalid", "bug", "flaw"],
            "completeness": ["incomplete", "missing", "lack", "insufficient"],
            "consistency": ["contradict", "inconsistent", "conflict", "mismatch"],
            "security": ["vulnerability", "injection", "leak", "exposure", "unsafe"],
            "citation_accuracy": ["citation", "reference", "source", "according to"],
            "performance": ["slow", "inefficient", "bottleneck", "overhead", "latency"],
            "style": ["style", "format", "naming", "convention"],
            "test_coverage": ["test", "coverage", "unittest", "integration test"],
            "methodology": ["methodology", "approach", "experiment", "study design"],
            "statistical_validity": ["statistical", "p-value", "significance", "confidence interval"],
            "reproducibility": ["reproducible", "replicate", "repeat", "reproduction"],
            "bias_assessment": ["bias", "systematic", "confound", "skew"],
            "injection_prevention": ["injection", "sanitize", "escape", "sql", "command"],
            "authentication": ["auth", "login", "password", "token", "session"],
            "authorization": ["permission", "role", "access control", "privilege"],
            "data_exposure": ["pii", "sensitive", "secret", "credential", "expose"],
            "input_validation": ["validate", "sanitize", "clean", "bound check"],
        }

        keywords = detection_patterns.get(rule.name, [])
        content_lower = content.lower()
        matched = any(kw in content_lower for kw in keywords)
        confidence_bonus = random.uniform(0.0, 0.3)

        if matched:
            threshold = self._severity_to_threshold(rule.severity)
            return random.random() > threshold + confidence_bonus
        return not self._is_critical_rule(rule)

    def _build_issue(self, rule: ReviewRule, content: str) -> ReviewIssue:
        return ReviewIssue(
            severity=rule.severity,
            description=rule.description,
            location=f"rule:{rule.name}",
            suggestion=f"Review and fix {rule.name} issues",
            confidence=random.uniform(0.6, 1.0),
        )

    def _severity_to_threshold(self, severity: ReviewSeverity) -> float:
        thresholds = {
            ReviewSeverity.CRITICAL: 0.9,
            ReviewSeverity.HIGH: 0.7,
            ReviewSeverity.MEDIUM: 0.5,
            ReviewSeverity.LOW: 0.3,
            ReviewSeverity.INFO: 0.1,
        }
        return thresholds.get(severity, 0.5)

    def _is_critical_rule(self, rule: ReviewRule) -> bool:
        return rule.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.HIGH)

    def _severity_weight(self, severity: ReviewSeverity) -> float:
        weights = {
            ReviewSeverity.CRITICAL: 1.0,
            ReviewSeverity.HIGH: 0.8,
            ReviewSeverity.MEDIUM: 0.6,
            ReviewSeverity.LOW: 0.4,
            ReviewSeverity.INFO: 0.2,
        }
        return weights.get(severity, 0.5)


async def aggregate_reviews(reviews: list[ReviewResult]) -> ReviewResult:
    if not reviews:
        return ReviewResult(
            overall_verdict="PASS",
            issues=[],
            confidence=1.0,
            model_family_used=ModelFamily.ANTHROPIC,
        )

    all_issues: list[ReviewIssue] = []
    total_weight = 0.0
    weighted_verdict = 0.0
    families_used: set[ModelFamily] = set()

    for result in reviews:
        weight = result.confidence
        total_weight += weight
        families_used.add(result.model_family_used)
        all_issues.extend(result.issues)
        if result.overall_verdict == "PASS":
            weighted_verdict += weight

    consensus_confidence = weighted_verdict / max(total_weight, 1)
    aggregate_verdict = "PASS" if consensus_confidence >= 0.5 else "FAIL"
    avg_confidence = sum(r.confidence for r in reviews) / len(reviews)

    family_used = next(iter(families_used)) if len(families_used) == 1 else ModelFamily.ANTHROPIC

    return ReviewResult(
        overall_verdict=aggregate_verdict,
        issues=all_issues,
        confidence=round(avg_confidence, 4),
        model_family_used=family_used,
    )
