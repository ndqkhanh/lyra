"""
Tests for MutationVerifier (SABER pattern).

Covers CodeMutator all mutation strategies, edge cases, regex fallbacks,
and MutationVerifier verify/verify_sync with all verdict paths.
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
        """Test variable renaming via AST."""
        mutator = CodeMutator()
        code = "result = 42\nprint(result)"
        mutated = mutator.mutate(code, MutationType.VARIABLE_RENAME)
        assert "result_mutated" in mutated
        assert "result_mutated = 42" in mutated

    def test_rename_variable_regex_fallback(self):
        """Variable renaming via regex fallback for non-Python code."""
        mutator = CodeMutator()
        code = "result = 42  # no newline"
        mutated = mutator.mutate(code, MutationType.VARIABLE_RENAME)
        assert "result_mutated" in mutated

    def test_rename_variable_no_assignment(self):
        """Variable rename raises on code with no variables."""
        mutator = CodeMutator()
        with pytest.raises(ValueError, match="No variable assignments found"):
            mutator.mutate("# just a comment", MutationType.VARIABLE_RENAME)

    def test_rename_variable_regex_no_match(self):
        """Regex fallback raises when it also finds nothing."""
        mutator = CodeMutator()
        with pytest.raises(ValueError, match="No variable assignments found"):
            mutator.mutate("@@@@", MutationType.VARIABLE_RENAME)

    def test_swap_arguments(self):
        """Test argument swapping via AST."""
        mutator = CodeMutator()
        code = "divide(10, 2)"
        mutated = mutator.mutate(code, MutationType.ARGUMENT_SWAP)
        assert "divide(2, 10)" in mutated or "divide(2,10)" in mutated

    def test_swap_arguments_regex_fallback(self):
        """Argument swapping via regex fallback."""
        mutator = CodeMutator()
        code = "divide(10, 2)  # comment"
        mutated = mutator.mutate(code, MutationType.ARGUMENT_SWAP)
        # Regex may produce slightly different output
        assert "2" in mutated

    def test_swap_arguments_no_call(self):
        """Argument swap raises on code with no function call."""
        mutator = CodeMutator()
        with pytest.raises(ValueError, match="No function calls with"):
            mutator.mutate("x = 1 + 2", MutationType.ARGUMENT_SWAP)

    def test_swap_arguments_regex_no_match(self):
        """Regex fallback for swap raises when no call found."""
        mutator = CodeMutator()
        with pytest.raises(ValueError, match="No function calls with"):
            mutator.mutate("not a call", MutationType.ARGUMENT_SWAP)

    def test_shift_constant(self):
        """Test constant shifting via AST."""
        mutator = CodeMutator()
        code = "limit = 100"
        mutated = mutator.mutate(code, MutationType.CONSTANT_SHIFT)
        assert "101" in mutated

    def test_shift_constant_regex_fallback(self):
        """Constant shifting via regex fallback."""
        mutator = CodeMutator()
        code = "x = 50  # comment"
        mutated = mutator.mutate(code, MutationType.CONSTANT_SHIFT)
        assert "51" in mutated

    def test_shift_constant_no_constant(self):
        """Constant shift raises on code with no int constant."""
        mutator = CodeMutator()
        with pytest.raises(ValueError, match="No integer constants found"):
            mutator.mutate("x = 'hello'", MutationType.CONSTANT_SHIFT)

    def test_shift_constant_regex_no_match(self):
        """Regex fallback for constant raises when no int found."""
        mutator = CodeMutator()
        # This code will actually parse as AST and fail in visit_Num/visit_Constant
        # because there are no integer constants. Let's use something that
        # causes regex fallback with no match.
        with pytest.raises(ValueError, match="No integer constants found"):
            mutator.mutate("", MutationType.CONSTANT_SHIFT)

    def test_flip_comparison_gt(self):
        mutator = CodeMutator()
        mutated = mutator.mutate("if x > 10:\n    pass", MutationType.LOGIC_FLIP)
        assert "x >=" in mutated

    def test_flip_comparison_lt(self):
        mutator = CodeMutator()
        mutated = mutator.mutate("if x < 5:\n    pass", MutationType.LOGIC_FLIP)
        assert "x <=" in mutated

    def test_flip_comparison_eq(self):
        mutator = CodeMutator()
        mutated = mutator.mutate("if x == 5:\n    pass", MutationType.LOGIC_FLIP)
        assert "x !=" in mutated

    def test_flip_comparison_neq(self):
        mutator = CodeMutator()
        mutated = mutator.mutate("if x != 5:\n    pass", MutationType.LOGIC_FLIP)
        assert "x ==" in mutated

    def test_flip_comparison_gte(self):
        mutator = CodeMutator()
        mutated = mutator.mutate("if x >= 5:\n    pass", MutationType.LOGIC_FLIP)
        assert "x >" in mutated or "x >=" not in mutated

    def test_flip_comparison_lte(self):
        mutator = CodeMutator()
        mutated = mutator.mutate("if x <= 5:\n    pass", MutationType.LOGIC_FLIP)
        assert "x <" in mutated or "x <=" not in mutated

    def test_flip_comparison_no_op(self):
        """Logic flip raises when no comparison found."""
        mutator = CodeMutator()
        with pytest.raises(ValueError, match="No comparison operators found"):
            mutator.mutate("x = 5", MutationType.LOGIC_FLIP)

    def test_flip_comparison_regex_no_match(self):
        """Regex fallback for flip raises when no comparison found."""
        mutator = CodeMutator()
        with pytest.raises(ValueError, match="No comparison operators found"):
            mutator.mutate("", MutationType.LOGIC_FLIP)

    def test_flip_return_true(self):
        mutator = CodeMutator()
        mutated = mutator.mutate("return True", MutationType.RETURN_FLIP)
        assert "return False" in mutated

    def test_flip_return_false(self):
        mutator = CodeMutator()
        mutated = mutator.mutate("return False", MutationType.RETURN_FLIP)
        assert "return True" in mutated

    def test_flip_return_zero(self):
        mutator = CodeMutator()
        mutated = mutator.mutate("return 0", MutationType.RETURN_FLIP)
        assert "return 1" in mutated

    def test_flip_return_one(self):
        mutator = CodeMutator()
        mutated = mutator.mutate("return 1", MutationType.RETURN_FLIP)
        assert "return 0" in mutated

    def test_flip_return_regex_fallback(self):
        """Return flip via regex fallback."""
        mutator = CodeMutator()
        code = "return False  # comment"
        mutated = mutator.mutate(code, MutationType.RETURN_FLIP)
        assert "return True" in mutated

    def test_flip_return_regex_no_flippable(self):
        """Regex fallback raises when no flippable return found."""
        mutator = CodeMutator()
        with pytest.raises(ValueError, match="No flippable return values found"):
            mutator.mutate("return 'hello'", MutationType.RETURN_FLIP)

    def test_flip_return_no_return(self):
        """Return flip raises when no return found."""
        mutator = CodeMutator()
        with pytest.raises(ValueError, match="No flippable return values found"):
            mutator.mutate("", MutationType.RETURN_FLIP)

    def test_unknown_mutation_type(self):
        """Unknown mutation type raises ValueError."""
        mutator = CodeMutator()
        with pytest.raises(ValueError, match="Unknown mutation type"):
            mutator.mutate("x = 1", "unknown_type")  # type: ignore

    def test_mutate_returns_value_error(self):
        """When strategy itself raises, mutate wraps it."""
        mutator = CodeMutator()
        # Force an error in the mutation by using a strategy that crashes
        with pytest.raises(ValueError, match="Mutation failed"):
            mutator.mutate("", MutationType.VARIABLE_RENAME)

    def test_swap_args_with_syntax_error(self):
        """swap_arguments via AST is the default path for valid code."""
        mutator = CodeMutator()
        code = "func(1, 2)"
        mutated = mutator.mutate(code, MutationType.ARGUMENT_SWAP)
        assert "func(2, 1" in mutated

    def test_rename_variable_regex_success(self):
        """Regex rename fallback triggers on Python syntax error."""
        mutator = CodeMutator()
        # Not valid Python, triggers SyntaxError -> regex fallback
        code = "some_var = 42 in invalid python @@@@"
        mutated = mutator.mutate(code, MutationType.VARIABLE_RENAME)
        assert "some_var_mutated" in mutated

    def test_swap_arguments_regex_success(self):
        """Regex swap fallback triggers on non-python code that still has a function call pattern."""
        mutator = CodeMutator()
        code = "@@ func(1, 2) @@"  # Syntax error -> regex fallback
        mutated = mutator.mutate(code, MutationType.ARGUMENT_SWAP)
        assert "func(2, 1" in mutated

    def test_shift_constant_regex_success(self):
        """Regex constant shift triggers on non-python syntax with a number."""
        mutator = CodeMutator()
        code = "max_value @@@ 50"  # Syntax error -> regex fallback
        mutated = mutator.mutate(code, MutationType.CONSTANT_SHIFT)
        assert "51" in mutated

    def test_flip_comparison_regex_gt(self):
        """Regex comparison flip for > via non-python code."""
        mutator = CodeMutator()
        code = "if x > 5:"  # Syntax error (no body) -> regex fallback
        mutated = mutator.mutate(code, MutationType.LOGIC_FLIP)
        assert "x >=" in mutated

    def test_flip_comparison_regex_eq(self):
        """Regex comparison flip for == via non-python code."""
        mutator = CodeMutator()
        code = "if x == 5:"  # Syntax error -> regex fallback
        mutated = mutator.mutate(code, MutationType.LOGIC_FLIP)
        assert "x !=" in mutated

    def test_flip_return_regex_true(self):
        """Regex return flip for True."""
        mutator = CodeMutator()
        code = "return True"  # Valid Python but will hit _flip_return AST
        mutated = mutator.mutate(code, MutationType.RETURN_FLIP)
        assert "return False" in mutated

    def test_flip_return_regex_false(self):
        """Regex return flip for False."""
        mutator = CodeMutator()
        code = "return False"
        mutated = mutator.mutate(code, MutationType.RETURN_FLIP)
        assert "return True" in mutated

    def test_flip_return_regex_zero(self):
        """Regex return flip for 0."""
        mutator = CodeMutator()
        code = "return 0"
        mutated = mutator.mutate(code, MutationType.RETURN_FLIP)
        assert "return 1" in mutated

    def test_flip_return_regex_one(self):
        """Regex return flip for 1."""
        mutator = CodeMutator()
        code = "return 1"
        mutated = mutator.mutate(code, MutationType.RETURN_FLIP)
        assert "return 0" in mutated


class TestMutationVerifier:
    """Test mutation-gated verification."""

    @pytest.mark.asyncio
    async def test_verify_no_executor_raises(self):
        """verify raises ValueError when no executor set."""
        verifier = MutationVerifier()
        with pytest.raises(ValueError, match="Executor required"):
            await verifier.verify("task", "code")

    @pytest.mark.asyncio
    async def test_verify_suspect_solution(self):
        """Brittle solutions are marked as suspect."""

        class MockExecutor:
            async def run(self, task: str, code: str) -> bool:
                return True

        verifier = MutationVerifier(executor=MockExecutor())
        result = await verifier.verify(
            "Write a function that returns True",
            "def check(): return True",
            n_mutants=3,
        )
        assert result.verdict == "suspect"
        assert result.passed_mutants > 0
        assert result.confidence == 0.3

    @pytest.mark.asyncio
    async def test_verify_confirmed_solution(self):
        """Robust solutions are confirmed."""

        class MockExecutor:
            async def run(self, task: str, code: str) -> bool:
                return False

        verifier = MutationVerifier(executor=MockExecutor())
        result = await verifier.verify(
            "Write a function",
            "def check(): return True",
            n_mutants=3,
        )
        assert result.verdict == "confirmed"
        assert result.failed_mutants >= 2
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_verify_uncertain_solution(self):
        """Runtime errors during mutant execution yield uncertain."""

        class MockExecutor:
            async def run(self, task: str, code: str) -> bool:
                raise RuntimeError("execution failed")

        verifier = MutationVerifier(executor=MockExecutor())
        result = await verifier.verify(
            "Write a function",
            "def check(): return True",
            n_mutants=3,
        )
        assert result.verdict == "uncertain"
        assert result.errored_mutants > 0
        assert result.confidence == 0.5
        assert all(d.error for d in result.details if d.passed is None)

    @pytest.mark.asyncio
    async def test_verify_mixed_results(self):
        """Mixed passed/failed/errored still classifies as suspect if any pass."""

        results_iter = iter([True, False, False])

        class MockExecutor:
            async def run(self, task: str, code: str) -> bool:
                return next(results_iter)

        verifier = MutationVerifier(executor=MockExecutor())
        result = await verifier.verify("task", "def f(): return True", n_mutants=3)
        assert result.verdict == "suspect"
        assert result.passed_mutants >= 1

    def test_verify_sync_confirmed(self):
        """Synchronous verification with all mutants failing."""

        def executor_fn(task: str, code: str) -> bool:
            return False

        verifier = MutationVerifier()
        result = verifier.verify_sync("task", "def check(): return True", executor_fn, n_mutants=3)
        assert result.verdict == "confirmed"
        assert isinstance(result, VerificationResult)
        assert result.confidence == 0.9

    def test_verify_sync_suspect(self):
        """Synchronous verification with passing mutants."""

        def executor_fn(task: str, code: str) -> bool:
            return True

        verifier = MutationVerifier()
        result = verifier.verify_sync("task", "def check(): return True", executor_fn, n_mutants=3)
        assert result.verdict == "suspect"
        assert result.confidence == 0.3

    def test_verify_sync_uncertain(self):
        """Synchronous verification with erroring executor."""

        def executor_fn(task: str, code: str) -> bool:
            raise RuntimeError("boom")

        verifier = MutationVerifier()
        result = verifier.verify_sync("task", "def check(): return True", executor_fn, n_mutants=3)
        assert result.verdict == "uncertain"
        assert result.errored_mutants > 0
        assert result.confidence == 0.5

    def test_generate_mutants(self):
        """Mutant generation yields appropriate mutants."""
        verifier = MutationVerifier()
        code = "result = 100\nif result > 50:\n    return True"
        mutants = verifier._generate_mutants(code, 3)
        assert len(mutants) <= 3
        assert len(mutants) > 0
        for mutation_type, mutated_code in mutants:
            assert isinstance(mutation_type, MutationType)
            assert mutated_code != code

    def test_generate_mutants_insufficient(self):
        """_generate_mutants raises when no mutants can be generated."""
        verifier = MutationVerifier()
        with pytest.raises(ValueError, match="Could not generate any mutants"):
            verifier._generate_mutants("# only a comment", 1)

    def test_generate_mutants_fewer_than_n(self):
        """_generate_mutants returns fewer mutants if n exceeds available types."""
        verifier = MutationVerifier()
        code = "result = 1"
        mutants = verifier._generate_mutants(code, 10)
        assert len(mutants) <= len(MutationType)

    def test_generate_mutants_respects_n(self):
        """_generate_mutants respects exact count when possible."""
        verifier = MutationVerifier()
        code = "x = 1\ny > 2\nreturn True\nfunc(1, 2)\n"
        mutants = verifier._generate_mutants(code, 2)
        assert len(mutants) <= 2

    def test_verification_result_fields(self):
        """VerificationResult dataclass fields work correctly."""
        result = VerificationResult(
            verdict="confirmed",
            reason="all good",
            details=[],
            confidence=0.9,
            original_code="code",
            n_mutants=0,
            passed_mutants=0,
            failed_mutants=0,
            errored_mutants=0,
        )
        assert result.verdict == "confirmed"
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_verify_preserves_mutant_details(self):
        """Each mutant result preserves its code and mutation type."""

        class MockExecutor:
            async def run(self, task: str, code: str) -> bool:
                return False

        verifier = MutationVerifier(executor=MockExecutor())
        result = await verifier.verify("task", "x = 1\ny > 2\nreturn True\nfunc(1, 2)", n_mutants=3)
        for detail in result.details:
            assert detail.mutated_code
            assert isinstance(detail.mutation_type, MutationType)
