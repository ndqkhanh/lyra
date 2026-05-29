"""
Tests for Context Validation System
"""

import pytest
from lyra_core.validation import (
    ValidationLevel,
    ValidationIssue,
    ValidationResult,
    ContextValidator,
    QualityChecker,
    ConsistencyChecker,
    ValidationPipeline,
    required_fields_rule,
    content_length_rule,
    type_check_rule
)


class TestValidationIssue:
    """Test ValidationIssue"""

    def test_initialization(self):
        """Test issue initialization"""
        issue = ValidationIssue(
            level=ValidationLevel.ERROR,
            message="Test error"
        )
        assert issue.level == ValidationLevel.ERROR
        assert issue.message == "Test error"


class TestValidationResult:
    """Test ValidationResult"""

    def test_initialization(self):
        """Test result initialization"""
        result = ValidationResult(valid=True, score=1.0)
        assert result.valid is True
        assert result.score == 1.0

    def test_add_issue(self):
        """Test adding issues"""
        result = ValidationResult(valid=True, score=1.0)
        issue = ValidationIssue(
            level=ValidationLevel.ERROR,
            message="Test error"
        )

        result.add_issue(issue)
        assert len(result.issues) == 1
        assert result.valid is False  # Error makes it invalid


class TestContextValidator:
    """Test ContextValidator"""

    def test_initialization(self):
        """Test validator initialization"""
        validator = ContextValidator()
        assert len(validator.rules) == 0

    def test_add_rule(self):
        """Test adding rules"""
        validator = ContextValidator()

        def test_rule(context):
            return None

        validator.add_rule(test_rule)
        assert len(validator.rules) == 1

    def test_validate_valid_context(self):
        """Test validating valid context"""
        validator = ContextValidator()
        context = {'id': '1', 'content': 'test'}

        result = validator.validate(context)
        assert result.valid is True

    def test_validate_with_rule(self):
        """Test validation with rule"""
        validator = ContextValidator()

        def error_rule(context):
            return ValidationIssue(
                level=ValidationLevel.ERROR,
                message="Test error"
            )

        validator.add_rule(error_rule)
        context = {'id': '1', 'content': 'test'}

        result = validator.validate(context)
        assert result.valid is False
        assert len(result.issues) == 1

    def test_quality_score(self):
        """Test quality score calculation"""
        validator = ContextValidator()
        context = {'id': '1', 'content': 'test'}

        result = validator.validate(context)
        assert result.score > 0.0


class TestQualityChecker:
    """Test QualityChecker"""

    def test_initialization(self):
        """Test checker initialization"""
        checker = QualityChecker()
        assert len(checker.metrics) == 0

    def test_add_metric(self):
        """Test adding metrics"""
        checker = QualityChecker()

        def test_metric(context):
            return 1.0

        checker.add_metric("test", test_metric)
        assert "test" in checker.metrics

    def test_check(self):
        """Test checking metrics"""
        checker = QualityChecker()

        def test_metric(context):
            return 0.8

        checker.add_metric("test", test_metric)
        context = {'id': '1', 'content': 'test'}

        scores = checker.check(context)
        assert scores["test"] == 0.8

    def test_overall_score(self):
        """Test overall score"""
        checker = QualityChecker()

        checker.add_metric("metric1", lambda c: 0.8)
        checker.add_metric("metric2", lambda c: 0.6)

        context = {'id': '1', 'content': 'test'}
        score = checker.get_overall_score(context)

        assert score == 0.7  # Average of 0.8 and 0.6


class TestConsistencyChecker:
    """Test ConsistencyChecker"""

    def test_initialization(self):
        """Test checker initialization"""
        checker = ConsistencyChecker()
        assert len(checker.items) == 0

    def test_add_item(self):
        """Test adding items"""
        checker = ConsistencyChecker()
        checker.add_item({'id': '1', 'content': 'test'})

        assert len(checker.items) == 1

    def test_check_duplicates(self):
        """Test duplicate detection"""
        checker = ConsistencyChecker()
        checker.add_item({'id': '1', 'content': 'test1'})
        checker.add_item({'id': '1', 'content': 'test2'})

        issues = checker.check_consistency()
        assert len(issues) > 0
        assert any('Duplicate' in i.message for i in issues)

    def test_check_conflicts(self):
        """Test conflict detection"""
        checker = ConsistencyChecker()
        checker.add_item({'id': '1', 'content': 'test1'})
        checker.add_item({'id': '1', 'content': 'test2'})

        issues = checker.check_consistency()
        # Should detect conflicting content
        assert len(issues) > 0


class TestValidationPipeline:
    """Test ValidationPipeline"""

    def test_initialization(self):
        """Test pipeline initialization"""
        pipeline = ValidationPipeline()
        assert len(pipeline.validators) == 0

    def test_add_validator(self):
        """Test adding validators"""
        pipeline = ValidationPipeline()
        validator = ContextValidator()

        pipeline.add_validator(validator)
        assert len(pipeline.validators) == 1

    def test_validate(self):
        """Test validation"""
        pipeline = ValidationPipeline()
        validator = ContextValidator()
        pipeline.add_validator(validator)

        context = {'id': '1', 'content': 'test'}
        result = pipeline.validate(context)

        assert result is not None
        assert isinstance(result, ValidationResult)

    def test_validate_batch(self):
        """Test batch validation"""
        pipeline = ValidationPipeline()
        validator = ContextValidator()
        pipeline.add_validator(validator)

        contexts = [
            {'id': '1', 'content': 'test1'},
            {'id': '2', 'content': 'test2'}
        ]

        results = pipeline.validate_batch(contexts)
        assert len(results) == 2


class TestBuiltInRules:
    """Test built-in validation rules"""

    def test_required_fields_rule(self):
        """Test required fields rule"""
        rule = required_fields_rule(['id', 'content'])

        # Valid context
        context = {'id': '1', 'content': 'test'}
        issue = rule(context)
        assert issue is None

        # Missing field
        context = {'id': '1'}
        issue = rule(context)
        assert issue is not None
        assert issue.level == ValidationLevel.ERROR

    def test_content_length_rule(self):
        """Test content length rule"""
        rule = content_length_rule(min_length=5, max_length=100)

        # Valid length
        context = {'content': 'test content'}
        issue = rule(context)
        assert issue is None

        # Too short
        context = {'content': 'hi'}
        issue = rule(context)
        assert issue is not None
        assert issue.level == ValidationLevel.WARNING

    def test_type_check_rule(self):
        """Test type check rule"""
        rule = type_check_rule('id', str)

        # Valid type
        context = {'id': '1'}
        issue = rule(context)
        assert issue is None

        # Wrong type
        context = {'id': 123}
        issue = rule(context)
        assert issue is not None
        assert issue.level == ValidationLevel.ERROR


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
