"""Data models for testing and quality assurance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class TestType(Enum):
    """Type of test."""

    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    SECURITY = "security"


class TestStatus(Enum):
    """Status of a test execution."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass(frozen=True)
class TestStrategy:
    """Immutable test strategy.

    Attributes:
        id: Unique identifier
        requirements_id: ID of associated requirements
        coverage_target: Target coverage percentage
        test_types: Types of tests to implement
        frameworks: Testing frameworks to use
        ci_integration: CI/CD integration notes
        created_at: ISO 8601 timestamp
    """

    id: str
    requirements_id: str
    coverage_target: int
    test_types: tuple[TestType, ...]
    frameworks: tuple[str, ...]
    ci_integration: str
    created_at: str

    @staticmethod
    def create(
        id: str,
        requirements_id: str,
        coverage_target: int = 80,
        test_types: list[TestType] | None = None,
        frameworks: list[str] | None = None,
        ci_integration: str = "",
    ) -> TestStrategy:
        """Create test strategy with auto-generated timestamp.

        Args:
            id: Unique identifier
            requirements_id: Requirements ID
            coverage_target: Target coverage (default 80%)
            test_types: Types of tests
            frameworks: Testing frameworks
            ci_integration: CI/CD integration notes

        Returns:
            New TestStrategy instance
        """
        return TestStrategy(
            id=id,
            requirements_id=requirements_id,
            coverage_target=coverage_target,
            test_types=tuple(test_types or [TestType.UNIT, TestType.INTEGRATION]),
            frameworks=tuple(frameworks or []),
            ci_integration=ci_integration,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


@dataclass(frozen=True)
class Test:
    """Immutable test case.

    Attributes:
        id: Unique identifier
        name: Test name
        type: Test type
        description: Test description
        file_path: Path to test file
        function_name: Test function name
        created_at: ISO 8601 timestamp
    """

    id: str
    name: str
    type: TestType
    description: str
    file_path: str
    function_name: str
    created_at: str

    @staticmethod
    def create(
        id: str,
        name: str,
        type: TestType,
        description: str,
        file_path: str,
        function_name: str,
    ) -> Test:
        """Create test with auto-generated timestamp.

        Args:
            id: Unique identifier
            name: Test name
            type: Test type
            description: Test description
            file_path: Test file path
            function_name: Test function name

        Returns:
            New Test instance
        """
        return Test(
            id=id,
            name=name,
            type=type,
            description=description,
            file_path=file_path,
            function_name=function_name,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


@dataclass(frozen=True)
class TestResult:
    """Immutable test execution result.

    Attributes:
        test_id: ID of executed test
        status: Test status
        duration_ms: Execution duration in milliseconds
        error_message: Error message if failed
        stack_trace: Stack trace if failed
    """

    test_id: str
    status: TestStatus
    duration_ms: int
    error_message: str | None = None
    stack_trace: str | None = None


@dataclass(frozen=True)
class TestResults:
    """Immutable test execution results.

    Attributes:
        id: Unique identifier
        total: Total number of tests
        passed: Number of passed tests
        failed: Number of failed tests
        skipped: Number of skipped tests
        coverage_percentage: Code coverage percentage
        results: Individual test results
        created_at: ISO 8601 timestamp
    """

    id: str
    total: int
    passed: int
    failed: int
    skipped: int
    coverage_percentage: float
    results: tuple[TestResult, ...]
    created_at: str

    @staticmethod
    def create(
        id: str,
        results: list[TestResult],
        coverage_percentage: float = 0.0,
    ) -> TestResults:
        """Create test results with auto-generated timestamp and counts.

        Args:
            id: Unique identifier
            results: List of test results
            coverage_percentage: Coverage percentage

        Returns:
            New TestResults instance
        """
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)

        return TestResults(
            id=id,
            total=len(results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            coverage_percentage=coverage_percentage,
            results=tuple(results),
            created_at=datetime.now(timezone.utc).isoformat(),
        )


@dataclass(frozen=True)
class QualityReport:
    """Immutable quality assurance report.

    Attributes:
        id: Unique identifier
        test_results: Test execution results
        quality_gates_passed: Whether quality gates passed
        issues: List of quality issues
        recommendations: List of recommendations
        approved: Whether release is approved
        created_at: ISO 8601 timestamp
    """

    id: str
    test_results: TestResults
    quality_gates_passed: bool
    issues: tuple[str, ...]
    recommendations: tuple[str, ...]
    approved: bool
    created_at: str

    @staticmethod
    def create(
        id: str,
        test_results: TestResults,
        quality_gates_passed: bool,
        approved: bool,
        issues: list[str] | None = None,
        recommendations: list[str] | None = None,
    ) -> QualityReport:
        """Create quality report with auto-generated timestamp.

        Args:
            id: Unique identifier
            test_results: Test results
            quality_gates_passed: Quality gates status
            approved: Approval status
            issues: Optional issues
            recommendations: Optional recommendations

        Returns:
            New QualityReport instance
        """
        return QualityReport(
            id=id,
            test_results=test_results,
            quality_gates_passed=quality_gates_passed,
            issues=tuple(issues or []),
            recommendations=tuple(recommendations or []),
            approved=approved,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


__all__ = [
    "TestStrategy",
    "Test",
    "TestResults",
    "TestResult",
    "QualityReport",
    "TestType",
    "TestStatus",
]
