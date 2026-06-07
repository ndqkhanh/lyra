"""
Mutation-Gated Verification (SABER pattern).

Instead of asking "is this answer correct?" (which LLMs overestimate),
mutate the answer and check if the mutant still "passes."
If a mutant passes, the original is likely brittle/copied.

Based on software engineering mutation testing adapted to LLM outputs.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Literal


class MutationType(Enum):
    """Types of mutations to apply."""

    VARIABLE_RENAME = "variable_rename"
    ARGUMENT_SWAP = "argument_swap"
    CONSTANT_SHIFT = "constant_shift"
    LOGIC_FLIP = "logic_flip"
    RETURN_FLIP = "return_flip"


@dataclass
class MutantResult:
    """Result of executing a mutant."""

    name: str
    mutation_type: MutationType
    passed: bool | None  # None = runtime error
    error: str | None = None
    mutated_code: str = ""


@dataclass
class VerificationResult:
    """Result of mutation-gated verification."""

    verdict: Literal["confirmed", "suspect", "uncertain"]
    reason: str
    details: list[MutantResult]
    confidence: float
    original_code: str
    n_mutants: int
    passed_mutants: int
    failed_mutants: int
    errored_mutants: int


class CodeMutator:
    """Apply mutations to code for verification testing."""

    def __init__(self):
        """Initialize code mutator."""
        self.strategies: dict[MutationType, Callable[[str], str]] = {
            MutationType.VARIABLE_RENAME: self._rename_variable,
            MutationType.ARGUMENT_SWAP: self._swap_arguments,
            MutationType.CONSTANT_SHIFT: self._shift_constant,
            MutationType.LOGIC_FLIP: self._flip_comparison,
            MutationType.RETURN_FLIP: self._flip_return,
        }

    def mutate(self, code: str, mutation_type: MutationType) -> str:
        """
        Apply a mutation to code.

        Args:
            code: Source code to mutate
            mutation_type: Type of mutation to apply

        Returns:
            Mutated code
        """
        strategy = self.strategies.get(mutation_type)
        if not strategy:
            raise ValueError(f"Unknown mutation type: {mutation_type}")

        try:
            return strategy(code)
        except Exception as e:
            # If mutation fails, return original (will be caught in verification)
            raise ValueError(f"Mutation failed: {e}") from e

    def _rename_variable(self, code: str) -> str:
        """
        Rename a variable in the code.

        Strategy: Find first variable assignment and rename it throughout.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # Not valid Python, try regex fallback
            return self._rename_variable_regex(code)

        # Find first assignment
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        old_name = target.id
                        new_name = f"{old_name}_mutated"

                        # Replace all occurrences
                        mutated = code.replace(old_name, new_name)
                        return mutated

        # No assignment found
        raise ValueError("No variable assignments found to rename")

    def _rename_variable_regex(self, code: str) -> str:
        """Fallback: rename variable using regex."""
        # Find variable assignment pattern
        match = re.search(r"\b([a-z_][a-z0-9_]*)\s*=", code, re.IGNORECASE)
        if match:
            old_name = match.group(1)
            new_name = f"{old_name}_mutated"
            return re.sub(rf"\b{old_name}\b", new_name, code)

        raise ValueError("No variable assignments found")

    def _swap_arguments(self, code: str) -> str:
        """
        Swap function arguments.

        Strategy: Find first function call with 2+ args and swap first two.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return self._swap_arguments_regex(code)

        class ArgSwapper(ast.NodeTransformer):
            def __init__(self):
                self.swapped = False

            def visit_Call(self, node):
                if not self.swapped and len(node.args) >= 2:
                    # Swap first two arguments
                    node.args[0], node.args[1] = node.args[1], node.args[0]
                    self.swapped = True
                return node

        swapper = ArgSwapper()
        mutated_tree = swapper.visit(tree)

        if not swapper.swapped:
            raise ValueError("No function calls with 2+ args found")

        return ast.unparse(mutated_tree)

    def _swap_arguments_regex(self, code: str) -> str:
        """Fallback: swap arguments using regex."""
        # Find function call with 2+ args: func(arg1, arg2, ...)
        match = re.search(r"(\w+)\(([^,)]+),\s*([^,)]+)", code)
        if match:
            func_name = match.group(1)
            arg1 = match.group(2)
            arg2 = match.group(3)
            original = match.group(0)
            swapped = f"{func_name}({arg2}, {arg1}"
            return code.replace(original, swapped, 1)

        raise ValueError("No function calls with 2+ args found")

    def _shift_constant(self, code: str) -> str:
        """
        Shift a numeric constant.

        Strategy: Find first integer constant and increment by 1.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return self._shift_constant_regex(code)

        class ConstantShifter(ast.NodeTransformer):
            def __init__(self):
                self.shifted = False

            def visit_Constant(self, node):
                if not self.shifted and isinstance(node.value, int):
                    node.value += 1
                    self.shifted = True
                return node

            # Backward compatibility for Python < 3.8
            def visit_Num(self, node):
                if not self.shifted and isinstance(node.n, int):
                    node.n += 1
                    self.shifted = True
                return node

        shifter = ConstantShifter()
        mutated_tree = shifter.visit(tree)

        if not shifter.shifted:
            raise ValueError("No integer constants found")

        return ast.unparse(mutated_tree)

    def _shift_constant_regex(self, code: str) -> str:
        """Fallback: shift constant using regex."""
        match = re.search(r"\b(\d+)\b", code)
        if match:
            old_val = match.group(1)
            new_val = str(int(old_val) + 1)
            return code.replace(old_val, new_val, 1)

        raise ValueError("No integer constants found")

    def _flip_comparison(self, code: str) -> str:
        """
        Flip a comparison operator.

        Strategy: > becomes >=, < becomes <=, == becomes !=, etc.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return self._flip_comparison_regex(code)

        class ComparisonFlipper(ast.NodeTransformer):
            def __init__(self):
                self.flipped = False

            def visit_Compare(self, node):
                if not self.flipped and node.ops:
                    # Flip first comparison
                    op = node.ops[0]
                    if isinstance(op, ast.Gt):
                        node.ops[0] = ast.GtE()
                    elif isinstance(op, ast.Lt):
                        node.ops[0] = ast.LtE()
                    elif isinstance(op, ast.Eq):
                        node.ops[0] = ast.NotEq()
                    elif isinstance(op, ast.NotEq):
                        node.ops[0] = ast.Eq()
                    elif isinstance(op, ast.GtE):
                        node.ops[0] = ast.Gt()
                    elif isinstance(op, ast.LtE):
                        node.ops[0] = ast.Lt()
                    self.flipped = True
                return node

        flipper = ComparisonFlipper()
        mutated_tree = flipper.visit(tree)

        if not flipper.flipped:
            raise ValueError("No comparison operators found")

        return ast.unparse(mutated_tree)

    def _flip_comparison_regex(self, code: str) -> str:
        """Fallback: flip comparison using regex."""
        # Try common comparisons
        replacements = [
            (r"(?<![><=!])>(?!=)", ">="),
            (r"(?<![><=!])<(?!=)", "<="),
            (r"==", "!="),
        ]

        for pattern, replacement in replacements:
            if re.search(pattern, code):
                return re.sub(pattern, replacement, code, count=1)

        raise ValueError("No comparison operators found")

    def _flip_return(self, code: str) -> str:
        """
        Flip a return value.

        Strategy: True -> False, False -> True, 0 -> 1, 1 -> 0.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return self._flip_return_regex(code)

        class ReturnFlipper(ast.NodeTransformer):
            def __init__(self):
                self.flipped = False

            def visit_Return(self, node):
                if not self.flipped and node.value:
                    if isinstance(node.value, ast.Constant):
                        if node.value.value is True:
                            node.value.value = False
                            self.flipped = True
                        elif node.value.value is False:
                            node.value.value = True
                            self.flipped = True
                        elif node.value.value == 0:
                            node.value.value = 1
                            self.flipped = True
                        elif node.value.value == 1:
                            node.value.value = 0
                            self.flipped = True
                    # Backward compatibility
                    elif isinstance(node.value, ast.NameConstant):
                        if node.value.value is True:
                            node.value.value = False
                            self.flipped = True
                        elif node.value.value is False:
                            node.value.value = True
                            self.flipped = True
                return node

        flipper = ReturnFlipper()
        mutated_tree = flipper.visit(tree)

        if not flipper.flipped:
            raise ValueError("No flippable return values found")

        return ast.unparse(mutated_tree)

    def _flip_return_regex(self, code: str) -> str:
        """Fallback: flip return using regex."""
        replacements = [
            (r"\breturn\s+True\b", "return False"),
            (r"\breturn\s+False\b", "return True"),
            (r"\breturn\s+0\b", "return 1"),
            (r"\breturn\s+1\b", "return 0"),
        ]

        for pattern, replacement in replacements:
            if re.search(pattern, code):
                return re.sub(pattern, replacement, code, count=1)

        raise ValueError("No flippable return values found")


class MutationVerifier:
    """
    Mutation-gated verification using the SABER pattern.

    Verifies outputs by checking if mutations break them correctly.
    """

    def __init__(self, executor: Any | None = None):
        """
        Initialize mutation verifier.

        Args:
            executor: Task executor to run mutants (must have async run method)
        """
        self.executor = executor
        self.mutator = CodeMutator()

    async def verify(
        self, task: str, solution: str, n_mutants: int = 3
    ) -> VerificationResult:
        """
        Verify a solution using mutation-gated testing.

        Args:
            task: Task description
            solution: Solution to verify
            n_mutants: Number of mutants to generate (default 3)

        Returns:
            Verification result with verdict

        Process:
        1. Generate n_mutants mutated versions of the solution
        2. Run each mutant through the same task
        3. If any mutant passes: original is SUSPECT
        4. If all mutants fail: original is CONFIRMED
        5. If mutants error: UNCERTAIN
        """
        if not self.executor:
            raise ValueError("Executor required for verification")

        # Generate mutants
        mutants = self._generate_mutants(solution, n_mutants)
        results: list[MutantResult] = []

        # Execute each mutant
        for mutation_type, mutant_code in mutants:
            try:
                passed = await self.executor.run(task, mutant_code)
                results.append(
                    MutantResult(
                        name=mutation_type.value,
                        mutation_type=mutation_type,
                        passed=passed,
                        mutated_code=mutant_code,
                    )
                )
            except Exception as e:
                results.append(
                    MutantResult(
                        name=mutation_type.value,
                        mutation_type=mutation_type,
                        passed=None,
                        error=str(e),
                        mutated_code=mutant_code,
                    )
                )

        # Analyze results
        passed_mutants = [r for r in results if r.passed is True]
        failed_mutants = [r for r in results if r.passed is False]
        errored = [r for r in results if r.passed is None]

        # Determine verdict
        if passed_mutants:
            # If mutations still pass, original is suspect
            verdict = "suspect"
            reason = (
                f"{len(passed_mutants)}/{n_mutants} mutations still pass - "
                "original may be brittle or copied"
            )
            confidence = 0.3
        elif not errored:
            # All mutations correctly break the solution
            verdict = "confirmed"
            reason = "All mutations correctly break the solution"
            confidence = 0.9
        else:
            # Some mutants produced runtime errors
            verdict = "uncertain"
            reason = f"{len(errored)}/{n_mutants} mutants produced runtime errors"
            confidence = 0.5

        return VerificationResult(
            verdict=verdict,
            reason=reason,
            details=results,
            confidence=confidence,
            original_code=solution,
            n_mutants=n_mutants,
            passed_mutants=len(passed_mutants),
            failed_mutants=len(failed_mutants),
            errored_mutants=len(errored),
        )

    def _generate_mutants(
        self, code: str, n: int
    ) -> list[tuple[MutationType, str]]:
        """
        Generate n mutated versions of code.

        Args:
            code: Original code
            n: Number of mutants to generate

        Returns:
            List of (mutation_type, mutated_code) tuples
        """
        mutants: list[tuple[MutationType, str]] = []
        mutation_types = list(MutationType)

        # Try each mutation type until we have n mutants
        for i, mutation_type in enumerate(mutation_types):
            if len(mutants) >= n:
                break

            try:
                mutated = self.mutator.mutate(code, mutation_type)
                mutants.append((mutation_type, mutated))
            except ValueError:
                # Mutation not applicable to this code, skip
                continue

        if not mutants:
            raise ValueError("Could not generate any mutants for this code")

        return mutants[:n]

    def verify_sync(
        self, task: str, solution: str, executor_fn: Callable[[str, str], bool],
        n_mutants: int = 3
    ) -> VerificationResult:
        """
        Synchronous version of verify for non-async executors.

        Args:
            task: Task description
            solution: Solution to verify
            executor_fn: Synchronous function that executes (task, code) -> passed
            n_mutants: Number of mutants to generate

        Returns:
            Verification result
        """
        # Generate mutants
        mutants = self._generate_mutants(solution, n_mutants)
        results: list[MutantResult] = []

        # Execute each mutant
        for mutation_type, mutant_code in mutants:
            try:
                passed = executor_fn(task, mutant_code)
                results.append(
                    MutantResult(
                        name=mutation_type.value,
                        mutation_type=mutation_type,
                        passed=passed,
                        mutated_code=mutant_code,
                    )
                )
            except Exception as e:
                results.append(
                    MutantResult(
                        name=mutation_type.value,
                        mutation_type=mutation_type,
                        passed=None,
                        error=str(e),
                        mutated_code=mutant_code,
                    )
                )

        # Analyze results
        passed_mutants = [r for r in results if r.passed is True]
        failed_mutants = [r for r in results if r.passed is False]
        errored = [r for r in results if r.passed is None]

        # Determine verdict
        if passed_mutants:
            verdict = "suspect"
            reason = (
                f"{len(passed_mutants)}/{n_mutants} mutations still pass - "
                "original may be brittle"
            )
            confidence = 0.3
        elif not errored:
            verdict = "confirmed"
            reason = "All mutations correctly break the solution"
            confidence = 0.9
        else:
            verdict = "uncertain"
            reason = f"{len(errored)}/{n_mutants} mutants produced runtime errors"
            confidence = 0.5

        return VerificationResult(
            verdict=verdict,
            reason=reason,
            details=results,
            confidence=confidence,
            original_code=solution,
            n_mutants=n_mutants,
            passed_mutants=len(passed_mutants),
            failed_mutants=len(failed_mutants),
            errored_mutants=len(errored),
        )
