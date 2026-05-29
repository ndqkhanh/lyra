"""
Context Validation System

Validates context quality and consistency.

Features:
- Quality scoring
- Consistency checking
- Validation rules
- Error detection
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum


class ValidationLevel(Enum):
    """Validation severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Validation issue"""
    level: ValidationLevel
    message: str
    field: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validation"""
    valid: bool
    score: float
    issues: List[ValidationIssue] = field(default_factory=list)

    def add_issue(self, issue: ValidationIssue):
        """Add validation issue"""
        self.issues.append(issue)
        if issue.level == ValidationLevel.ERROR:
            self.valid = False


class ContextValidator:
    """
    Context validator

    Validates context items for quality and consistency.
    """

    def __init__(self):
        self.rules: List[Callable] = []
        self.min_quality_score = 0.5

    def add_rule(self, rule: Callable[[Dict], Optional[ValidationIssue]]):
        """Add validation rule"""
        self.rules.append(rule)

    def validate(self, context: Dict) -> ValidationResult:
        """Validate context"""
        result = ValidationResult(valid=True, score=1.0)

        # Apply all rules
        for rule in self.rules:
            issue = rule(context)
            if issue:
                result.add_issue(issue)

        # Calculate quality score
        result.score = self._calculate_quality_score(context, result)

        # Check minimum quality
        if result.score < self.min_quality_score:
            result.add_issue(ValidationIssue(
                level=ValidationLevel.WARNING,
                message=f"Quality score {result.score:.2f} below minimum {self.min_quality_score}"
            ))

        return result

    def _calculate_quality_score(
        self,
        context: Dict,
        result: ValidationResult
    ) -> float:
        """Calculate quality score"""
        score = 1.0

        # Penalize for errors
        error_count = sum(1 for i in result.issues if i.level == ValidationLevel.ERROR)
        score -= error_count * 0.3

        # Penalize for warnings
        warning_count = sum(1 for i in result.issues if i.level == ValidationLevel.WARNING)
        score -= warning_count * 0.1

        # Check completeness
        required_fields = ['id', 'content']
        missing = [f for f in required_fields if f not in context]
        score -= len(missing) * 0.2

        return max(0.0, score)


class QualityChecker:
    """
    Quality checker

    Checks context quality metrics.
    """

    def __init__(self):
        self.metrics: Dict[str, Callable] = {}

    def add_metric(self, name: str, metric: Callable[[Dict], float]):
        """Add quality metric"""
        self.metrics[name] = metric

    def check(self, context: Dict) -> Dict[str, float]:
        """Check all metrics"""
        scores = {}
        for name, metric in self.metrics.items():
            scores[name] = metric(context)
        return scores

    def get_overall_score(self, context: Dict) -> float:
        """Get overall quality score"""
        scores = self.check(context)
        if not scores:
            return 0.0
        return sum(scores.values()) / len(scores)


class ConsistencyChecker:
    """
    Consistency checker

    Checks consistency across context items.
    """

    def __init__(self):
        self.items: List[Dict] = []

    def add_item(self, item: Dict):
        """Add item for consistency checking"""
        self.items.append(item)

    def check_consistency(self) -> List[ValidationIssue]:
        """Check consistency across items"""
        issues = []

        # Check for duplicates
        ids = [item.get('id') for item in self.items]
        duplicates = [id for id in ids if ids.count(id) > 1]
        if duplicates:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Duplicate IDs found: {set(duplicates)}"
            ))

        # Check for conflicts
        conflicts = self._check_conflicts()
        issues.extend(conflicts)

        return issues

    def _check_conflicts(self) -> List[ValidationIssue]:
        """Check for conflicting information"""
        issues = []

        # Group items by ID
        by_id: Dict[str, List[Dict]] = {}
        for item in self.items:
            item_id = item.get('id')
            if item_id:
                if item_id not in by_id:
                    by_id[item_id] = []
                by_id[item_id].append(item)

        # Check for conflicts within same ID
        for item_id, items in by_id.items():
            if len(items) > 1:
                # Check if content differs
                contents = [item.get('content') for item in items]
                if len(set(str(c) for c in contents)) > 1:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.WARNING,
                        message=f"Conflicting content for ID: {item_id}"
                    ))

        return issues


class ValidationPipeline:
    """
    Validation pipeline

    Runs multiple validators in sequence.
    """

    def __init__(self):
        self.validators: List[ContextValidator] = []
        self.quality_checker = QualityChecker()
        self.consistency_checker = ConsistencyChecker()

    def add_validator(self, validator: ContextValidator):
        """Add validator to pipeline"""
        self.validators.append(validator)

    def validate(self, context: Dict) -> ValidationResult:
        """Run validation pipeline"""
        result = ValidationResult(valid=True, score=1.0)

        # Run all validators
        for validator in self.validators:
            val_result = validator.validate(context)
            result.issues.extend(val_result.issues)
            if not val_result.valid:
                result.valid = False
            result.score = min(result.score, val_result.score)

        # Check quality
        quality_score = self.quality_checker.get_overall_score(context)
        result.score = (result.score + quality_score) / 2

        return result

    def validate_batch(self, contexts: List[Dict]) -> List[ValidationResult]:
        """Validate multiple contexts"""
        results = []

        # Add all to consistency checker
        for context in contexts:
            self.consistency_checker.add_item(context)

        # Check consistency
        consistency_issues = self.consistency_checker.check_consistency()

        # Validate each context
        for context in contexts:
            result = self.validate(context)
            # Add consistency issues to first result
            if results == [] and consistency_issues:
                result.issues.extend(consistency_issues)
            results.append(result)

        return results


# Built-in validation rules
def required_fields_rule(required: List[str]) -> Callable:
    """Rule to check required fields"""
    def rule(context: Dict) -> Optional[ValidationIssue]:
        missing = [f for f in required if f not in context]
        if missing:
            return ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Missing required fields: {missing}",
                suggestion=f"Add fields: {', '.join(missing)}"
            )
        return None
    return rule


def content_length_rule(min_length: int = 1, max_length: int = 10000) -> Callable:
    """Rule to check content length"""
    def rule(context: Dict) -> Optional[ValidationIssue]:
        content = str(context.get('content', ''))
        length = len(content)

        if length < min_length:
            return ValidationIssue(
                level=ValidationLevel.WARNING,
                message=f"Content too short: {length} < {min_length}",
                field='content'
            )
        elif length > max_length:
            return ValidationIssue(
                level=ValidationLevel.WARNING,
                message=f"Content too long: {length} > {max_length}",
                field='content'
            )
        return None
    return rule


def type_check_rule(field: str, expected_type: type) -> Callable:
    """Rule to check field type"""
    def rule(context: Dict) -> Optional[ValidationIssue]:
        if field in context:
            value = context[field]
            if not isinstance(value, expected_type):
                return ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"Field '{field}' has wrong type: {type(value).__name__} (expected {expected_type.__name__})",
                    field=field
                )
        return None
    return rule
