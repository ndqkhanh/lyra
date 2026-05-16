"""
Closed-Loop Control with Verification.

Implements verification loops that check outputs and retry with corrections.
Target: +25% success rate through iterative refinement.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable


@dataclass
class VerificationResult:
    """Result of output verification."""

    passed: bool
    score: float  # 0.0 to 1.0
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class LoopIteration:
    """A single iteration in the closed loop."""

    iteration_id: str
    iteration_num: int
    input_data: Any
    output_data: Any
    verification: VerificationResult
    corrections_applied: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ClosedLoopExecution:
    """A complete closed-loop execution."""

    execution_id: str
    task_description: str
    max_iterations: int
    iterations: List[LoopIteration] = field(default_factory=list)
    final_success: bool = False
    final_output: Optional[Any] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


class ClosedLoopController:
    """
    Closed-loop control with verification and correction.

    Features:
    - Output verification after each iteration
    - Automatic correction based on verification feedback
    - Iterative refinement until success or max iterations
    - Learning from successful correction patterns
    """

    def __init__(self, max_iterations: int = 3):
        self.max_iterations = max_iterations
        self.executions: List[ClosedLoopExecution] = []

        # Statistics
        self.stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_iterations": 0,
            "avg_iterations_to_success": 0.0,
        }

    def execute_with_verification(
        self,
        task_description: str,
        execute_fn: Callable[[Any], Any],
        verify_fn: Callable[[Any], VerificationResult],
        correct_fn: Callable[[Any, VerificationResult], Any],
        initial_input: Any,
        max_iterations: Optional[int] = None
    ) -> tuple[bool, Any, List[LoopIteration]]:
        """
        Execute a task with closed-loop verification.

        Args:
            task_description: Description of the task
            execute_fn: Function to execute the task
            verify_fn: Function to verify the output
            correct_fn: Function to correct based on verification
            initial_input: Initial input to the task
            max_iterations: Max iterations (overrides default)

        Returns:
            (success, final_output, iterations)
        """
        max_iter = max_iterations or self.max_iterations

        execution = ClosedLoopExecution(
            execution_id=f"exec_{len(self.executions):06d}",
            task_description=task_description,
            max_iterations=max_iter,
        )

        current_input = initial_input
        success = False

        for i in range(max_iter):
            # Execute
            output = execute_fn(current_input)

            # Verify
            verification = verify_fn(output)

            # Create iteration record
            iteration = LoopIteration(
                iteration_id=f"{execution.execution_id}_iter_{i:02d}",
                iteration_num=i + 1,
                input_data=current_input,
                output_data=output,
                verification=verification,
            )

            execution.iterations.append(iteration)
            self.stats["total_iterations"] += 1

            # Check if verification passed
            if verification.passed:
                success = True
                execution.final_success = True
                execution.final_output = output
                break

            # Apply corrections for next iteration
            if i < max_iter - 1:  # Don't correct on last iteration
                corrections = self._generate_corrections(verification)
                iteration.corrections_applied = corrections
                current_input = correct_fn(current_input, verification)

        # Finalize execution
        execution.completed_at = datetime.now().isoformat()
        self.executions.append(execution)

        # Update statistics
        self.stats["total_executions"] += 1
        if success:
            self.stats["successful_executions"] += 1
            # Update average iterations to success
            total_success = self.stats["successful_executions"]
            current_avg = self.stats["avg_iterations_to_success"]
            new_avg = (current_avg * (total_success - 1) + len(execution.iterations)) / total_success
            self.stats["avg_iterations_to_success"] = new_avg
        else:
            self.stats["failed_executions"] += 1
            execution.final_output = execution.iterations[-1].output_data if execution.iterations else None

        return success, execution.final_output, execution.iterations

    def _generate_corrections(self, verification: VerificationResult) -> List[str]:
        """
        Generate correction actions from verification result.

        Args:
            verification: Verification result

        Returns:
            List of correction actions
        """
        corrections = []

        # Generate corrections based on issues
        for issue in verification.issues:
            if "syntax" in issue.lower():
                corrections.append("Fix syntax errors")
            elif "type" in issue.lower():
                corrections.append("Fix type errors")
            elif "logic" in issue.lower():
                corrections.append("Fix logic errors")
            elif "test" in issue.lower():
                corrections.append("Fix failing tests")
            elif "style" in issue.lower():
                corrections.append("Fix style issues")
            else:
                corrections.append(f"Address: {issue}")

        # Add suggestions as corrections
        for suggestion in verification.suggestions:
            corrections.append(f"Apply: {suggestion}")

        return corrections

    def get_success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.stats["total_executions"] == 0:
            return 0.0

        return self.stats["successful_executions"] / self.stats["total_executions"]

    def get_improvement_rate(self) -> float:
        """
        Calculate improvement rate from closed-loop control.

        Compares success rate with vs without verification loops.
        Assumes 60% baseline success rate without loops.
        """
        baseline_success_rate = 0.60
        actual_success_rate = self.get_success_rate()

        if baseline_success_rate == 0:
            return 0.0

        return (actual_success_rate - baseline_success_rate) / baseline_success_rate

    def get_stats(self) -> Dict[str, Any]:
        """Get closed-loop statistics."""
        success_rate = self.get_success_rate()
        improvement_rate = self.get_improvement_rate()

        return {
            **self.stats,
            "success_rate": success_rate,
            "improvement_rate": improvement_rate,
            "improvement_pct": improvement_rate * 100,
        }


class SimpleVerifier:
    """
    Simple verifier for common verification tasks.

    Provides basic verification functions for testing.
    """

    @staticmethod
    def verify_code_syntax(code: str) -> VerificationResult:
        """Verify code syntax (placeholder)."""
        # Simple heuristic checks
        issues = []

        if not code.strip():
            issues.append("Empty code")

        # Check for common syntax issues
        if code.count("(") != code.count(")"):
            issues.append("Unmatched parentheses")

        if code.count("{") != code.count("}"):
            issues.append("Unmatched braces")

        if code.count("[") != code.count("]"):
            issues.append("Unmatched brackets")

        passed = len(issues) == 0
        score = 1.0 if passed else 0.5

        return VerificationResult(
            passed=passed,
            score=score,
            issues=issues,
            suggestions=["Fix syntax errors"] if issues else [],
        )

    @staticmethod
    def verify_test_results(test_output: str) -> VerificationResult:
        """Verify test results (placeholder)."""
        issues = []

        # Check for test failures
        if "FAILED" in test_output or "ERROR" in test_output:
            issues.append("Tests failed")

        # Check if exactly 0 tests passed (not "10 passed", "20 passed", etc.)
        import re
        if re.search(r'\b0\s+passed\b', test_output):
            issues.append("No tests passed")

        passed = len(issues) == 0
        score = 1.0 if passed else 0.3

        return VerificationResult(
            passed=passed,
            score=score,
            issues=issues,
            suggestions=["Fix failing tests"] if issues else [],
        )

    @staticmethod
    def verify_output_quality(output: str, min_length: int = 10) -> VerificationResult:
        """Verify output quality (placeholder)."""
        issues = []

        if len(output) < min_length:
            issues.append(f"Output too short (min: {min_length})")

        if not output.strip():
            issues.append("Empty output")

        passed = len(issues) == 0
        score = 1.0 if passed else 0.4

        return VerificationResult(
            passed=passed,
            score=score,
            issues=issues,
            suggestions=["Provide more detailed output"] if issues else [],
        )
