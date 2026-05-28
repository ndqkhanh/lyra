"""
Debugging Assistant Skill - Structured debugging and root cause analysis.

Given error/bug description, produces:
- Root cause analysis (5 Whys)
- Hypothesis generation
- Diagnostic steps
- Fix suggestions with confidence levels
- Regression test suggestions

Outputs structured debugging plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ConfidenceLevel(StrEnum):
    """Confidence level for a diagnosis or fix."""

    CERTAIN = "CERTAIN"  # Proven by evidence
    HIGH = "HIGH"  # Strong evidence support
    MEDIUM = "MEDIUM"  # Plausible, needs more evidence
    LOW = "LOW"  # Speculative
    GUESS = "GUESS"  # Educated guess


class BugCategory(StrEnum):
    """Categories of software bugs."""

    LOGIC = "logic_error"
    NULL_POINTER = "null_pointer"
    RACE_CONDITION = "race_condition"
    MEMORY_LEAK = "memory_leak"
    TYPE_ERROR = "type_error"
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    PERFORMANCE = "performance"
    SECURITY = "security"
    NETWORK = "network"
    CONCURRENCY = "concurrency"
    REGRESSION = "regression"
    ENVIRONMENT = "environment"
    DATA = "data_issue"
    BOUNDARY = "boundary_condition"


@dataclass(frozen=True)
class WhyAnalysis:
    """A single level in the 5 Whys analysis."""

    level: int
    question: str
    answer: str
    evidence: str


@dataclass(frozen=True)
class Hypothesis:
    """A single debugging hypothesis."""

    id: str
    description: str
    category: BugCategory
    confidence: ConfidenceLevel
    supporting_evidence: tuple[str, ...]
    contradicting_evidence: tuple[str, ...]


@dataclass(frozen=True)
class DiagnosticStep:
    """A recommended diagnostic step."""

    step_number: int
    action: str
    tool_or_command: str
    expected_outcome: str
    estimated_time: str
    priority: str


@dataclass(frozen=True)
class FixSuggestion:
    """A suggested fix with confidence level."""

    id: str
    description: str
    confidence: ConfidenceLevel
    rationale: str
    code_change: str
    risk_of_change: str
    tested: bool


@dataclass(frozen=True)
class RegressionTestSuggestion:
    """A suggested regression test to prevent recurrence."""

    test_name: str
    description: str
    test_type: str
    input_conditions: str
    expected_behavior: str


@dataclass(frozen=True)
class DebuggingPlan:
    """Complete debugging plan."""

    error_summary: str
    environment: str
    bug_category: BugCategory | None
    five_whys: tuple[WhyAnalysis, ...]
    hypotheses: tuple[Hypothesis, ...]
    diagnostic_steps: tuple[DiagnosticStep, ...]
    fix_suggestions: tuple[FixSuggestion, ...]
    regression_tests: tuple[RegressionTestSuggestion, ...]
    recommendations: tuple[str, ...]


class DebuggingAssistant:
    """Debugging skill producing structured root cause analyses."""

    def run(self, input_data: dict) -> dict:
        """Run debugging analysis.

        Args:
            input_data: Dictionary with keys:
                - error_description: Description of the error or bug
                - environment: Optional environment details (default "Unknown")
                - stack_trace: Optional stack trace for deeper analysis
                - code_context: Optional relevant source code

        Returns:
            Dictionary with debugging plan data.
        """
        error_desc = input_data.get("error_description", "")
        if not error_desc:
            return {"error": "No error description provided"}

        environment = input_data.get("environment", "Unknown")
        stack_trace = input_data.get("stack_trace", "")
        code_context = input_data.get("code_context", "")

        combined = f"{error_desc}\n{stack_trace}\n{code_context}".lower()

        bug_category = self._classify_bug(combined)
        five_whys = self._run_five_whys(error_desc, stack_trace)
        hypotheses = self._generate_hypotheses(combined, error_desc)
        diagnostics = self._generate_diagnostic_steps(combined)
        fixes = self._generate_fixes(combined, bug_category)
        regression_tests = self._generate_regression_tests(bug_category, error_desc)
        recommendations = self._generate_recommendations(bug_category)

        return DebuggingPlan(
            error_summary=error_desc[:200],
            environment=environment,
            bug_category=bug_category,
            five_whys=tuple(five_whys),
            hypotheses=tuple(hypotheses),
            diagnostic_steps=tuple(diagnostics),
            fix_suggestions=tuple(fixes),
            regression_tests=tuple(regression_tests),
            recommendations=tuple(recommendations),
        ).__dict__ | {
            "hypotheses": [h.__dict__ for h in hypotheses],
            "diagnostic_steps": [d.__dict__ for d in diagnostics],
            "fix_suggestions": [f.__dict__ for f in fixes],
            "regression_tests": [t.__dict__ for t in regression_tests],
        }

    @staticmethod
    def _classify_bug(combined: str) -> BugCategory | None:
        mappings: list[tuple[list[str], BugCategory]] = [
            (["null", "none", "nil", "undefined", "attributeerror", "keyerror",
              "indexerror", "zerodivision"], BugCategory.NULL_POINTER),
            (["race", "deadlock", "starvation", "thread", "mutex", "lock"],
             BugCategory.RACE_CONDITION),
            (["memory", "leak", "oom", "out of memory", "allocation"],
             BugCategory.MEMORY_LEAK),
            (["typeerror", "type mismatch", "type", "cast", "conversion"],
             BugCategory.TYPE_ERROR),
            (["config", "setting", "environment variable", "env", "ini", "yaml",
              "toml"], BugCategory.CONFIGURATION),
            (["timeout", "connection", "socket", "http", "network", "dns"],
             BugCategory.NETWORK),
            (["slow", "latency", "timeout", "performance", "bottleneck"],
             BugCategory.PERFORMANCE),
            (["sql", "injection", "xss", "csrf", "auth", "permission", "access denied"],
             BugCategory.SECURITY),
            (["concurrent", "parallel", "async", "await", "coroutine"],
             BugCategory.CONCURRENCY),
            (["regression", "used to work", "previously", "broke", "stopped working"],
             BugCategory.REGRESSION),
            (["import", "module", "package", "library", "version", "dependency"],
             BugCategory.DEPENDENCY),
            (["unexpected value", "boundary", "edge case", "off-by-one", "overflow"],
             BugCategory.BOUNDARY),
        ]

        for keywords, category in mappings:
            if any(kw in combined for kw in keywords):
                return category

        return BugCategory.LOGIC  # Default

    @staticmethod
    def _run_five_whys(
        error_desc: str, stack_trace: str
    ) -> list[WhyAnalysis]:
        whys: list[tuple[str, str, str]] = [
            (
                f"Why did the {error_desc.split()[0] if error_desc.split() else 'error'} occur?",
                "Initial observation shows unexpected behavior in the system",
                "Error/failure observed at runtime",
            ),
            (
                "Why did that condition exist?",
                "A code path did not handle this specific case",
                "Stack trace shows execution reached unexpected code path",
            ),
            (
                "Why was this code path not handled?",
                "Missing validation or edge case handling in the logic",
                "Code review reveals no guard clause for this condition",
            ),
            (
                "Why was the validation not implemented?",
                "The requirement/design did not specify this edge case",
                "Requirements document does not cover this scenario",
            ),
            (
                "Why was the requirement incomplete?",
                "The edge case was not identified during requirement analysis",
                "Similar edge cases found in related features also lack coverage",
            ),
        ]

        analyses: list[WhyAnalysis] = []
        for i, (question, answer, evidence) in enumerate(whys, 1):
            analyses.append(
                WhyAnalysis(
                    level=i,
                    question=question,
                    answer=answer,
                    evidence=evidence,
                )
            )
        return analyses

    @staticmethod
    def _generate_hypotheses(
        combined: str, error_desc: str
    ) -> list[Hypothesis]:
        has_null = any(kw in combined for kw in ["null", "none", "empty", "missing"])
        has_type = "type" in combined or "typeerror" in combined
        has_input = any(kw in combined for kw in ["input", "parameter", "argument", "value"])
        has_config = any(kw in combined for kw in ["config", "setting", "environment"])
        has_state = any(kw in combined for kw in ["state", "cache", "stale", "mutation"])

        hypotheses: list[Hypothesis] = []

        if has_null or has_input:
            hypotheses.append(
                Hypothesis(
                    id="H-001",
                    description="Input validation failure: unexpected None/null value propagated",
                    category=BugCategory.NULL_POINTER if has_null else BugCategory.LOGIC,
                    confidence=ConfidenceLevel.HIGH,
                    supporting_evidence=(f"Error context mentions null/missing values: {error_desc[:100]}",),
                    contradicting_evidence=("Input validation code exists but may be bypassed",),
                )
            )

        if has_type:
            hypotheses.append(
                Hypothesis(
                    id="H-002",
                    description="Type mismatch: variable received unexpected type",
                    category=BugCategory.TYPE_ERROR,
                    confidence=ConfidenceLevel.HIGH,
                    supporting_evidence=("TypeError mentioned in error context",),
                    contradicting_evidence=("Type hints suggest correct types",),
                )
            )

        if has_config:
            hypotheses.append(
                Hypothesis(
                    id="H-003",
                    description="Configuration error: wrong or missing environment settings",
                    category=BugCategory.CONFIGURATION,
                    confidence=ConfidenceLevel.MEDIUM,
                    supporting_evidence=("Configuration-related keywords found in context",),
                    contradicting_evidence=("Configuration validated at startup",),
                )
            )

        if has_state:
            hypotheses.append(
                Hypothesis(
                    id="H-004",
                    description="Stale or corrupted state: cached data does not reflect current reality",
                    category=BugCategory.DATA,
                    confidence=ConfidenceLevel.MEDIUM,
                    supporting_evidence=("State/cache/mutation keywords in error context",),
                    contradicting_evidence=("State management appears correct in normal flow",),
                )
            )

        # Always add a generic hypothesis
        hypotheses.append(
            Hypothesis(
                id="H-005",
                description="Race condition: concurrent access to shared resource",
                category=BugCategory.RACE_CONDITION,
                confidence=ConfidenceLevel.LOW,
                supporting_evidence=("Intermittent failures suggest timing-related bug",),
                contradicting_evidence=("No explicit async/concurrency code in call path",),
            )
        )

        return hypotheses

    @staticmethod
    def _generate_diagnostic_steps(combined: str) -> list[DiagnosticStep]:
        return [
            DiagnosticStep(
                step_number=1,
                action="Reproduce the error with minimal, deterministic inputs",
                tool_or_command="Unit test with specific input values",
                expected_outcome="Consistent reproduction of the error",
                estimated_time="15 min",
                priority="HIGH",
            ),
            DiagnosticStep(
                step_number=2,
                action="Add logging at entry/exit points of suspect function",
                tool_or_command="print() / logging.debug() / structured logging",
                expected_outcome="Log output reveals input values and execution path",
                estimated_time="10 min",
                priority="HIGH",
            ),
            DiagnosticStep(
                step_number=3,
                action="Verify all input values are within expected ranges and types",
                tool_or_command="Assertions / type checks / boundary testing",
                expected_outcome="Identify out-of-range or unexpected input values",
                estimated_time="10 min",
                priority="HIGH",
            ),
            DiagnosticStep(
                step_number=4,
                action="Check for side effects: does function modify shared state?",
                tool_or_command="Code review / breakpoint on state mutations",
                expected_outcome="Identify unintended state modifications",
                estimated_time="20 min",
                priority="MEDIUM",
            ),
            DiagnosticStep(
                step_number=5,
                action="Inspect stack trace at point of failure",
                tool_or_command="pdb / ipdb / IDE debugger",
                expected_outcome="Identify exact line and variable values at failure",
                estimated_time="15 min",
                priority="HIGH",
            ),
            DiagnosticStep(
                step_number=6,
                action="Check for recent changes in the suspect code path",
                tool_or_command="git log / git blame / git diff",
                expected_outcome="Identify the commit that introduced the bug",
                estimated_time="10 min",
                priority="MEDIUM",
            ),
            DiagnosticStep(
                step_number=7,
                action="Write and run a focused unit test for the suspect function",
                tool_or_command="pytest with targeted test case",
                expected_outcome="Test confirms or rules out the hypothesis",
                estimated_time="20 min",
                priority="MEDIUM",
            ),
        ]

    @staticmethod
    def _generate_fixes(
        combined: str, bug_category: BugCategory | None
    ) -> list[FixSuggestion]:
        fixes: list[FixSuggestion] = []

        fixes.append(
            FixSuggestion(
                id="F-001",
                description="Add null/empty check before accessing the suspect value",
                confidence=ConfidenceLevel.HIGH,
                rationale="Most common cause: missing guard clause for None/null values",
                code_change='if value is None:\n    return default_value  # or handle gracefully',
                risk_of_change="LOW",
                tested=False,
            )
        )

        fixes.append(
            FixSuggestion(
                id="F-002",
                description="Add input validation and type checking at function boundary",
                confidence=ConfidenceLevel.MEDIUM,
                rationale="Prevents invalid data from propagating through the system",
                code_change="def func(value: ExpectedType) -> Result:\n    if not isinstance(value, ExpectedType):\n        raise TypeError(f'Expected {ExpectedType}, got {type(value)}')",
                risk_of_change="LOW",
                tested=False,
            )
        )

        if bug_category == BugCategory.CONFIGURATION:
            fixes.append(
                FixSuggestion(
                    id="F-003",
                    description="Add configuration validation at startup with clear error messages",
                    confidence=ConfidenceLevel.HIGH,
                    rationale="Fail fast with clear message instead of cryptic runtime error",
                    code_change="def validate_config():\n    required_keys = [...]\n    missing = [k for k in required_keys if k not in config]\n    if missing:\n        raise ConfigError(f'Missing: {missing}')",
                    risk_of_change="LOW",
                    tested=False,
                )
            )
        elif bug_category in (BugCategory.RACE_CONDITION, BugCategory.CONCURRENCY):
            fixes.append(
                FixSuggestion(
                    id="F-003",
                    description="Add synchronization (lock/mutex) around shared resource access",
                    confidence=ConfidenceLevel.HIGH,
                    rationale="Prevents concurrent access from corrupting shared state",
                    code_change="from threading import Lock\n\n_lock = Lock()\ndef shared_operation():\n    with _lock:\n        # critical section",
                    risk_of_change="MEDIUM",
                    tested=False,
                )
            )
        else:
            fixes.append(
                FixSuggestion(
                    id="F-003",
                    description="Add specific edge case handling for the failing scenario",
                    confidence=ConfidenceLevel.MEDIUM,
                    rationale="The failing case was not accounted for in the original implementation",
                    code_change="# Add handling for the specific edge case identified\nif edge_condition:\n    handle_specially()",
                    risk_of_change="LOW",
                    tested=False,
                )
            )

        return fixes

    @staticmethod
    def _generate_regression_tests(
        bug_category: BugCategory | None, error_desc: str
    ) -> list[RegressionTestSuggestion]:
        return [
            RegressionTestSuggestion(
                test_name="test_reproduce_reported_error",
                description=f"Create a test that reproduces the exact error: {error_desc[:80]}",
                test_type="Unit test",
                input_conditions="Use the same inputs/conditions that triggered the bug",
                expected_behavior="Should pass without error after fix is applied",
            ),
            RegressionTestSuggestion(
                test_name="test_null_input_handling",
                description="Ensure all functions in the call chain handle null/None gracefully",
                test_type="Property-based test",
                input_conditions="Pass None/null values to each function in the call chain",
                expected_behavior="Functions either handle null gracefully or raise clear TypeError",
            ),
            RegressionTestSuggestion(
                test_name="test_boundary_values",
                description="Test edge cases at boundaries of input domain",
                test_type="Boundary value test",
                input_conditions="Test with min, max, empty, and overflow values",
                expected_behavior="All boundary cases handled without crash",
            ),
            RegressionTestSuggestion(
                test_name="test_error_message_clarity",
                description="Verify error messages are actionable and clear",
                test_type="Integration test",
                input_conditions="Trigger each known error condition",
                expected_behavior="Error messages identify the problem and suggest next steps",
            ),
        ]

    @staticmethod
    def _generate_recommendations(
        bug_category: BugCategory | None,
    ) -> list[str]:
        base_recs: list[str] = [
            "Add regression test before applying the fix (test-driven debugging)",
            "Apply the fix in isolation and run full test suite",
            "Consider a broader audit for similar patterns in the codebase",
        ]

        if bug_category:
            category_recs: dict[BugCategory, list[str]] = {
                BugCategory.NULL_POINTER: [
                    "Adopt Optional types or null-safety patterns",
                    "Add preconditions (guards) at all public API boundaries",
                ],
                BugCategory.RACE_CONDITION: [
                    "Audit all shared state for thread safety",
                    "Consider using immutable data structures",
                ],
                BugCategory.CONFIGURATION: [
                    "Implement configuration schema validation",
                    "Add startup health check that validates all config",
                ],
                BugCategory.PERFORMANCE: [
                    "Add performance benchmarks to CI pipeline",
                    "Set latency alert thresholds in production monitoring",
                ],
                BugCategory.SECURITY: [
                    "Run security audit (bandit/safety) on affected modules",
                    "Review OWASP Top 10 for related categories",
                ],
            }
            base_recs.extend(category_recs.get(bug_category, []))

        return base_recs
