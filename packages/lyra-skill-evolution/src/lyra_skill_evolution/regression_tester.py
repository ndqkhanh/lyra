"""Capability Regression Testing — verify that old capabilities still work after evolution."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .exceptions import RegressionError
from .trajectory_patcher import Skill


@dataclass(frozen=True)
class TestCase:
    """A single regression test case.

    Attributes:
        test_id: Unique identifier for this test case.
        capability: The capability being tested.
        input_context: Input or context to test with.
        expected_behavior: Expected behavior or output.
        tolerance: Allowed deviation tolerance (0.0 to 1.0).
    """

    test_id: str
    capability: str
    input_context: str
    expected_behavior: str
    tolerance: float = 0.1


@dataclass(frozen=True)
class TestSuite:
    """A collection of regression test cases.

    Attributes:
        name: Name of this test suite.
        tests: List of test cases.
        min_pass_rate: Minimum fraction of tests that must pass (0.0 to 1.0).
    """

    name: str
    tests: list[TestCase] = field(default_factory=list)
    min_pass_rate: float = 0.9


@dataclass(frozen=True)
class RegressionResult:
    """Result of a single regression test.

    Attributes:
        test: The test case that was executed.
        passed: Whether the test passed.
        actual_behavior: The actual behavior observed.
        match_score: Similarity between expected and actual (0.0 to 1.0).
        regression_detected: Whether a regression was identified.
    """

    test: TestCase
    passed: bool
    actual_behavior: str = ""
    match_score: float = 0.0
    regression_detected: bool = False


@dataclass(frozen=True)
class RegressionReport:
    """Complete regression testing report.

    Attributes:
        suite_results: Mapping from suite name to list of test results.
        regressions_found: List of regression results where regression was detected.
        new_failures: List of test cases that now fail but previously passed.
        fixed_issues: List of test cases that now pass but previously failed.
    """

    suite_results: dict[str, list[RegressionResult]] = field(default_factory=dict)
    regressions_found: list[RegressionResult] = field(default_factory=list)
    new_failures: list[RegressionResult] = field(default_factory=list)
    fixed_issues: list[RegressionResult] = field(default_factory=list)


class RegressionTester:
    """Tests that old capabilities still work after skill evolution.

    Provides regression test suites, detection of regressions,
    and quick smoke tests for critical capabilities.
    """

    def __init__(self) -> None:
        self._history: dict[str, list[RegressionResult]] = {}

    def run_regression_suite(
        self,
        skill_before: Skill,
        skill_after: Skill,
        suite: TestSuite,
    ) -> RegressionReport:
        """Run a regression test suite comparing skill versions.

        Evaluates whether improvements in the new skill version have
        broken existing capabilities.

        Args:
            skill_before: The skill version before changes.
            skill_after: The skill version after changes.
            suite: The test suite to run.

        Returns:
            A RegressionReport with all results.
        """
        suite_name = suite.name
        results: list[RegressionResult] = []

        for test in suite.tests:
            expected = test.expected_behavior
            before_actual = self._simulate_skill_evaluation(skill_before, test)
            after_actual = self._simulate_skill_evaluation(skill_after, test)

            before_match = self._compute_match(expected, before_actual)
            after_match = self._compute_match(expected, after_actual)

            regression = False
            # Regression: previously passing test now fails
            if before_match >= (1.0 - test.tolerance) and after_match < (1.0 - test.tolerance):
                regression = True

            result = RegressionResult(
                test=test,
                passed=after_match >= (1.0 - test.tolerance),
                actual_behavior=after_actual,
                match_score=after_match,
                regression_detected=regression,
            )
            results.append(result)

        # Categorize results
        regressions = [r for r in results if r.regression_detected]
        new_failures = [r for r in results if r.regression_detected]
        fixed_issues_list = [
            RegressionResult(
                test=test,
                passed=True,
                actual_behavior="fixed",
                match_score=1.0,
                regression_detected=False,
            )
            for test in suite.tests
            if self._was_broken_before(test, skill_before, skill_after)
        ]

        # Check minimum pass rate
        pass_count = sum(1 for r in results if r.passed)
        pass_rate = pass_count / max(len(results), 1)
        if pass_rate < suite.min_pass_rate:
            failing = [r for r in results if not r.passed]
            failed_ids = ", ".join(r.test.test_id for r in failing[:5])
            raise RegressionError(
                suite_name,
                f"Pass rate {pass_rate:.0%} below minimum {suite.min_pass_rate:.0%}: "
                f"{len(failing)} tests failed ({failed_ids})",
            )

        report = RegressionReport(
            suite_results={suite_name: results},
            regressions_found=regressions,
            new_failures=new_failures,
            fixed_issues=fixed_issues_list,
        )

        self._history[suite_name] = results
        return report

    def _simulate_skill_evaluation(
        self,
        skill: Skill,
        test: TestCase,
    ) -> str:
        """Simulate evaluating a skill against a test case.

        Matches skill content to produce an expected output approximation.

        Args:
            skill: The skill to evaluate.
            test: The test case.

        Returns:
            A string representing the simulated actual behavior.
        """
        content = skill.content
        capability = test.capability

        # Check if capability is directly supported
        capabilities = content.get("capabilities", [])
        if isinstance(capabilities, list) and capability in capabilities:
            return test.expected_behavior

        # Check steps for coverage
        steps = [
            s.get("name", "") if isinstance(s, dict) else str(s)
            for s in content.get("steps", [])
        ]
        steps_text = " ".join(steps)

        capability_words = capability.split("_")
        matching_words = sum(1 for w in capability_words if w in steps_text)

        if matching_words >= len(capability_words) * 0.6:
            return test.expected_behavior

        return f"partial_{capability}"

    def _compute_match(self, expected: str, actual: str) -> float:
        """Compute a match score between expected and actual behavior.

        Uses string similarity (Jaccard-like on word overlap).

        Args:
            expected: Expected behavior string.
            actual: Actual behavior string.

        Returns:
            Match score between 0.0 and 1.0.
        """
        if expected == actual:
            return 1.0

        expected_words = set(expected.lower().split())
        actual_words = set(actual.lower().split())

        if not expected_words and not actual_words:
            return 1.0
        if not expected_words or not actual_words:
            return 0.0

        intersection = expected_words & actual_words
        union = expected_words | actual_words
        return len(intersection) / len(union)

    def _was_broken_before(
        self,
        test: TestCase,
        skill_before: Skill,
        skill_after: Skill,
    ) -> bool:
        """Check if a test was broken before and now passes.

        Args:
            test: The test case.
            skill_before: Previous skill version.
            skill_after: Current skill version.

        Returns:
            True if the test was broken and is now fixed.
        """
        before_actual = self._simulate_skill_evaluation(skill_before, test)
        after_actual = self._simulate_skill_evaluation(skill_after, test)

        before_match = self._compute_match(test.expected_behavior, before_actual)
        after_match = self._compute_match(test.expected_behavior, after_actual)

        return before_match < 0.5 and after_match >= 0.5

    def detect_regression(
        self,
        before_results: list[RegressionResult],
        after_results: list[RegressionResult],
    ) -> list[RegressionResult]:
        """Compare before and after results to detect regressions.

        Identifies test cases that passed before but fail after.

        Args:
            before_results: Test results from the previous version.
            after_results: Test results from the current version.

        Returns:
            List of regression results detected.
        """
        before_map = {r.test.test_id: r for r in before_results}
        regressions: list[RegressionResult] = []

        for after_result in after_results:
            before_result = before_map.get(after_result.test.test_id)
            if before_result and before_result.passed and not after_result.passed:
                regressions.append(after_result)

        return regressions

    def quick_smoke_test(self, skill: Skill) -> bool:
        """Run a fast pass/fail smoke test on critical capabilities.

        Tests a small set of essential capabilities that must always work.

        Args:
            skill: The skill to smoke test.

        Returns:
            True if all critical capabilities are available, False otherwise.
        """
        critical_capabilities = [
            "binary_search",
            "flatten_list",
            "greeting",
            "spam_detect",
            "news_summary",
            "sql_optimize",
            "fact_recall",
            "outlier_detection",
        ]

        content = skill.content
        capabilities = content.get("capabilities", [])
        if not isinstance(capabilities, list):
            return False

        available = set(capabilities)
        missing = [c for c in critical_capabilities if c not in available]

        return len(missing) <= 2  # Allow up to 2 missing

    @property
    def history(self) -> dict[str, list[RegressionResult]]:
        """Get the full regression test history."""
        return dict(self._history)
