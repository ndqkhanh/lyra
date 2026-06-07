"""
Tests for MutationVerifier (SABER pattern).
"""

import pytest

from lyra.verification.mutation_verifier import (
    CodeMutator,
    MutationType,
    MutationVerifier,
    VerificationResult,
)


class TestCodeMutator:
    """Test code mutation strategies."""

    def test_rename_variable(self):
        """Test variable renaming."""
        mutator = CodeMutator()
        code = "result = 42\nprint(result)"

        mutated = mutator.mutate(code, MutationType.VARIABLE_RENAME)

        assert "result_mutated" in mutated
        assert "result = 42" not in mutated or "result_mutated = 42" in mutated

    def test_swap_arguments(self):
        """Test argument swapping."""
        mutator = CodeMutator()
        code = "divide(10, 2)"

        mutated = mutator.mutate(code, MutationType.ARGUMENT_SWAP)

        assert "divide(2, 10)" in mutated

    def test_shift_constant(self):
        """Test constant shifting."""
        mutator = CodeMutator()
        code = "limit = 100"

        mutated = mutator.mutate(code, MutationType.CONSTANT_SHIFT)

        assert "101" in mutated

    def test_flip_comparison(self):
        """Test comparison flipping."""
        mutator = CodeMutator()
        code = "if x > 10:"

        mutated = mutator.mutate(code, MutationType.LOGIC_FLIP)

        assert "x >=" in mutated

    def test_flip_return(self):
        """Test return value flipping."""
        mutator = CodeMutator()
        code = "return True"

        mutated = mutator.mutate(code, MutationType.RETURN_FLIP)

        assert "return False" in mutated

    def test_mutation_failure_on_invalid_code(self):
        """Test that mutation raises error for non-applicable code."""
        mutator = CodeMutator()
        code = "# Just a comment"

        with pytest.raises(ValueError):
            mutator.mutate(code, MutationType.VARIABLE_RENAME)


class TestMutationVerifier:
    """Test mutation-gated verification."""

    @pytest.mark.asyncio
    async def test_verify_suspect_solution(self):
        """Test that brittle solutions are marked as suspect."""

        class MockExecutor:
            async def run(self, task: str, code: str) -> bool:
                # Always pass - indicates brittle solution
                return True

        verifier = MutationVerifier(executor=MockExecutor())
        task = "Write a function that returns True"
        solution = "def check(): return True"

        result = await verifier.verify(task, solution, n_mutants=3)

        assert result.verdict == "suspect"
        assert result.passed_mutants > 0
        assert result.confidence < 0.5

    @pytest.mark.asyncio
    async def test_verify_confirmed_solution(self):
        """Test that robust solutions are confirmed."""

        class MockExecutor:
            async def run(self, task: str, code: str) -> bool:
                # Always fail - indicates mutations correctly break the solution
                return False

        verifier = MutationVerifier(executor=MockExecutor())
        task = "Write a function"
        solution = "def check(): return True"

        result = await verifier.verify(task, solution, n_mutants=3)

        assert result.verdict == "confirmed"
        assert result.failed_mutants >= 2  # At least 2 mutations should be generated
        assert result.confidence > 0.8

    def test_verify_sync(self):
        """Test synchronous verification."""

        def executor_fn(task: str, code: str) -> bool:
            # Mutations should fail
            return False

        verifier = MutationVerifier()
        task = "Write a function"
        solution = "def check(): return True"

        result = verifier.verify_sync(task, solution, executor_fn, n_mutants=3)

        assert result.verdict == "confirmed"
        assert isinstance(result, VerificationResult)

    def test_generate_mutants(self):
        """Test mutant generation."""
        verifier = MutationVerifier()
        code = "result = 100\nif result > 50:\n    return True"

        mutants = verifier._generate_mutants(code, 3)

        assert len(mutants) <= 3
        for mutation_type, mutated_code in mutants:
            assert isinstance(mutation_type, MutationType)
            assert mutated_code != code
